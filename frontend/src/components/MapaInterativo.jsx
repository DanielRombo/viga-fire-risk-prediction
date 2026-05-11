import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
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

function MapaInterativo({ camadasAtivas, onToggleCamada }) {
    return (
        <div style={{ flex: 1, position: 'relative', minHeight: '320px' }}>
            <MapContainer
                center={[39.5, -8.0]}
                zoom={6}
                style={{ width: '100%', height: '100%' }}
                zoomControl={true}
            >
                <TileLayer
                    attribution='&copy; OpenStreetMap contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Marker position={[38.72, -9.14]}>
                    <Popup>Lisboa — Risco Muito Alto</Popup>
                </Marker>
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