import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { getPlaybook, addRule, deleteRule, type PlaybookRule, type CreateRuleData } from '@/api/client';

const RISK_LEVELS = [
    { value: 'red', label: 'Critical', className: 'bg-red-50 text-red-600' },
    { value: 'yellow', label: 'Warning', className: 'bg-amber-50 text-amber-600' },
    { value: 'green', label: 'Safe', className: 'bg-green-50 text-green-600' },
];

const MATCH_TYPES = [
    { value: 'exact', label: 'Exact Match', hint: 'Auto-escapes for lawyers' },
    { value: 'fuzzy', label: 'Fuzzy Match', hint: 'Word boundary matching' },
    { value: 'regex', label: 'Regex', hint: 'For power users' },
];

const inputClass = "w-full px-3 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 outline-none bg-white focus:ring-2 focus:ring-slate-900 focus:border-transparent";
const labelClass = "block text-[13px] font-semibold text-slate-700 mb-1.5";

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
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
            </div>
        );
    }

    if (error || !playbook) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center">
                    <p className="text-red-600 mb-4">Error loading playbook</p>
                    <button onClick={() => navigate('/playbooks')} className="text-blue-600 bg-transparent border-none cursor-pointer underline">
                        Back to Playbooks
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Header */}
            <header className="bg-white border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-8 h-16 flex items-center gap-4">
                    <Link to="/playbooks" className="flex items-center text-slate-500 no-underline hover:text-slate-700">
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </Link>
                    <Link to="/dashboard">
                        <img src="/logo.png" alt="ContraRed" className="h-8" />
                    </Link>
                    <span className="text-slate-200 text-lg">&rsaquo;</span>
                    <Link to="/playbooks" className="text-sm text-slate-500 no-underline font-medium hover:text-slate-700">Playbooks</Link>
                    <span className="text-slate-200 text-lg">&rsaquo;</span>
                    <span className="text-sm font-semibold text-slate-900">{playbook.name}</span>
                    <span className={`ml-2 px-2.5 py-0.5 text-xs font-semibold rounded-md ${
                        playbook.is_public ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500'
                    }`}>
                        {playbook.is_public ? 'Public' : 'Private'}
                    </span>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-8 py-10">
                {/* Title row */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Rules ({playbook.rules.length})</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            Detection rules applied when scanning documents with this playbook.
                        </p>
                    </div>
                    <button
                        onClick={() => setShowAddRule(true)}
                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
                    >
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                        Add Rule
                    </button>
                </div>

                {/* Add Rule Panel */}
                {showAddRule && (
                    <div className="bg-white rounded-xl border border-slate-200 p-7 mb-6">
                        <h3 className="text-base font-bold text-slate-900 mb-5">New Detection Rule</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className={labelClass}>Clause Type</label>
                                <input
                                    type="text"
                                    value={newRule.clause_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, clause_type: e.target.value }))}
                                    className={inputClass}
                                    placeholder="e.g., Unlimited Liability"
                                />
                            </div>
                            <div>
                                <label className={labelClass}>Risk Level</label>
                                <select
                                    value={newRule.risk_level}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, risk_level: e.target.value }))}
                                    className={inputClass}
                                >
                                    {RISK_LEVELS.map(level => (
                                        <option key={level.value} value={level.value}>{level.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className={labelClass}>Match Type</label>
                                <select
                                    value={newRule.match_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, match_type: e.target.value }))}
                                    className={inputClass}
                                >
                                    {MATCH_TYPES.map(type => (
                                        <option key={type.value} value={type.value}>{type.label}</option>
                                    ))}
                                </select>
                                <p className="text-xs text-slate-400 mt-1">
                                    {MATCH_TYPES.find(t => t.value === newRule.match_type)?.hint}
                                </p>
                            </div>
                            <div className="flex items-center gap-2.5 pt-6">
                                <input
                                    type="checkbox"
                                    id="dealBreaker"
                                    checked={newRule.is_deal_breaker}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, is_deal_breaker: e.target.checked }))}
                                    className="w-4 h-4 accent-slate-900 cursor-pointer"
                                />
                                <label htmlFor="dealBreaker" className="text-sm font-medium text-slate-700 cursor-pointer">
                                    Deal Breaker
                                </label>
                            </div>
                            <div className="md:col-span-2">
                                <label className={labelClass}>Suggested Fix</label>
                                <input
                                    type="text"
                                    value={newRule.primary_position}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, primary_position: e.target.value }))}
                                    className={inputClass}
                                    placeholder="e.g., Liability capped at 12 months of fees paid"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className={labelClass}>Detection Patterns</label>
                                <div className="flex gap-2 mb-2">
                                    <input
                                        type="text"
                                        value={patternInput}
                                        onChange={(e) => setPatternInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddPattern())}
                                        className={`${inputClass} flex-1`}
                                        placeholder="e.g., unlimited liability"
                                    />
                                    <button
                                        type="button"
                                        onClick={handleAddPattern}
                                        className="px-4 py-2.5 text-sm font-medium bg-slate-100 text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-200 transition-colors"
                                    >
                                        Add
                                    </button>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {(newRule.detection_patterns || []).map((pattern, idx) => (
                                        <span key={idx} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 text-blue-600 text-[13px] rounded-md font-medium">
                                            {pattern}
                                            <button
                                                onClick={() => handleRemovePattern(idx)}
                                                className="bg-transparent border-none text-slate-500 cursor-pointer text-base leading-none p-0 hover:text-slate-700"
                                            >&times;</button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-100">
                            <button
                                onClick={() => setShowAddRule(false)}
                                className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => addRuleMutation.mutate(newRule)}
                                disabled={!newRule.clause_type || !newRule.primary_position || addRuleMutation.isPending}
                                className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                            >
                                {addRuleMutation.isPending ? 'Adding...' : 'Add Rule'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Rules Table */}
                {playbook.rules.length > 0 ? (
                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="bg-slate-50 border-b border-slate-200">
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Clause Type</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Match</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Patterns</th>
                                    <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {playbook.rules.map((rule: PlaybookRule) => {
                                    const riskLevel = RISK_LEVELS.find(l => l.value === rule.risk_level) || RISK_LEVELS[0];
                                    return (
                                        <tr key={rule.id} className="border-b border-slate-100">
                                            <td className="px-6 py-4">
                                                <span className="font-semibold text-slate-900 text-sm">{rule.clause_type}</span>
                                                {rule.is_deal_breaker && (
                                                    <span className="ml-2 text-[11px] font-bold bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                                                        DEAL BREAKER
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2.5 py-1 text-xs font-semibold rounded-md ${riskLevel.className}`}>
                                                    {riskLevel.label}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-[13px] text-slate-500">{rule.match_type}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-1 max-w-[260px]">
                                                    {rule.detection_patterns.slice(0, 3).map((p, i) => (
                                                        <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{p}</span>
                                                    ))}
                                                    {rule.detection_patterns.length > 3 && (
                                                        <span className="text-xs text-slate-400">+{rule.detection_patterns.length - 3} more</span>
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
                                                    className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                        <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <h3 className="text-lg font-semibold text-slate-900 mb-2">No rules yet</h3>
                        <p className="text-sm text-slate-500 mb-6">Add your first detection rule to start flagging risky clauses.</p>
                        <button
                            onClick={() => setShowAddRule(true)}
                            className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                        >
                            Add Rule
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
}
