import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
})

export const getRiscoRegiao = async (idRegiao) => {
    const response = await api.get(`/risco/${idRegiao}`)
    return response.data
}

export const getMeteorologia = async (latitude, longitude) => {
    const response = await api.get('/meteorologia', {
        params: { latitude, longitude }
    })
    return response.data
}

export const getRegioes = async () => {
    const response = await api.get('/regioes/concelhos')
    return response.data
}

export const getFocosIncendio = async () => {
    const response = await api.get('/incendios/focos')
    return response.data
}

export const getAlertas = async () => {
    const response = await api.get('/alertas')
    return response.data
}

export const pesquisarRegioes = async (q) => {
    const response = await api.get('/regioes/pesquisa', { params: { q } })
    return response.data
}

export const getDetalhesRegiao = async (idRegiao) => {
    const response = await api.get(`/regioes/${idRegiao}/detalhes`)
    return response.data
}

export const getDistritos = async () => {
    const response = await api.get('/regioes/distritos')
    return response.data
}

export const forcarAtualizacao = async () => {
    const response = await api.post('/meteorologia/atualizar-agora')
    return response.data
}

export default api