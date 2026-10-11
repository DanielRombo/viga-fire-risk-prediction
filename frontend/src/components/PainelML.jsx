import { formatarProbabilidade, percentagemDisponivel } from '../utils/disponibilidade'
import IndicadorLegado from './IndicadorLegado'

function PainelML({ risco }) {
    const probabilidade = risco?.ml?.probabilidade_incendio
    const percentagem = percentagemDisponivel(probabilidade)

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {risco?.ml?.estado && risco.ml.estado !== 'ok' && <div role="status">{risco.ml.mensagem}</div>}
            <div style={{
                fontSize: '11px', fontWeight: '500', color: 'var(--texto-tertiary)',
                textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px'
            }}>
                Indicadores ML (experimentais)
            </div>

            <div style={{
                background: 'var(--cinza-fundo)', borderRadius: '8px', padding: '10px 12px'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>Classe do modelo</span>
                    <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                        {risco?.ml?.nivel_risco_ml || 'Indisponível'}
                    </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>Pontuação ML</span>
                    <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--texto-primary)' }}>
                        {formatarProbabilidade(probabilidade)}
                    </span>
                </div>

                <div style={{ height: '6px', borderRadius: '99px', background: 'var(--cinza-borda)', marginTop: '6px' }}>
                    {percentagem !== null && <div style={{
                        height: '6px', borderRadius: '99px',
                        background: '#888888',
                        width: `${percentagem}%`, transition: 'width 0.3s'
                    }} />}
                </div>

                <p style={{ fontSize: '11px' }}>Não representa a probabilidade de um incêndio futuro.</p>
            </div>
            <IndicadorLegado valor={risco?.fwi?.fwi} />
        </div>
    )
}

export default PainelML
