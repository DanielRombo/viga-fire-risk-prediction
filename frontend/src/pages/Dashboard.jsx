import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import Sidebar from '../components/Sidebar'
import MapaInterativo from '../components/MapaInterativo'
import PainelAlertas from '../components/PainelAlertas'
import PainelML from '../components/PainelML'
import { getRiscoRegiao, getRegioesMonitorizadas } from '../services/api'
import { mensagemErro, mensagemEstado } from '../utils/disponibilidade'

function Dashboard({ darkMode, onToggleDark }) {
    const [risco, setRisco] = useState(null)
    const [loading, setLoading] = useState(true)
    const [camadasAtivas, setCamadasAtivas] = useState(['focos', 'fwi'])
    const [regiaoSelecionada, setRegiaoSelecionada] = useState(null)
    const [erroDados, setErroDados] = useState('')
    const [dadosFocos, setDadosFocos] = useState({ estado: 'carregando', total: null })
    const [regioes, setRegioes] = useState([])
    const idRegiao = regiaoSelecionada?.id_regiao ?? regioes.find(r => r.nome === 'Lisboa')?.id_regiao

    useEffect(() => {
        let ativo = true
        getRegioesMonitorizadas().then(dados => { if (ativo) setRegioes(dados.regioes) })
            .catch(erro => { if (ativo) { setErroDados(mensagemErro(erro)); setLoading(false) } })
        return () => { ativo = false }
    }, [])
    const localidade = regiaoSelecionada?.nome || 'Lisboa'

    useEffect(() => {
        let ativo = true
        let ultimoPedido = 0
        if (idRegiao == null) return
        const carregarDados = async () => {
            const pedido = ++ultimoPedido
            try {
                const dados = await getRiscoRegiao(idRegiao)
                if (!ativo || pedido !== ultimoPedido) return
                setRisco(dados)
                setErroDados('')
            } catch (err) {
                if (!ativo || pedido !== ultimoPedido) return
                setRisco(null)
                setErroDados(mensagemErro(err))
                console.error('Erro ao carregar dados:', err)
            } finally {
                if (ativo && pedido === ultimoPedido) setLoading(false)
            }
        }
        carregarDados()
        const interval = setInterval(carregarDados, 60000)
        return () => {
            ativo = false
            clearInterval(interval)
        }
    }, [idRegiao])

    const selecionarRegiao = (regiao) => {
        if (regiao.id_regiao !== idRegiao) {
            setRisco(null)
            setErroDados('')
            setLoading(true)
        }
        setRegiaoSelecionada(regiao)
    }

    const toggleCamada = (id) => {
        setCamadasAtivas(prev =>
            prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
        )
    }

    return (
        <div className="app">
            <Navbar
                dataObservacao={risco?.data_hora}
                estado={loading ? 'carregando' : erroDados ? 'erro_fonte' : risco?.estado}
                risco={risco?.fwi?.nivel_risco}
                localidade={localidade}
                darkMode={darkMode}
                onToggleDark={onToggleDark}
            />
            {(loading || erroDados || mensagemEstado(risco?.estado)) && <div role="status">{loading ? 'A carregar dados...' : erroDados || mensagemEstado(risco?.estado)}</div>}
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                <Sidebar
                    risco={risco}
                    dados={risco?.estado === 'ok' ? risco.dados_meteorologicos : null}
                    onRegiaoSelecionada={selecionarRegiao}
                    localidade={localidade}
                    dadosFocos={dadosFocos}
                />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <MapaInterativo
                        regioes={regioes}
                        onRegiaoSelecionada={selecionarRegiao}
                        camadasAtivas={camadasAtivas}
                        onToggleCamada={toggleCamada}
                        regiaoSelecionada={regiaoSelecionada}
                        onDadosFocos={setDadosFocos}
                    />
                    <div style={{
                        background: 'var(--cinza-card)',
                        borderTop: '0.5px solid var(--cinza-borda)',
                        padding: '10px 16px',
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '12px',
                        maxHeight: '180px',
                        flexShrink: 0
                    }}>
                        <PainelAlertas />
                        <PainelML risco={risco} />
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
