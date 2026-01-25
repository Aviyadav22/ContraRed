import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { getPlaybook, addRule, deleteRule, type PlaybookRule, type CreateRuleData } from '@/api/client';

const RISK_LEVELS = [
    { value: 'red', label: 'Red (Critical)', color: 'bg-red-100 text-red-700' },
    { value: 'yellow', label: 'Yellow (Warning)', color: 'bg-yellow-100 text-yellow-700' },
    { value: 'green', label: 'Green (Safe)', color: 'bg-green-100 text-green-700' },
];

const MATCH_TYPES = [
    { value: 'exact', label: 'Exact Match', hint: 'Auto-escapes for lawyers' },
    { value: 'fuzzy', label: 'Fuzzy Match', hint: 'Word boundary matching' },
    { value: 'regex', label: 'Regex', hint: 'For power users' },
];

export default function PlaybookEditor() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [showAddRule, setShowAddRule] = useState(false);
    const [newRule, setNewRule] = useState<CreateRuleData>({
        clause_type: '',
        primary_position: '',
        risk_level: 'yellow',
        match_type: 'exact',
        is_deal_breaker: false,
        detection_patterns: [],
    });
    const [patternInput, setPatternInput] = useState('');

    const { data: playbook, isLoading, error } = useQuery({
        queryKey: ['playbook', id],
        queryFn: () => getPlaybook(id!),
        enabled: !!id,
    });

    const addRuleMutation = useMutation({
        mutationFn: (data: CreateRuleData) => addRule(id!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            setShowAddRule(false);
            setNewRule({ clause_type: '', primary_position: '', risk_level: 'yellow', match_type: 'exact', is_deal_breaker: false, detection_patterns: [] });
            setPatternInput('');
        },
    });

    const deleteRuleMutation = useMutation({
        mutationFn: (ruleId: string) => deleteRule(id!, ruleId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbook', id] }),
    });

    const handleAddPattern = () => {
        if (patternInput.trim()) {
            setNewRule(prev => ({
                ...prev,
                detection_patterns: [...(prev.detection_patterns || []), patternInput.trim()],
            }));
            setPatternInput('');
        }
    };

    const handleRemovePattern = (index: number) => {
        setNewRule(prev => ({
            ...prev,
            detection_patterns: (prev.detection_patterns || []).filter((_, i) => i !== index),
        }));
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (error || !playbook) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-600 mb-4">Error loading playbook</p>
                    <button onClick={() => navigate('/playbooks')} className="text-blue-600 hover:underline">
                        Back to Playbooks
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-4">
                            <Link to="/playbooks" className="text-slate-500 hover:text-slate-700">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                </svg>
                            </Link>
                            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">{playbook.name}</h1>
                            <span className={`px-2 py-0.5 text-xs rounded ${playbook.is_public ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                                {playbook.is_public ? '🌐 Public' : '🔒 Private'}
                            </span>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Rules Section */}
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Rules ({playbook.rules.length})</h2>
                    <button
                        onClick={() => setShowAddRule(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition flex items-center gap-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Add Rule
                    </button>
                </div>

                {/* Add Rule Form */}
                {showAddRule && (
                    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">New Rule</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Clause Type</label>
                                <input
                                    type="text"
                                    value={newRule.clause_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, clause_type: e.target.value }))}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                    placeholder="e.g., Unlimited Liability"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Risk Level</label>
                                <select
                                    value={newRule.risk_level}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, risk_level: e.target.value }))}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                >
                                    {RISK_LEVELS.map(level => (
                                        <option key={level.value} value={level.value}>{level.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Match Type</label>
                                <select
                                    value={newRule.match_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, match_type: e.target.value }))}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                >
                                    {MATCH_TYPES.map(type => (
                                        <option key={type.value} value={type.value}>{type.label}</option>
                                    ))}
                                </select>
                                <p className="text-xs text-slate-500 mt-1">{MATCH_TYPES.find(t => t.value === newRule.match_type)?.hint}</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="dealBreaker"
                                    checked={newRule.is_deal_breaker}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, is_deal_breaker: e.target.checked }))}
                                    className="w-4 h-4 rounded border-slate-300"
                                />
                                <label htmlFor="dealBreaker" className="text-sm font-medium text-slate-700 dark:text-slate-300">Deal Breaker</label>
                            </div>
                            <div className="col-span-2">
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Suggested Fix</label>
                                <input
                                    type="text"
                                    value={newRule.primary_position}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, primary_position: e.target.value }))}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                    placeholder="e.g., Liability capped at 12 months of fees"
                                />
                            </div>
                            <div className="col-span-2">
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Detection Patterns</label>
                                <div className="flex gap-2 mb-2">
                                    <input
                                        type="text"
                                        value={patternInput}
                                        onChange={(e) => setPatternInput(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddPattern())}
                                        className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                        placeholder="e.g., unlimited liability"
                                    />
                                    <button
                                        type="button"
                                        onClick={handleAddPattern}
                                        className="px-3 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-600 dark:hover:bg-slate-500 rounded-lg transition"
                                    >
                                        Add
                                    </button>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {(newRule.detection_patterns || []).map((pattern, idx) => (
                                        <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded text-sm">
                                            {pattern}
                                            <button onClick={() => handleRemovePattern(idx)} className="hover:text-red-600">×</button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                            <button
                                onClick={() => setShowAddRule(false)}
                                className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => addRuleMutation.mutate(newRule)}
                                disabled={!newRule.clause_type || !newRule.primary_position || addRuleMutation.isPending}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg transition"
                            >
                                {addRuleMutation.isPending ? 'Adding...' : 'Add Rule'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Rules Table */}
                {playbook.rules.length > 0 ? (
                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <table className="w-full">
                            <thead className="bg-slate-50 dark:bg-slate-700/50">
                                <tr>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Clause Type</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Risk</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Match Type</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Patterns</th>
                                    <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                {playbook.rules.map((rule: PlaybookRule) => (
                                    <tr key={rule.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                                        <td className="px-6 py-4">
                                            <span className="font-medium text-slate-900 dark:text-white">{rule.clause_type}</span>
                                            {rule.is_deal_breaker && (
                                                <span className="ml-2 text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">DEAL BREAKER</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 text-xs font-medium rounded ${RISK_LEVELS.find(l => l.value === rule.risk_level)?.color || 'bg-slate-100 text-slate-700'}`}>
                                                {rule.risk_level.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 dark:text-slate-400 text-sm">
                                            {rule.match_type}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-wrap gap-1 max-w-xs">
                                                {rule.detection_patterns.slice(0, 3).map((p, i) => (
                                                    <span key={i} className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 px-1.5 py-0.5 rounded">
                                                        {p}
                                                    </span>
                                                ))}
                                                {rule.detection_patterns.length > 3 && (
                                                    <span className="text-xs text-slate-500">+{rule.detection_patterns.length - 3} more</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={() => {
                                                    if (confirm('Delete this rule?')) {
                                                        deleteRuleMutation.mutate(rule.id);
                                                    }
                                                }}
                                                className="text-red-600 hover:text-red-700 font-medium text-sm"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <p className="text-slate-500 dark:text-slate-400 mb-4">No rules yet. Add your first detection rule.</p>
                        <button
                            onClick={() => setShowAddRule(true)}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition"
                        >
                            Add Rule
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
}
