// Reutiliza o cenário Edge com API simulada e mantém a regressão existente.
import test from 'node:test'
import assert from 'node:assert/strict'
import { preparar, selecionar, regioes, diario } from './dashboard.browser.mjs'

const painel = page => page.getByRole('region', { name: /^FWI diário/ })
const valor = page => painel(page).getByTestId('valor-fwi-diario')

test('FWI diário no dashboard: operacional, zero, null e estados técnicos neutros', async t => {
    const { page, controlo } = await preparar(t)
    await painel(page).getByText('Operacional estabelecido', { exact: true }).waitFor()
    for (const [estado, inicializacao, fwi, label] of [
        ['ok','estabelecido',0,'Atual'],
        ['indisponivel','sem_estado',null,'Indisponível'],
        ['em_inicializacao','reconstruido',18,'Em inicialização'],
        ['em_inicializacao','inicializado_convencionalmente',19,'Em inicialização'],
        ['em_reconstrucao','em_reconstrucao',20,'Em reconstrução'],
        ['desatualizado','estabelecido',21,'Desatualizado'],
        ['dados_incompletos','sem_estado',null,'Dados incompletos'],
        ['erro_fonte','sem_estado',null,'Erro da fonte'],
        ['estado_anterior_ausente','sem_estado',null,'Estado anterior ausente'],
    ]) {
        controlo.fwi = async (id, route) => { await route.fulfill({ json: { ...diario(id), estado,
            estado_inicializacao: inicializacao, fwi, operacional: estado === 'ok', mensagem: 'Mensagem técnica da API.' } }); return true }
        await page.reload()
        await painel(page).getByRole('status').filter({ hasText: new RegExp(`^${label}$`) }).waitFor()
        assert.equal(await valor(page).innerText(), fwi === null ? 'Indisponível' : String(fwi))
        assert.doesNotMatch(await painel(page).innerText(), /Baixo|Elevado|Extremo/)
        if (estado !== 'ok') assert.match(await painel(page).innerText(), /Não operacional — valor técnico/)
    }
    assert.match(await page.locator('body').innerText(), /Índice legado \(experimental\): 10/)
})

test('FWI diário: mudança de região, resposta atrasada, erro HTTP e um refresh por minuto', async t => {
    const { page, controlo } = await preparar(t)
    let pendente, pedidosPorto = 0
    controlo.fwi = async (id, route) => {
        if (id === 3263) { pendente = route; return true }
        if (id === 3261) pedidosPorto++
        return false
    }
    await selecionar(page, regioes[1])
    await painel(page).getByText('A carregar FWI diário…', { exact: true }).waitFor()
    assert.equal(await valor(page).innerText(), 'Indisponível')
    await selecionar(page, regioes[2])
    await page.waitForFunction(() => document.querySelector('[data-testid="valor-fwi-diario"]')?.textContent === '32')
    await pendente.fulfill({ json: { ...diario(3263), fwi: 999 } })
    assert.equal(await valor(page).innerText(), '32')
    const antes = pedidosPorto
    const atualizado = page.waitForResponse(r => r.url().endsWith('/api/fwi-diario/3261'))
    await page.clock.fastForward(61000)
    await atualizado
    assert.equal(pedidosPorto, antes + 1)
    controlo.fwi = async (id, route) => { await route.fulfill({ status: 503, json: { detail: 'Erro simulado' } }); return true }
    await selecionar(page, regioes[1])
    await painel(page).getByText('Não foi possível obter o FWI diário.', { exact: true }).waitFor()
    assert.equal(await valor(page).innerText(), 'Indisponível')
    assert.match(await page.locator('body').innerText(), /Índice legado \(experimental\): 11/)
})

test('detalhes: Continente, Madeira e Açores, seis índices, timestamps e histórico', async t => {
    const { page } = await preparar(t)
    for (const r of [regioes[0], regioes[3], regioes[4]]) {
        await page.goto(`http://127.0.0.1:5174/regiao/${r.id_regiao}`)
        await page.getByRole('heading', { name: r.nome, exact: true }).waitFor()
        await painel(page).getByRole('table').waitFor()
        const texto = await painel(page).innerText()
        for (const k of ['FFMC','DMC','DC','ISI','BUI','FWI','Origem','Método','Versão','Inicialização']) assert.match(texto, new RegExp(k))
        assert.match(texto, r.id_regiao === 3279 ? /13:00:00 UTC/ : /12:00:00 UTC/)
        assert.match(texto, /14:10:00 UTC/)
        assert.match(texto, /04\/10\/2026/)
        assert.match(texto, /0\.62\.0/)
        assert.match(await page.locator('body').innerText(), /Índice legado/)
        assert.equal(await painel(page).getByRole('row').count(), 2)
    }
})

