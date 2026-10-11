import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDetalhesRegiao, getRiscoRegiao, getFWIDiario, getHistoricoFWIDiario } from '../services/api'
import Navbar from '../components/Navbar'
import PainelFWIDiario from '../components/PainelFWIDiario'
import { criarCarregadorFWI } from '../utils/fwiDiario'
import IndicadorLegado from '../components/IndicadorLegado'
import { formatarValor, formatarProbabilidade, mensagemErro, mensagemEstado } from '../utils/disponibilidade'

function DetalheRegiao({ darkMode, onToggleDark }) {
    const { id } = useParams()
    const navigate = useNavigate()
    const [detalhes, setDetalhes] = useState(null)
    const [risco, setRisco] = useState(null)
    const [loading, setLoading] = useState(true)
    const [tecnicoAberto, setTecnicoAberto] = useState(false)
    const [erroDados, setErroDados] = useState('')
    const [erroRisco, setErroRisco] = useState('')
    const [fwiDiario, setFWIDiario] = useState(null)
    const [idDados, setIdDados] = useState(null)

    useEffect(() => {
        let ativo = true
        let ultimoPedido = 0
        const diario = criarCarregadorFWI({ idRegiao: id, consultar: getFWIDiario,
            consultarHistorico: getHistoricoFWIDiario, onChange: setFWIDiario })
        const carregarDados = async (inicial = true) => {
            const pedido = ++ultimoPedido
            diario.carregar()
            if (inicial) { setLoading(true); setDetalhes(null); setRisco(null) }
            const [det, risc] = await Promise.allSettled([getDetalhesRegiao(id), getRiscoRegiao(id)])
            if (!ativo || pedido !== ultimoPedido) return
            setDetalhes(det.status === 'fulfilled' ? det.value : null)
            setRisco(risc.status === 'fulfilled' ? risc.value : null)
            setErroDados(det.status === 'rejected' ? mensagemErro(det.reason) : '')
            setErroRisco(risc.status === 'rejected' ? mensagemErro(risc.reason) : '')
            setIdDados(id)
            setLoading(false)
        }
        carregarDados()
        const intervalo = setInterval(() => carregarDados(false), 60000)
        return () => { ativo = false; diario.cancelar(); clearInterval(intervalo) }
    }, [id])

    if (loading || idDados !== id) return (
        <div style={{ height: '100vh', overflowY: 'auto', padding: '24px', color: 'var(--texto-secondary)' }}>
            A carregar detalhes...
            <PainelFWIDiario estado={fwiDiario} idRegiao={id} />
        </div>
    )

    if (!detalhes || detalhes.erro) return (
        <div style={{ height: '100vh', overflowY: 'auto', padding: '24px' }}>
            <div role="status" style={{ color: 'var(--texto-secondary)' }}>{erroDados || detalhes?.erro || 'Dados indisponíveis'}</div>
            <button onClick={() => navigate('/')} style={{ padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#639922', color: 'white', cursor: 'pointer' }}>
                Voltar ao Dashboard
            </button>
            <PainelFWIDiario estado={fwiDiario} idRegiao={id} />
        </div>
    )


    return (
        <div className="app">
            <Navbar
                dataObservacao={detalhes.atual?.data_hora}
                estado={erroRisco ? 'erro_fonte' : detalhes.estado}
                localidade={detalhes.regiao?.nome}
                darkMode={darkMode}
                onToggleDark={onToggleDark}
            />
            {mensagemEstado(detalhes.estado) && <div role="status">{mensagemEstado(detalhes.estado)}</div>}
            {(erroRisco || mensagemEstado(risco?.estado)) && <div role="status">{erroRisco || mensagemEstado(risco?.estado)}</div>}
            {risco?.ml?.estado && risco.ml.estado !== 'ok' && <div role="status">{risco.ml.mensagem}</div>}

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

                    </div>

                    <PainelFWIDiario estado={fwiDiario} idRegiao={id} localidade={detalhes.regiao?.nome} />

                    {/* ML e Previsão */}
                    {risco && (
                        <div style={{ background: 'var(--cinza-card)', borderRadius: '12px', padding: '20px', border: '0.5px solid var(--cinza-borda)' }}>
                            <h2 style={{ fontSize: '14px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '16px' }}>
                                Indicadores ML (experimentais)
                            </h2>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                <div style={{ background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '11px', color: 'var(--texto-tertiary)', marginBottom: '4px' }}>Pontuação ML</div>
                                    <div style={{ fontSize: '24px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                                        {formatarProbabilidade(risco.ml?.probabilidade_incendio)}
                                    </div>
                                    <p>Não representa a probabilidade de um incêndio futuro.</p>
                                </div>
                            </div>
                        </div>
                    )}

                    <IndicadorLegado valor={detalhes.atual?.fwi} tendencia={detalhes.tendencia} />

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
                                            {['Data/Hora', 'Temp (°C)', 'Humidade (%)', 'Vento (km/h)', 'Índice legado (experimental)'].map(h => (
                                                <th key={h} style={{ padding: '8px', textAlign: 'left', color: 'var(--texto-tertiary)', fontWeight: '500', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {detalhes.historico.map((h, i) => {
                                            return (
                                                <tr key={i}>
                                                    <td style={{ padding: '8px', color: 'var(--texto-secondary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>
                                                        {new Date(h.data_hora).toLocaleString('pt-PT')}
                                                    </td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.temperatura ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.humidade ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{h.velocidade_vento ?? '--'}</td>
                                                    <td style={{ padding: '8px', color: 'var(--texto-primary)', borderBottom: '0.5px solid var(--cinza-borda)' }}>{formatarValor(h.fwi)}</td>

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
