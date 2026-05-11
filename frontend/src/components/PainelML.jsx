import { useState } from 'react'

const tooltips = {
    FWI: 'Fire Weather Index — índice global de risco de incêndio. Combina temperatura, humidade, vento e precipitação. Quanto maior, maior o risco.',
    FFMC: 'Fine Fuel Moisture Code — humidade dos combustíveis finos (folhas secas, erva). Valores altos indicam vegetação muito seca e facilmente inflamável.',
    ISI: 'Initial Spread Index — velocidade esperada de propagação do fogo, combinando o efeito do vento com a secura da vegetação fina.'
}

function FwiItem({ label, value }) {
    const [hover, setHover] = useState(false)

    return (
        <div
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            style={{
                flex: 1, background: 'var(--cinza-card)',
                borderRadius: '8px', padding: '6px 8px',
                textAlign: 'center', border: '0.5px solid var(--cinza-borda)',
                position: 'relative', cursor: 'help'
            }}
        >
            <div style={{ fontSize: '10px', color: 'var(--texto-tertiary)', textDecoration: 'underline dotted', textUnderlineOffset: '2px' }}>
                {label}
            </div>
            <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                {value ?? '--'}
            </div>
            {hover && (
                <div style={{
                    position: 'absolute', bottom: 'calc(100% + 8px)', left: '50%',
                    transform: 'translateX(-50%)', background: 'var(--cinza-card)',
                    border: '0.5px solid var(--cinza-borda)', borderRadius: '8px',
                    padding: '8px 10px', fontSize: '11px', color: 'var(--texto-secondary)',
                    whiteSpace: 'normal', textAlign: 'left', lineHeight: '1.5',
                    zIndex: 100, minWidth: '180px', pointerEvents: 'none'
                }}>
                    {tooltips[label]}
                </div>
            )}
        </div>
    )
}

function PainelML({ risco }) {
    const probabilidade = risco?.ml?.probabilidade_incendio
    const percentagem = probabilidade ? Math.round(probabilidade * 100) : 0

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{
                fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px'
            }}>
                Previsão ML + FWI
            </div>

            <div style={{
                background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '10px 12px'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>Nível de risco ML</span>
                    <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                        {risco?.ml?.nivel_risco_ml || '--'}
                    </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>Probabilidade</span>
                    <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                        {percentagem}%
                    </span>
                </div>

                <div style={{ height: '6px', borderRadius: '99px', background: 'var(--cinza-borda)', marginTop: '6px' }}>
                    <div style={{
                        height: '6px', borderRadius: '99px',
                        background: percentagem > 70 ? '#E24B4A' : percentagem > 50 ? '#BA7517' : '#639922',
                        width: `${percentagem}%`, transition: 'width 0.3s'
                    }} />
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <FwiItem label="FWI" value={risco?.fwi?.fwi} />
                    <FwiItem label="FFMC" value={risco?.fwi?.componentes?.ffmc} />
                    <FwiItem label="ISI" value={risco?.fwi?.componentes?.isi} />
                </div>
            </div>
        </div>
    )
}

export default PainelML