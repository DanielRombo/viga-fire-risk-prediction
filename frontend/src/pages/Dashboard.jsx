import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import Sidebar from '../components/Sidebar'
import MapaInterativo from '../components/MapaInterativo'
import PainelAlertas from '../components/PainelAlertas'
import PainelML from '../components/PainelML'
import { getRiscoRegiao } from '../services/api'

function Dashboard({ darkMode, onToggleDark }) {
    const [risco, setRisco] = useState(null)
    const [loading, setLoading] = useState(true)
    const [camadasAtivas, setCamadasAtivas] = useState(['focos', 'fwi'])

    useEffect(() => {
        carregarDados()
        const interval = setInterval(carregarDados, 60000)
        return () => clearInterval(interval)
    }, [])

    const carregarDados = async () => {
        try {
            const dados = await getRiscoRegiao(1)
            setRisco(dados)
        } catch (err) {
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
                localidade="Lisboa"
                darkMode={darkMode}
                onToggleDark={onToggleDark}
            />
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                <Sidebar risco={risco} dados={risco?.dados_meteorologicos} />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <MapaInterativo camadasAtivas={camadasAtivas} onToggleCamada={toggleCamada} />
                    <div style={{
                        background: 'var(--cinza-card)',
                        borderTop: '0.5px solid var(--cinza-borda)',
                        padding: '12px 16px',
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '12px'
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