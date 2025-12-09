import { AgentEvent } from '../types';
import { Activity } from 'lucide-react';

interface LiveFeedProps {
    events: AgentEvent[];
}

export function LiveFeed({ events }: LiveFeedProps) {
    const getEventIcon = (type: AgentEvent['type']) => {
        switch (type) {
            case 'delegation': return '🔄';
            case 'tool_call': return '🔧';
            case 'notification': return '📣';
            case 'response': return '💬';
            default: return '📝';
        }
    };

    const getEventColor = (type: AgentEvent['type']) => {
        switch (type) {
            case 'delegation': return 'border-purple-500';
            case 'tool_call': return 'border-blue-500';
            case 'notification': return 'border-yellow-500';
            case 'response': return 'border-green-500';
            default: return 'border-gray-500';
        }
    };

    return (
        <div className="glass-card p-4 h-full flex flex-col">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-green-500" />
                Live Feed
                {events.length > 0 && (
                    <span className="ml-auto text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full pulse-glow">
                        LIVE
                    </span>
                )}
            </h2>

            <div className="flex-1 overflow-y-auto space-y-3">
                {events.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <p className="text-sm">No events yet</p>
                        <p className="text-xs mt-1">Submit an incident to see real-time updates</p>
                    </div>
                ) : (
                    events.map((event) => (
                        <div
                            key={event.id}
                            className={`bg-white/5 rounded-lg p-3 border-l-4 ${getEventColor(event.type)} animate-in slide-in-from-right duration-300`}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span>{getEventIcon(event.type)}</span>
                                <span className="font-semibold text-sm">{event.agentName}</span>
                                <span className="text-xs text-gray-500 ml-auto">
                                    {event.timestamp.toLocaleTimeString()}
                                </span>
                            </div>
                            <p className="text-sm text-gray-300">{event.action}</p>
                            {event.details && (
                                <p className="text-xs text-gray-500 mt-1">{event.details}</p>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
