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

export default api