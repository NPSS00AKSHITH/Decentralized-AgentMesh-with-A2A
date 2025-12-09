import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import { Icon, LatLngExpression } from 'leaflet';
import { Incident } from '../types';

// Custom marker icons
const createIcon = (color: string) => new Icon({
    iconUrl: `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
      <circle cx="12" cy="12" r="10" fill="${color}" stroke="white" stroke-width="2"/>
      <circle cx="12" cy="12" r="4" fill="white"/>
    </svg>
  `)}`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
});

const INCIDENT_ICONS: Record<string, Icon> = {
    fire: createIcon('#ef4444'),
    medical: createIcon('#22c55e'),
    crime: createIcon('#3b82f6'),
    gas_leak: createIcon('#f59e0b'),
    flood: createIcon('#06b6d4'),
};

interface MapClickHandlerProps {
    onMapClick: (lat: number, lng: number) => void;
}

function MapClickHandler({ onMapClick }: MapClickHandlerProps) {
    useMapEvents({
        click: (e) => {
            onMapClick(e.latlng.lat, e.latlng.lng);
        },
    });
    return null;
}

interface IncidentMapProps {
    incidents: Incident[];
    onMapClick?: (lat: number, lng: number) => void;
    center?: LatLngExpression;
}

export function IncidentMap({
    incidents,
    onMapClick,
    center = [17.7245, 83.3063] // Default: Visakhapatnam
}: IncidentMapProps) {
    return (
        <div className="glass-card p-2 h-full">
            <MapContainer
                center={center}
                zoom={12}
                className="h-full w-full rounded-xl"
                style={{ minHeight: '400px' }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {onMapClick && <MapClickHandler onMapClick={onMapClick} />}

                {incidents.map((incident) => (
                    <Marker
                        key={incident.id}
                        position={[incident.location.lat, incident.location.lng]}
                        icon={INCIDENT_ICONS[incident.type] || INCIDENT_ICONS.fire}
                    >
                        <Popup>
                            <div className="text-sm">
                                <h3 className="font-bold capitalize">{incident.type.replace('_', ' ')}</h3>
                                <p className="text-gray-600">{incident.location.address}</p>
                                <p className="text-xs mt-1">
                                    <span className="font-semibold">Severity:</span> {incident.severity}
                                </p>
                                <p className="text-xs">
                                    <span className="font-semibold">Status:</span> {incident.status}
                                </p>
                            </div>
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
}
