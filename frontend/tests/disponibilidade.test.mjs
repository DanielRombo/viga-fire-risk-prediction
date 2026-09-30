import assert from 'node:assert/strict'
import test from 'node:test'
import { apresentarAlertas, formatarValor, formatarProbabilidade, percentagemDisponivel, mensagemErro } from '../src/utils/disponibilidade.js'

test('zero verdadeiro permanece zero em valores e percentagens', () => {
    assert.equal(formatarValor(0), '0')
    assert.equal(formatarProbabilidade(0), '0%')
    assert.equal(percentagemDisponivel(0), 0)
})

test('ausência e valores inválidos nunca são convertidos em zero', () => {
    for (const value of [undefined, null, NaN, Infinity, '', false, '0', {}, []]) {
        assert.equal(formatarValor(value), 'Indisponível')
        assert.equal(formatarProbabilidade(value), 'Indisponível')
        assert.equal(percentagemDisponivel(value), null)
    }
    assert.equal(formatarProbabilidade(-1), 'Indisponível')
    assert.equal(formatarProbabilidade(2), 'Indisponível')
})

test('uma avaliação válida sem alertas apresenta zero alertas', () => {
    const result = apresentarAlertas({ estado: 'ok', alertas: [], cobertura: { regioes_avaliadas: 2 }, mensagem: 'Sem alertas nas regiões avaliadas.' })
    assert.equal(result.total, 0)
    assert.match(result.mensagem, /regiões avaliadas/)
})

test('base vazia, dados incompletos e antigos não aparecem como ausência de alertas', () => {
    for (const estado of ['sem_dados', 'dados_incompletos', 'desatualizado']) {
        const result = apresentarAlertas({ estado, alertas: [], cobertura: { regioes_avaliadas: 0 } })
        assert.equal(result.total, null)
        assert.doesNotMatch(result.mensagem, /Sem alertas|Condições normais/)
        assert.ok(result.mensagem)
    }
})

test('cobertura parcial mantém aviso mesmo sem alertas', () => {
    const result = apresentarAlertas({ estado: 'cobertura_parcial', alertas: [], cobertura: { regioes_avaliadas: 1 } })
    assert.equal(result.total, 0)
    assert.match(result.mensagem, /Cobertura parcial/)
})

test('falha no pedido invalida resultados antigos e não apresenta zero', () => {
    const previous = { estado: 'ok', alertas: [{ id: 'old' }], cobertura: { regioes_avaliadas: 1 } }
    const result = apresentarAlertas(previous, true)
    assert.equal(result.total, null)
    assert.deepEqual(result.alertas, [])
    assert.match(result.mensagem, /indisponíveis/)
})

test('resposta incompleta da API não se converte em lista vazia de sucesso', () => {
    for (const response of [null, {}, { estado: 'ok' }, { alertas: [] }]) {
        assert.equal(apresentarAlertas(response).total, null)
    }
})

test('mensagens distinguem erro externo, inexistência e falta de observação', () => {
    for (const mensagem of ['Falha da fonte', 'Região não encontrada', 'Sem observação atual']) {
        assert.equal(mensagemErro({ response: { data: { detail: { mensagem } } } }), mensagem)
    }
    assert.match(mensagemErro(new Error('network')), /Falha/)
})
