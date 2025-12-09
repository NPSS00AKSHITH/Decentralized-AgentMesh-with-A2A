import { useState } from 'react';
import { AGENTS } from '../types';

interface AgentNode {
    id: string;
    name: string;
    icon: string;
    type: 'input' | 'orchestrator' | 'specialist' | 'output';
    x: number;
    y: number;
    color: string;
}

interface Connection {
    from: string;
    to: string;
    label?: string;
    type: 'primary' | 'failover';
}

const NODES: AgentNode[] = [
    // Input Layer
    { id: 'iot-sensor', name: 'IoT Sensor', icon: '📊', type: 'input', x: 80, y: 80, color: '#06b6d4' },
    { id: 'camera', name: 'Camera', icon: '📹', type: 'input', x: 80, y: 180, color: '#ec4899' },
    { id: 'human-intake', name: 'Human Intake', icon: '📞', type: 'input', x: 80, y: 280, color: '#64748b' },

    // Orchestrator
    { id: 'dispatch', name: 'Dispatch', icon: '📡', type: 'orchestrator', x: 300, y: 180, color: '#8b5cf6' },

    // Specialists
    { id: 'fire-chief', name: 'Fire Chief', icon: '🔥', type: 'specialist', x: 520, y: 60, color: '#ef4444' },
    { id: 'medical', name: 'Medical', icon: '🏥', type: 'specialist', x: 520, y: 140, color: '#22c55e' },
    { id: 'police-chief', name: 'Police Chief', icon: '🚔', type: 'specialist', x: 520, y: 220, color: '#3b82f6' },
    { id: 'utility', name: 'Utility', icon: '⚡', type: 'specialist', x: 520, y: 300, color: '#f59e0b' },

    // Output
    { id: 'civic-alert', name: 'Civic Alert', icon: '📢', type: 'output', x: 720, y: 180, color: '#a855f7' },
];

const CONNECTIONS: Connection[] = [
    // ===== PRIMARY PATHS =====

    // Input Layer -> Dispatch (Primary flow)
    { from: 'iot-sensor', to: 'dispatch', type: 'primary' },
    { from: 'camera', to: 'dispatch', type: 'primary' },
    { from: 'human-intake', to: 'dispatch', type: 'primary' },

    // Dispatch -> Specialists (Routing)
    { from: 'dispatch', to: 'fire-chief', label: 'fire/hazmat', type: 'primary' },
    { from: 'dispatch', to: 'medical', label: 'medical', type: 'primary' },
    { from: 'dispatch', to: 'police-chief', label: 'security', type: 'primary' },
    { from: 'dispatch', to: 'utility', label: 'infrastructure', type: 'primary' },

    // Specialists -> Civic Alert (Public Warnings)
    { from: 'fire-chief', to: 'civic-alert', label: 'evacuation', type: 'primary' },
    { from: 'medical', to: 'civic-alert', label: 'health alert', type: 'primary' },
    { from: 'police-chief', to: 'civic-alert', label: 'warning', type: 'primary' },
    { from: 'utility', to: 'civic-alert', label: 'outage', type: 'primary' },

    // ===== CROSS-DELEGATION (Specialist to Specialist) =====

    // Fire Chief delegates to Medical, Utility, and Police (for security/cordon)
    { from: 'fire-chief', to: 'medical', label: 'injuries', type: 'primary' },
    { from: 'fire-chief', to: 'utility', label: 'gas/power', type: 'primary' },
    { from: 'fire-chief', to: 'police-chief', label: 'cordon/security', type: 'primary' },

    // Medical delegates to Fire, Utility, and Police (for security)
    { from: 'medical', to: 'fire-chief', label: 'hazmat', type: 'primary' },
    { from: 'medical', to: 'utility', label: 'infrastructure', type: 'primary' },
    { from: 'medical', to: 'police-chief', label: 'crowd control', type: 'primary' },

    // Police delegates to Fire, Medical, and Utility
    { from: 'police-chief', to: 'fire-chief', label: 'fire', type: 'primary' },
    { from: 'police-chief', to: 'medical', label: 'casualties', type: 'primary' },
    { from: 'police-chief', to: 'utility', label: 'shutoff', type: 'primary' },

    // Utility delegates to Fire and Medical
    { from: 'utility', to: 'fire-chief', label: 'explosion', type: 'primary' },
    { from: 'utility', to: 'medical', label: 'injuries', type: 'primary' },

    // ===== INPUT AGENT DIRECT PATHS =====

    // Camera delegates to Police (fight/crowd detection) - always enabled
    { from: 'camera', to: 'police-chief', label: 'fight/crowd', type: 'primary' },

    // Camera delegates to Fire (fire detection) - always enabled
    { from: 'camera', to: 'fire-chief', label: 'fire detected', type: 'primary' },

    // ===== FAILOVER PATHS (Dispatch bypass) =====

    // IoT Sensor failover (when Dispatch is down)
    { from: 'iot-sensor', to: 'fire-chief', label: 'fire/smoke', type: 'failover' },
    { from: 'iot-sensor', to: 'utility', label: 'gas leak', type: 'failover' },

    // Human Intake failover (panic mode / Dispatch unreachable)
    { from: 'human-intake', to: 'fire-chief', label: 'fire', type: 'failover' },
    { from: 'human-intake', to: 'medical', label: 'medical', type: 'failover' },
    { from: 'human-intake', to: 'police-chief', label: 'crime', type: 'failover' },
    { from: 'human-intake', to: 'utility', label: 'gas/power', type: 'failover' },

    // ===== CIVIC ALERT FAILOVER (Police PA System) =====
    // When Civic Alert Agent is unavailable, specialists use Police PA broadcast
    { from: 'fire-chief', to: 'police-chief', label: 'PA failover', type: 'failover' },
    { from: 'medical', to: 'police-chief', label: 'PA failover', type: 'failover' },
    { from: 'utility', to: 'police-chief', label: 'PA failover', type: 'failover' },
];

