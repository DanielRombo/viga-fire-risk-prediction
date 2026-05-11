function Sidebar({ risco, dados }) {
    const corRiscoNacional = () => {
        switch (risco?.fwi?.nivel_risco) {
            case 'Muito Alto': return { bg: '#FCEBEB', border: '#F09595', label: '#A32D2D', value: '#501313' }
            case 'Alto': return { bg: '#FCEBEB', border: '#F7C1C1', label: '#A32D2D', value: '#791F1F' }
            case 'Medio': return { bg: '#FAEEDA', border: '#FAC775', label: '#854F0B', value: '#633806' }
            default: return { bg: '#EAF3DE', border: '#C0DD97', label: '#3B6D11', value: '#27500A' }
        }
    }

    const cores = corRiscoNacional()

    return (
        <aside style={{
            background: 'var(--cinza-card)',
            borderRight: '0.5px solid var(--cinza-borda)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            overflowY: 'auto',
            width: '260px',
            flexShrink: 0
        }}>
            <div style={{
                borderRadius: '12px',
                background: cores.bg,
                border: `0.5px solid ${cores.border}`,
                padding: '14px',
                textAlign: 'center'
            }}>
                <div style={{ fontSize: '10px', color: cores.label, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
                    Risco nacional
                </div>
                <div style={{ fontSize: '20px', fontWeight: '500', color: cores.value }}>
                    {risco?.fwi?.nivel_risco || 'Sem dados'}
                </div>
                <div style={{ fontSize: '11px', color: cores.label, marginTop: '2px' }}>
                    FWI {risco?.fwi?.fwi || '--'} — ML {risco?.ml?.probabilidade_incendio ? Math.round(risco.ml.probabilidade_incendio * 100) + '%' : '--'}
                </div>
            </div>

            <div style={{ fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: '4px' }}>
                Pesquisa
            </div>

            <input
                type="text"
                placeholder="Pesquisar localidade..."
                style={{
                    width: '100%', padding: '7px 10px',
                    borderRadius: '8px', border: '0.5px solid var(--cinza-borda)',
                    background: 'var(--cinza-fundo)', fontSize: '12px',
                    color: 'var(--texto-primary)', outline: 'none'
                }}
            />

            <select style={{
                width: '100%', padding: '7px 10px',
                borderRadius: '8px', border: '0.5px solid var(--cinza-borda)',
                background: 'var(--cinza-fundo)', fontSize: '12px',
                color: 'var(--texto-primary)'
            }}>
                <option>Todos os distritos</option>
                <option>Lisboa</option>
                <option>Porto</option>
                <option>Faro</option>
                <option>Castelo Branco</option>
            </select>

            <div style={{ fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: '4px' }}>
                Condições atuais
            </div>

            {[
                { icon: '🌡', label: 'Temperatura', value: dados?.temperatura, unit: '°C', bg: '#FFF3CD' },
                { icon: '💧', label: 'Humidade', value: dados?.humidade, unit: '%', bg: '#E3F2FD' },
                { icon: '💨', label: 'Vento', value: dados?.velocidade_vento, unit: 'km/h', bg: '#E8F5E9' },
                { icon: '🔥', label: 'Focos ativos', value: 0, unit: 'hoje', bg: '#FCE4EC' },
            ].map((item, i) => (
                <div key={i} style={{
                    background: 'var(--cinza-fundo)',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                }}>
                    <div style={{
                        width: '32px', height: '32px', borderRadius: '8px',
                        background: item.bg, display: 'flex',
                        alignItems: 'center', justifyContent: 'center', fontSize: '14px'
                    }}>
                        {item.icon}
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', color: 'var(--texto-secondary)' }}>{item.label}</div>
                        <div style={{ fontSize: '15px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                            {item.value ?? '--'} <span style={{ fontSize: '11px', color: 'var(--texto-tertiary)' }}>{item.unit}</span>
                        </div>
                    </div>
                </div>
            ))}
        </aside>
    )
}

export default Sidebar