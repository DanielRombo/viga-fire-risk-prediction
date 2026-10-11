import { Sun, Moon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { logout, getUtilizadorAtual } from '../services/auth'
import { formatarDataObservacao, estadoDados } from '../utils/disponibilidade'

function Navbar({ localidade, darkMode, onToggleDark, dataObservacao, estado }) {

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
                Meteorologia atualizada em: <strong style={{ color: 'var(--texto-primary)' }}>{formatarDataObservacao(dataObservacao)}</strong>
            </span>

            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '11px', color: 'var(--texto-secondary)' }}>
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: estado === 'ok' ? '#639922' : '#888888', display: 'inline-block', marginRight: '4px' }} />
                    {estadoDados(estado)}
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
