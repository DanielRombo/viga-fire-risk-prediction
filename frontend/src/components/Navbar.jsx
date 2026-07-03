import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { logout, getUtilizadorAtual } from '../services/auth'

function Navbar({ risco, localidade, darkMode, onToggleDark }) {
    const [hora, setHora] = useState('')

    useEffect(() => {
        const atualizar = () => {
            const agora = new Date()
            const h = String(agora.getHours()).padStart(2, '0')
            const m = String(agora.getMinutes()).padStart(2, '0')
            const s = String(agora.getSeconds()).padStart(2, '0')
            setHora(`${h}:${m}:${s}`)
        }
        atualizar()
        const interval = setInterval(atualizar, 1000)
        return () => clearInterval(interval)
    }, [])

    const corRisco = () => {
        switch (risco) {
            case 'Muito Alto': return { bg: '#FCEBEB', color: '#A32D2D' }
            case 'Alto': return { bg: '#FCEBEB', color: '#A32D2D' }
            case 'Medio': return { bg: '#FAEEDA', color: '#854F0B' }
            case 'Baixo': return { bg: '#EAF3DE', color: '#3B6D11' }
            default: return { bg: '#f0f0ec', color: '#666660' }
        }
    }

    const { bg, color } = corRisco()

    const navigate = useNavigate()
    const utilizador = getUtilizadorAtual()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <nav style={{
            background: 'var(--cinza-card)',
            borderBottom: '0.5px solid var(--cinza-borda)',
            padding: '0 20px',
            height: '52px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            flexShrink: 0
        }}>
            <span style={{ fontSize: '18px', fontWeight: '500', color: '#3B6D11', letterSpacing: '1px' }}>
                VIGA
            </span>

            <div style={{ width: '0.5px', height: '24px', background: 'var(--cinza-borda)' }} />

            <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>
                <strong style={{ color: 'var(--texto-primary)' }}>{localidade || 'Portugal'}</strong>
            </span>

            <div style={{ width: '0.5px', height: '24px', background: 'var(--cinza-borda)' }} />

            <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>
                Última atualização: <strong style={{ color: 'var(--texto-primary)' }}>{hora}</strong>
            </span>

            {risco && (
                <span style={{
                    padding: '4px 10px', borderRadius: '99px',
                    fontSize: '11px', fontWeight: '500',
                    background: bg, color: color
                }}>
                    Risco {risco}
                </span>
            )}

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '12px', color: 'var(--texto-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {hora}
                </span>

                <span style={{ fontSize: '11px', color: 'var(--texto-secondary)' }}>
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#639922', display: 'inline-block', marginRight: '4px' }} />
                    Sistema ativo
                </span>

                {utilizador && (
                    <span style={{ fontSize: '12px', color: 'var(--texto-secondary)' }}>
                        {utilizador.nome}
                    </span>
                )}

                <button onClick={handleLogout} style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '4px 10px', borderRadius: '99px',
                    border: '0.5px solid var(--cinza-borda)',
                    background: 'var(--cinza-fundo)',
                    cursor: 'pointer', fontSize: '11px',
                    color: 'var(--texto-secondary)'
                }}>
                    Sair
                </button>

                <button onClick={onToggleDark} style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '4px 10px', borderRadius: '99px',
                    border: '0.5px solid var(--cinza-borda)',
                    background: 'var(--cinza-fundo)',
                    cursor: 'pointer', fontSize: '11px',
                    color: 'var(--texto-secondary)'
                }}>
                    {darkMode ? <Moon size={13} /> : <Sun size={13} />}
                    {darkMode ? 'Escuro' : 'Claro'}
                </button>
            </div>
        </nav>
    )
}

export default Navbar