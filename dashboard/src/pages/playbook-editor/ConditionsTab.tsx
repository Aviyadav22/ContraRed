import { type PlaybookRule, type PlaybookCondition } from '@/api/client';
import { type UseMutationResult } from '@tanstack/react-query';
import { RISK_LEVELS, CONDITION_TYPES, OPERATORS, inputClass, labelClass } from './constants';
import { ConditionValueEditor } from './ConditionValueEditor';
import { ConditionPreview } from './ConditionPreview';

export interface ConditionsTabProps {
    conditions: PlaybookCondition[] | undefined;
    rules: PlaybookRule[];
    showAddCondition: boolean;
    setShowAddCondition: (v: boolean) => void;
    newCondition: {
        name: string;
        description: string;
        condition_type: string;
        operator: string;
        condition_value: string;
        is_active: boolean;
        priority: number;
    };
    setNewCondition: React.Dispatch<React.SetStateAction<{
        name: string;
        description: string;
        condition_type: string;
        operator: string;
        condition_value: string;
        is_active: boolean;
        priority: number;
    }>>;
    expandedConditionId: string | null;
    setExpandedConditionId: (v: string | null) => void;
    showAddOverride: string | null;
    setShowAddOverride: (v: string | null) => void;
    newOverride: {
        rule_id: string;
        override_risk_level: string;
        override_position_text: string;
        suppress_rule: boolean;
    };
    setNewOverride: React.Dispatch<React.SetStateAction<{
        rule_id: string;
        override_risk_level: string;
        override_position_text: string;
        suppress_rule: boolean;
    }>>;
    createConditionMutation: UseMutationResult<PlaybookCondition, Error, void>;
    deleteConditionMutation: UseMutationResult<void, Error, string>;
    addOverrideMutation: UseMutationResult<unknown, Error, string>;
}

