export const numeroDisponivel = valor => typeof valor === 'number' && Number.isFinite(valor)
export const formatarValor = valor => numeroDisponivel(valor) ? String(valor) : 'Indisponível'
export const percentagemDisponivel = valor => numeroDisponivel(valor) && valor >= 0 && valor <= 1 ? Math.round(valor * 100) : null
export const formatarProbabilidade = valor => {
    const percentagem = percentagemDisponivel(valor)
    return percentagem === null ? 'Indisponível' : `${percentagem}%`
}

export function mensagemEstado(estado) {
    return {
        sem_dados: 'Sem dados disponíveis.',
        dados_incompletos: 'Dados incompletos; avaliação indisponível.',
        desatualizado: 'Dados desatualizados; avaliação atual indisponível.',
        erro_fonte: 'Falha ao obter dados. Informação indisponível.',
        cobertura_parcial: 'Cobertura parcial: a ausência de alertas não indica normalidade nas regiões sem dados.',
    }[estado] || ''
}

export function mensagemErro(erro) {
    const detalhe = erro?.response?.data?.detail
    return typeof detalhe === 'string' ? detalhe : detalhe?.mensagem || 'Falha ao obter dados. Informação indisponível.'
}

export function apresentarAlertas(dados, erro = false) {
    if (erro || !dados || !Array.isArray(dados.alertas) || !dados.estado) {
        return { alertas: [], total: null, mensagem: 'Alertas indisponíveis: não foi possível obter uma avaliação válida.' }
    }
    const avaliadas = dados.cobertura?.regioes_avaliadas
    const temAvaliacao = numeroDisponivel(avaliadas) && avaliadas > 0 && ['ok', 'cobertura_parcial'].includes(dados.estado)
    return {
        alertas: temAvaliacao ? dados.alertas : [],
        total: temAvaliacao ? dados.alertas.length : null,
        mensagem: dados.mensagem || mensagemEstado(dados.estado) || 'Avaliação indisponível.',
    }
}
