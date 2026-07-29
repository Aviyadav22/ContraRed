import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import {
    getPlaybook, getPlaybookQuality, addRule, updateRule, deleteRule,
    listTiers, upsertTiers,
    listConditions, createCondition, deleteCondition, addOverride,
    listDependencies, createDependency, deleteDependency,
    listVersions, createVersionSnapshot, rollbackToVersion,
    type CreateRuleData,
    type RuleTier,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { TABS } from './constants';
import { RulesTab } from './RulesTab';
import { ConditionsTab } from './ConditionsTab';
import { DependenciesTab } from './DependenciesTab';
import { HistoryTab } from './HistoryTab';
import { AnalyticsTab } from './AnalyticsTab';

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
    const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
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

    const { data: quality } = useQuery({
        queryKey: ['playbook-quality', id],
        queryFn: () => getPlaybookQuality(id!),
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
            queryClient.invalidateQueries({ queryKey: ['playbook-quality', id] });
            setShowAddRule(false);
            setNewRule({ clause_type: '', primary_position: '', risk_level: 'yellow', match_type: 'exact', is_deal_breaker: false, detection_patterns: [], detection_mode: 'keywords_only' });
            setPatternInput('');
        },
    });

    const deleteRuleMutation = useMutation({
        mutationFn: (ruleId: string) => deleteRule(id!, ruleId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            queryClient.invalidateQueries({ queryKey: ['playbook-quality', id] });
        },
    });

    const updateRuleMutation = useMutation({
        mutationFn: ({ ruleId, data }: { ruleId: string; data: Partial<CreateRuleData> }) =>
            updateRule(id!, ruleId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            queryClient.invalidateQueries({ queryKey: ['playbook-quality', id] });
            setShowAddRule(false);
            setEditingRuleId(null);
            setNewRule({ clause_type: '', primary_position: '', risk_level: 'yellow', match_type: 'exact', is_deal_breaker: false, detection_patterns: [], detection_mode: 'keywords_only' });
            setPatternInput('');
        },
        onError: () => alert('Failed to update rule.'),
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
        onError: () => alert('Failed to save tiers. Please try again.'),
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
        onError: () => alert('Failed to create condition.'),
    });

    const deleteConditionMutation = useMutation({
        mutationFn: (conditionId: string) => deleteCondition(id!, conditionId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conditions', id] }),
        onError: () => alert('Failed to delete condition.'),
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
        onError: () => alert('Failed to create dependency.'),
    });

    const deleteDepMutation = useMutation({
        mutationFn: (depId: string) => deleteDependency(id!, depId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dependencies', id] }),
        onError: () => alert('Failed to delete dependency.'),
    });

    const createSnapshotMutation = useMutation({
        mutationFn: () => createVersionSnapshot(id!, snapshotSummary),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', id] });
            setShowCreateSnapshot(false);
            setSnapshotSummary('');
        },
        onError: () => alert('Failed to create snapshot.'),
    });

    const rollbackMutation = useMutation({
        mutationFn: (versionId: string) => rollbackToVersion(id!, versionId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['playbook', id] });
            queryClient.invalidateQueries({ queryKey: ['versions', id] });
        },
        onError: () => alert('Rollback failed. Your playbook was not changed.'),
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
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-app)' }}>
                <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            </div>
        );
    }

    if (error || !playbook) {
        return (
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-app)' }}>
                <div style={{ textAlign: 'center' }}>
                    <p style={{ color: 'var(--risk-critical)', marginBottom: 16 }}>Error loading playbook</p>
                    <button onClick={() => navigate('/playbooks')} style={{ color: 'var(--info)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                        Back to Playbooks
                    </button>
                </div>
            </div>
        );
    }

    // ══════════════════════════════════════════════════════════════════════
    // Main Render
    // ══════════════════════════════════════════════════════════════════════

    return (
        <AppLayout>

            {/* Breadcrumb */}
            <div className="bg-[var(--bg-surface)] border-b border-[var(--border)]">
                <div className="max-w-7xl mx-auto px-8 h-12 flex items-center gap-2 text-sm">
                    <Link to="/playbooks" className="text-[var(--text-muted)] no-underline font-medium hover:text-[var(--text-primary)]">
                        Playbooks
                    </Link>
                    <span className="text-[var(--text-muted)]">/</span>
                    <span className="font-semibold text-[var(--text-primary)]">{playbook.name}</span>
                    <span className={`ml-2 px-2.5 py-0.5 text-xs font-semibold rounded-md ${
                        playbook.is_public ? 'bg-green-50 text-green-600' : 'bg-[var(--bg-elevated)] text-[var(--text-muted)]'
                    }`}>
                        {playbook.is_public ? 'Public' : 'Private'}
                    </span>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="bg-[var(--bg-surface)] border-b border-[var(--border)]">
                <div className="max-w-7xl mx-auto px-8">
                    <nav className="flex gap-8">
                        {TABS.map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`relative py-3.5 text-sm font-medium bg-transparent border-none cursor-pointer transition-colors ${
                                    activeTab === tab.key
                                        ? 'text-[var(--text-primary)]'
                                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                                }`}
                            >
                                {tab.label}
                                {activeTab === tab.key && (
                                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent)] rounded-full" />
                                )}
                            </button>
                        ))}
                    </nav>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-8 py-10">
                {quality && (
                    <section className={`mb-8 rounded-xl border p-5 ${
                        quality.publishable
                            ? 'border-green-200 bg-green-50'
                            : 'border-amber-200 bg-amber-50'
                    }`}>
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <h2 className="m-0 text-sm font-bold text-[var(--text-primary)]">
                                    {quality.publishable ? 'Ready to publish' : 'Playbook needs legal context'}
                                </h2>
                                <p className="mt-1 mb-0 text-sm text-[var(--text-secondary)]">
                                    {quality.publishable
                                        ? `${quality.rules_count} rule${quality.rules_count === 1 ? '' : 's'} can be used for review.`
                                        : 'Resolve the blocking items below before sharing this playbook.'}
                                </p>
                            </div>
                            <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                                quality.publishable ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-800'
                            }`}>
                                {quality.publishable ? 'Publishable' : `${quality.issues.length} blocking`}
                            </span>
                        </div>
                        {quality.issues.length > 0 && (
                            <ul className="mt-4 mb-0 space-y-1.5 pl-5 text-sm text-amber-900">
                                {quality.issues.slice(0, 8).map(issue => <li key={issue}>{issue}</li>)}
                                {quality.issues.length > 8 && (
                                    <li>{quality.issues.length - 8} more blocking items</li>
                                )}
                            </ul>
                        )}
                        {quality.recommendations.length > 0 && (
                            <details className="mt-4 text-sm text-[var(--text-secondary)]">
                                <summary className="cursor-pointer font-semibold">
                                    {quality.recommendations.length} recommended improvement{quality.recommendations.length === 1 ? '' : 's'}
                                </summary>
                                <ul className="mt-2 mb-0 space-y-1.5 pl-5">
                                    {quality.recommendations.slice(0, 8).map(item => <li key={item}>{item}</li>)}
                                    {quality.recommendations.length > 8 && (
                                        <li>{quality.recommendations.length - 8} more recommendations</li>
                                    )}
                                </ul>
                            </details>
                        )}
                    </section>
                )}
                {activeTab === 'rules' && (
                    <RulesTab
                        rules={playbook.rules}
                        showAddRule={showAddRule}
                        setShowAddRule={setShowAddRule}
                        editingRuleId={editingRuleId}
                        setEditingRuleId={setEditingRuleId}
                        newRule={newRule}
                        setNewRule={setNewRule}
                        patternInput={patternInput}
                        setPatternInput={setPatternInput}
                        expandedRuleId={expandedRuleId}
                        tiersLoading={tiersLoading}
                        tiers={tiers}
                        tierDrafts={tierDrafts}
                        setTierDrafts={setTierDrafts}
                        handleAddPattern={handleAddPattern}
                        handleRemovePattern={handleRemovePattern}
                        handleExpandRule={handleExpandRule}
                        syncTierDrafts={syncTierDrafts}
                        addRuleMutation={addRuleMutation}
                        updateRuleMutation={updateRuleMutation}
                        deleteRuleMutation={deleteRuleMutation}
                        upsertTiersMutation={upsertTiersMutation}
                    />
                )}
                {activeTab === 'conditions' && (
                    <ConditionsTab
                        conditions={conditions}
                        rules={playbook.rules}
                        showAddCondition={showAddCondition}
                        setShowAddCondition={setShowAddCondition}
                        newCondition={newCondition}
                        setNewCondition={setNewCondition}
                        expandedConditionId={expandedConditionId}
                        setExpandedConditionId={setExpandedConditionId}
                        showAddOverride={showAddOverride}
                        setShowAddOverride={setShowAddOverride}
                        newOverride={newOverride}
                        setNewOverride={setNewOverride}
                        createConditionMutation={createConditionMutation}
                        deleteConditionMutation={deleteConditionMutation}
                        addOverrideMutation={addOverrideMutation}
                    />
                )}
                {activeTab === 'dependencies' && (
                    <DependenciesTab
                        dependencies={dependencies}
                        rules={playbook.rules}
                        showAddDep={showAddDep}
                        setShowAddDep={setShowAddDep}
                        newDep={newDep}
                        setNewDep={setNewDep}
                        getRuleName={getRuleName}
                        createDepMutation={createDepMutation}
                        deleteDepMutation={deleteDepMutation}
                    />
                )}
                {activeTab === 'history' && (
                    <HistoryTab
                        versions={versions}
                        showCreateSnapshot={showCreateSnapshot}
                        setShowCreateSnapshot={setShowCreateSnapshot}
                        snapshotSummary={snapshotSummary}
                        setSnapshotSummary={setSnapshotSummary}
                        createSnapshotMutation={createSnapshotMutation}
                        rollbackMutation={rollbackMutation}
                    />
                )}
                {activeTab === 'analytics' && <AnalyticsTab />}
            </main>
        </AppLayout>
    );
}
