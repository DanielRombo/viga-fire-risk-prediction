import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker, GeoJSON } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { getFocosIncendio, getRiscoRegiao } from '../services/api'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const iconeBase = { iconSize: [28, 28], iconAnchor: [14, 28], popupAnchor: [0, -28] }

const iconeFogo = L.divIcon({ html: '<div style="font-size:22px;line-height:1">🔥</div>', className: '', ...iconeBase })
const iconeRegiao = L.divIcon({ html: '<div style="font-size:18px;line-height:1">📍</div>', className: '', ...iconeBase })

const camadas = [
    { id: 'focos', label: 'Focos ativos' },
    { id: 'fwi', label: 'Risco FWI' },
    { id: 'temperatura', label: 'Temperatura' },
    { id: 'vento', label: 'Vento' },
    { id: 'humidade', label: 'Humidade' },
    { id: 'satelite', label: 'Satélite' },
]

const legendaRisco = [
    { cor: '#639922', label: 'Baixo' },
    { cor: '#BA7517', label: 'Médio' },
    { cor: '#E24B4A', label: 'Alto' },
    { cor: '#791F1F', label: 'Muito Alto' },
]

const CIDADES = [
    { id: 1, nome: "Lisboa", lat: 38.7169, lon: -9.1399 },
    { id: 3261, nome: "Porto", lat: 41.1579, lon: -8.6291 },
    { id: 3262, nome: "Braga", lat: 41.5503, lon: -8.42 },
    { id: 3263, nome: "Coimbra", lat: 40.2033, lon: -8.4103 },
    { id: 3264, nome: "Faro", lat: 37.0194, lon: -9.3322 },
    { id: 3265, nome: "Aveiro", lat: 40.6405, lon: -8.6538 },
    { id: 3266, nome: "Setubal", lat: 38.5244, lon: -8.8882 },
    { id: 3267, nome: "Viseu", lat: 40.6566, lon: -7.9122 },
    { id: 3268, nome: "Leiria", lat: 39.7436, lon: -8.8071 },
    { id: 3269, nome: "Evora", lat: 38.5714, lon: -7.9101 },
    { id: 3270, nome: "Castelo Branco", lat: 39.8194, lon: -7.4906 },
    { id: 3272, nome: "Beja", lat: 38.015, lon: -7.8653 },
    { id: 3271, nome: "Guarda", lat: 40.5374, lon: -7.265 },
    { id: 3273, nome: "Portalegre", lat: 39.2967, lon: -7.4286 },
    { id: 3274, nome: "Santarem", lat: 39.2369, lon: -8.6881 },
    { id: 3275, nome: "Braganca", lat: 41.8061, lon: -6.7588 },
    { id: 3276, nome: "Vila Real", lat: 41.1006, lon: -7.7457 },
    { id: 3277, nome: "Viana do Castelo", lat: 41.6918, lon: -8.8341 },
    { id: 3278, nome: "Funchal", lat: 32.6669, lon: -16.9241 },
    { id: 3279, nome: "Ponta Delgada", lat: 37.7412, lon: -25.6756 },
]

function CentrarMapa({ regiao }) {
    const map = useMap()
    useEffect(() => {
        if (regiao?.latitude && regiao?.longitude) {
            map.flyTo([regiao.latitude, regiao.longitude], 12, { duration: 1.5 })
        }
    }, [regiao, map])
    return null
}

const corFWI = (nivel) => {
    switch (nivel) {
        case 'Muito Alto': return '#791F1F'
        case 'Alto': return '#E24B4A'
        case 'Medio': return '#BA7517'
        default: return '#639922'
    }
}

const corTemperatura = (temp) => {
    if (!temp) return '#cccccc'
    if (temp > 35) return '#791F1F'
    if (temp > 28) return '#E24B4A'
    if (temp > 20) return '#BA7517'
    if (temp > 12) return '#639922'
    return '#3B6D11'
}

const corVento = (vento) => {
    if (!vento) return '#cccccc'
    if (vento > 50) return '#791F1F'
    if (vento > 30) return '#E24B4A'
    if (vento > 15) return '#BA7517'
    return '#639922'
}

