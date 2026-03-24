import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import {
    getPlaybook, addRule, deleteRule,
    listTiers, upsertTiers,
    listConditions, createCondition, deleteCondition, addOverride, deleteOverride,
    listDependencies, createDependency, deleteDependency,
    listVersions, createVersionSnapshot, rollbackToVersion,
    type PlaybookRule, type CreateRuleData,
    type RuleTier, type PlaybookCondition,
    type RuleDependency, type PlaybookVersionSummary,
} from '@/api/client';
import AppHeader from '@/components/AppHeader';

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

const DETECTION_MODES = [
    { value: 'keywords_only', label: 'Keywords Only', hint: 'Regex pattern matching' },
    { value: 'ai_with_keywords', label: 'AI + Keywords', hint: 'AI detection with keyword pre-filtering' },
    { value: 'ai_only', label: 'AI Only', hint: 'Pure AI detection for context-dependent rules' },
];

const TIER_LABELS = ['Ideal', 'Acceptable', 'Walk-Away', 'Escalate'];

const CONDITION_TYPES = [
    { value: 'counterparty_type', label: 'Counterparty Type' },
    { value: 'deal_size', label: 'Deal Size' },
    { value: 'jurisdiction', label: 'Jurisdiction' },
    { value: 'contract_side', label: 'Contract Side' },
];

const OPERATORS = [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'in', label: 'In' },
    { value: 'greater_than', label: 'Greater Than' },
    { value: 'less_than', label: 'Less Than' },
    { value: 'between', label: 'Between' },
];

const TRIGGER_CONDITIONS = [
    { value: 'source_is_red', label: 'Source is Red' },
    { value: 'source_is_yellow', label: 'Source is Yellow' },
    { value: 'source_missing', label: 'Source Missing' },
    { value: 'source_uncapped', label: 'Source Uncapped' },
    { value: 'source_deal_breaker', label: 'Source is Deal Breaker' },
];

const EFFECTS = [
    { value: 'escalate_risk', label: 'Escalate Risk' },
    { value: 'add_flag', label: 'Add Flag' },
    { value: 'change_position', label: 'Change Position' },
    { value: 'suppress', label: 'Suppress' },
];

const TABS = [
    { key: 'rules', label: 'Rules' },
    { key: 'conditions', label: 'Conditions' },
    { key: 'dependencies', label: 'Dependencies' },
    { key: 'history', label: 'History' },
    { key: 'analytics', label: 'Analytics' },
];

const inputClass = "w-full px-3 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 outline-none bg-white focus:ring-2 focus:ring-slate-900 focus:border-transparent";
const labelClass = "block text-[13px] font-semibold text-slate-700 mb-1.5";

