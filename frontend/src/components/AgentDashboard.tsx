import { Agent } from '../types';

interface AgentCardProps {
    agent: Agent;
    isOnline: boolean;
    onClick: () => void;
    isSelected: boolean;
}

export function AgentCard({ agent, isOnline, onClick, isSelected }: AgentCardProps) {
    return (
        <button
            onClick={onClick}
            className={`glass-card p-4 w-full text-left transition-all duration-300 hover:scale-[1.02] ${isSelected ? 'ring-2 ring-white/30' : ''
                }`}
        >
            <div className="flex items-center gap-3">
                <span className="text-2xl">{agent.icon}</span>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-sm truncate">{agent.name}</h3>
                        <span
                            className={`w-2 h-2 rounded-full ${isOnline ? 'status-online' : 'status-offline'
                                }`}
                        />
                    </div>
                    <p className="text-xs text-gray-400 truncate">{agent.description}</p>
                </div>
            </div>
        </button>
    );
}

interface AgentDashboardProps {
    agents: Agent[];
    healthStatuses: Record<string, boolean>;
    selectedAgent: Agent | null;
    onSelectAgent: (agent: Agent) => void;
}

export function AgentDashboard({
    agents,
    healthStatuses,
    selectedAgent,
    onSelectAgent,
}: AgentDashboardProps) {
    const onlineCount = Object.values(healthStatuses).filter(Boolean).length;

    return (
        <div className="glass-card p-4 h-full flex flex-col">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold">🤖 Agents</h2>
                <span className="text-sm text-gray-400">
                    {onlineCount}/{agents.length} online
                </span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-2">
                {agents.map((agent) => (
                    <AgentCard
                        key={agent.id}
                        agent={agent}
                        isOnline={healthStatuses[agent.port] ?? false}
                        onClick={() => onSelectAgent(agent)}
                        isSelected={selectedAgent?.id === agent.id}
                    />
                ))}
            </div>
        </div>
    );
}
