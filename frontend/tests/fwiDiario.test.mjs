import test from 'node:test'
import assert from 'node:assert/strict'
import { apresentacaoFWI, estadosFWI, formatarDataFWI, formatarIndiceFWI, criarCarregadorFWI } from '../src/utils/fwiDiario.js'

const dados = (id = 1) => ({ id_regiao: id, estado: 'ok', operacional: true, estabelecido: true,
    estado_inicializacao: 'estabelecido', qualidade: 'estabelecido', validade: 'valido',
    fwi: 0, ffmc: 0, dmc: 0, dc: 0, isi: 0, bui: 0, serie: 'operacional', revisao: null, data_referencia: '2024-03-01' })
const pendente = () => { let resolver; const promise = new Promise(r => { resolver = r }); return { promise, resolver } }

test('FWI diário: zero é válido; null e valores inválidos são indisponíveis', () => {
    assert.equal(formatarIndiceFWI(0), '0')
    for (const v of [null, undefined, NaN, Infinity, -1, '0', false]) assert.equal(formatarIndiceFWI(v), 'Indisponível')
    assert.equal(apresentacaoFWI(dados()).operacional, true)
})
test('todos os estados têm designação explícita sem classes do legado', () => {
    for (const estado of Object.keys(estadosFWI)) {
        const p = apresentacaoFWI({ ...dados(), estado, operacional: estado === 'ok' })
        assert.equal(p.estado, estadosFWI[estado])
        assert.equal(p.operacional, estado === 'ok')
        assert.doesNotMatch(p.estado, /Baixo|Elevado|Extremo/)
    }
})
test('reconstruído, convencional e reconstrução nunca são operacionais, mesmo com contrato contraditório', () => {
    for (const estado_inicializacao of ['reconstruido', 'inicializado_convencionalmente', 'em_reconstrucao', 'sem_estado']) {
        assert.equal(apresentacaoFWI({ ...dados(), estado_inicializacao }).operacional, false)
    }
    for (const patch of [{ operacional: false }, { operacional: 'true' }, { estabelecido: false }, { fwi: null }, { revisao_ativa: false }]) {
        assert.equal(apresentacaoFWI({ ...dados(), ...patch }).operacional, false)
    }
})
test('datas de referência preservam o calendário, incluindo ano bissexto', () => {
    assert.equal(formatarDataFWI('2024-02-29'), '29/02/2024')
    assert.equal(formatarDataFWI('2023-02-29'), 'Indisponível')
    assert.equal(formatarDataFWI(null), 'Indisponível')
})
test('cancelamento ignora a resposta da região anterior e limpa valores enquanto carrega', async () => {
    const p = pendente(), estados = []
    const anterior = criarCarregadorFWI({ idRegiao: 1, consultar: () => p.promise, onChange: s => estados.push(s) })
    const chamada = anterior.carregar()
    assert.equal(estados.at(-1).dados, null)
    anterior.cancelar()
    const novo = criarCarregadorFWI({ idRegiao: 2, consultar: async () => dados(2), onChange: s => estados.push(s) })
    await novo.carregar()
    p.resolver(dados(1))
    await chamada
    assert.equal(estados.at(-1).dados.id_regiao, 2)
})
test('refresh sobreposto ignora a resposta mais antiga', async () => {
    const p = pendente(), estados = []; let n = 0
    const c = criarCarregadorFWI({ idRegiao: 1, consultar: () => ++n === 1 ? p.promise : Promise.resolve({ ...dados(), fwi: 12 }), onChange: s => estados.push(s) })
    const primeira = c.carregar()
    await c.carregar()
    p.resolver(dados())
    await primeira
    assert.equal(estados.at(-1).dados.fwi, 12)
})
test('erro HTTP e região incompatível não preservam dados anteriores', async () => {
    for (const consultar of [async () => { throw new Error('HTTP 503') }, async () => dados(9)]) {
        const estados = []
        await criarCarregadorFWI({ idRegiao: 1, consultar, onChange: s => estados.push(s) }).carregar()
        assert.equal(estados.at(-1).dados, null)
        assert.equal(estados.at(-1).carregando, false)
        assert.equal(estados.at(-1).erro, 'Não foi possível obter o FWI diário.')
    }
})
test('histórico fixa série, revisão e janela a partir da data da API', async () => {
    let params, ultimo
    const d = { ...dados(), serie: 'reconstrucao', revisao: 3 }
    await criarCarregadorFWI({ idRegiao: 1, consultar: async () => d, onChange: s => { ultimo = s },
        consultarHistorico: async (id, p) => { params = p; return { id_regiao: id, serie: d.serie, revisao: 3, resultados: [d] } },
    }).carregar()
    assert.deepEqual(params, { serie: 'reconstrucao', revisao: 3, inicio: '2024-02-01', fim: '2024-03-01', limite: 30 })
    assert.equal(ultimo.historico.length, 1)
})
test('histórico duplicado ou de outra revisão é rejeitado sem perder o resultado diário', async () => {
    for (const resultados of [[dados(), dados()], [{ ...dados(), revisao: 2 }]]) {
        let ultimo
        await criarCarregadorFWI({ idRegiao: 1, consultar: async () => dados(), onChange: s => { ultimo = s },
            consultarHistorico: async () => ({ id_regiao: 1, serie: 'operacional', revisao: null, resultados }),
        }).carregar()
        assert.equal(ultimo.dados.fwi, 0)
        assert.equal(ultimo.erroHistorico, 'Não foi possível obter o histórico FWI diário.')
    }
})
test('resposta histórica atrasada é ignorada depois do cancelamento', async () => {
    const p = pendente(); let ultimo
    const c = criarCarregadorFWI({ idRegiao: 1, consultar: async () => dados(), onChange: s => { ultimo = s }, consultarHistorico: () => p.promise })
    const chamada = c.carregar()
    await Promise.resolve()
    c.cancelar()
    const antes = ultimo
    p.resolver({ id_regiao: 1, serie: 'operacional', revisao: null, resultados: [dados()] })
    await chamada
    assert.equal(ultimo, antes)
})
