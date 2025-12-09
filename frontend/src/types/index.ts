export interface Agent {
    id: string;
    name: string;
    port: number;
    status: 'online' | 'busy' | 'offline';
    icon: string;
    color: string;
    description: string;
}

export interface Incident {
    id: string;
    type: 'fire' | 'medical' | 'crime' | 'gas_leak' | 'flood' | 'fight' | 'crowd_rush' | 'power_outage' | 'traffic_accident' | 'earthquake';
    location: {
        lat: number;
        lng: number;
        address: string;
    };
    severity: 'minor' | 'moderate' | 'major' | 'critical';
    status: 'reported' | 'dispatched' | 'responding' | 'resolved';
    timestamp: Date;
    description: string;
}

export interface AgentEvent {
    id: string;
    agentId: string;
    agentName: string;
    action: string;
    details: string;
    timestamp: Date;
    type: 'delegation' | 'tool_call' | 'notification' | 'response';
}

export interface Message {
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    agentName?: string;
}

export const AGENTS: Agent[] = [
    { id: 'human-intake', name: 'Human Intake', port: 9001, status: 'online', icon: '📞', color: '#64748b', description: 'Emergency call intake' },
    { id: 'dispatch', name: 'Dispatch', port: 9002, status: 'online', icon: '📡', color: '#8b5cf6', description: 'Incident routing' },
    { id: 'fire-chief', name: 'Fire Chief', port: 9003, status: 'online', icon: '🔥', color: '#ef4444', description: 'Fire response commander' },
    { id: 'civic-alert', name: 'Civic Alert', port: 9004, status: 'online', icon: '📢', color: '#a855f7', description: 'Public warnings' },
    { id: 'medical', name: 'Medical', port: 9005, status: 'online', icon: '🏥', color: '#22c55e', description: 'Medical response' },
    { id: 'police-chief', name: 'Police Chief', port: 9006, status: 'online', icon: '🚔', color: '#3b82f6', description: 'Law enforcement' },
    { id: 'utility', name: 'Utility', port: 9007, status: 'online', icon: '⚡', color: '#f59e0b', description: 'Infrastructure control' },
    { id: 'iot-sensor', name: 'IoT Sensor', port: 9008, status: 'online', icon: '📊', color: '#06b6d4', description: 'Sensor monitoring' },
    { id: 'camera', name: 'Camera', port: 9009, status: 'online', icon: '📹', color: '#ec4899', description: 'Visual surveillance' },
];

export const INCIDENT_TYPES = [
    { value: 'fire', label: '🔥 Fire', color: '#ef4444' },
    { value: 'medical', label: '🏥 Medical Emergency', color: '#22c55e' },
    { value: 'crime', label: '🚔 Crime/Security', color: '#3b82f6' },
    { value: 'gas_leak', label: '💨 Gas Leak', color: '#f59e0b' },
    { value: 'flood', label: '🌊 Flood', color: '#06b6d4' },
    { value: 'fight', label: '🥊 Fight/Violence', color: '#dc2626' },
    { value: 'crowd_rush', label: '👥 Crowd Rush', color: '#7c3aed' },
    { value: 'power_outage', label: '⚡ Power Outage', color: '#eab308' },
    { value: 'traffic_accident', label: '🚗 Traffic Accident', color: '#f97316' },
    { value: 'earthquake', label: '🌍 Earthquake', color: '#78716c' },
];

export const SEVERITY_LEVELS = [
    { value: 'minor', label: 'Minor', color: '#22c55e' },
    { value: 'moderate', label: 'Moderate', color: '#f59e0b' },
    { value: 'major', label: 'Major', color: '#f97316' },
    { value: 'critical', label: 'Critical', color: '#ef4444' },
];
