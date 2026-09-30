import { useState, useEffect } from 'react'
import { getAlertas } from '../services/api'
import { apresentarAlertas } from '../utils/disponibilidade'

function PainelAlertas() {
    const [resposta, setResposta] = useState(null)
    const [erro, setErro] = useState(false)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        carregarAlertas()
        const interval = setInterval(carregarAlertas, 60000)
        return () => clearInterval(interval)
    }, [])

    const carregarAlertas = async () => {
        try {
            const dados = await getAlertas()
            setResposta(dados)
            setErro(false)
        } catch (err) {
            setErro(true)
            setResposta(null)
            console.error('Erro ao carregar alertas:', err)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return (
        <div style={{ fontSize: '12px', color: 'var(--texto-tertiary)' }}>
            A carregar alertas...
        </div>
    )

    const { alertas, total, mensagem } = apresentarAlertas(resposta, erro)
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', overflow: 'hidden', height: '100%' }}>
            <div style={{
                fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0
            }}>
                Alertas prioritários ({total ?? 'Indisponível'})
            </div>

            <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                <div role="status" style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>{mensagem}</div>
                {alertas.length > 0 && (
                    alertas.map(alerta => (
                        <div key={alerta.id} style={{
                            display: 'flex', alignItems: 'flex-start', gap: '8px',
                            padding: '5px 8px', borderRadius: '6px',
                            border: '0.5px solid var(--cinza-borda)',
                            background: 'var(--cinza-fundo)', flexShrink: 0
                        }}>
                            <div style={{
                                width: '7px', height: '7px', borderRadius: '50%',
                                background: alerta.cor, flexShrink: 0, marginTop: '3px'
                            }} />
                            <div>
                                <div style={{ fontSize: '11px', color: 'var(--texto-primary)', lineHeight: '1.3' }}>
                                    {alerta.texto}
                                </div>
                                <div style={{ fontSize: '10px', color: 'var(--texto-tertiary)', marginTop: '1px' }}>
                                    {alerta.meta}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

export default PainelAlertas
