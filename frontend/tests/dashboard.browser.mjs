// Com o Vite em http://127.0.0.1:5174:
// node --test --test-isolation=none tests/dashboard.browser.mjs
// VIGA_PLAYWRIGHT_MODULE permite usar uma instalação temporária do Playwright.
import test from 'node:test'
import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'

const { chromium } = await import(process.env.VIGA_PLAYWRIGHT_MODULE
    ? pathToFileURL(process.env.VIGA_PLAYWRIGHT_MODULE).href : 'playwright')
const regioes = [
    { id_regiao: 1, nome: 'Lisboa', latitude: 38.7169, longitude: -9.1399 },
    { id_regiao: 3263, nome: 'Coimbra', latitude: 40.2033, longitude: -8.4103 },
    { id_regiao: 3261, nome: 'Porto', latitude: 41.1579, longitude: -8.6291 },
]
const respostas = Object.fromEntries(regioes.map((r, i) => [r.id_regiao, {
    id_regiao: r.id_regiao, estado: 'ok',
    dados_meteorologicos: { temperatura: 21 + i, humidade: 51 + i, velocidade_vento: 11 + i, precipitacao: 0 },
    fwi: { fwi: 10 + i, nivel_risco: ['Baixo', 'Moderado', 'Elevado'][i] },
    ml: { probabilidade_incendio: (31 + i) / 100, nivel_risco_ml: ['Baixo', 'Moderado', 'Elevado'][i] },
}]))

async function preparar(t) {
    const browser = await chromium.launch({ channel: 'msedge', headless: true })
    t.after(() => browser.close())
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    await page.clock.install()
    await page.addInitScript(() => localStorage.setItem('token', 'teste-local'))
    const pedidos = []
    const controlo = { resposta: null }
    await page.route('**/*', async route => {
        const url = new URL(route.request().url())
        if (url.pathname === '/src/components/MapaInterativo.jsx') {
            // Expor apenas a referência do mapa ao teste; flyTo continua real.
            const response = await route.fetch()
            const body = (await response.text()).replace('const map = useMap();',
                'const map = useMap(); window.mapaDoTeste = map;')
            return route.fulfill({ response, body })
        }
        if (!url.pathname.startsWith('/api/')) {
            return url.hostname === '127.0.0.1' ? route.continue() : route.abort()
        }
        const json = body => route.fulfill({ json: body })
        if (url.pathname === '/api/regioes/pesquisa') {
            return json({ resultados: regioes.filter(r => r.nome.toLowerCase().includes(url.searchParams.get('q').toLowerCase())) })
        }
        if (url.pathname === '/api/regioes/distritos') return json({ distritos: [] })
        if (url.pathname === '/api/incendios/focos') return json({ total: 0, focos: [] })
        if (url.pathname === '/api/alertas') return json({ estado: 'sem_dados', alertas: [], cobertura: { regioes_avaliadas: 0 } })
        const detalhe = url.pathname.match(/^\/api\/regioes\/(\d+)\/detalhes$/)
        if (detalhe) {
            const risco = respostas[detalhe[1]]
            return json({ regiao: regioes.find(r => r.id_regiao === Number(detalhe[1])), estado: 'ok',
                atual: { ...risco.dados_meteorologicos, ...risco.fwi }, historico: [] })
        }
        const risco = url.pathname.match(/^\/api\/risco\/(\d+)$/)
        if (risco) {
            const id = Number(risco[1])
            pedidos.push(id)
            if (controlo.resposta && await controlo.resposta(id, route)) return
            return json(respostas[id] || { estado: 'sem_dados' })
        }
        throw new Error(`Pedido inesperado: ${url.pathname}`)
    })
    await page.goto(process.env.VIGA_TEST_URL || 'http://127.0.0.1:5174')
    await page.waitForFunction(() => document.querySelector('aside')?.textContent.includes('FWI 10 — ML 31%'))
    await page.evaluate(() => {
        window.elementoMapaInicial = document.querySelector('.leaflet-container')
    })
    return { page, pedidos, controlo }
}

async function selecionar(page, regiao) {
    await page.getByPlaceholder('Pesquisar localidade...').fill(regiao.nome)
    await page.locator('aside').getByText(regiao.nome, { exact: true }).click()
}