test('histórico reconstruído mantém a revisão e falha sem ocultar o FWI diário', async t => {
    const { page, controlo } = await preparar(t)
    let historicoFalha = false, parametros
    controlo.fwi = async (id, route, historico) => {
        const d = { ...diario(id), estado: 'em_inicializacao', estado_inicializacao: 'reconstruido',
            operacional: false, estabelecido: false, serie: 'reconstrucao', revisao: 2, revisao_ativa: true,
            mensagem: 'Sequência reconstruída, ainda não estabelecida.' }
        if (historico) {
            parametros = new URL(route.request().url()).searchParams
            await route.fulfill(historicoFalha ? { status: 503, json: {} }
                : { json: { id_regiao: id, serie: 'reconstrucao', revisao: 2, resultados: [d] } })
        } else await route.fulfill({ json: d })
        return true
    }
    await page.goto('http://127.0.0.1:5174/regiao/1')
    await painel(page).getByRole('table').waitFor()
    assert.equal(parametros.get('revisao'), '2')
    assert.equal(parametros.get('serie'), 'reconstrucao')
    assert.match(await painel(page).innerText(), /Reconstruído, não estabelecido/)
    historicoFalha = true
    await page.reload()
    await painel(page).getByText('Não foi possível obter o histórico FWI diário.').waitFor()
    assert.equal(await valor(page).innerText(), '30')
})

test('falha da meteorologia nos detalhes não oculta o FWI diário independente', async t => {
    const { page, controlo } = await preparar(t)
    controlo.detalhe = { erro: 'Meteorologia indisponível no teste.' }
    await page.goto('http://127.0.0.1:5174/regiao/1')
    await painel(page).getByText('Operacional estabelecido', { exact: true }).waitFor()
    assert.equal(await valor(page).innerText(), '30')
})

test('detalhes sem reload: troca de região descarta resposta atrasada e mantém um refresh', async t => {
    const { page, controlo } = await preparar(t)
    await page.goto('http://127.0.0.1:5174/regiao/1')
    await painel(page).getByRole('table').waitFor()
    let pendente, pedidosPorto = 0
    controlo.fwi = async (id, route, historico) => {
        if (id === 3263 && !historico) { pendente = route; return true }
        if (id === 3261 && !historico) pedidosPorto++
        return false
    }
    const navegar = id => page.evaluate(id => {
        window.history.pushState({}, '', `/regiao/${id}`)
        window.dispatchEvent(new PopStateEvent('popstate'))
    }, id)
    await navegar(3263)
    await painel(page).getByText('A carregar FWI diário…', { exact: true }).waitFor()
    assert.equal(await valor(page).innerText(), 'Indisponível')
    await navegar(3261)
    await page.getByRole('heading', { name: 'Porto', exact: true }).waitFor()
    await painel(page).getByRole('table').waitFor()
    await pendente.fulfill({ json: { ...diario(3263), fwi: 999 } })
    await page.waitForTimeout(100)
    assert.equal(await valor(page).innerText(), '32')
    const antes = pedidosPorto
    const refresh = page.waitForResponse(r => r.url().endsWith('/api/fwi-diario/3261'))
    await page.clock.fastForward(61000)
    await refresh
    assert.equal(pedidosPorto, antes + 1)
})


test('FWI principal independente do legado e sem classes heurísticas no cabeçalho', async t => {
    const { page, controlo } = await preparar(t)
    assert.equal(await page.locator('aside > :first-child').getAttribute('aria-label'), 'FWI diário — Lisboa')
    assert.doesNotMatch(await page.locator('nav').innerText(), /Risco|Baixo|Elevado|Extremo/)
    assert.equal(await page.locator('aside').getByText('Índice legado', { exact: true }).count(), 0)
    controlo.resposta = async (_id, route) => {
        await route.fulfill({ status: 503, json: { detail: 'Legado indisponível' } })
        return true
    }
    await selecionar(page, regioes[1])
    await page.waitForFunction(() => document.querySelector('[data-testid="valor-fwi-diario"]')?.textContent === '31')
    await page.getByText('Índice legado (experimental): Indisponível', { exact: true }).waitFor()
    assert.match(await page.locator('body').innerText(), /Não representa a probabilidade de um incêndio futuro/)
})
