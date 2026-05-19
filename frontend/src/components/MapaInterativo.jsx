import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { getFocosIncendio, getRiscoRegiao } from '../services/api'
import { GeoJSON } from 'react-leaflet'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const iconeBase = {
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
}

const iconeFogo = L.divIcon({
    html: '<div style="font-size:22px;line-height:1">🔥</div>',
    className: '',
    ...iconeBase
})

const iconeRegiao = L.divIcon({
    html: '<div style="font-size:18px;line-height:1">📍</div>',
    className: '',
    ...iconeBase
})

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

function MapaInterativo({ camadasAtivas, onToggleCamada, regiaoSelecionada }) {
    const [focos, setFocos] = useState([])
    const [riscosCidades, setRiscosCidades] = useState([])

    useEffect(() => {
        carregarFocos()
        const interval = setInterval(carregarFocos, 300000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        if (camadasAtivas.includes('fwi') || camadasAtivas.includes('temperatura') || camadasAtivas.includes('vento') || camadasAtivas.includes('humidade')) {
            carregarRiscos()
        }
    }, [camadasAtivas])

    const carregarFocos = async () => {
        try {
            const dados = await getFocosIncendio()
            setFocos(dados.focos || [])
        } catch (err) {
            console.error('Erro ao carregar focos:', err)
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

    const [geoData, setGeoData] = useState(null)

    useEffect(() => {
        fetch('/portugal_distritos.json')
            .then(r => r.json())
            .then(data => setGeoData(data))
            .catch(err => console.error('Erro ao carregar GeoJSON:', err))
    }, [])

    return (
        <div style={{ flex: 1, position: 'relative', minHeight: '320px' }}>
            <MapContainer
                center={[39.5, -8.0]}
                zoom={6}
                style={{ width: '100%', height: '100%' }}
                zoomControl={true}
            >
                {camadasAtivas.includes('satelite') ? (
                    <TileLayer
                        attribution='Tiles &copy; Esri'
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                ) : (
                    <TileLayer
                        attribution='&copy; OpenStreetMap contributors'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                )}

                <CentrarMapa regiao={regiaoSelecionada} />

                {camadasAtivas.includes('fwi') && geoData && (
                    <GeoJSON
                        key={riscosCidades.map(c => c.risco?.fwi?.nivel_risco).join(',')}
                        data={geoData}
                        style={(feature) => {
                            const nome = feature.properties.name
                            const cidade = riscosCidades.find(c =>
                                nome?.toLowerCase().includes(c.nome.toLowerCase()) ||
                                c.nome.toLowerCase().includes(nome?.toLowerCase())
                            )
                            const nivel = cidade?.risco?.fwi?.nivel_risco
                            return {
                                fillColor: corFWI(nivel),
                                fillOpacity: nivel ? 0.5 : 0.1,
                                color: 'white',
                                weight: 1
                            }
                        }}
                        onEachFeature={(feature, layer) => {
                            const nome = feature.properties.name
                            const cidade = riscosCidades.find(c =>
                                nome?.toLowerCase().includes(c.nome.toLowerCase()) ||
                                c.nome.toLowerCase().includes(nome?.toLowerCase())
                            )
                            if (cidade?.risco) {
                                layer.bindPopup(`
                    <strong>${nome}</strong><br/>
                    FWI: ${cidade.risco?.fwi?.fwi}<br/>
                    Risco: ${cidade.risco?.fwi?.nivel_risco}
                `)
                            }
                        }}
                    />
                )}

                <Marker position={[38.72, -9.14]} icon={iconeRegiao}>
                    <Popup>
                        <strong>Lisboa</strong><br />
                        Risco monitorizado
                    </Popup>
                </Marker>

                {camadasAtivas.includes('focos') && focos.map((foco, i) => (
                    <Marker key={i} position={[foco.latitude, foco.longitude]} icon={iconeFogo}>
                        <Popup>
                            <strong>Foco ativo</strong><br />
                            Lat: {foco.latitude}<br />
                            Lon: {foco.longitude}<br />
                            Data: {foco.data}<br />
                            Fonte: {foco.fonte}
                        </Popup>
                    </Marker>
                ))}

                {camadasAtivas.includes('fwi') && riscosCidades.map(cidade => (
                    <CircleMarker
                        key={`fwi-${cidade.id}`}
                        center={[cidade.lat, cidade.lon]}
                        radius={14}
                        fillColor={corFWI(cidade.risco?.fwi?.nivel_risco)}
                        color="white"
                        weight={2}
                        fillOpacity={0.85}
                    >
                        <Popup>
                            <strong>{cidade.nome}</strong><br />
                            FWI: {cidade.risco?.fwi?.fwi}<br />
                            Risco: {cidade.risco?.fwi?.nivel_risco}<br />
                            ML: {cidade.risco?.ml?.nivel_risco_ml}
                        </Popup>
                    </CircleMarker>
                ))}

                {camadasAtivas.includes('temperatura') && riscosCidades.map(cidade => (
                    <CircleMarker
                        key={`temp-${cidade.id}`}
                        center={[cidade.lat, cidade.lon]}
                        radius={14}
                        fillColor={cidade.risco?.dados_meteorologicos?.temperatura > 30 ? '#E24B4A' : cidade.risco?.dados_meteorologicos?.temperatura > 20 ? '#BA7517' : '#639922'}
                        color="white"
                        weight={2}
                        fillOpacity={0.85}
                    >
                        <Popup>
                            <strong>{cidade.nome}</strong><br />
                            Temperatura: {cidade.risco?.dados_meteorologicos?.temperatura}°C
                        </Popup>
                    </CircleMarker>
                ))}

                {camadasAtivas.includes('vento') && riscosCidades.map(cidade => (
                    <CircleMarker
                        key={`vento-${cidade.id}`}
                        center={[cidade.lat, cidade.lon]}
                        radius={14}
                        fillColor={cidade.risco?.dados_meteorologicos?.velocidade_vento > 40 ? '#E24B4A' : cidade.risco?.dados_meteorologicos?.velocidade_vento > 20 ? '#BA7517' : '#639922'}
                        color="white"
                        weight={2}
                        fillOpacity={0.85}
                    >
                        <Popup>
                            <strong>{cidade.nome}</strong><br />
                            Vento: {cidade.risco?.dados_meteorologicos?.velocidade_vento} km/h
                        </Popup>
                    </CircleMarker>
                ))}

                {camadasAtivas.includes('humidade') && riscosCidades.map(cidade => (
                    <CircleMarker
                        key={`hum-${cidade.id}`}
                        center={[cidade.lat, cidade.lon]}
                        radius={14}
                        fillColor={cidade.risco?.dados_meteorologicos?.humidade < 25 ? '#E24B4A' : cidade.risco?.dados_meteorologicos?.humidade < 50 ? '#BA7517' : '#639922'}
                        color="white"
                        weight={2}
                        fillOpacity={0.85}
                    >
                        <Popup>
                            <strong>{cidade.nome}</strong><br />
                            Humidade: {cidade.risco?.dados_meteorologicos?.humidade}%
                        </Popup>
                    </CircleMarker>
                ))}

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
                        <div
                            onClick={() => onToggleCamada(c.id)}
                            style={{
                                width: '28px', height: '16px', borderRadius: '99px',
                                background: camadasAtivas.includes(c.id) ? '#639922' : 'var(--cinza-borda)',
                                position: 'relative', cursor: 'pointer', flexShrink: 0
                            }}
                        >
                            <div style={{
                                position: 'absolute', width: '12px', height: '12px',
                                borderRadius: '50%', background: 'white', top: '2px',
                                left: camadasAtivas.includes(c.id) ? '14px' : '2px',
                                transition: 'left 0.15s'
                            }} />
                        </div>
                        {c.label}
                        {c.id === 'focos' && focos.length > 0 && (
                            <span style={{
                                background: '#E24B4A', color: 'white',
                                borderRadius: '99px', fontSize: '9px',
                                padding: '1px 5px', fontWeight: '500'
                            }}>
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
                    Nível de risco
                </div>
                {legendaRisco.map(item => (
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