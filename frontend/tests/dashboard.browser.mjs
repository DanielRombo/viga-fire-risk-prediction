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
    { id_regiao: 3279, nome: 'Ponta Delgada', distrito: 'Açores', latitude: 37.7412, longitude: -25.6756 },
    { id_regiao: 3278, nome: 'Funchal', distrito: 'Madeira', latitude: 32.6669, longitude: -16.9241 },
]
const respostas = Object.fromEntries(regioes.map((r, i) => [r.id_regiao, {
    id_regiao: r.id_regiao, estado: 'ok',
    data_hora: '2026-10-01T12:15:00+00:00',
    dados_meteorologicos: { temperatura: 21 + i, humidade: 51 + i, velocidade_vento: 11 + i, precipitacao: 0 },
    fwi: { fwi: 10 + i, nivel_risco: ['Baixo', 'Moderado', 'Elevado'][i % 3] },
    ml: { probabilidade_incendio: (31 + i) / 100, nivel_risco_ml: ['Baixo', 'Moderado', 'Elevado'][i % 3] },
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
        if (url.pathname === '/api/regioes/monitorizadas') return json({ regioes })
        if (url.pathname === '/api/regioes/pesquisa') {
            return json({ resultados: regioes.filter(r => r.nome.toLowerCase().includes(url.searchParams.get('q').toLowerCase())) })
        }
        if (url.pathname === '/api/regioes/distritos') return json({ distritos: [] })
        if (url.pathname === '/api/incendios/focos') return json({ total: 0, focos: [] })
        if (url.pathname === '/api/alertas') return json({ estado: 'sem_dados', alertas: [], cobertura: { regioes_avaliadas: 0 } })
        const detalhe = url.pathname.match(/^\/api\/regioes\/(\d+)\/detalhes$/)
        if (detalhe) {
            if (controlo.detalhe) return json(controlo.detalhe)
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

test('zeros reais e null no dashboard, painel ML e detalhes', async t => {
    const { page, controlo } = await preparar(t)
    const zeros = { ...respostas[3263],
        dados_meteorologicos: { temperatura: 0, humidade: 0, velocidade_vento: 0, precipitacao: 0 },
        fwi: { fwi: 0, nivel_risco: 'Baixo', componentes: { ffmc: 0, isi: 0 } },
        ml: { probabilidade_incendio: 0, nivel_risco_ml: 'Baixo' } }
    controlo.resposta = async (id, route) => {
        if (id !== 3263) return false
        await route.fulfill({ json: zeros })
        return true
    }
    await selecionar(page, regioes[1])
    await page.waitForFunction(() => document.querySelector('aside')?.textContent.includes('FWI 0 — ML 0%'))
    const sidebar = await page.locator('aside').innerText()
    for (const label of ['Temperatura', 'Humidade', 'Vento']) assert.match(sidebar, new RegExp(`${label}\\s+0`))
    const painel = page.getByText('Previsão ML + FWI', { exact: true }).locator('..')
    assert.match(await painel.innerText(), /Probabilidade\s+0%/)
    assert.doesNotMatch(await painel.innerText(), /Indisponível/)
    controlo.detalhe = { regiao: regioes[1], estado: 'ok', historico: [],
        atual: { ...zeros.dados_meteorologicos, ...zeros.fwi } }
    await page.getByPlaceholder('Pesquisar localidade...').fill('')
    await page.getByPlaceholder('Pesquisar localidade...').fill('Coimbra')
    await page.locator('aside').getByText('Detalhes', { exact: true }).click()
    await page.getByRole('heading', { name: 'Coimbra', exact: true }).waitFor()
    assert.match(await page.locator('body').innerText(), /Temperatura\s+0/)
    assert.match(await page.locator('body').innerText(), /Probabilidade\s+0%/)
    // Uma resposta incompleta nunca deve originar o fator "baixa humidade" por coerção de null.
    controlo.detalhe.atual.humidade = null
    await page.reload()
    await page.getByText('Sem dados suficientes para análise.', { exact: true }).waitFor()
    assert.match(await page.locator('body').innerText(), /Humidade\s+Indisponível/)
    assert.doesNotMatch(await page.locator('body').innerText(), /devido a baixa humidade/)
})

test('ilhas: dados reais, timestamp, dados antigos e ausência explícita', async t => {
    const { page, controlo } = await preparar(t)
    for (const [nome, regiao] of [['Azores', regioes[3]], ['Madeira', regioes[4]]]) {
        await page.waitForFunction(nome => {
            let pronto = false
            window.mapaDoTeste?.eachLayer(layer => {
                if (layer.feature?.properties.name === nome && layer.getPopup()?.getContent().includes('Observação em')) pronto = true
            })
            return pronto
        }, nome)
        await page.evaluate(nome => {
            window.mapaDoTeste.eachLayer(layer => {
                if (layer.feature?.properties.name === nome) layer.fire('click')
            })
        }, nome)
        await confirmarIndicadores(page, regiao)
    }
    for (const regiao of regioes.slice(3)) {
        await selecionar(page, regiao)
        await confirmarIndicadores(page, regiao)
        const texto = await page.locator('nav').innerText()
        assert.match(texto, /12:15:00 UTC/)
        assert.match(texto, /Dados atuais/)
        assert.doesNotMatch(texto, /Sistema ativo/)
    }
    controlo.resposta = async (id, route) => {
        if (id !== 3279) return false
        await route.fulfill({ json: { ...respostas[id], estado: 'desatualizado', fwi: null, ml: null } })
        return true
    }
    await selecionar(page, regioes[3])
    await page.getByRole('status').filter({ hasText: 'Dados desatualizados;' }).waitFor()
    assert.match(await page.locator('nav').innerText(), /Dados desatualizados/)
    assert.match(await page.locator('aside').innerText(), /Temperatura\s+Indisponível/)
    controlo.resposta = async (id, route) => {
        if (id !== 3278) return false
        await route.fulfill({ json: { estado: 'sem_dados' } })
        return true
    }
    await selecionar(page, regioes[4])
    await page.locator('nav').getByText('Sem dados', { exact: true }).waitFor()
    await page.getByRole('status').filter({ hasText: 'Sem dados disponíveis.' }).first().waitFor()
    assert.match(await page.locator('nav').innerText(), /Sem dados/)
    assert.match(await page.locator('aside').innerText(), /Temperatura\s+Indisponível/)
})

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
    for (const regiao of regioes.slice(0, 3)) {
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
