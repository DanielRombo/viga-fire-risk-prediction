import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import Sidebar from '../components/Sidebar'
import MapaInterativo from '../components/MapaInterativo'
import PainelAlertas from '../components/PainelAlertas'
import PainelML from '../components/PainelML'
import { getRiscoRegiao } from '../services/api'
import { mensagemErro, mensagemEstado } from '../utils/disponibilidade'

function Dashboard({ darkMode, onToggleDark }) {
    const [risco, setRisco] = useState(null)
    const [loading, setLoading] = useState(true)
    const [camadasAtivas, setCamadasAtivas] = useState(['focos', 'fwi'])
    const [regiaoSelecionada, setRegiaoSelecionada] = useState(null)
    const [erroDados, setErroDados] = useState('')
    const [dadosFocos, setDadosFocos] = useState({ estado: 'carregando', total: null })

    useEffect(() => {
        carregarDados()
        const interval = setInterval(carregarDados, 60000)
        return () => clearInterval(interval)
    }, [])

    const carregarDados = async () => {
        try {
            const dados = await getRiscoRegiao(1)
            setRisco(dados)
            setErroDados('')
        } catch (err) {
            setRisco(null)
            setErroDados(mensagemErro(err))
            console.error('Erro ao carregar dados:', err)
        } finally {
            setLoading(false)
        }
    }

    const toggleCamada = (id) => {
        setCamadasAtivas(prev =>
            prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
        )
    }

    if (loading) return (
        <div style={{
            height: '100vh', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            color: 'var(--texto-secondary)', fontSize: '14px'
        }}>
            A carregar dados...
        </div>
    )

    return (
        <div className="app">
            <Navbar
                risco={risco?.fwi?.nivel_risco}
                localidade={regiaoSelecionada?.nome || 'Portugal'}
                darkMode={darkMode}
                onToggleDark={onToggleDark}
            />
            {(erroDados || mensagemEstado(risco?.estado)) && <div role="status">{erroDados || mensagemEstado(risco?.estado)}</div>}
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                <Sidebar
                    risco={risco}
                    dados={risco?.dados_meteorologicos}
                    onRegiaoSelecionada={setRegiaoSelecionada}
                    dadosFocos={dadosFocos}
                />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <MapaInterativo
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