export function ConditionsTab({
    conditions, rules,
    showAddCondition, setShowAddCondition,
    newCondition, setNewCondition,
    expandedConditionId, setExpandedConditionId,
    showAddOverride, setShowAddOverride,
    newOverride, setNewOverride,
    createConditionMutation, deleteConditionMutation, addOverrideMutation,
}: ConditionsTabProps) {
    return (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-[var(--text-primary)]">Conditions ({conditions?.length || 0})</h1>
                    <p className="text-sm text-[var(--text-muted)] mt-1">
                        Deal context conditions that modify rule behavior based on counterparty, deal size, jurisdiction, or contract side.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddCondition(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-[var(--accent)] text-white text-sm font-semibold rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Add Condition
                </button>
            </div>

            {/* Add Condition Form */}
            {showAddCondition && (
                <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] p-7 mb-6">
                    <h3 className="text-base font-bold text-[var(--text-primary)] mb-5">New Condition</h3>
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
                                onChange={(e) => setNewCondition(prev => ({
                                    ...prev,
                                    condition_type: e.target.value,
                                    operator: e.target.value === 'deal_size' ? 'between' : 'equals',
                                    condition_value: '{}',
                                }))}
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
                                onChange={(e) => setNewCondition(prev => ({
                                    ...prev,
                                    operator: e.target.value,
                                    condition_value: '{}',
                                }))}
                                className={inputClass}
                            >
                                {newCondition.condition_type === 'deal_size' ? (
                                    <>
                                        <option value="between">Between</option>
                                        <option value="greater_than">Greater than</option>
                                        <option value="less_than">Less than</option>
                                        <option value="equals">Equals</option>
                                    </>
                                ) : (
                                    <>
                                        <option value="equals">Equals</option>
                                        <option value="not_equals">Not equals</option>
                                        <option value="in">In (any of)</option>
                                        <option value="contains">Contains</option>
                                    </>
                                )}
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
                            <ConditionValueEditor
                                conditionType={newCondition.condition_type}
                                operator={newCondition.operator}
                                value={newCondition.condition_value}
                                onChange={(val) => setNewCondition(prev => ({ ...prev, condition_value: val }))}
                            />
                            <ConditionPreview condition={newCondition} />
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
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-[var(--border)]">
                        <button
                            onClick={() => setShowAddCondition(false)}
                            className="px-5 py-2.5 text-sm font-medium text-[var(--text-muted)] bg-transparent border border-[var(--border)] rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createConditionMutation.mutate()}
                            disabled={!newCondition.name || createConditionMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
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
                        <div key={condition.id} className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] overflow-hidden">
                            <div
                                className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-[var(--bg-surface)] transition-colors"
                                onClick={() => setExpandedConditionId(expandedConditionId === condition.id ? null : condition.id)}
                            >
                                <div className="flex items-center gap-4">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-sm text-[var(--text-primary)]">{condition.name}</span>
                                            <span className={`px-2 py-0.5 text-[11px] font-semibold rounded ${condition.is_active ? 'bg-green-50 text-green-600' : 'bg-[var(--bg-elevated)] text-[var(--text-muted)]'}`}>
                                                {condition.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-[var(--text-muted)] mt-0.5">
                                            {CONDITION_TYPES.find(ct => ct.value === condition.condition_type)?.label || condition.condition_type}
                                            {' '}{OPERATORS.find(op => op.value === condition.operator)?.label || condition.operator}
                                            {' '}
                                            <span className="font-mono">{JSON.stringify(condition.condition_value)}</span>
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="text-xs text-[var(--text-muted)]">{condition.overrides_count} override{condition.overrides_count !== 1 ? 's' : ''}</span>
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
                                <div className="border-t border-[var(--border)] px-6 py-5 bg-[var(--bg-surface)]">
                                    <div className="flex justify-between items-center mb-4">
                                        <h4 className="text-sm font-semibold text-[var(--text-primary)]">Rule Overrides</h4>
                                        <button
                                            onClick={() => setShowAddOverride(showAddOverride === condition.id ? null : condition.id)}
                                            className="text-xs font-semibold text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border)] px-3 py-1.5 rounded-lg hover:bg-[var(--bg-elevated)] transition-colors"
                                        >
                                            + Add Override
                                        </button>
                                    </div>

                                    {/* Add Override Form */}
                                    {showAddOverride === condition.id && (
                                        <div className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border)] p-5 mb-4">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className={labelClass}>Target Rule</label>
                                                    <select
                                                        value={newOverride.rule_id}
                                                        onChange={(e) => setNewOverride(prev => ({ ...prev, rule_id: e.target.value }))}
                                                        className={inputClass}
                                                    >
                                                        <option value="">Select a rule...</option>
                                                        {rules.map((r: PlaybookRule) => (
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
                                                        className="w-4 h-4 accent-[var(--accent)] cursor-pointer"
                                                    />
                                                    <label htmlFor={`suppress-${condition.id}`} className="text-sm font-medium text-[var(--text-primary)] cursor-pointer">
                                                        Suppress Rule
                                                    </label>
                                                </div>
                                            </div>
                                            <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-[var(--border)]">
                                                <button
                                                    onClick={() => setShowAddOverride(null)}
                                                    className="px-4 py-2 text-sm font-medium text-[var(--text-muted)] bg-transparent border border-[var(--border)] rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    onClick={() => addOverrideMutation.mutate(condition.id)}
                                                    disabled={!newOverride.rule_id || addOverrideMutation.isPending}
                                                    className="px-4 py-2 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
                                                >
                                                    {addOverrideMutation.isPending ? 'Adding...' : 'Add Override'}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {condition.overrides_count === 0 && showAddOverride !== condition.id && (
                                        <p className="text-xs text-[var(--text-muted)] italic">No overrides configured for this condition.</p>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-16 px-8 bg-[var(--bg-surface)] rounded-xl border border-[var(--border)]">
                    <svg width="48" height="48" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                    </svg>
                    <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">No conditions yet</h3>
                    <p className="text-sm text-[var(--text-muted)] mb-6">Add conditions to dynamically adjust rules based on deal context.</p>
                    <button
                        onClick={() => setShowAddCondition(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                    >
                        Add Condition
                    </button>
                </div>
            )}
        </>
    );
}
