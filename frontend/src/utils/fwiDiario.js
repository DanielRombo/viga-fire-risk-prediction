import { numeroDisponivel } from './disponibilidade.js'

export const estadosFWI = {
    ok: 'Atual', desatualizado: 'Desatualizado', indisponivel: 'Indisponível',
    em_inicializacao: 'Em inicialização', em_reconstrucao: 'Em reconstrução',
    dados_incompletos: 'Dados incompletos', erro_fonte: 'Erro da fonte',
    estado_anterior_ausente: 'Estado anterior ausente',
}
export const inicializacoesFWI = {
    sem_estado: 'Sem estado anterior', inicializado_convencionalmente: 'Inicializado convencionalmente',
    em_inicializacao: 'Em inicialização', em_reconstrucao: 'Em reconstrução',
    reconstruido: 'Reconstruído, não estabelecido', estabelecido: 'Estabelecido',
    falha_reconstrucao: 'Falha na reconstrução',
}
export const componentesFWI = ['ffmc', 'dmc', 'dc', 'isi', 'bui', 'fwi']
export const formatarIndiceFWI = valor => numeroDisponivel(valor) && valor >= 0
    ? valor.toLocaleString('pt-PT', { maximumFractionDigits: 2 }) : 'Indisponível'
export function formatarDataFWI(valor) {
    if (typeof valor !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(valor)) return 'Indisponível'
    const data = new Date(`${valor}T00:00:00Z`)
    return Number.isNaN(data.getTime()) || data.toISOString().slice(0, 10) !== valor
        ? 'Indisponível' : data.toLocaleDateString('pt-PT', { timeZone: 'UTC' })
}
export function apresentacaoFWI(dados) {
    const operacional = dados?.operacional === true && dados?.estabelecido === true && dados?.estado === 'ok'
        && dados?.estado_inicializacao === 'estabelecido' && dados?.qualidade === 'estabelecido'
        && ['valido', 'calculado'].includes(dados?.validade) && dados?.revisao_ativa !== false
        && componentesFWI.every(k => numeroDisponivel(dados?.[k]) && dados[k] >= 0)
    return {
        operacional,
        estado: dados?.estado === 'ok' && !operacional ? 'Não operacional' : estadosFWI[dados?.estado] || 'Indisponível',
        inicializacao: inicializacoesFWI[dados?.estado_inicializacao] || 'Indisponível',
    }
}

// Sem timers: o chamador utiliza o refresh que já existe na página.
export function criarCarregadorFWI({ idRegiao, consultar, consultarHistorico, onChange }) {
    let ativo = true
    let sequencia = 0
    return {
        cancelar() { ativo = false; sequencia++ },
        async carregar() {
            const pedido = ++sequencia
            const atual = () => ativo && pedido === sequencia
            if (!ativo) return
            let estado = { idRegiao, dados: null, carregando: true, erro: '', historico: null, erroHistorico: '', carregandoHistorico: false }
            onChange(estado)
            try {
                const dados = await consultar(idRegiao)
                if (!atual()) return
                if (!dados || String(dados.id_regiao) !== String(idRegiao) || !Object.hasOwn(estadosFWI, dados.estado)) {
                    throw new Error('Resposta FWI incompatível com a região ou o contrato.')
                }
                estado = { ...estado, dados, carregando: false }
                const temData = formatarDataFWI(dados.data_referencia) !== 'Indisponível'
                const temSerie = ['operacional', 'reconstrucao'].includes(dados.serie)
                if (!consultarHistorico || !temData || !temSerie) {
                    onChange({ ...estado, historico: [] })
                    return
                }
                onChange({ ...estado, carregandoHistorico: true })
                try {
                    const inicio = new Date(`${dados.data_referencia}T00:00:00Z`)
                    inicio.setUTCDate(inicio.getUTCDate() - 29)
                    const params = { serie: dados.serie, inicio: inicio.toISOString().slice(0, 10),
                        fim: dados.data_referencia, limite: 30 }
                    if (dados.serie === 'reconstrucao') {
                        if (!Number.isInteger(dados.revisao) || dados.revisao < 1) throw new Error('Revisão ausente.')
                        params.revisao = dados.revisao
                    }
                    const resposta = await consultarHistorico(idRegiao, params)
                    if (!atual()) return
                    if (String(resposta?.id_regiao) !== String(idRegiao) || resposta?.serie !== dados.serie
                        || (resposta?.revisao ?? null) !== (dados.revisao ?? null) || !Array.isArray(resposta?.resultados)
                        || resposta.resultados.some(r => String(r.id_regiao) !== String(idRegiao)
                            || r.serie !== dados.serie || (r.revisao ?? null) !== (dados.revisao ?? null)
                            || formatarDataFWI(r.data_referencia) === 'Indisponível'
                            || r.data_referencia < params.inicio || r.data_referencia > params.fim)
                        || new Set(resposta.resultados.map(r => r.data_referencia)).size !== resposta.resultados.length) {
                        throw new Error('Histórico incompatível com a seleção.')
                    }
                    onChange({ ...estado, historico: [...resposta.resultados].sort((a, b) => a.data_referencia.localeCompare(b.data_referencia)) })
                } catch {
                    if (atual()) onChange({ ...estado, erroHistorico: 'Não foi possível obter o histórico FWI diário.' })
                }
            } catch {
                if (atual()) onChange({ ...estado, dados: null, carregando: false, erro: 'Não foi possível obter o FWI diário.' })
            }
        },
    }
}