interface AgentFlowDiagramProps {
    healthStatuses: Record<number, boolean>;
}

export function AgentFlowDiagram({ healthStatuses }: AgentFlowDiagramProps) {
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [showFailover, setShowFailover] = useState(true);

    const getNodeStatus = (nodeId: string): boolean => {
        const agent = AGENTS.find(a => a.id === nodeId);
        if (agent) {
            return healthStatuses[agent.port] ?? false;
        }
        return false;
    };

    const getConnectionPath = (from: AgentNode, to: AgentNode): string => {
        const startX = from.x + 60;
        const startY = from.y + 25;
        const endX = to.x;
        const endY = to.y + 25;

        const midX = (startX + endX) / 2;

        return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
    };

    return (
        <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg">🔗 Decentralized Agent Mesh</h3>
                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={showFailover}
                        onChange={(e) => setShowFailover(e.target.checked)}
                        className="rounded"
                    />
                    Show Failover Paths
                </label>
            </div>

            <svg viewBox="0 0 820 380" className="w-full h-auto">
                {/* Background gradient */}
                <defs>
                    <linearGradient id="primaryGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.8" />
                    </linearGradient>
                    <linearGradient id="failoverGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.5" />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0.5" />
                    </linearGradient>
                </defs>

                {/* Layer Labels */}
                <text x="80" y="35" className="fill-gray-500 text-xs font-semibold">INPUT</text>
                <text x="280" y="35" className="fill-gray-500 text-xs font-semibold">ORCHESTRATOR</text>
                <text x="500" y="35" className="fill-gray-500 text-xs font-semibold">SPECIALISTS</text>
                <text x="700" y="35" className="fill-gray-500 text-xs font-semibold">OUTPUT</text>

                {/* Connections */}
                {CONNECTIONS.map((conn, idx) => {
                    const fromNode = NODES.find(n => n.id === conn.from);
                    const toNode = NODES.find(n => n.id === conn.to);
                    if (!fromNode || !toNode) return null;

                    if (conn.type === 'failover' && !showFailover) return null;

                    const isHighlighted = hoveredNode === conn.from || hoveredNode === conn.to;

                    return (
                        <path
                            key={idx}
                            d={getConnectionPath(fromNode, toNode)}
                            fill="none"
                            stroke={conn.type === 'failover' ? 'url(#failoverGradient)' : 'url(#primaryGradient)'}
                            strokeWidth={isHighlighted ? 3 : conn.type === 'failover' ? 1.5 : 2}
                            strokeDasharray={conn.type === 'failover' ? '5,5' : 'none'}
                            opacity={isHighlighted ? 1 : 0.6}
                            className="transition-all duration-300"
                        />
                    );
                })}

                {/* Nodes */}
                {NODES.map((node) => {
                    const isOnline = getNodeStatus(node.id);
                    const isHovered = hoveredNode === node.id;

                    return (
                        <g
                            key={node.id}
                            transform={`translate(${node.x}, ${node.y})`}
                            onMouseEnter={() => setHoveredNode(node.id)}
                            onMouseLeave={() => setHoveredNode(null)}
                            className="cursor-pointer"
                        >
                            {/* Node background */}
                            <rect
                                x="0"
                                y="0"
                                width="120"
                                height="50"
                                rx="8"
                                fill={isHovered ? `${node.color}40` : '#1e293b'}
                                stroke={node.color}
                                strokeWidth={isHovered ? 2 : 1}
                                className="transition-all duration-200"
                            />

                            {/* Status indicator */}
                            <circle
                                cx="110"
                                cy="10"
                                r="5"
                                fill={isOnline ? '#22c55e' : '#ef4444'}
                                className={isOnline ? 'animate-pulse' : ''}
                            />

                            {/* Icon */}
                            <text x="15" y="32" className="text-xl">{node.icon}</text>

                            {/* Name */}
                            <text x="45" y="30" className="fill-white text-xs font-medium">
                                {node.name}
                            </text>

                            {/* Type badge */}
                            <text x="45" y="42" className="fill-gray-500 text-[9px]">
                                {node.type.toUpperCase()}
                            </text>
                        </g>
                    );
                })}

                {/* Legend */}
                <g transform="translate(20, 340)">
                    <line x1="0" y1="10" x2="30" y2="10" stroke="url(#primaryGradient)" strokeWidth="2" />
                    <text x="40" y="14" className="fill-gray-400 text-xs">Primary Path</text>

                    <line x1="150" y1="10" x2="180" y2="10" stroke="url(#failoverGradient)" strokeWidth="2" strokeDasharray="5,5" />
                    <text x="190" y="14" className="fill-gray-400 text-xs">Failover Path</text>

                    <circle cx="320" cy="10" r="5" fill="#22c55e" />
                    <text x="330" y="14" className="fill-gray-400 text-xs">Online</text>

                    <circle cx="400" cy="10" r="5" fill="#ef4444" />
                    <text x="410" y="14" className="fill-gray-400 text-xs">Offline</text>
                </g>
            </svg>

            <p className="text-xs text-gray-500 mt-3 text-center">
                No single point of failure • Specialists cross-delegate (Fire↔Medical↔Utility) • Input agents can bypass Dispatch if down
            </p>
        </div>
    );
}
