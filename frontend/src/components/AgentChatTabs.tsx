import { useState, useRef, useEffect as useReactEffect } from 'react';
import { Agent, Message, AGENTS } from '../types';
import { Send, Bot, User, X, MessageCircle } from 'lucide-react';

interface AgentChatTabsProps {
    onClose?: () => void;
}

export function AgentChatTabs({ onClose }: AgentChatTabsProps) {
    const [activeAgent, setActiveAgent] = useState<Agent>(AGENTS[2]); // Default to Fire Chief
    const [chatHistories, setChatHistories] = useState<Record<string, Message[]>>({});
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const messages = chatHistories[activeAgent.id] || [];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setChatHistories(prev => ({
            ...prev,
            [activeAgent.id]: [...(prev[activeAgent.id] || []), userMessage],
        }));

        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`http://localhost:${activeAgent.port}/a2a`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'message/send',
                    id: Date.now().toString(),
                    params: {
                        message: {
                            role: 'user',
                            parts: [{ kind: 'text', text: input }],
                            messageId: crypto.randomUUID(),
                        },
                    },
                }),
            });

            const result = await response.json();
            console.log('A2A Response:', JSON.stringify(result, null, 2));

            // Try multiple response formats
            let responseText = '';

            // Format 1: result.result.parts (A2A protocol format)
            if (result.result?.parts && Array.isArray(result.result.parts)) {
                responseText = result.result.parts
                    .filter((p: { kind?: string; type?: string }) => p.kind === 'text' || p.type === 'text')
                    .map((p: { text?: string }) => p.text || '')
                    .join('\n');
            }
            // Format 2: result.result.message.parts (alternative A2A)
            else if (result.result?.message?.parts) {
                responseText = result.result.message.parts
                    .filter((p: { kind?: string; type?: string }) => p.kind === 'text' || p.type === 'text')
                    .map((p: { text?: string }) => p.text || '')
                    .join('\n');
            }
            // Format 3: result.result.artifacts (alternative structure)
            else if (result.result?.artifacts) {
                responseText = result.result.artifacts
                    .filter((a: { parts?: Array<{ text?: string }> }) => a.parts)
                    .flatMap((a: { parts: Array<{ text?: string }> }) => a.parts)
                    .filter((p: { text?: string }) => p.text)
                    .map((p: { text?: string }) => p.text)
                    .join('\n');
            }
            // Format 4: Directly in result (some A2A implementations)
            else if (result.result?.text) {
                responseText = result.result.text;
            }
            // Format 5: Error in result
            else if (result.error) {
                responseText = `Error: ${result.error.message || JSON.stringify(result.error)}`;
            }

            if (responseText) {
                const agentMessage: Message = {
                    role: 'agent',
                    content: responseText,
                    timestamp: new Date(),
                    agentName: activeAgent.name,
                };

                setChatHistories(prev => ({
                    ...prev,
                    [activeAgent.id]: [...(prev[activeAgent.id] || []), agentMessage],
                }));
            } else {
                console.warn('Could not parse response:', result);
                // Show raw result if we can't parse it
                const agentMessage: Message = {
                    role: 'agent',
                    content: `⚠️ Response received but format unknown. Check console for details.\nRaw: ${JSON.stringify(result).slice(0, 200)}...`,
                    timestamp: new Date(),
                    agentName: activeAgent.name,
                };
                setChatHistories(prev => ({
                    ...prev,
                    [activeAgent.id]: [...(prev[activeAgent.id] || []), agentMessage],
                }));
            }
        } catch (error) {
            const errorMessage: Message = {
                role: 'agent',
                content: `❌ Error: Could not reach ${activeAgent.name}. Make sure the A2A server is running on port ${activeAgent.port}.`,
                timestamp: new Date(),
                agentName: activeAgent.name,
            };
            setChatHistories(prev => ({
                ...prev,
                [activeAgent.id]: [...(prev[activeAgent.id] || []), errorMessage],
            }));
        } finally {
            setIsLoading(false);
        }
    };

    useReactEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="glass-card h-full flex flex-col">
            {/* Header with close button */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <MessageCircle className="w-5 h-5 text-blue-400" />
                    <h2 className="font-bold">Agent Chat</h2>
                </div>
                {onClose && (
                    <button onClick={onClose} className="p-1 hover:bg-white/10 rounded">
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* Agent Tabs */}
            <div className="flex overflow-x-auto border-b border-white/10 bg-black/20">
                {AGENTS.map((agent) => {
                    const hasMessages = (chatHistories[agent.id]?.length || 0) > 0;
                    return (
                        <button
                            key={agent.id}
                            onClick={() => setActiveAgent(agent)}
                            className={`flex items-center gap-2 px-4 py-2 text-sm whitespace-nowrap transition-all border-b-2 ${activeAgent.id === agent.id
                                ? 'border-blue-500 bg-white/10 text-white'
                                : 'border-transparent text-gray-400 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            <span>{agent.icon}</span>
                            <span className="hidden sm:inline">{agent.name}</span>
                            {hasMessages && (
                                <span className="w-2 h-2 rounded-full bg-green-500" />
                            )}
                        </button>
                    );
                })}
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="text-center text-gray-500 py-12">
                        <span className="text-4xl mb-4 block">{activeAgent.icon}</span>
                        <p className="font-semibold">{activeAgent.name}</p>
                        <p className="text-sm mt-1">{activeAgent.description}</p>
                        <p className="text-xs mt-4 text-gray-600">
                            Port: {activeAgent.port} • Send a message to start testing
                        </p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {msg.role === 'agent' && (
                                <div
                                    className="w-8 h-8 rounded-full flex items-center justify-center text-lg"
                                    style={{ backgroundColor: `${activeAgent.color}30` }}
                                >
                                    {activeAgent.icon}
                                </div>
                            )}
                            <div
                                className={`max-w-[75%] rounded-2xl px-4 py-2 ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-white/10 text-gray-200'
                                    }`}
                            >
                                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                <p className="text-xs opacity-50 mt-1">
                                    {msg.timestamp.toLocaleTimeString()}
                                </p>
                            </div>
                            {msg.role === 'user' && (
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center">
                                    <User className="w-4 h-4" />
                                </div>
                            )}
                        </div>
                    ))
                )}
                {isLoading && (
                    <div className="flex gap-3 justify-start">
                        <div
                            className="w-8 h-8 rounded-full flex items-center justify-center"
                            style={{ backgroundColor: `${activeAgent.color}30` }}
                        >
                            {activeAgent.icon}
                        </div>
                        <div className="bg-white/10 rounded-2xl px-4 py-3">
                            <div className="flex gap-1">
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={`Message ${activeAgent.name}...`}
                        disabled={isLoading}
                        className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 rounded-xl transition-colors"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
                <p className="text-xs text-gray-500 mt-2 text-center">
                    Testing {activeAgent.name} on localhost:{activeAgent.port}
                </p>
            </form>
        </div>
    );
}
