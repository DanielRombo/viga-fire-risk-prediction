import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, registar } from '../services/auth'

function Login() {
    const navigate = useNavigate()
    const [modo, setModo] = useState('login')
    const [nome, setNome] = useState('')
    const [email, setEmail] = useState('')
    const [senha, setSenha] = useState('')
    const [erro, setErro] = useState('')
    const [loading, setLoading] = useState(false)

    const submeter = async (e) => {
        e.preventDefault()
        setErro('')
        setLoading(true)
        try {
            if (modo === 'login') {
                await login(email, senha)
            } else {
                await registar(nome, email, senha)
            }
            navigate('/')
        } catch (err) {
            setErro(err.response?.data?.detail || 'Erro ao autenticar')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            height: '100vh', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            background: 'var(--cinza-fundo)'
        }}>
            <div style={{
                background: 'var(--cinza-card)',
                border: '0.5px solid var(--cinza-borda)',
                borderRadius: '16px', padding: '32px',
                width: '360px', display: 'flex',
                flexDirection: 'column', gap: '20px'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '24px', fontWeight: '500', color: '#3B6D11', letterSpacing: '2px' }}>
                        VIGA
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--texto-tertiary)', marginTop: '4px' }}>
                        Vigilância Inteligente e Gestão de Alertas
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                    {['login', 'registar'].map(m => (
                        <button key={m} onClick={() => setModo(m)} style={{
                            flex: 1, padding: '8px',
                            borderRadius: '8px', border: 'none',
                            background: modo === m ? '#639922' : 'var(--cinza-fundo)',
                            color: modo === m ? 'white' : 'var(--texto-secondary)',
                            cursor: 'pointer', fontSize: '13px',
                            fontWeight: modo === m ? '500' : '400'
                        }}>
                            {m === 'login' ? 'Entrar' : 'Registar'}
                        </button>
                    ))}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {modo === 'registar' && (
                        <input
                            type="text"
                            placeholder="Nome completo"
                            value={nome}
                            onChange={e => setNome(e.target.value)}
                            style={{
                                padding: '10px 12px', borderRadius: '8px',
                                border: '0.5px solid var(--cinza-borda)',
                                background: 'var(--cinza-fundo)', fontSize: '13px',
                                color: 'var(--texto-primary)', outline: 'none'
                            }}
                        />
                    )}
                    <input
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        style={{
                            padding: '10px 12px', borderRadius: '8px',
                            border: '0.5px solid var(--cinza-borda)',
                            background: 'var(--cinza-fundo)', fontSize: '13px',
                            color: 'var(--texto-primary)', outline: 'none'
                        }}
                    />
                    <input
                        type="password"
                        placeholder="Senha"
                        value={senha}
                        onChange={e => setSenha(e.target.value)}
                        style={{
                            padding: '10px 12px', borderRadius: '8px',
                            border: '0.5px solid var(--cinza-borda)',
                            background: 'var(--cinza-fundo)', fontSize: '13px',
                            color: 'var(--texto-primary)', outline: 'none'
                        }}
                    />
                </div>

                {erro && (
                    <div style={{
                        padding: '8px 12px', borderRadius: '8px',
                        background: '#FCEBEB', color: '#A32D2D',
                        fontSize: '12px'
                    }}>
                        {erro}
                    </div>
                )}

                <button
                    onClick={submeter}
                    disabled={loading}
                    style={{
                        padding: '10px', borderRadius: '8px',
                        border: 'none', background: '#639922',
                        color: 'white', cursor: loading ? 'not-allowed' : 'pointer',
                        fontSize: '13px', fontWeight: '500',
                        opacity: loading ? 0.7 : 1
                    }}
                >
                    {loading ? 'A carregar...' : modo === 'login' ? 'Entrar' : 'Criar conta'}
                </button>
            </div>
        </div>
    )
}

export default Login