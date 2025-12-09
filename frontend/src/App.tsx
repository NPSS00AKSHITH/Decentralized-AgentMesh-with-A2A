import { useState, useCallback } from 'react';
import { AgentDashboard } from './components/AgentDashboard';
import { IncidentReporter } from './components/IncidentReporter';
import { LiveFeed } from './components/LiveFeed';
import { IncidentMap } from './components/IncidentMap';
import { AgentChatTabs } from './components/AgentChatTabs';
import { AgentFlowDiagram } from './components/AgentFlowDiagram';
import { useAllAgentsHealth } from './hooks/useAgentConnection';
import { AGENTS, Incident, AgentEvent } from './types';
import { Shield, Zap, MessageCircle, Map, GitBranch } from 'lucide-react';

type ViewMode = 'dashboard' | 'chat' | 'flow';

function App() {
  const healthStatuses = useAllAgentsHealth();
  const [viewMode, setViewMode] = useState<ViewMode>('flow');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<string>('');

  const addEvent = useCallback((event: Omit<AgentEvent, 'id' | 'timestamp'>) => {
    setEvents(prev => [{
      ...event,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    }, ...prev].slice(0, 50));
  }, []);

  const handleIncidentSubmit = async (data: {
    type: string;
    types?: string[];
    location: string;
    severity: string;
    description: string;
  }) => {
    setIsLoading(true);
    setLastResponse('');

    const newIncident: Incident = {
      id: crypto.randomUUID(),
      type: data.type as Incident['type'],
      location: {
        lat: 17.7245 + (Math.random() - 0.5) * 0.1,
        lng: 83.3063 + (Math.random() - 0.5) * 0.1,
        address: data.location,
      },
      severity: data.severity as Incident['severity'],
      status: 'reported',
      timestamp: new Date(),
      description: data.description,
    };

    setIncidents(prev => [...prev, newIncident]);

    addEvent({
      agentId: 'human-intake',
      agentName: 'Human Intake',
      action: `New ${data.type} incident reported`,
      details: `Location: ${data.location}, Severity: ${data.severity}`,
      type: 'notification',
    });

    try {
      const dispatchPort = 9002;
      const response = await fetch(`http://localhost:${dispatchPort}/a2a`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'message/send',
          id: Date.now().toString(),
          params: {
            message: {
              role: 'user',
              parts: [{
                kind: 'text',
                text: `EMERGENCY REPORT: ${data.type} at ${data.location}. Severity: ${data.severity}. ${data.description}`
              }],
              messageId: crypto.randomUUID(),
            },
          },
        }),
      });

      const result = await response.json();
      console.log('A2A Response:', JSON.stringify(result, null, 2));

      addEvent({
        agentId: 'dispatch',
        agentName: 'Dispatch',
        action: 'Processing incident',
        details: 'Analyzing and routing to specialists...',
        type: 'tool_call',
      });

      // Helper function to extract text from message parts
      const extractTextFromParts = (parts: Array<{ kind?: string; type?: string; text?: string }>) => {
        return parts
          .filter((p) => p.kind === 'text' || p.type === 'text' || p.text)
          .map((p) => p.text || '')
          .filter(Boolean)
          .join('\n');
      };

      // Try multiple response formats from A2A SDK
      let responseText = '';

      // Format 1: result.result.parts (A2A SDK direct message with parts)
      if (result.result?.parts) {
        responseText = extractTextFromParts(result.result.parts);
      }
      // Format 2: result.result.message.parts (JSON-RPC wrapped)
      else if (result.result?.message?.parts) {
        responseText = extractTextFromParts(result.result.message.parts);
      }
      // Format 3: result.message.parts (direct message response)
      else if (result.message?.parts) {
        responseText = extractTextFromParts(result.message.parts);
      }
      // Format 3: result.result.artifacts (A2A task with artifacts)
      else if (result.result?.artifacts) {
        const artifacts = result.result.artifacts;
        const parts = artifacts.flatMap((a: { parts?: Array<{ text?: string }> }) => a.parts || []);
        responseText = extractTextFromParts(parts);
      }
      // Format 4: result.artifacts (direct artifacts)
      else if (result.artifacts) {
        const parts = result.artifacts.flatMap((a: { parts?: Array<{ text?: string }> }) => a.parts || []);
        responseText = extractTextFromParts(parts);
      }
      // Format 5: result.result.status.message (task status message)
      else if (result.result?.status?.message) {
        responseText = result.result.status.message;
      }
      // Format 6: result.status.message (direct status)
      else if (result.status?.message) {
        responseText = result.status.message;
      }
      // Format 7: Check for history/messages in the result
      else if (result.result?.history) {
        const lastMsg = result.result.history.filter((m: { role: string }) => m.role !== 'user').pop();
        if (lastMsg?.parts) {
          responseText = extractTextFromParts(lastMsg.parts);
        }
      }

      if (responseText) {
        setLastResponse(responseText);

        addEvent({
          agentId: 'dispatch',
          agentName: 'Dispatch',
          action: 'Response received',
          details: responseText.slice(0, 200) + (responseText.length > 200 ? '...' : ''),
          type: 'response',
        });

        setIncidents(prev => prev.map(i =>
          i.id === newIncident.id ? { ...i, status: 'dispatched' } : i
        ));
      } else {
        // Could not parse response - show raw for debugging
        const rawResponse = JSON.stringify(result, null, 2);
        setLastResponse(`⚠️ Received response but couldn't parse it:\n${rawResponse.slice(0, 500)}`);
        console.warn('Could not extract text from A2A response:', result);
      }
    } catch (error) {
      console.error('Failed to send to dispatch:', error);
      setLastResponse('❌ Error: Could not reach Dispatch agent. Make sure A2A servers are running.');
      addEvent({
        agentId: 'system',
        agentName: 'System',
        action: 'Connection failed',
        details: 'Could not reach Dispatch agent. Is it running?',
        type: 'notification',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const onlineCount = Object.values(healthStatuses).filter(Boolean).length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-lg border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">DDMS Control Center</h1>
              <p className="text-xs text-gray-400">Decentralized Disaster Management System</p>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-white/5 rounded-xl p-1">
            <button
              onClick={() => setViewMode('flow')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${viewMode === 'flow'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              <GitBranch className="w-4 h-4" />
              Flow
            </button>
            <button
              onClick={() => setViewMode('dashboard')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${viewMode === 'dashboard'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              <Map className="w-4 h-4" />
              Dashboard
            </button>
            <button
              onClick={() => setViewMode('chat')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${viewMode === 'chat'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white'
                }`}
            >
              <MessageCircle className="w-4 h-4" />
              Testing
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <Zap className="w-4 h-4 text-green-500" />
              <span className="text-gray-400">{onlineCount}/9 agents online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1800px] mx-auto p-6">
        {viewMode === 'flow' ? (
          /* Flow Diagram View */
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-8">
              <AgentFlowDiagram healthStatuses={healthStatuses} />
            </div>
            <div className="col-span-4 space-y-6">
              <IncidentReporter onSubmit={handleIncidentSubmit} isLoading={isLoading} />

              {/* Response Panel */}
              <div className="glass-card p-4">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-blue-400" />
                  Agent Response
                </h3>
                <div className="bg-black/30 rounded-xl p-4 min-h-[120px] max-h-[200px] overflow-y-auto">
                  {isLoading ? (
                    <div className="flex items-center gap-3 text-gray-400">
                      <span className="animate-spin">⏳</span>
                      <span>Waiting for agent response...</span>
                    </div>
                  ) : lastResponse ? (
                    <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans">
                      {lastResponse}
                    </pre>
                  ) : (
                    <p className="text-gray-500 text-sm">
                      Submit an incident to see agent responses here.
                    </p>
                  )}
                </div>
              </div>

              <div className="h-[300px]">
                <LiveFeed events={events} />
              </div>
            </div>
          </div>
        ) : viewMode === 'dashboard' ? (
          /* Dashboard View */
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-2">
              <AgentDashboard
                agents={AGENTS}
                healthStatuses={healthStatuses}
                selectedAgent={null}
                onSelectAgent={() => setViewMode('chat')}
              />
            </div>

            <div className="col-span-6 space-y-6">
              <div className="h-[400px]">
                <IncidentMap incidents={incidents} />
              </div>

              <div className="glass-card p-4">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <MessageCircle className="w-5 h-5 text-blue-400" />
                  Agent Response
                </h3>
                <div className="bg-black/30 rounded-xl p-4 min-h-[150px] max-h-[300px] overflow-y-auto">
                  {isLoading ? (
                    <div className="flex items-center gap-3 text-gray-400">
                      <span className="animate-spin">⏳</span>
                      <span>Waiting for agent response...</span>
                    </div>
                  ) : lastResponse ? (
                    <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans">
                      {lastResponse}
                    </pre>
                  ) : (
                    <p className="text-gray-500 text-sm">
                      Submit an incident to see agent responses here.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="col-span-4 space-y-6">
              <IncidentReporter onSubmit={handleIncidentSubmit} isLoading={isLoading} />
              <div className="h-[400px]">
                <LiveFeed events={events} />
              </div>
            </div>
          </div>
        ) : (
          /* Agent Testing View */
          <div className="grid grid-cols-12 gap-6 h-[calc(100vh-120px)]">
            <div className="col-span-8">
              <AgentChatTabs />
            </div>
            <div className="col-span-4 flex flex-col gap-6">
              <div className="glass-card p-4">
                <h3 className="font-bold mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-green-500" />
                  Agent Status
                </h3>
                <div className="space-y-2">
                  {AGENTS.map(agent => (
                    <div key={agent.id} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <span>{agent.icon}</span>
                        <span>{agent.name}</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">:{agent.port}</span>
                        <span className={`w-2 h-2 rounded-full ${healthStatuses[agent.port] ? 'bg-green-500' : 'bg-red-500'
                          }`} />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex-1 min-h-[400px]">
                <LiveFeed events={events} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