const corHumidade = (hum) => {
    if (!hum) return '#cccccc'
    if (hum < 20) return '#791F1F'
    if (hum < 35) return '#E24B4A'
    if (hum < 50) return '#BA7517'
    return '#639922'
}

const legendas = {
    fwi: [{ cor: '#639922', label: 'Baixo' }, { cor: '#BA7517', label: 'Médio' }, { cor: '#E24B4A', label: 'Alto' }, { cor: '#791F1F', label: 'Muito Alto' }],
    temperatura: [{ cor: '#3B6D11', label: '< 12°C' }, { cor: '#639922', label: '12-20°C' }, { cor: '#BA7517', label: '20-28°C' }, { cor: '#E24B4A', label: '28-35°C' }, { cor: '#791F1F', label: '> 35°C' }],
    vento: [{ cor: '#639922', label: '< 15 km/h' }, { cor: '#BA7517', label: '15-30 km/h' }, { cor: '#E24B4A', label: '30-50 km/h' }, { cor: '#791F1F', label: '> 50 km/h' }],
    humidade: [{ cor: '#791F1F', label: '< 20%' }, { cor: '#E24B4A', label: '20-35%' }, { cor: '#BA7517', label: '35-50%' }, { cor: '#639922', label: '> 50%' }],
}

function MapaInterativo({ camadasAtivas, onToggleCamada, regiaoSelecionada }) {
    const [focos, setFocos] = useState([])
    const [riscosCidades, setRiscosCidades] = useState([])
    const [geoData, setGeoData] = useState(null)

    useEffect(() => {
        carregarFocos()
        fetch('/portugal_distritos.json')
            .then(r => r.json())
            .then(data => setGeoData(data))
            .catch(err => console.error('Erro GeoJSON:', err))
        const interval = setInterval(carregarFocos, 300000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        const precisaCidades = ['fwi', 'temperatura', 'vento', 'humidade'].some(c => camadasAtivas.includes(c))
        if (precisaCidades && riscosCidades.length === 0) carregarRiscos()
    }, [camadasAtivas])

    const carregarFocos = async () => {
        try {
            const dados = await getFocosIncendio()
            setFocos(dados.focos || [])
        } catch (err) {
            console.error('Erro focos:', err)
        }
    }

    const carregarRiscos = async () => {
        const resultados = await Promise.allSettled(
            CIDADES.map(async cidade => {
                try {
                    const risco = await getRiscoRegiao(cidade.id)
                    return { ...cidade, risco }
                } catch {
                    return { ...cidade, risco: null }
                }
            })
        )
        setRiscosCidades(
            resultados
                .filter(r => r.status === 'fulfilled')
                .map(r => r.value)
                .filter(c => c.risco && !c.risco.erro)
        )
    }

    const normalizar = (str) => str?.toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim() || ""

    const encontrarCidade = (nomeDistrito) => {
        if (!nomeDistrito) return null
        const nomeNorm = normalizar(nomeDistrito)
        return riscosCidades.find(c => {
            const cidadeNorm = normalizar(c.nome)
            return nomeNorm === cidadeNorm ||
                nomeNorm.includes(cidadeNorm) ||
                cidadeNorm.includes(nomeNorm)
        })
    }

    const estiloGeoJSON = (camada) => (feature) => {
        const cidade = encontrarCidade(feature.properties.name)
        const dados = cidade?.risco?.dados_meteorologicos
        let cor = '#cccccc'
        let opacidade = cidade ? 0.5 : 0.1

        if (camada === 'fwi') cor = cidade ? corFWI(cidade.risco?.fwi?.nivel_risco) : '#cccccc'
        if (camada === 'temperatura') cor = corTemperatura(dados?.temperatura)
        if (camada === 'vento') cor = corVento(dados?.velocidade_vento)
        if (camada === 'humidade') cor = corHumidade(dados?.humidade)

        return { fillColor: cor, fillOpacity: opacidade, color: 'white', weight: 1 }
    }

    const popupGeoJSON = (camada) => (feature, layer) => {
        const cidade = encontrarCidade(feature.properties.name)
        const dados = cidade?.risco?.dados_meteorologicos
        if (!cidade) return
        let conteudo = `<strong>${feature.properties.name}</strong><br/>`
        if (camada === 'fwi') conteudo += `FWI: ${cidade.risco?.fwi?.fwi}<br/>Risco: ${cidade.risco?.fwi?.nivel_risco}`
        if (camada === 'temperatura') conteudo += `Temperatura: ${dados?.temperatura}°C`
        if (camada === 'vento') conteudo += `Vento: ${dados?.velocidade_vento} km/h`
        if (camada === 'humidade') conteudo += `Humidade: ${dados?.humidade}%`
        layer.bindPopup(conteudo)
    }

    const legendaAtiva = camadasAtivas.find(c => ['fwi', 'temperatura', 'vento', 'humidade'].includes(c))

    return (
        <div style={{ flex: 1, position: 'relative', minHeight: '320px' }}>
            <MapContainer center={[39.5, -8.0]} zoom={6} style={{ width: '100%', height: '100%' }} zoomControl={true}>
                {camadasAtivas.includes('satelite') ? (
                    <TileLayer attribution='Tiles &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
                ) : (
                    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                )}

                <CentrarMapa regiao={regiaoSelecionada} />

                <Marker position={[38.72, -9.14]} icon={iconeRegiao}>
                    <Popup><strong>Lisboa</strong><br />Risco monitorizado</Popup>
                </Marker>

                {camadasAtivas.includes('focos') && focos.map((foco, i) => (
                    <Marker key={i} position={[foco.latitude, foco.longitude]} icon={iconeFogo}>
                        <Popup>
                            <strong>Foco ativo</strong><br />
                            Lat: {foco.latitude}<br />Lon: {foco.longitude}<br />
                            Data: {foco.data}<br />Fonte: {foco.fonte}
                        </Popup>
                    </Marker>
                ))}

                {geoData && ['fwi', 'temperatura', 'vento', 'humidade'].map(camada =>
                    camadasAtivas.includes(camada) && (
                        <GeoJSON
                            key={`${camada}-${riscosCidades.length}`}
                            data={geoData}
                            style={estiloGeoJSON(camada)}
                            onEachFeature={popupGeoJSON(camada)}
                        />
                    )
                )}
            </MapContainer>

            <div style={{
                position: 'absolute', top: '12px', right: '12px',
                background: 'var(--cinza-card)', border: '0.5px solid var(--cinza-borda)',
                borderRadius: '8px', padding: '10px', zIndex: 1000,
                display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '140px'
            }}>
                <div style={{ fontSize: '10px', fontWeight: '500', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '2px' }}>
                    Camadas
                </div>
                {camadas.map(c => (
                    <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--texto-secondary)' }}>
                        <div onClick={() => onToggleCamada(c.id)} style={{
                            width: '28px', height: '16px', borderRadius: '99px',
                            background: camadasAtivas.includes(c.id) ? '#639922' : 'var(--cinza-borda)',
                            position: 'relative', cursor: 'pointer', flexShrink: 0
                        }}>
                            <div style={{
                                position: 'absolute', width: '12px', height: '12px',
                                borderRadius: '50%', background: 'white', top: '2px',
                                left: camadasAtivas.includes(c.id) ? '14px' : '2px', transition: 'left 0.15s'
                            }} />
                        </div>
                        {c.label}
                        {c.id === 'focos' && focos.length > 0 && (
                            <span style={{ background: '#E24B4A', color: 'white', borderRadius: '99px', fontSize: '9px', padding: '1px 5px', fontWeight: '500' }}>
                                {focos.length}
                            </span>
                        )}
                    </div>
                ))}
            </div>

            <div style={{
                position: 'absolute', bottom: '12px', left: '12px',
                background: 'var(--cinza-card)', border: '0.5px solid var(--cinza-borda)',
                borderRadius: '8px', padding: '8px 10px', zIndex: 1000
            }}>
                <div style={{ fontSize: '10px', color: 'var(--texto-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
                    {legendaAtiva === 'temperatura' ? 'Temperatura' : legendaAtiva === 'vento' ? 'Vento' : legendaAtiva === 'humidade' ? 'Humidade' : 'Nível de risco'}
                </div>
                {(legendas[legendaAtiva] || legendaRisco).map(item => (
                    <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--texto-secondary)', marginBottom: '4px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.cor, flexShrink: 0 }} />
                        {item.label}
                    </div>
                ))}
            </div>
        </div>
    )
}

export default MapaInterativo