export default function PlaybookEditor() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [activeTab, setActiveTab] = useState<string>('rules');

    // ── Rules state ──
    const [showAddRule, setShowAddRule] = useState(false);
    const [newRule, setNewRule] = useState<CreateRuleData>({
        clause_type: '',
        primary_position: '',
        risk_level: 'yellow',
        match_type: 'exact',
        is_deal_breaker: false,
        detection_patterns: [],
        detection_mode: 'keywords_only',
    });
    const [patternInput, setPatternInput] = useState('');
    const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null);
    const [tierDrafts, setTierDrafts] = useState<Record<number, { position_text: string; guidance_notes: string; risk_level_at_tier: string }>>({});

    // ── Conditions state ──
    const [showAddCondition, setShowAddCondition] = useState(false);
    const [newCondition, setNewCondition] = useState({
        name: '',
        description: '',
        condition_type: 'counterparty_type',
        operator: 'equals',
        condition_value: '{}',
        is_active: true,
        priority: 0,
    });
    const [expandedConditionId, setExpandedConditionId] = useState<string | null>(null);
    const [showAddOverride, setShowAddOverride] = useState<string | null>(null);
    const [newOverride, setNewOverride] = useState({
        rule_id: '',
        override_risk_level: '',
        override_position_text: '',
        suppress_rule: false,
    });

    // ── Dependencies state ──
    const [showAddDep, setShowAddDep] = useState(false);
    const [newDep, setNewDep] = useState({
        source_rule_id: '',
        target_rule_id: '',
        trigger_condition: 'source_is_red',
        effect: 'escalate_risk',
        effect_params: '{}',
        is_active: true,
    });

    // ── History state ──
    const [showCreateSnapshot, setShowCreateSnapshot] = useState(false);
    const [snapshotSummary, setSnapshotSummary] = useState('');

    // ══════════════════════════════════════════════════════════════════════
    // Queries
    // ══════════════════════════════════════════════════════════════════════

    const { data: playbook, isLoading, error } = useQuery({
        queryKey: ['playbook', id],
        queryFn: () => getPlaybook(id!),
        enabled: !!id,
    });

    const { data: tiers, isLoading: tiersLoading } = useQuery({
        queryKey: ['tiers', id, expandedRuleId],
        queryFn: () => listTiers(id!, expandedRuleId!),
        enabled: !!id && !!expandedRuleId,
    });

    const { data: conditions } = useQuery({
        queryKey: ['conditions', id],
        queryFn: () => listConditions(id!),
        enabled: !!id && activeTab === 'conditions',
    });

    const { data: dependencies } = useQuery({
        queryKey: ['dependencies', id],
        queryFn: () => listDependencies(id!),
        enabled: !!id && activeTab === 'dependencies',
    });

    const { data: versions } = useQuery({
        queryKey: ['versions', id],
        queryFn: () => listVersions(id!),
        enabled: !!id && activeTab === 'history',
    });

    // ══════════════════════════════════════════════════════════════════════
    // Mutations
    // ══════════════════════════════════════════════════════════════════════

    const addRuleMutation = useMutation({
        mutationFn: (data: CreateRuleData) => addRule(id!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            setShowAddRule(false);
            setNewRule({ clause_type: '', primary_position: '', risk_level: 'yellow', match_type: 'exact', is_deal_breaker: false, detection_patterns: [], detection_mode: 'keywords_only' });
            setPatternInput('');
        },
    });

    const deleteRuleMutation = useMutation({
        mutationFn: (ruleId: string) => deleteRule(id!, ruleId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbook', id] }),
    });

    const upsertTiersMutation = useMutation({
        mutationFn: (ruleId: string) => {
            const tiersPayload = [1, 2, 3, 4].map(level => ({
                tier_level: level,
                position_text: tierDrafts[level]?.position_text || '',
                guidance_notes: tierDrafts[level]?.guidance_notes || '',
                risk_level_at_tier: tierDrafts[level]?.risk_level_at_tier || 'green',
            }));
            return upsertTiers(id!, ruleId, tiersPayload);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tiers', id, expandedRuleId] });
        },
    });

    const createConditionMutation = useMutation({
        mutationFn: () => {
            let parsedValue: Record<string, unknown> = {};
            try { parsedValue = JSON.parse(newCondition.condition_value); } catch { /* empty */ }
            return createCondition(id!, {
                name: newCondition.name,
                description: newCondition.description || undefined,
                condition_type: newCondition.condition_type,
                operator: newCondition.operator,
                condition_value: parsedValue,
                is_active: newCondition.is_active,
                priority: newCondition.priority,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['conditions', id] });
            setShowAddCondition(false);
            setNewCondition({ name: '', description: '', condition_type: 'counterparty_type', operator: 'equals', condition_value: '{}', is_active: true, priority: 0 });
        },
    });

    const deleteConditionMutation = useMutation({
        mutationFn: (conditionId: string) => deleteCondition(id!, conditionId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conditions', id] }),
    });

    const addOverrideMutation = useMutation({
        mutationFn: (conditionId: string) => addOverride(id!, conditionId, {
            rule_id: newOverride.rule_id,
            override_risk_level: newOverride.override_risk_level || undefined,
            override_position_text: newOverride.override_position_text || undefined,
            suppress_rule: newOverride.suppress_rule,
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['conditions', id] });
            setShowAddOverride(null);
            setNewOverride({ rule_id: '', override_risk_level: '', override_position_text: '', suppress_rule: false });
        },
    });

    const _deleteOverrideMutation = useMutation({
        mutationFn: ({ conditionId, overrideId }: { conditionId: string; overrideId: string }) =>
            deleteOverride(id!, conditionId, overrideId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conditions', id] }),
    });
    // Available for future use when override listing is implemented
    void _deleteOverrideMutation;

    const createDepMutation = useMutation({
        mutationFn: () => {
            let parsedParams: Record<string, unknown> = {};
            try { parsedParams = JSON.parse(newDep.effect_params); } catch { /* empty */ }
            return createDependency(id!, {
                source_rule_id: newDep.source_rule_id,
                target_rule_id: newDep.target_rule_id,
                trigger_condition: newDep.trigger_condition,
                effect: newDep.effect,
                effect_params: parsedParams,
                is_active: newDep.is_active,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dependencies', id] });
            setShowAddDep(false);
            setNewDep({ source_rule_id: '', target_rule_id: '', trigger_condition: 'source_is_red', effect: 'escalate_risk', effect_params: '{}', is_active: true });
        },
    });

    const deleteDepMutation = useMutation({
        mutationFn: (depId: string) => deleteDependency(id!, depId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dependencies', id] }),
    });

    const createSnapshotMutation = useMutation({
        mutationFn: () => createVersionSnapshot(id!, snapshotSummary),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', id] });
            setShowCreateSnapshot(false);
            setSnapshotSummary('');
        },
    });

    const rollbackMutation = useMutation({
        mutationFn: (versionId: string) => rollbackToVersion(id!, versionId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            queryClient.invalidateQueries({ queryKey: ['versions', id] });
        },
    });

    // ══════════════════════════════════════════════════════════════════════
    // Handlers
    // ══════════════════════════════════════════════════════════════════════

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

    const handleExpandRule = (ruleId: string) => {
        if (expandedRuleId === ruleId) {
            setExpandedRuleId(null);
            setTierDrafts({});
        } else {
            setExpandedRuleId(ruleId);
            setTierDrafts({});
        }
    };

    // Sync fetched tiers into drafts when loaded
    const syncTierDrafts = (fetchedTiers: RuleTier[] | undefined) => {
        if (!fetchedTiers) return;
        const drafts: typeof tierDrafts = {};
        for (let i = 1; i <= 4; i++) {
            const existing = fetchedTiers.find(t => t.tier_level === i);
            drafts[i] = {
                position_text: existing?.position_text || '',
                guidance_notes: existing?.guidance_notes || '',
                risk_level_at_tier: existing?.risk_level_at_tier || 'green',
            };
        }
        setTierDrafts(drafts);
    };

    const getRuleName = (ruleId: string): string => {
        const rule = playbook?.rules.find(r => r.id === ruleId);
        return rule?.clause_type || ruleId.slice(0, 8);
    };

    // ══════════════════════════════════════════════════════════════════════
    // Loading / Error states
    // ══════════════════════════════════════════════════════════════════════

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

    // ══════════════════════════════════════════════════════════════════════
    // Tab Content Renderers
    // ══════════════════════════════════════════════════════════════════════

    const renderRulesTab = () => (
        <>
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
                        <div>
                            <label className={labelClass}>Detection Mode</label>
                            <select
                                value={newRule.detection_mode || 'keywords_only'}
                                onChange={(e) => setNewRule(prev => ({ ...prev, detection_mode: e.target.value }))}
                                className={inputClass}
                            >
                                {DETECTION_MODES.map(m => (
                                    <option key={m.value} value={m.value}>{m.label} — {m.hint}</option>
                                ))}
                            </select>
                        </div>
                        {newRule.detection_mode && newRule.detection_mode !== 'keywords_only' && (
                            <div className="md:col-span-2">
                                <label className={labelClass}>
                                    Risk Description
                                    <span className="text-xs text-slate-400 ml-1 font-normal">(what the AI should look for)</span>
                                </label>
                                <textarea
                                    value={newRule.risk_description || ''}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, risk_description: e.target.value }))}
                                    placeholder="Describe the risk in natural language, e.g., 'Liability cap is missing, unlimited, or disproportionately high relative to contract value'"
                                    className={`${inputClass} min-h-[72px]`}
                                    rows={3}
                                />
                            </div>
                        )}
                        {newRule.detection_mode && newRule.detection_mode !== 'keywords_only' && (
                            <div className="md:col-span-2">
                                <label className={labelClass}>
                                    Acceptable Position
                                    <span className="text-xs text-slate-400 ml-1 font-normal">(what's OK — prevents false positives)</span>
                                </label>
                                <textarea
                                    value={newRule.acceptable_position || ''}
                                    onChange={(e) => setNewRule(prev => ({ ...prev, acceptable_position: e.target.value }))}
                                    placeholder="e.g., 'Mutual liability capped at 12 months of fees paid'"
                                    className={`${inputClass} min-h-[52px]`}
                                    rows={2}
                                />
                            </div>
                        )}
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
                        {(!newRule.detection_mode || newRule.detection_mode !== 'ai_only') && (
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
                        )}
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
                                const isExpanded = expandedRuleId === rule.id;
                                return (
                                    <RuleRow
                                        key={rule.id}
                                        rule={rule}
                                        riskLevel={riskLevel}
                                        isExpanded={isExpanded}
                                        tiersLoading={tiersLoading && isExpanded}
                                        tiers={isExpanded ? tiers : undefined}
                                        tierDrafts={tierDrafts}
                                        onToggleExpand={() => handleExpandRule(rule.id)}
                                        onDelete={() => {
                                            if (confirm('Delete this rule?')) {
                                                deleteRuleMutation.mutate(rule.id);
                                            }
                                        }}
                                        onSyncTiers={() => syncTierDrafts(tiers)}
                                        onTierChange={(level, field, value) => {
                                            setTierDrafts(prev => ({
                                                ...prev,
                                                [level]: { ...prev[level], [field]: value },
                                            }));
                                        }}
                                        onSaveTiers={() => upsertTiersMutation.mutate(rule.id)}
                                        tiersSaving={upsertTiersMutation.isPending}
                                    />
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
        </>
    );

    const renderConditionsTab = () => (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Conditions ({conditions?.length || 0})</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Deal context conditions that modify rule behavior based on counterparty, deal size, jurisdiction, or contract side.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddCondition(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Add Condition
                </button>
            </div>

            {/* Add Condition Form */}
            {showAddCondition && (
                <div className="bg-white rounded-xl border border-slate-200 p-7 mb-6">
                    <h3 className="text-base font-bold text-slate-900 mb-5">New Condition</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className={labelClass}>Name</label>
                            <input
                                type="text"
                                value={newCondition.name}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, name: e.target.value }))}
                                className={inputClass}
                                placeholder="e.g., Large Enterprise Deals"
                            />
                        </div>
                        <div>
                            <label className={labelClass}>Condition Type</label>
                            <select
                                value={newCondition.condition_type}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, condition_type: e.target.value }))}
                                className={inputClass}
                            >
                                {CONDITION_TYPES.map(ct => (
                                    <option key={ct.value} value={ct.value}>{ct.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={labelClass}>Operator</label>
                            <select
                                value={newCondition.operator}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, operator: e.target.value }))}
                                className={inputClass}
                            >
                                {OPERATORS.map(op => (
                                    <option key={op.value} value={op.value}>{op.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={labelClass}>Priority</label>
                            <input
                                type="number"
                                value={newCondition.priority}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, priority: parseInt(e.target.value) || 0 }))}
                                className={inputClass}
                                min={0}
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className={labelClass}>Condition Value (JSON)</label>
                            <textarea
                                value={newCondition.condition_value}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, condition_value: e.target.value }))}
                                className={`${inputClass} min-h-[80px] font-mono text-xs`}
                                placeholder='{"values": ["enterprise", "government"]}'
                            />
                        </div>
                        <div className="md:col-span-2">
                            <label className={labelClass}>Description</label>
                            <input
                                type="text"
                                value={newCondition.description}
                                onChange={(e) => setNewCondition(prev => ({ ...prev, description: e.target.value }))}
                                className={inputClass}
                                placeholder="Optional description for this condition"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-100">
                        <button
                            onClick={() => setShowAddCondition(false)}
                            className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createConditionMutation.mutate()}
                            disabled={!newCondition.name || createConditionMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                        >
                            {createConditionMutation.isPending ? 'Creating...' : 'Create Condition'}
                        </button>
                    </div>
                </div>
            )}

            {/* Conditions List */}
            {conditions && conditions.length > 0 ? (
                <div className="space-y-4">
                    {conditions.map((condition: PlaybookCondition) => (
                        <div key={condition.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                            <div
                                className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-slate-50 transition-colors"
                                onClick={() => setExpandedConditionId(expandedConditionId === condition.id ? null : condition.id)}
                            >
                                <div className="flex items-center gap-4">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-sm text-slate-900">{condition.name}</span>
                                            <span className={`px-2 py-0.5 text-[11px] font-semibold rounded ${condition.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'}`}>
                                                {condition.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-500 mt-0.5">
                                            {CONDITION_TYPES.find(ct => ct.value === condition.condition_type)?.label || condition.condition_type}
                                            {' '}{OPERATORS.find(op => op.value === condition.operator)?.label || condition.operator}
                                            {' '}
                                            <span className="font-mono">{JSON.stringify(condition.condition_value)}</span>
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="text-xs text-slate-400">{condition.overrides_count} override{condition.overrides_count !== 1 ? 's' : ''}</span>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); if (confirm('Delete this condition?')) deleteConditionMutation.mutate(condition.id); }}
                                        className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
                                    >
                                        Delete
                                    </button>
                                    <svg
                                        width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                        className={`transition-transform ${expandedConditionId === condition.id ? 'rotate-180' : ''}`}
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </div>

                            {/* Expanded: Overrides */}
                            {expandedConditionId === condition.id && (
                                <div className="border-t border-slate-100 px-6 py-5 bg-slate-50">
                                    <div className="flex justify-between items-center mb-4">
                                        <h4 className="text-sm font-semibold text-slate-700">Rule Overrides</h4>
                                        <button
                                            onClick={() => setShowAddOverride(showAddOverride === condition.id ? null : condition.id)}
                                            className="text-xs font-semibold text-slate-900 bg-white border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                                        >
                                            + Add Override
                                        </button>
                                    </div>

                                    {/* Add Override Form */}
                                    {showAddOverride === condition.id && (
                                        <div className="bg-white rounded-lg border border-slate-200 p-5 mb-4">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className={labelClass}>Target Rule</label>
                                                    <select
                                                        value={newOverride.rule_id}
                                                        onChange={(e) => setNewOverride(prev => ({ ...prev, rule_id: e.target.value }))}
                                                        className={inputClass}
                                                    >
                                                        <option value="">Select a rule...</option>
                                                        {playbook.rules.map((r: PlaybookRule) => (
                                                            <option key={r.id} value={r.id}>{r.clause_type}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className={labelClass}>Override Risk Level</label>
                                                    <select
                                                        value={newOverride.override_risk_level}
                                                        onChange={(e) => setNewOverride(prev => ({ ...prev, override_risk_level: e.target.value }))}
                                                        className={inputClass}
                                                    >
                                                        <option value="">No change</option>
                                                        {RISK_LEVELS.map(level => (
                                                            <option key={level.value} value={level.value}>{level.label}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div className="md:col-span-2">
                                                    <label className={labelClass}>Override Position Text</label>
                                                    <input
                                                        type="text"
                                                        value={newOverride.override_position_text}
                                                        onChange={(e) => setNewOverride(prev => ({ ...prev, override_position_text: e.target.value }))}
                                                        className={inputClass}
                                                        placeholder="Leave blank to keep original"
                                                    />
                                                </div>
                                                <div className="flex items-center gap-2.5">
                                                    <input
                                                        type="checkbox"
                                                        id={`suppress-${condition.id}`}
                                                        checked={newOverride.suppress_rule}
                                                        onChange={(e) => setNewOverride(prev => ({ ...prev, suppress_rule: e.target.checked }))}
                                                        className="w-4 h-4 accent-slate-900 cursor-pointer"
                                                    />
                                                    <label htmlFor={`suppress-${condition.id}`} className="text-sm font-medium text-slate-700 cursor-pointer">
                                                        Suppress Rule
                                                    </label>
                                                </div>
                                            </div>
                                            <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-slate-100">
                                                <button
                                                    onClick={() => setShowAddOverride(null)}
                                                    className="px-4 py-2 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    onClick={() => addOverrideMutation.mutate(condition.id)}
                                                    disabled={!newOverride.rule_id || addOverrideMutation.isPending}
                                                    className="px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                                                >
                                                    {addOverrideMutation.isPending ? 'Adding...' : 'Add Override'}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {condition.overrides_count === 0 && showAddOverride !== condition.id && (
                                        <p className="text-xs text-slate-400 italic">No overrides configured for this condition.</p>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                    <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                    </svg>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No conditions yet</h3>
                    <p className="text-sm text-slate-500 mb-6">Add conditions to dynamically adjust rules based on deal context.</p>
                    <button
                        onClick={() => setShowAddCondition(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                        Add Condition
                    </button>
                </div>
            )}
        </>
    );

    const renderDependenciesTab = () => (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Dependencies ({dependencies?.length || 0})</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Cross-clause dependency graph. Define how one rule's outcome affects another.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddDep(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Add Dependency
                </button>
            </div>

            {/* Add Dependency Form */}
            {showAddDep && (
                <div className="bg-white rounded-xl border border-slate-200 p-7 mb-6">
                    <h3 className="text-base font-bold text-slate-900 mb-5">New Dependency</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className={labelClass}>Source Rule</label>
                            <select
                                value={newDep.source_rule_id}
                                onChange={(e) => setNewDep(prev => ({ ...prev, source_rule_id: e.target.value }))}
                                className={inputClass}
                            >
                                <option value="">Select source rule...</option>
                                {playbook.rules.map((r: PlaybookRule) => (
                                    <option key={r.id} value={r.id}>{r.clause_type}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={labelClass}>Target Rule</label>
                            <select
                                value={newDep.target_rule_id}
                                onChange={(e) => setNewDep(prev => ({ ...prev, target_rule_id: e.target.value }))}
                                className={inputClass}
                            >
                                <option value="">Select target rule...</option>
                                {playbook.rules.map((r: PlaybookRule) => (
                                    <option key={r.id} value={r.id}>{r.clause_type}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={labelClass}>Trigger Condition</label>
                            <select
                                value={newDep.trigger_condition}
                                onChange={(e) => setNewDep(prev => ({ ...prev, trigger_condition: e.target.value }))}
                                className={inputClass}
                            >
                                {TRIGGER_CONDITIONS.map(tc => (
                                    <option key={tc.value} value={tc.value}>{tc.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={labelClass}>Effect</label>
                            <select
                                value={newDep.effect}
                                onChange={(e) => setNewDep(prev => ({ ...prev, effect: e.target.value }))}
                                className={inputClass}
                            >
                                {EFFECTS.map(ef => (
                                    <option key={ef.value} value={ef.value}>{ef.label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="md:col-span-2">
                            <label className={labelClass}>Effect Parameters (JSON)</label>
                            <textarea
                                value={newDep.effect_params}
                                onChange={(e) => setNewDep(prev => ({ ...prev, effect_params: e.target.value }))}
                                className={`${inputClass} min-h-[80px] font-mono text-xs`}
                                placeholder='{"new_risk_level": "red"}'
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-100">
                        <button
                            onClick={() => setShowAddDep(false)}
                            className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createDepMutation.mutate()}
                            disabled={!newDep.source_rule_id || !newDep.target_rule_id || createDepMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                        >
                            {createDepMutation.isPending ? 'Creating...' : 'Create Dependency'}
                        </button>
                    </div>
                </div>
            )}

            {/* Dependencies List */}
            {dependencies && dependencies.length > 0 ? (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Source Rule</th>
                                <th scope="col" className="text-center px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide"></th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Target Rule</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Trigger</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Effect</th>
                                <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dependencies.map((dep: RuleDependency) => (
                                <tr key={dep.id} className="border-b border-slate-100">
                                    <td className="px-6 py-4">
                                        <span className="font-semibold text-sm text-slate-900">{getRuleName(dep.source_rule_id)}</span>
                                    </td>
                                    <td className="px-2 py-4 text-center">
                                        <svg width="20" height="20" fill="none" stroke="#94a3b8" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                        </svg>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="font-semibold text-sm text-slate-900">{getRuleName(dep.target_rule_id)}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="px-2.5 py-1 text-xs font-medium rounded-md bg-purple-50 text-purple-600">
                                            {TRIGGER_CONDITIONS.find(tc => tc.value === dep.trigger_condition)?.label || dep.trigger_condition}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="px-2.5 py-1 text-xs font-medium rounded-md bg-blue-50 text-blue-600">
                                            {EFFECTS.find(ef => ef.value === dep.effect)?.label || dep.effect}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button
                                            onClick={() => { if (confirm('Delete this dependency?')) deleteDepMutation.mutate(dep.id); }}
                                            className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
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
                <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                    <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No dependencies yet</h3>
                    <p className="text-sm text-slate-500 mb-6">Define cross-clause dependencies to link related rules together.</p>
                    <button
                        onClick={() => setShowAddDep(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                        Add Dependency
                    </button>
                </div>
            )}
        </>
    );

    const renderHistoryTab = () => (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Version History ({versions?.length || 0})</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Track changes and rollback to previous versions of this playbook.
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateSnapshot(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Create Snapshot
                </button>
            </div>

            {/* Create Snapshot Form */}
            {showCreateSnapshot && (
                <div className="bg-white rounded-xl border border-slate-200 p-7 mb-6">
                    <h3 className="text-base font-bold text-slate-900 mb-5">Create Version Snapshot</h3>
                    <div>
                        <label className={labelClass}>Change Summary</label>
                        <input
                            type="text"
                            value={snapshotSummary}
                            onChange={(e) => setSnapshotSummary(e.target.value)}
                            className={inputClass}
                            placeholder="e.g., Added liability cap rules for enterprise deals"
                        />
                    </div>
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-100">
                        <button
                            onClick={() => { setShowCreateSnapshot(false); setSnapshotSummary(''); }}
                            className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createSnapshotMutation.mutate()}
                            disabled={!snapshotSummary.trim() || createSnapshotMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                        >
                            {createSnapshotMutation.isPending ? 'Creating...' : 'Save Snapshot'}
                        </button>
                    </div>
                </div>
            )}

            {/* Versions List */}
            {versions && versions.length > 0 ? (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Version</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Summary</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
                                <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {versions.map((version: PlaybookVersionSummary) => (
                                <tr key={version.id} className="border-b border-slate-100">
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-sm font-bold text-slate-900">
                                            {version.version_number}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-sm text-slate-900">{version.change_summary || 'No summary'}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-[13px] text-slate-500">
                                            {new Date(version.created_at).toLocaleDateString('en-US', {
                                                year: 'numeric', month: 'short', day: 'numeric',
                                                hour: '2-digit', minute: '2-digit',
                                            })}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button
                                            onClick={() => {
                                                if (confirm(`Rollback to version ${version.version_number}? This will overwrite current rules, conditions, and dependencies.`)) {
                                                    rollbackMutation.mutate(version.id);
                                                }
                                            }}
                                            disabled={rollbackMutation.isPending}
                                            className="text-[13px] font-semibold text-amber-600 bg-transparent border-none cursor-pointer hover:text-amber-700 disabled:opacity-50"
                                        >
                                            {rollbackMutation.isPending ? 'Rolling back...' : 'Rollback'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                    <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">No version history</h3>
                    <p className="text-sm text-slate-500 mb-6">Create a snapshot to save the current state of this playbook.</p>
                    <button
                        onClick={() => setShowCreateSnapshot(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                    >
                        Create Snapshot
                    </button>
                </div>
            )}
        </>
    );

    const renderAnalyticsTab = () => (
        <div className="text-center py-24 px-8 bg-white rounded-xl border border-slate-200">
            <svg width="64" height="64" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-6">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Analytics dashboard coming in Phase 9</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
                Track rule hit rates, most flagged clauses, condition trigger frequency, and negotiation tier usage across all scans using this playbook.
            </p>
        </div>
    );

    // ══════════════════════════════════════════════════════════════════════
    // Main Render
    // ══════════════════════════════════════════════════════════════════════

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader activePage="playbooks" />

            {/* Breadcrumb */}
            <div className="bg-white border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-8 h-12 flex items-center gap-2 text-sm">
                    <Link to="/playbooks" className="text-slate-500 no-underline font-medium hover:text-slate-700">
                        Playbooks
                    </Link>
                    <span className="text-slate-300">/</span>
                    <span className="font-semibold text-slate-900">{playbook.name}</span>
                    <span className={`ml-2 px-2.5 py-0.5 text-xs font-semibold rounded-md ${
                        playbook.is_public ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500'
                    }`}>
                        {playbook.is_public ? 'Public' : 'Private'}
                    </span>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="bg-white border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-8">
                    <nav className="flex gap-8">
                        {TABS.map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`relative py-3.5 text-sm font-medium bg-transparent border-none cursor-pointer transition-colors ${
                                    activeTab === tab.key
                                        ? 'text-slate-900'
                                        : 'text-slate-400 hover:text-slate-600'
                                }`}
                            >
                                {tab.label}
                                {activeTab === tab.key && (
                                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 rounded-full" />
                                )}
                            </button>
                        ))}
                    </nav>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-8 py-10">
                {activeTab === 'rules' && renderRulesTab()}
                {activeTab === 'conditions' && renderConditionsTab()}
                {activeTab === 'dependencies' && renderDependenciesTab()}
                {activeTab === 'history' && renderHistoryTab()}
                {activeTab === 'analytics' && renderAnalyticsTab()}
            </main>
        </div>
    );
}

// ══════════════════════════════════════════════════════════════════════════════
// RuleRow sub-component (keeps the main component cleaner)
// ══════════════════════════════════════════════════════════════════════════════

interface RuleRowProps {
    rule: PlaybookRule;
    riskLevel: { value: string; label: string; className: string };
    isExpanded: boolean;
    tiersLoading: boolean;
    tiers: RuleTier[] | undefined;
    tierDrafts: Record<number, { position_text: string; guidance_notes: string; risk_level_at_tier: string }>;
    onToggleExpand: () => void;
    onDelete: () => void;
    onSyncTiers: () => void;
    onTierChange: (level: number, field: string, value: string) => void;
    onSaveTiers: () => void;
    tiersSaving: boolean;
}

function RuleRow({
    rule, riskLevel, isExpanded, tiersLoading, tiers, tierDrafts,
    onToggleExpand, onDelete, onSyncTiers, onTierChange, onSaveTiers, tiersSaving,
}: RuleRowProps) {
    // Sync tier drafts when tiers finish loading
    const prevTiersRef = useState<RuleTier[] | undefined>(undefined);
    if (isExpanded && tiers && tiers !== prevTiersRef[0] && Object.keys(tierDrafts).length === 0) {
        prevTiersRef[0] = tiers;
        // schedule sync for next microtask to avoid setState during render
        Promise.resolve().then(onSyncTiers);
    }

    return (
        <>
            <tr
                className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${isExpanded ? 'bg-slate-50' : ''}`}
                onClick={onToggleExpand}
            >
                <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                        <svg
                            width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            className={`transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        <span className="font-semibold text-slate-900 text-sm">{rule.clause_type}</span>
                        {rule.is_deal_breaker && (
                            <span className="ml-1 text-[11px] font-bold bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                                DEAL BREAKER
                            </span>
                        )}
                        {rule.detection_mode && rule.detection_mode !== 'keywords_only' && (
                            <span className={`ml-1 px-1.5 py-0.5 text-xs rounded ${
                                rule.detection_mode === 'ai_only'
                                    ? 'bg-purple-50 text-purple-600'
                                    : 'bg-blue-50 text-blue-600'
                            }`}>
                                {rule.detection_mode === 'ai_only' ? 'AI' : 'AI+KW'}
                            </span>
                        )}
                    </div>
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
                        onClick={(e) => { e.stopPropagation(); onDelete(); }}
                        className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
                    >
                        Delete
                    </button>
                </td>
            </tr>

            {/* Expanded Tier Accordion */}
            {isExpanded && (
                <tr>
                    <td colSpan={5} className="px-0 py-0">
                        <div className="bg-slate-50 border-b border-slate-200 px-10 py-6">
                            <h4 className="text-sm font-bold text-slate-900 mb-4">Negotiation Tiers</h4>
                            {tiersLoading ? (
                                <div className="flex items-center gap-2 py-4">
                                    <div className="w-4 h-4 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
                                    <span className="text-sm text-slate-500">Loading tiers...</span>
                                </div>
                            ) : (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {[1, 2, 3, 4].map(level => {
                                            const draft = tierDrafts[level] || { position_text: '', guidance_notes: '', risk_level_at_tier: 'green' };
                                            const tierLabel = TIER_LABELS[level - 1];
                                            const tierColors: Record<number, string> = {
                                                1: 'border-l-green-500',
                                                2: 'border-l-blue-500',
                                                3: 'border-l-amber-500',
                                                4: 'border-l-red-500',
                                            };
                                            return (
                                                <div key={level} className={`bg-white rounded-lg border border-slate-200 border-l-4 ${tierColors[level]} p-4`}>
                                                    <div className="flex items-center justify-between mb-3">
                                                        <span className="text-[13px] font-bold text-slate-900">{tierLabel}</span>
                                                        <select
                                                            value={draft.risk_level_at_tier}
                                                            onChange={(e) => onTierChange(level, 'risk_level_at_tier', e.target.value)}
                                                            className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-700 outline-none bg-white focus:ring-1 focus:ring-slate-900"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            {RISK_LEVELS.map(rl => (
                                                                <option key={rl.value} value={rl.value}>{rl.label}</option>
                                                            ))}
                                                        </select>
                                                    </div>
                                                    <div className="mb-3">
                                                        <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Position Text</label>
                                                        <textarea
                                                            value={draft.position_text}
                                                            onChange={(e) => onTierChange(level, 'position_text', e.target.value)}
                                                            onClick={(e) => e.stopPropagation()}
                                                            className={`${inputClass} min-h-[60px] text-xs`}
                                                            placeholder={`${tierLabel} position language...`}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Guidance Notes</label>
                                                        <textarea
                                                            value={draft.guidance_notes}
                                                            onChange={(e) => onTierChange(level, 'guidance_notes', e.target.value)}
                                                            onClick={(e) => e.stopPropagation()}
                                                            className={`${inputClass} min-h-[60px] text-xs`}
                                                            placeholder="Internal guidance for negotiators..."
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    <div className="flex justify-end mt-4">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onSaveTiers(); }}
                                            disabled={tiersSaving}
                                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                                        >
                                            {tiersSaving ? 'Saving...' : 'Save Tiers'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}
