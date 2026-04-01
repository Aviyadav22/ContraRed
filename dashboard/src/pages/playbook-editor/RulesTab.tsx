import { type PlaybookRule, type CreateRuleData, type RuleTier } from '@/api/client';
import { type UseMutationResult } from '@tanstack/react-query';
import { RISK_LEVELS, MATCH_TYPES, DETECTION_MODES, inputClass, labelClass } from './constants';
import { RuleRow } from './RuleRow';

export interface RulesTabProps {
    rules: PlaybookRule[];
    showAddRule: boolean;
    setShowAddRule: (v: boolean) => void;
    editingRuleId: string | null;
    setEditingRuleId: (v: string | null) => void;
    newRule: CreateRuleData;
    setNewRule: React.Dispatch<React.SetStateAction<CreateRuleData>>;
    patternInput: string;
    setPatternInput: (v: string) => void;
    expandedRuleId: string | null;
    tiersLoading: boolean;
    tiers: RuleTier[] | undefined;
    tierDrafts: Record<number, { position_text: string; guidance_notes: string; risk_level_at_tier: string }>;
    setTierDrafts: React.Dispatch<React.SetStateAction<Record<number, { position_text: string; guidance_notes: string; risk_level_at_tier: string }>>>;
    handleAddPattern: () => void;
    handleRemovePattern: (index: number) => void;
    handleExpandRule: (ruleId: string) => void;
    syncTierDrafts: (fetchedTiers: RuleTier[] | undefined) => void;
    addRuleMutation: UseMutationResult<PlaybookRule, Error, CreateRuleData>;
    updateRuleMutation: UseMutationResult<PlaybookRule, Error, { ruleId: string; data: Partial<CreateRuleData> }>;
    deleteRuleMutation: UseMutationResult<void, Error, string>;
    upsertTiersMutation: UseMutationResult<RuleTier[], Error, string>;
}

export function RulesTab({
    rules,
    showAddRule, setShowAddRule,
    editingRuleId, setEditingRuleId,
    newRule, setNewRule,
    patternInput, setPatternInput,
    expandedRuleId,
    tiersLoading, tiers, tierDrafts, setTierDrafts,
    handleAddPattern, handleRemovePattern, handleExpandRule, syncTierDrafts,
    addRuleMutation, updateRuleMutation, deleteRuleMutation, upsertTiersMutation,
}: RulesTabProps) {
    return (
        <>
            {/* Title row */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Rules ({rules.length})</h1>
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
                    <h3 className="text-base font-bold text-slate-900 mb-5">{editingRuleId ? 'Edit Rule' : 'New Detection Rule'}</h3>
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
                            onClick={() => { setShowAddRule(false); setEditingRuleId(null); setNewRule({ clause_type: '', primary_position: '', risk_level: 'yellow', match_type: 'exact', is_deal_breaker: false, detection_patterns: [], detection_mode: 'keywords_only' }); setPatternInput(''); }}
                            className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => {
                                if (editingRuleId) {
                                    updateRuleMutation.mutate({ ruleId: editingRuleId, data: newRule });
                                } else {
                                    addRuleMutation.mutate(newRule);
                                }
                            }}
                            disabled={!newRule.clause_type || !newRule.primary_position || addRuleMutation.isPending || updateRuleMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                        >
                            {editingRuleId
                                ? (updateRuleMutation.isPending ? 'Saving...' : 'Save Rule')
                                : (addRuleMutation.isPending ? 'Adding...' : 'Add Rule')}
                        </button>
                    </div>
                </div>
            )}

            {/* Rules Table */}
            {rules.length > 0 ? (
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
                            {rules.map((rule: PlaybookRule) => {
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
                                        onEdit={() => {
                                            setEditingRuleId(rule.id);
                                            setNewRule({
                                                clause_type: rule.clause_type,
                                                primary_position: rule.primary_position,
                                                risk_level: rule.risk_level,
                                                match_type: rule.match_type,
                                                is_deal_breaker: rule.is_deal_breaker,
                                                detection_patterns: [...(rule.detection_patterns || [])],
                                                detection_mode: rule.detection_mode || 'keywords_only',
                                                risk_description: rule.risk_description || '',
                                                acceptable_position: rule.acceptable_position || '',
                                            });
                                            setPatternInput('');
                                            setShowAddRule(true);
                                        }}
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
                    <svg width="48" height="48" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-4">
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
}
