import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { getPlaybook, addRule, deleteRule, type PlaybookRule, type CreateRuleData } from '@/api/client';

const RISK_LEVELS = [
    { value: 'red', label: 'Critical', bg: '#fef2f2', color: '#dc2626' },
    { value: 'yellow', label: 'Warning', bg: '#fffbeb', color: '#d97706' },
    { value: 'green', label: 'Safe', bg: '#f0fdf4', color: '#16a34a' },
];

const MATCH_TYPES = [
    { value: 'exact', label: 'Exact Match', hint: 'Auto-escapes for lawyers' },
    { value: 'fuzzy', label: 'Fuzzy Match', hint: 'Word boundary matching' },
    { value: 'regex', label: 'Regex', hint: 'For power users' },
];

const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 8,
    border: '1px solid #e2e8f0',
    fontSize: 14,
    color: '#0f172a',
    outline: 'none',
    backgroundColor: '#ffffff',
    boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    color: '#334155',
    marginBottom: 6,
};

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
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc' }}>
                <div style={{ width: 32, height: 32, border: '3px solid #e2e8f0', borderTopColor: '#0f172a', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
            </div>
        );
    }

    if (error || !playbook) {
        return (
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc' }}>
                <div style={{ textAlign: 'center' }}>
                    <p style={{ color: '#dc2626', marginBottom: 16 }}>Error loading playbook</p>
                    <button onClick={() => navigate('/playbooks')} style={{ color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                        Back to Playbooks
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ fontFamily: "'Inter', system-ui, sans-serif", minHeight: '100vh', backgroundColor: '#f8fafc' }}>
            {/* Header */}
            <header style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e2e8f0' }}>
                <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 32px', height: 64, display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Link to="/playbooks" style={{ display: 'flex', alignItems: 'center', color: '#64748b', textDecoration: 'none' }}>
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </Link>
                    <Link to="/dashboard">
                        <img src="/logo.png" alt="ContraRed" style={{ height: 32 }} />
                    </Link>
                    <span style={{ color: '#e2e8f0', fontSize: 18 }}>›</span>
                    <Link to="/playbooks" style={{ fontSize: 14, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Playbooks</Link>
                    <span style={{ color: '#e2e8f0', fontSize: 18 }}>›</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#0f172a' }}>{playbook.name}</span>
                    <span style={{
                        marginLeft: 8,
                        padding: '3px 10px',
                        fontSize: 12,
                        fontWeight: 600,
                        borderRadius: 6,
                        backgroundColor: playbook.is_public ? '#f0fdf4' : '#f1f5f9',
                        color: playbook.is_public ? '#16a34a' : '#64748b',
                    }}>
                        {playbook.is_public ? 'Public' : 'Private'}
                    </span>
                </div>
            </header>

            <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 32px' }}>
                {/* Title row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                    <div>
                        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', margin: 0 }}>Rules ({playbook.rules.length})</h1>
                        <p style={{ fontSize: 14, color: '#64748b', margin: '4px 0 0' }}>
                            Detection rules applied when scanning documents with this playbook.
                        </p>
                    </div>
                    <button
                        onClick={() => setShowAddRule(true)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '10px 20px',
                            backgroundColor: '#0f172a', color: '#ffffff',
                            fontSize: 14, fontWeight: 600,
                            borderRadius: 8, border: 'none', cursor: 'pointer',
                        }}
                    >
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                        Add Rule
                    </button>
                </div>

                {/* Add Rule Panel */}
                {showAddRule && (
                    <div style={{ backgroundColor: '#ffffff', borderRadius: 12, border: '1px solid #e2e8f0', padding: 28, marginBottom: 24 }}>
                        <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', margin: '0 0 20px' }}>New Detection Rule</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                                <label style={labelStyle}>Clause Type</label>
                                <input
                                    type="text"
                                    value={newRule.clause_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, clause_type: e.target.value }))}
                                    style={inputStyle}
                                    placeholder="e.g., Unlimited Liability"
                                />
                            </div>
                            <div>
                                <label style={labelStyle}>Risk Level</label>
                                <select
                                    value={newRule.risk_level}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, risk_level: e.target.value }))}
                                    style={inputStyle}
                                >
                                    {RISK_LEVELS.map(level => (
                                        <option key={level.value} value={level.value}>{level.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label style={labelStyle}>Match Type</label>
                                <select
                                    value={newRule.match_type}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, match_type: e.target.value }))}
                                    style={inputStyle}
                                >
                                    {MATCH_TYPES.map(type => (
                                        <option key={type.value} value={type.value}>{type.label}</option>
                                    ))}
                                </select>
                                <p style={{ fontSize: 12, color: '#94a3b8', margin: '4px 0 0' }}>
                                    {MATCH_TYPES.find(t => t.value === newRule.match_type)?.hint}
                                </p>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingTop: 24 }}>
                                <input
                                    type="checkbox"
                                    id="dealBreaker"
                                    checked={newRule.is_deal_breaker}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, is_deal_breaker: e.target.checked }))}
                                    style={{ width: 16, height: 16, accentColor: '#0f172a', cursor: 'pointer' }}
                                />
                                <label htmlFor="dealBreaker" style={{ fontSize: 14, fontWeight: 500, color: '#334155', cursor: 'pointer' }}>
                                    Deal Breaker
                                </label>
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                                <label style={labelStyle}>Suggested Fix</label>
                                <input
                                    type="text"
                                    value={newRule.primary_position}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, primary_position: e.target.value }))}
                                    style={inputStyle}
                                    placeholder="e.g., Liability capped at 12 months of fees paid"
                                />
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                                <label style={labelStyle}>Detection Patterns</label>
                                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                                    <input
                                        type="text"
                                        value={patternInput}
                                        onChange={(e) => setPatternInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddPattern())}
                                        style={{ ...inputStyle, flex: 1 }}
                                        placeholder="e.g., unlimited liability"
                                    />
                                    <button
                                        type="button"
                                        onClick={handleAddPattern}
                                        style={{
                                            padding: '10px 16px', fontSize: 14, fontWeight: 500,
                                            backgroundColor: '#f1f5f9', color: '#334155',
                                            border: '1px solid #e2e8f0', borderRadius: 8, cursor: 'pointer',
                                        }}
                                    >
                                        Add
                                    </button>
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                    {(newRule.detection_patterns || []).map((pattern, idx) => (
                                        <span key={idx} style={{
                                            display: 'inline-flex', alignItems: 'center', gap: 6,
                                            padding: '4px 10px',
                                            backgroundColor: '#eff6ff', color: '#2563eb',
                                            fontSize: 13, borderRadius: 6, fontWeight: 500,
                                        }}>
                                            {pattern}
                                            <button
                                                onClick={() => handleRemovePattern(idx)}
                                                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: 0 }}
                                            >×</button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 24, paddingTop: 20, borderTop: '1px solid #f1f5f9' }}>
                            <button
                                onClick={() => setShowAddRule(false)}
                                style={{
                                    padding: '10px 20px', fontSize: 14, fontWeight: 500, color: '#64748b',
                                    backgroundColor: 'transparent', border: '1px solid #e2e8f0', borderRadius: 8, cursor: 'pointer',
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => addRuleMutation.mutate(newRule)}
                                disabled={!newRule.clause_type || !newRule.primary_position || addRuleMutation.isPending}
                                style={{
                                    padding: '10px 20px', fontSize: 14, fontWeight: 600, color: '#ffffff',
                                    backgroundColor: '#0f172a', border: 'none', borderRadius: 8, cursor: 'pointer',
                                    opacity: (!newRule.clause_type || !newRule.primary_position || addRuleMutation.isPending) ? 0.5 : 1,
                                }}
                            >
                                {addRuleMutation.isPending ? 'Adding...' : 'Add Rule'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Rules Table */}
                {playbook.rules.length > 0 ? (
                    <div style={{ backgroundColor: '#ffffff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Clause Type</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Risk</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Match</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Patterns</th>
                                    <th style={{ textAlign: 'right', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {playbook.rules.map((rule: PlaybookRule) => {
                                    const riskLevel = RISK_LEVELS.find(l => l.value === rule.risk_level) || RISK_LEVELS[0];
                                    return (
                                        <tr key={rule.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '16px 24px' }}>
                                                <span style={{ fontWeight: 600, color: '#0f172a', fontSize: 14 }}>{rule.clause_type}</span>
                                                {rule.is_deal_breaker && (
                                                    <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 700, backgroundColor: '#fef2f2', color: '#dc2626', padding: '2px 6px', borderRadius: 4 }}>
                                                        DEAL BREAKER
                                                    </span>
                                                )}
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <span style={{ padding: '4px 10px', fontSize: 12, fontWeight: 600, borderRadius: 6, backgroundColor: riskLevel.bg, color: riskLevel.color }}>
                                                    {riskLevel.label}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px 24px', fontSize: 13, color: '#64748b' }}>{rule.match_type}</td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 260 }}>
                                                    {rule.detection_patterns.slice(0, 3).map((p, i) => (
                                                        <span key={i} style={{ fontSize: 12, backgroundColor: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 4 }}>{p}</span>
                                                    ))}
                                                    {rule.detection_patterns.length > 3 && (
                                                        <span style={{ fontSize: 12, color: '#94a3b8' }}>+{rule.detection_patterns.length - 3} more</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                                <button
                                                    onClick={() => {
                                                        if (confirm('Delete this rule?')) {
                                                            deleteRuleMutation.mutate(rule.id);
                                                        }
                                                    }}
                                                    style={{ fontSize: 13, fontWeight: 600, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}
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
                    <div style={{ textAlign: 'center', padding: '64px 32px', backgroundColor: '#ffffff', borderRadius: 12, border: '1px solid #e2e8f0' }}>
                        <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" style={{ margin: '0 auto 16px' }}>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <h3 style={{ fontSize: 18, fontWeight: 600, color: '#0f172a', margin: '0 0 8px' }}>No rules yet</h3>
                        <p style={{ fontSize: 14, color: '#64748b', margin: '0 0 24px' }}>Add your first detection rule to start flagging risky clauses.</p>
                        <button
                            onClick={() => setShowAddRule(true)}
                            style={{
                                padding: '10px 24px', fontSize: 14, fontWeight: 600,
                                color: '#ffffff', backgroundColor: '#0f172a',
                                border: 'none', borderRadius: 8, cursor: 'pointer',
                            }}
                        >
                            Add Rule
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
}
