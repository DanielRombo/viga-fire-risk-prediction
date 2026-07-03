import api from './api'

export const login = async (email, senha) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', senha)
    const response = await api.post('/auth/login', formData)
    const { access_token, utilizador } = response.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('utilizador', JSON.stringify(utilizador))
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    return utilizador
}

export const registar = async (nome, email, senha) => {
    const response = await api.post('/auth/registar', { nome, email, senha })
    const { access_token, utilizador } = response.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('utilizador', JSON.stringify(utilizador))
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    return utilizador
}

export const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('utilizador')
    delete api.defaults.headers.common['Authorization']
}

export const getUtilizadorAtual = () => {
    const user = localStorage.getItem('utilizador')
    return user ? JSON.parse(user) : null
}

export const getToken = () => localStorage.getItem('token')

export const isAutenticado = () => !!getToken()

// Adiciona token automaticamente se existir
const token = getToken()
if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}