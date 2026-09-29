// Apresentação apenas: não calcula nem altera o risco recebido da API.
const niveis = [
    { label: 'Muito Baixo', color: '#2E7D32', bg: '#E8F5E9', recomendacao: 'Manter vigilância habitual e acompanhar as informações oficiais.' },
    { label: 'Baixo', color: '#558B2F', bg: '#F1F8E9', recomendacao: 'Manter vigilância habitual e acompanhar as informações oficiais.' },
    { label: 'Moderado', color: '#996515', bg: '#FFF8E1', recomendacao: 'Reforçar a atenção e acompanhar a evolução do risco e as informações oficiais.' },
    { label: 'Elevado', color: '#C2410C', bg: '#FFF3E0', recomendacao: 'Redobrar a atenção em zonas florestais. Evitar atividades com fogo e acompanhar as informações oficiais.' },
    { label: 'Muito Elevado', color: '#B91C1C', bg: '#FEE2E2', recomendacao: 'Evitar atividades com fogo. Acompanhar os avisos e seguir as indicações das autoridades.' },
    { label: 'Extremo', color: '#7F1D1D', bg: '#FECACA', recomendacao: 'Risco extremo. Evitar atividades com fogo e seguir os avisos e indicações das autoridades.' },
    { label: 'Muito Extremo', color: '#581C87', bg: '#F3E8FF', recomendacao: 'Risco muito extremo. Evitar atividades com fogo e seguir os avisos e indicações das autoridades.' },
].map(nivel => Object.freeze({ ...nivel, border: nivel.color, conhecido: true }))

const indisponivel = Object.freeze({
    label: 'Indisponível',
    color: '#666666',
    bg: '#F0F0F0',
    border: '#666666',
    conhecido: false,
    recomendacao: 'Risco indisponível. Consultar informações oficiais atualizadas; a ausência de dados não indica segurança.',
})

const porNome = new Map(niveis.map(nivel => [nivel.label, nivel]))
// Nomes atualmente emitidos pelo backend, sem mudar a classificação na API.
porNome.set('Medio', porNome.get('Moderado'))
porNome.set('Médio', porNome.get('Moderado'))
porNome.set('Alto', porNome.get('Elevado'))
porNome.set('Muito Alto', porNome.get('Muito Elevado'))

export function obterApresentacaoRisco(nivel) {
    return typeof nivel === 'string' ? porNome.get(nivel) ?? indisponivel : indisponivel
}

export const legendaRisco = Object.freeze([...niveis, indisponivel].map(nivel =>
    Object.freeze({ label: nivel.label, cor: nivel.color })
))
