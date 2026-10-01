import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker, GeoJSON } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { getFocosIncendio, getRiscoRegiao } from '../services/api'
import { legendaRisco, obterApresentacaoRisco } from '../utils/risco'
import { numeroDisponivel, formatarValor, mensagemErro, mensagemEstado, formatarDataObservacao } from '../utils/disponibilidade'

import { encontrarRegiaoMapa } from '../utils/regioesMapa'

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

function CentrarMapa({ regiao }) {
    const map = useMap()
    useEffect(() => {
        if (regiao?.latitude && regiao?.longitude) {
            map.flyTo([regiao.latitude, regiao.longitude], 12, { duration: 1.5 })
        }
    }, [regiao, map])
    return null
}

const corTemperatura = (temp) => {
    if (!numeroDisponivel(temp)) return '#cccccc'
    if (temp > 35) return '#791F1F'
    if (temp > 28) return '#E24B4A'
    if (temp > 20) return '#BA7517'
    if (temp > 12) return '#639922'
    return '#3B6D11'
}

const corVento = (vento) => {
    if (!numeroDisponivel(vento)) return '#cccccc'
    if (vento > 50) return '#791F1F'
    if (vento > 30) return '#E24B4A'
    if (vento > 15) return '#BA7517'
    return '#639922'
}

const corHumidade = (hum) => {
    if (!numeroDisponivel(hum)) return '#cccccc'
    if (hum < 20) return '#791F1F'
    if (hum < 35) return '#E24B4A'
    if (hum < 50) return '#BA7517'
    return '#639922'
}

const legendas = {
    fwi: legendaRisco,
    temperatura: [{ cor: '#3B6D11', label: '< 12°C' }, { cor: '#639922', label: '12-20°C' }, { cor: '#BA7517', label: '20-28°C' }, { cor: '#E24B4A', label: '28-35°C' }, { cor: '#791F1F', label: '> 35°C' }],
    vento: [{ cor: '#639922', label: '< 15 km/h' }, { cor: '#BA7517', label: '15-30 km/h' }, { cor: '#E24B4A', label: '30-50 km/h' }, { cor: '#791F1F', label: '> 50 km/h' }],
    humidade: [{ cor: '#791F1F', label: '< 20%' }, { cor: '#E24B4A', label: '20-35%' }, { cor: '#BA7517', label: '35-50%' }, { cor: '#639922', label: '> 50%' }],
}

function MapaInterativo({ camadasAtivas, onToggleCamada, regiaoSelecionada, onDadosFocos, regioes = [], onRegiaoSelecionada }) {
    const [focos, setFocos] = useState([])
    const [estadoFocos, setEstadoFocos] = useState('carregando')
    const [erroFocos, setErroFocos] = useState('')
    const [riscosCidades, setRiscosCidades] = useState([])
    const [versaoDados, setVersaoDados] = useState(0)
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
        let ativo = true
        let pedido = 0
        const carregarRiscos = async () => {
            const atual = ++pedido
            const resultados = await Promise.all(regioes.map(async cidade => {
                try { return { ...cidade, risco: await getRiscoRegiao(cidade.id_regiao) } }
                catch (erro) { return { ...cidade, risco: { estado: 'erro_fonte' }, erro: mensagemErro(erro) } }
            }))
            if (ativo && atual === pedido) {
                setRiscosCidades(resultados)
                setVersaoDados(v => v + 1)
            }
        }
        carregarRiscos()
        const intervalo = setInterval(carregarRiscos, 60000)
        return () => { ativo = false; clearInterval(intervalo) }
    }, [regioes])

    const carregarFocos = async () => {
        try {
            const dados = await getFocosIncendio()
            if (!Array.isArray(dados.focos)) throw new Error('Resposta de focos inválida')
            setFocos(dados.focos)
            setEstadoFocos('ok')
            setErroFocos('')
            onDadosFocos?.({ estado: 'ok', total: dados.focos.length })
        } catch (err) {
            setFocos([])
            setEstadoFocos('erro_fonte')
            setErroFocos(mensagemErro(err))
            onDadosFocos?.({ estado: 'erro_fonte', total: null })
            console.error('Erro focos:', err)
        }
    }

    const encontrarCidade = nome => encontrarRegiaoMapa(riscosCidades, nome)

    const estiloGeoJSON = (camada) => (feature) => {
        const cidade = encontrarCidade(feature.properties.name)
        const dados = cidade?.risco?.estado === 'ok' ? cidade.risco.dados_meteorologicos : null
        let cor = '#cccccc'
        let opacidade = cidade ? 0.5 : 0.1

        if (camada === 'fwi') cor = obterApresentacaoRisco(cidade?.risco?.fwi?.nivel_risco).color
        if (camada === 'temperatura') cor = corTemperatura(dados?.temperatura)
        if (camada === 'vento') cor = corVento(dados?.velocidade_vento)
        if (camada === 'humidade') cor = corHumidade(dados?.humidade)

        return { fillColor: cor, fillOpacity: opacidade, color: 'white', weight: 1 }
    }

    const popupGeoJSON = (camada) => (feature, layer) => {
        const cidade = encontrarCidade(feature.properties.name)
        const dados = cidade?.risco?.estado === 'ok' ? cidade.risco.dados_meteorologicos : null
        let conteudo = `<strong>${feature.properties.name === 'Azores' ? 'Açores' : feature.properties.name}</strong><br/>`
        if (cidade) conteudo += `Observação em ${cidade.nome}<br/>Última atualização: ${formatarDataObservacao(cidade.risco?.data_hora)}<br/>`
        if (camada === 'fwi') conteudo += `FWI: ${cidade?.risco?.fwi?.fwi ?? '--'}<br/>Risco: ${obterApresentacaoRisco(cidade?.risco?.fwi?.nivel_risco).label}`
        if (camada === 'temperatura') conteudo += `Temperatura: ${formatarValor(dados?.temperatura)}${numeroDisponivel(dados?.temperatura) ? '°C' : ''}`
        if (camada === 'vento') conteudo += `Vento: ${formatarValor(dados?.velocidade_vento)}${numeroDisponivel(dados?.velocidade_vento) ? ' km/h' : ''}`
        if (camada === 'humidade') conteudo += `Humidade: ${formatarValor(dados?.humidade)}${numeroDisponivel(dados?.humidade) ? '%' : ''}`
        conteudo += `<br/>${cidade?.erro || mensagemEstado(cidade?.risco?.estado || 'sem_dados')}`
        layer.bindPopup(conteudo)
        if (cidade) layer.on('click', () => onRegiaoSelecionada?.(cidade))
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
                            key={`${camada}-${versaoDados}`}
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
                        {c.id === 'focos' && (
                            <span style={{ background: estadoFocos === 'ok' && focos.length > 0 ? '#E24B4A' : '#666666', color: 'white', borderRadius: '99px', fontSize: '9px', padding: '1px 5px', fontWeight: '500' }}>
                                {estadoFocos === 'ok' ? focos.length : 'Indisponível'}
                            </span>
                        )}
                    </div>
                ))}
                {estadoFocos !== 'ok' && <div role="status" style={{ maxWidth: '190px', fontSize: '11px' }}>{estadoFocos === 'carregando' ? 'A carregar focos…' : erroFocos}</div>}
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
