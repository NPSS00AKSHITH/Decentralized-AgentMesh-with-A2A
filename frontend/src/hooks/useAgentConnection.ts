import { useState, useEffect, useCallback } from 'react';

interface UseAgentConnectionOptions {
    agentPort: number;
}

export function useAgentConnection({ agentPort }: UseAgentConnectionOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const checkHealth = useCallback(async () => {
        try {
            const response = await fetch(`http://localhost:${agentPort}/health`, {
                method: 'GET',
                mode: 'cors',
            });
            if (response.ok) {
                setIsConnected(true);
                return true;
            }
        } catch (error) {
            console.log(`Agent on port ${agentPort} not available`);
        }
        setIsConnected(false);
        return false;
    }, [agentPort]);

    const sendMessage = useCallback(async (message: string) => {
        setIsLoading(true);
        try {
            const response = await fetch(`http://localhost:${agentPort}/a2a`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'message/send',
                    id: Date.now().toString(),
                    params: {
                        message: {
                            role: 'user',
                            parts: [{ kind: 'text', text: message }],
                            messageId: crypto.randomUUID(),
                        },
                    },
                }),
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Failed to send message:', error);
            throw error;
        } finally {
            setIsLoading(false);
        }
    }, [agentPort]);

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 10000);
        return () => clearInterval(interval);
    }, [checkHealth]);

    return { isConnected, isLoading, sendMessage, checkHealth };
}

export function useAllAgentsHealth() {
    const [statuses, setStatuses] = useState<Record<number, boolean>>({});

    useEffect(() => {
        const ports = [9001, 9002, 9003, 9004, 9005, 9006, 9007, 9008, 9009];

        const checkAll = async () => {
            const results: Record<number, boolean> = {};
            await Promise.all(
                ports.map(async (port) => {
                    try {
                        const response = await fetch(`http://localhost:${port}/health`, { mode: 'cors' });
                        results[port] = response.ok;
                    } catch {
                        results[port] = false;
                    }
                })
            );
            setStatuses(results);
        };

        checkAll();
        const interval = setInterval(checkAll, 5000);
        return () => clearInterval(interval);
    }, []);

    return statuses;
}
