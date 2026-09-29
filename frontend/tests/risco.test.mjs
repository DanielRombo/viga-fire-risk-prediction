import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { legendaRisco, obterApresentacaoRisco } from '../src/utils/risco.js'

const niveis = [
    ['Muito Baixo', '#2E7D32'],
    ['Baixo', '#558B2F'],
    ['Moderado', '#996515'],
    ['Elevado', '#C2410C'],
    ['Muito Elevado', '#B91C1C'],
    ['Extremo', '#7F1D1D'],
    ['Muito Extremo', '#581C87'],
]

for (const [nivel, cor] of niveis) {
    test(`${nivel}: apresentação explícita e legenda correspondente`, () => {
        const resultado = obterApresentacaoRisco(nivel)
        assert.equal(resultado.conhecido, true)
        assert.equal(resultado.label, nivel)
        assert.equal(resultado.color, cor)
        assert.ok(resultado.bg)
        assert.ok(resultado.recomendacao)
        assert.deepEqual(legendaRisco.find(item => item.label === nivel), { label: nivel, cor })
    })
}

for (const [alias, nivel] of [
    ['Medio', 'Moderado'], ['Médio', 'Moderado'],
    ['Alto', 'Elevado'], ['Muito Alto', 'Muito Elevado'],
]) {
    test(`${alias}: compatível com ${nivel}`, () => {
        assert.deepEqual(obterApresentacaoRisco(alias), obterApresentacaoRisco(nivel))
    })
}

for (const nivel of ['Extremo', 'Muito Extremo']) {
    test(`${nivel}: nunca usa a apresentação ou recomendação de baixo risco`, () => {
        const resultado = obterApresentacaoRisco(nivel)
        for (const baixo of ['Muito Baixo', 'Baixo']) {
            const seguro = obterApresentacaoRisco(baixo)
            assert.notEqual(resultado.color, seguro.color)
            assert.notEqual(resultado.bg, seguro.bg)
            assert.notEqual(resultado.recomendacao, seguro.recomendacao)
        }
        assert.match(resultado.recomendacao, /Evitar atividades com fogo/)
        assert.doesNotMatch(resultado.recomendacao, /Condições normais|vigilância habitual/)
    })
}

test('valores ausentes, inesperados e nomes de propriedades recebem estado neutro', () => {
    const inesperados = [undefined, null, '', 'Desconhecido', 'extremo', 'constructor',
        '__proto__', 'toString', 0, 1, NaN, false, true, {}, [], ['Baixo']]
    for (const nivel of inesperados) {
        const resultado = obterApresentacaoRisco(nivel)
        assert.equal(resultado.label, 'Indisponível')
        assert.equal(resultado.conhecido, false)
        assert.equal(resultado.color, '#666666')
        assert.match(resultado.recomendacao, /ausência de dados não indica segurança/)
        assert.deepEqual(legendaRisco.find(item => item.label === resultado.label), {
            label: 'Indisponível', cor: resultado.color,
        })
    }
})

test('legenda completa, ordenada e sem duplicação dos aliases', () => {
    assert.deepEqual(legendaRisco.map(item => item.label), [...niveis.map(([nivel]) => nivel), 'Indisponível'])
})

test('todos os níveis atualmente emitidos pelo backend têm apresentação conhecida', () => {
    for (const [ficheiro, variavel] of [['fwi.py', 'nivel'], ['modelo_ml.py', 'nivel']]) {
        const codigo = readFileSync(new URL(`../../backend/services/${ficheiro}`, import.meta.url), 'utf8')
        const emitidos = [...codigo.matchAll(new RegExp(`${variavel} = "([^"]+)"`, 'g'))]
        assert.ok(emitidos.length > 0)
        for (const [, nivel] of emitidos) {
            assert.equal(obterApresentacaoRisco(nivel).conhecido, true, `${ficheiro}: ${nivel}`)
        }
    }
})
