import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDetalhesRegiao, getRiscoRegiao } from '../services/api'
import Navbar from '../components/Navbar'
import { obterApresentacaoRisco } from '../utils/risco'
import { formatarValor, formatarProbabilidade, percentagemDisponivel, mensagemErro, mensagemEstado } from '../utils/disponibilidade'

function DetalheRegiao({ darkMode, onToggleDark }) {
    const { id } = useParams()
    const navigate = useNavigate()
    const [detalhes, setDetalhes] = useState(null)
    const [risco, setRisco] = useState(null)
    const [loading, setLoading] = useState(true)
    const [tecnicoAberto, setTecnicoAberto] = useState(false)
    const [erroDados, setErroDados] = useState('')
    const [erroRisco, setErroRisco] = useState('')

    useEffect(() => {
        carregarDados()
        const intervalo = setInterval(() => carregarDados(false), 60000)
        return () => clearInterval(intervalo)
    }, [id])

    const carregarDados = async (inicial = true) => {
        if (inicial) setLoading(true)
        setErroDados('')
        setErroRisco('')
        try {
            const [det, risc] = await Promise.all([
                getDetalhesRegiao(id),
                getRiscoRegiao(id).catch(err => { setErroRisco(mensagemErro(err)); return null })
            ])
            setDetalhes(det)
            setRisco(risc)
        } catch (err) {
            setDetalhes(null)
            setRisco(null)
            setErroDados(mensagemErro(err))
            console.error('Erro ao carregar detalhes:', err)
        } finally {
            setLoading(false)
        }
    }

    const gerarInsight = () => {
        if (!detalhes?.atual) return 'Sem dados suficientes para análise.'
        const { temperatura, humidade, velocidade_vento, nivel_risco } = detalhes.atual
        const apresentacao = obterApresentacaoRisco(nivel_risco)
        if (!apresentacao.conhecido) return 'Risco indisponível. Não é possível avaliar o nível de risco com os dados apresentados.'
        const fatores = []
        if (humidade < 30) fatores.push('baixa humidade')
        if (velocidade_vento > 25) fatores.push('vento forte')
        if (temperatura > 30) fatores.push('temperatura elevada')
        if (fatores.length === 0) return `Risco ${apresentacao.label}. Sem fatores adicionais identificados nos dados apresentados.`
        return `Risco ${apresentacao.label} devido a ${fatores.join(' + ')}.`
    }

    if (loading) return (
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--texto-secondary)' }}>
            A carregar detalhes...
        </div>
    )

    if (!detalhes || detalhes.erro) return (
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '16px' }}>
            <div role="status" style={{ color: 'var(--texto-secondary)' }}>{erroDados || detalhes?.erro || 'Dados indisponíveis'}</div>
            <button onClick={() => navigate('/')} style={{ padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#639922', color: 'white', cursor: 'pointer' }}>
                Voltar ao Dashboard
            </button>
        </div>
    )

    const cores = obterApresentacaoRisco(detalhes.atual?.nivel_risco)
    const coresML = obterApresentacaoRisco(risco?.ml?.nivel_risco_ml)
    const percentagem = percentagemDisponivel(risco?.ml?.probabilidade_incendio)

    return (
        <div className="app">
            <Navbar
                dataObservacao={detalhes.atual?.data_hora}
                estado={erroRisco ? 'erro_fonte' : detalhes.estado}
                risco={detalhes.atual?.nivel_risco}
                localidade={detalhes.regiao?.nome}
                darkMode={darkMode}
                onToggleDark={onToggleDark}
            />
            {mensagemEstado(detalhes.estado) && <div role="status">{mensagemEstado(detalhes.estado)}</div>}
            {(erroRisco || mensagemEstado(risco?.estado)) && <div role="status">{erroRisco || mensagemEstado(risco?.estado)}</div>}

            <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
                <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>

                    {/* Botão voltar */}
                    <button onClick={() => navigate('/')} style={{
                        alignSelf: 'flex-start', padding: '6px 12px', borderRadius: '8px',
                        border: '0.5px solid var(--cinza-borda)', background: 'var(--cinza-card)',
                        color: 'var(--texto-secondary)', cursor: 'pointer', fontSize: '12px'
                    }}>
                        ← Voltar ao Dashboard
                    </button>

                    {/* Resumo */}
                    <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', padding: '20px', border: '0.5px solid var(--cinza-borda)' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                            <div>
                                <h1 style={{ fontSize: '24px', fontWeight: '500', color: 'var(--texto-primary)' }}>{detalhes.regiao?.nome}</h1>
                                <div style={{ fontSize: '13px', color: 'var(--texto-secondary)', marginTop: '4px' }}>{detalhes.regiao?.distrito}</div>
                            </div>
                            <span style={{
                                padding: '6px 14px', borderRadius: '99px', fontSize: '13px',
                                fontWeight: '500', background: cores.bg, color: cores.color
                            }}>
                                Risco {cores.label}
                            </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                            {[
                                { label: 'Temperatura', value: detalhes.atual?.temperatura, unit: '°C', icon: '🌡' },
                                { label: 'Humidade', value: detalhes.atual?.humidade, unit: '%', icon: '💧' },
                                { label: 'Vento', value: detalhes.atual?.velocidade_vento, unit: 'km/h', icon: '💨' },
                                { label: 'Precipitação', value: detalhes.atual?.precipitacao, unit: 'mm', icon: '🌧' },
                            ].map((item, i) => (
                                <div key={i} style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '20px', marginBottom: '4px' }}>{item.icon}</div>
                                    <div style={{ fontSize: '11px', color: 'var(--texto-tertiary)' }}>{item.label}</div>
                                    <div style={{ fontSize: '18px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                                        {formatarValor(item.value)} <span style={{ fontSize: '11px', color: 'var(--texto-tertiary)' }}>{item.unit}</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {detalhes.tendencia && (
                            <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--texto-secondary)' }}>
                                Tendência: <strong style={{ color: detalhes.tendencia === 'a aumentar' ? '#E24B4A' : detalhes.tendencia === 'a diminuir' ? '#639922' : 'var(--texto-primary)' }}>
                                    {detalhes.tendencia}
                                </strong>
                            </div>
                        )}
                    </div>

                    {/* ML e Previsão */}
                    {risco && (
                        <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', padding: '20px', border: '0.5px solid var(--cinza-borda)' }}>
                            <h2 style={{ fontSize: '14px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px' }}>
                                Previsão ML + FWI
                            </h2>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                                <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '11px', color: 'var(--texto-tertiary)', marginBottom: '4px' }}>Probabilidade</div>
                                    <div style={{ fontSize: '24px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                                        {formatarProbabilidade(risco.ml?.probabilidade_incendio)}
                                    </div>
                                    <div style={{ height: '4px', borderRadius: '99px', background: 'var(--cinza-borda)', marginTop: '8px' }}>
                                        {percentagem !== null && <div style={{ height: '4px', borderRadius: '99px', background: '#E24B4A', width: `${percentagem}%` }} />}
                                    </div>
                                </div>
                                <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '11px', color: 'var(--texto-tertiary)', marginBottom: '4px' }}>FWI</div>
                                    <div style={{ fontSize: '24px', fontWeight: '500', color: 'var(--texto-primary)' }}>{formatarValor(risco.fwi?.fwi)}</div>
                                </div>
                                <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '11px', color: 'var(--texto-tertiary)', marginBottom: '4px' }}>Nível ML</div>
                                    <div style={{ fontSize: '16px', fontWeight: '500', color: coresML.color }}>{coresML.label}</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Insights */}
                    <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', padding: '20px', border: '0.5px solid var(--cinza-borda)' }}>
                        <h2 style={{ fontSize: '14px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px' }}>
                            Análise automática
                        </h2>
                        <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', marginBottom: '12px' }}>
                            <div style={{ fontSize: '12px', color: 'var(--texto-secondary)', marginBottom: '4px' }}>Diagnóstico</div>
                            <div style={{ fontSize: '13px', color: 'var(--texto-primary)' }}>{gerarInsight()}</div>
                        </div>
                        <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px' }}>
                            <div style={{ fontSize: '12px', color: 'var(--texto-secondary)', marginBottom: '4px' }}>Recomendação</div>
                            <div style={{ fontSize: '13px', color: 'var(--texto-primary)' }}>{cores.recomendacao}</div>
                        </div>
                    </div>

                    {/* Histórico */}
                    {detalhes.historico?.length > 0 && (
                        <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', padding: '20px', border: '0.5px solid var(--cinza-borda)' }}>
                            <h2 style={{ fontSize: '14px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px' }}>
                                Histórico recente
                            </h2>
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                                    <thead>
                                        <tr>
                                            {['Data/Hora', 'Temp (°C)', 'Humidade (%)', 'Vento (km/h)', 'FWI', 'Nível'].map(h => (
                                                <th key={h} style={{ padding: '8px', textAlign: 'left', color: 'var(--texto-tertiary)', fontWeight: '500', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {detalhes.historico.map((h, i) => {
                                            const c = obterApresentacaoRisco(h.nivel_risco)
                                            return (
                                                <tr key={i}>
                                                    <td style={{ padding: '8px', color: 'var(--texto-secondary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>
                                                        {new Date(h.data_hora).toLocaleString('pt-PT')}
                                                    </td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.temperatura ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.humidade ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.velocidade_vento ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{formatarValor(h.fwi)}</td>
                                                    <td style={{ padding: '8px', borderBottom: '0.5px solid var(--cinza-borda)' }}>
                                                        <span style={{ padding: '2px 8px', borderRadius: '99px', background: c.bg, color: c.color, fontSize: '11px' }}>
                                                            {c.label}
                                                        </span>
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Dados técnicos */}
                    <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', border: '0.5px solid var(--cinza-borda)' }}>
                        <div
                            onClick={() => setTecnicoAberto(!tecnicoAberto)}
                            style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                        >
                            <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                Dados técnicos
                            </span>
                            <span style={{ color: 'var(--texto-tertiary)' }}>{tecnicoAberto ? '▲' : '▼'}</span>
                        </div>
                        {tecnicoAberto && (
                            <div style={{ padding: '0 20px 20px', borderTop: '0.5px solid var(--cinza-borda)' }}>
                                <pre style={{ fontSize: '11px', color: 'var(--texto-secondary)', overflowX: 'auto', marginTop: '12px', lineHeight: '1.6' }}>
                                    {JSON.stringify({ regiao: detalhes.regiao, atual: detalhes.atual, risco }, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    )
}

export default DetalheRegiao
