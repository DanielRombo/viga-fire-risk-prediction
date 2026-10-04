import { apresentacaoFWI, componentesFWI, formatarDataFWI, formatarIndiceFWI } from '../utils/fwiDiario'
import { formatarDataObservacao } from '../utils/disponibilidade'
import './PainelFWIDiario.css'

export default function PainelFWIDiario({ estado, idRegiao, localidade, compacto = false }) {
    const atual = estado && String(estado.idRegiao) === String(idRegiao) ? estado : null
    const carregando = idRegiao != null && (!atual || atual.carregando)
    const dados = atual?.dados
    const apresentacao = apresentacaoFWI(dados)
    const titulo = `FWI diário${localidade ? ` — ${localidade}` : ''}`
    return <section className={`painel-fwi-diario${compacto ? ' compacto' : ''}`} aria-label={titulo} aria-busy={carregando}>
        <h2>{titulo}</h2>
        <div role="status">{carregando ? 'A carregar FWI diário…' : atual?.erro ? 'Erro da fonte' : apresentacao.estado}</div>
        <div className="valor-fwi-diario" data-testid="valor-fwi-diario">{formatarIndiceFWI(dados?.fwi)}</div>
        <div>Data de referência: <strong>{formatarDataFWI(dados?.data_referencia)}</strong></div>
        <p>{apresentacao.operacional ? 'Operacional estabelecido' : 'Não operacional — valor técnico, quando disponível.'}</p>
        {!carregando && <p role="status">{atual?.erro || dados?.mensagem || 'FWI diário indisponível.'}</p>}
        {!compacto && <>
            <div className="indices-fwi-diario">
                {componentesFWI.map(k => <div key={k}><span>{k.toUpperCase()}</span><strong>{formatarIndiceFWI(dados?.[k])}</strong></div>)}
            </div>
            <dl>
                {[
                    ['Instante de referência', formatarDataObservacao(dados?.instante_referencia_utc)],
                    ['Calculado em', formatarDataObservacao(dados?.calculado_em)],
                    ['Origem', dados?.origem || 'Indisponível'], ['Método', dados?.metodo || 'Indisponível'],
                    ['Versão', dados?.versao || 'Indisponível'], ['Versão xclim', dados?.versao_xclim || 'Indisponível'],
                    ['Variante', dados?.variante || 'Indisponível'], ['Inicialização', apresentacao.inicializacao],
                    ['Série', dados?.serie === 'operacional' ? 'Série operacional' : dados?.serie === 'reconstrucao' ? 'Reconstrução histórica' : 'Indisponível'],
                    ['Revisão', dados?.revisao == null ? 'Não aplicável' : `${dados.revisao} — ${dados.revisao_ativa === true ? 'ativa' : 'não ativa'}`],
                ].map(([label, valor]) => <div key={label}><dt>{label}</dt><dd>{valor}</dd></div>)}
            </dl>
            <p>Valor numérico sem classificação de risco nesta fase.</p>
            <h3>Histórico FWI diário</h3>
            <p>Até 30 dias, na mesma série e revisão do resultado apresentado.</p>
            {carregando || atual?.carregandoHistorico ? <p role="status">A carregar histórico FWI diário…</p>
                : atual?.erroHistorico || atual?.erro ? <p role="status">{atual.erroHistorico || 'Histórico FWI diário indisponível.'}</p>
                    : atual?.historico?.length ? <div className="historico-fwi-diario"><table>
                        <thead><tr>{['Data de referência', 'FWI diário', 'Estado', 'Operacional'].map(h => <th key={h}>{h}</th>)}</tr></thead>
                        <tbody>{atual.historico.map(r => {
                            const p = apresentacaoFWI(r)
                            return <tr key={`${r.serie}-${r.revisao}-${r.data_referencia}`}>
                                <td>{formatarDataFWI(r.data_referencia)}</td><td>{formatarIndiceFWI(r.fwi)}</td>
                                <td>{p.estado}</td><td>{p.operacional ? 'Sim' : 'Não'}</td>
                            </tr>
                        })}</tbody>
                    </table></div> : <p>Sem histórico diário disponível.</p>}
        </>}
    </section>
}
