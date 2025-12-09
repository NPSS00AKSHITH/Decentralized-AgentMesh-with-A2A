import { useState, useRef, useEffect } from 'react';
import { Agent, Message } from '../types';
import { Send, Bot, User } from 'lucide-react';

interface ChatPanelProps {
    agent: Agent | null;
    messages: Message[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
}

export function ChatPanel({ agent, messages, onSendMessage, isLoading }: ChatPanelProps) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading || !agent) return;
        onSendMessage(input);
        setInput('');
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    if (!agent) {
        return (
            <div className="glass-card p-6 h-full flex items-center justify-center">
                <div className="text-center text-gray-400">
                    <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select an agent to start chatting</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card p-4 h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-white/10">
                <span className="text-2xl">{agent.icon}</span>
                <div>
                    <h2 className="font-bold">{agent.name}</h2>
                    <p className="text-xs text-gray-400">Port {agent.port}</p>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <p className="text-sm">Start a conversation with {agent.name}</p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {msg.role === 'agent' && (
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-sm">
                                    {agent.icon}
                                </div>
                            )}
                            <div
                                className={`max-w-[80%] rounded-2xl px-4 py-2 ${msg.role === 'user'
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
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                            {agent.icon}
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
            <form onSubmit={handleSubmit} className="flex gap-2 pt-4 border-t border-white/10">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Message ${agent.name}...`}
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
            </form>
        </div>
    );
}
