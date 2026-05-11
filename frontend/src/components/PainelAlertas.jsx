const alertas = [
    {
        id: 1,
        texto: 'Vento forte previsto — Castelo Branco',
        meta: 'há 5 min · Severidade alta',
        cor: '#E24B4A'
    },
    {
        id: 2,
        texto: 'Humidade crítica — Algarve interior',
        meta: 'há 18 min · Severidade média',
        cor: '#BA7517'
    },
    {
        id: 3,
        texto: 'Condições normais — Porto e Norte',
        meta: 'há 32 min · Informativo',
        cor: '#639922'
    },
]

function PainelAlertas() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{
                fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px'
            }}>
                Alertas prioritários
            </div>

            {alertas.map(alerta => (
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
            ))}
        </div>
    )
}

export default PainelAlertas