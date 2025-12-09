import { useState } from 'react';
import { INCIDENT_TYPES, SEVERITY_LEVELS } from '../types';
import { Send, MapPin, AlertTriangle } from 'lucide-react';

interface IncidentReporterProps {
    onSubmit: (incident: {
        type: string;
        types: string[];
        location: string;
        severity: string;
        description: string;
    }) => void;
    isLoading: boolean;
}

export function IncidentReporter({ onSubmit, isLoading }: IncidentReporterProps) {
    const [selectedTypes, setSelectedTypes] = useState<string[]>(['fire']);
    const [location, setLocation] = useState('');
    const [severity, setSeverity] = useState('moderate');
    const [description, setDescription] = useState('');

    const toggleType = (typeValue: string) => {
        setSelectedTypes(prev => {
            if (prev.includes(typeValue)) {
                // Don't allow deselecting if it's the only one selected
                if (prev.length === 1) return prev;
                return prev.filter(t => t !== typeValue);
            } else {
                return [...prev, typeValue];
            }
        });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!location.trim() || selectedTypes.length === 0) return;

        // Create combined type string for backwards compatibility
        const typeString = selectedTypes.join(' + ');

        onSubmit({
            type: typeString,
            types: selectedTypes,
            location,
            severity,
            description
        });
    };

    const getTypeColor = (typeValue: string): string => {
        const found = INCIDENT_TYPES.find(t => t.value === typeValue);
        return found?.color || '#6b7280';
    };

    return (
        <div className="glass-card p-4">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                Report Incident
                {selectedTypes.length > 1 && (
                    <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">
                        {selectedTypes.length} types selected
                    </span>
                )}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Incident Type - Multi-select */}
                <div>
                    <label className="block text-sm text-gray-400 mb-2">
                        Type(s) <span className="text-xs opacity-60">(select multiple)</span>
                    </label>
                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                        {INCIDENT_TYPES.map((t) => {
                            const isSelected = selectedTypes.includes(t.value);
                            return (
                                <button
                                    key={t.value}
                                    type="button"
                                    onClick={() => toggleType(t.value)}
                                    className={`p-2 rounded-lg text-sm transition-all flex items-center gap-1 ${isSelected
                                        ? 'ring-2 shadow-lg'
                                        : 'bg-white/5 hover:bg-white/10'
                                        }`}
                                    style={{
                                        backgroundColor: isSelected ? `${t.color}30` : undefined,
                                        boxShadow: isSelected ? `0 0 0 2px ${t.color}` : undefined,
                                    }}
                                >
                                    {isSelected && <span className="text-xs">✓</span>}
                                    {t.label}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Selected Types Preview */}
                {selectedTypes.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {selectedTypes.map(type => {
                            const typeInfo = INCIDENT_TYPES.find(t => t.value === type);
                            return (
                                <span
                                    key={type}
                                    className="text-xs px-2 py-1 rounded-full"
                                    style={{
                                        backgroundColor: `${getTypeColor(type)}30`,
                                        color: getTypeColor(type)
                                    }}
                                >
                                    {typeInfo?.label || type}
                                </span>
                            );
                        })}
                    </div>
                )}

                {/* Location */}
                <div>
                    <label className="block text-sm text-gray-400 mb-2">
                        <MapPin className="w-4 h-4 inline mr-1" />
                        Location
                    </label>
                    <input
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        placeholder="e.g., Kommadi Main Road, Visakhapatnam"
                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                {/* Severity */}
                <div>
                    <label className="block text-sm text-gray-400 mb-2">Severity</label>
                    <div className="flex gap-2">
                        {SEVERITY_LEVELS.map((s) => (
                            <button
                                key={s.value}
                                type="button"
                                onClick={() => setSeverity(s.value)}
                                className={`flex-1 p-2 rounded-lg text-xs transition-all ${severity === s.value
                                    ? 'ring-2'
                                    : 'bg-white/5 hover:bg-white/10'
                                    }`}
                                style={{
                                    backgroundColor: severity === s.value ? `${s.color}30` : undefined,
                                    borderColor: severity === s.value ? s.color : undefined,
                                }}
                            >
                                {s.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Description */}
                <div>
                    <label className="block text-sm text-gray-400 mb-2">Details</label>
                    <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Describe the situation..."
                        rows={2}
                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    />
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={isLoading || !location.trim() || selectedTypes.length === 0}
                    className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-all"
                >
                    {isLoading ? (
                        <span className="animate-spin">⏳</span>
                    ) : (
                        <>
                            <Send className="w-4 h-4" />
                            Submit Report {selectedTypes.length > 1 && `(${selectedTypes.length} types)`}
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
