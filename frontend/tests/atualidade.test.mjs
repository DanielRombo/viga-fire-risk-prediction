import test from 'node:test'
import assert from 'node:assert/strict'
import { encontrarRegiaoMapa } from '../src/utils/regioesMapa.js'
import { formatarDataObservacao, estadoDados } from '../src/utils/disponibilidade.js'

test('ilhas resolvidas por nome e distrito, com IDs reais', () => {
    const regioes = [
        { nome: 'Ponta Delgada', distrito: 'Madeira', id_regiao: 1 },
        { nome: 'Ponta Delgada', distrito: 'Açores', id_regiao: 9123 },
        { nome: 'Funchal', distrito: 'Madeira', id_regiao: 9456 },
    ]
    assert.equal(encontrarRegiaoMapa(regioes, 'Azores').id_regiao, 9123)
    assert.equal(encontrarRegiaoMapa(regioes, 'Açores').id_regiao, 9123)
    assert.equal(encontrarRegiaoMapa(regioes, 'Madeira').id_regiao, 9456)
    assert.equal(encontrarRegiaoMapa([], 'Madeira'), undefined)
})

test('última atualização usa a observação UTC e não o relógio', () => {
    const data = formatarDataObservacao('2026-01-02T12:34:00Z')
    assert.match(data, /02\/01\/2026/)
    assert.match(data, /12:34:00 UTC/)
    assert.equal(formatarDataObservacao('2026-01-02T13:34:00+01:00'), data)
    assert.equal(formatarDataObservacao('2026-01-02T12:34:00'), data)
    assert.equal(formatarDataObservacao(null), 'Indisponível')
    assert.equal(formatarDataObservacao('inválida'), 'Indisponível')
})

test('estado reflete dados atuais, antigos, ausentes e erros', () => {
    assert.equal(estadoDados('ok'), 'Dados atuais')
    assert.equal(estadoDados('desatualizado'), 'Dados desatualizados')
    assert.equal(estadoDados('sem_dados'), 'Sem dados')
    assert.equal(estadoDados('erro_fonte'), 'Dados indisponíveis')
    assert.equal(estadoDados(undefined), 'Dados indisponíveis')
})
