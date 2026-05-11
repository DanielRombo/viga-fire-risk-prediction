import { useState, useEffect } from 'react'
import { getAlertas } from '../services/api'

function PainelAlertas() {
    const [alertas, setAlertas] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        carregarAlertas()
        const interval = setInterval(carregarAlertas, 60000)
        return () => clearInterval(interval)
    }, [])

    const carregarAlertas = async () => {
        try {
            const dados = await getAlertas()
            setAlertas(dados.alertas || [])
        } catch (err) {
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

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{
                fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px'
            }}>
                Alertas prioritários ({alertas.length})
            </div>

            {alertas.length === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>
                    Sem alertas ativos
                </div>
            ) : (
                alertas.map(alerta => (
                    <div key={alerta.id} style={{
                        display: 'flex', alignItems: 'flex-start', gap: '8px',
                        padding: '7px 10px', borderRadius: '8px',
                        border: '0.5px solid var(--cinza-borda)',
                        background: 'var(--cinza-fundo)'
                    }}>
                        <div style={{
                            width: '8px', height: '8px', borderRadius: '50%',
                            background: alerta.cor, flexShrink: 0, marginTop: '3px'
                        }} />
                        <div>
                            <div style={{ fontSize: '12px', color: 'var(--texto-primary)', lineHeight: '1.4' }}>
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
    )
}

export default PainelAlertas