async function confirmarIndicadores(page, regiao) {
    const dados = respostas[regiao.id_regiao]
    await page.waitForFunction(({ nome, fwi, ml }) => {
        const texto = document.querySelector('aside')?.textContent || ''
        return texto.includes(`Risco — ${nome}`) && texto.includes(`FWI ${fwi} — ML ${ml}%`)
    }, { nome: regiao.nome, fwi: dados.fwi.fwi, ml: Math.round(dados.ml.probabilidade_incendio * 100) })
    const texto = await page.locator('aside').innerText()
    for (const [nome, valor] of [['Temperatura', dados.dados_meteorologicos.temperatura],
        ['Humidade', dados.dados_meteorologicos.humidade], ['Vento', dados.dados_meteorologicos.velocidade_vento]]) {
        assert.match(texto, new RegExp(`${nome}\\s+${valor}`))
    }
    assert.match(await page.locator('nav').innerText(), new RegExp(regiao.nome))
    const painel = page.getByText('Previsão ML + FWI', { exact: true }).locator('..')
    assert.match(await painel.innerText(), new RegExp(`${Math.round(dados.ml.probabilidade_incendio * 100)}%`))
    assert.doesNotMatch(await page.locator('body').innerText(), /Risco nacional/i)
}

test('Lisboa, Coimbra e Porto: indicadores, mapa, atualização periódica e detalhes', async t => {
    const { page, pedidos } = await preparar(t)
    await confirmarIndicadores(page, regioes[0])
    for (const regiao of regioes) {
        await selecionar(page, regiao)
        await confirmarIndicadores(page, regiao)
        await page.clock.runFor(2000)
        await page.waitForFunction(({ latitude, longitude }) => {
            const mapa = window.mapaDoTeste
            return mapa && mapa.getZoom() === 12 && Math.abs(mapa.getCenter().lat - latitude) < 0.001
                && Math.abs(mapa.getCenter().lng - longitude) < 0.001
        }, regiao)
        assert.equal(await page.evaluate(() => window.elementoMapaInicial === document.querySelector('.leaflet-container')), true)
    }
    const anteriores = pedidos.filter(id => id === 3261).length
    const atualizacao = page.waitForResponse(r => r.url().endsWith('/api/risco/3261'))
    await page.clock.fastForward(61000)
    await atualizacao
    assert.ok(pedidos.filter(id => id === 3261).length > anteriores)
    await confirmarIndicadores(page, regioes[2])
    await page.getByPlaceholder('Pesquisar localidade...').fill('Coimbra')
    await page.locator('aside').getByText('Detalhes', { exact: true }).click()
    await page.waitForURL('**/regiao/3263')
    await page.getByRole('heading', { name: 'Coimbra', exact: true }).waitFor()
    assert.match(await page.locator('body').innerText(), /Temperatura\s+22/)
    assert.match(await page.locator('body').innerText(), /Humidade\s+52/)
    assert.match(await page.locator('body').innerText(), /Vento\s+12/)
})

test('respostas atrasadas, erros e dados ausentes não apresentam valores de outra região', async t => {
    const { page, controlo } = await preparar(t)
    let pendente
    controlo.resposta = async (id, route) => {
        if (id !== 3263) return false
        pendente = route
        return true
    }
    await selecionar(page, regioes[1])
    await page.getByRole('status').filter({ hasText: 'A carregar dados...' }).waitFor()
    assert.doesNotMatch(await page.locator('aside').innerText(), /FWI 10 — ML 31%/)
    assert.match(await page.locator('aside').innerText(), /Indisponível/)
    await selecionar(page, regioes[2])
    await confirmarIndicadores(page, regioes[2])
    await pendente.fulfill({ json: respostas[3263] })
    await page.waitForTimeout(200)
    await confirmarIndicadores(page, regioes[2])
    controlo.resposta = async (id, route) => {
        if (id !== 3263) return false
        await route.fulfill({ status: 502, json: { detail: { mensagem: 'Falha ao obter dados. Informação indisponível.' } } })
        return true
    }
    await selecionar(page, regioes[1])
    await page.getByRole('status').filter({ hasText: 'Falha ao obter dados.' }).waitFor()
    assert.doesNotMatch(await page.locator('aside').innerText(), /FWI 12 — ML 33%/)
    controlo.resposta = async (id, route) => {
        if (id !== 1) return false
        await route.fulfill({ json: { estado: 'sem_dados' } })
        return true
    }
    await selecionar(page, regioes[0])
    await page.getByRole('status').filter({ hasText: 'Sem dados disponíveis.' }).waitFor()
    assert.match(await page.locator('aside').innerText(), /Risco — Lisboa/i)
    assert.match(await page.locator('aside').innerText(), /FWI Indisponível — ML Indisponível/)
})
