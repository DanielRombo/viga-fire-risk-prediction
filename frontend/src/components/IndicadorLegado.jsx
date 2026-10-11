import { formatarValor } from '../utils/disponibilidade'

export default function IndicadorLegado({ valor, tendencia }) {
    return <details style={{ color: 'var(--texto-secondary)', fontSize: '12px' }}>
        <summary>Índice legado (experimental): {formatarValor(valor)}</summary>
        <p>Indicador heurístico baseado na meteorologia atual; não é o FWI diário nem uma classificação oficial de risco.</p>
        {tendencia && <p>Tendência do índice legado: {tendencia}</p>}
    </details>
}
