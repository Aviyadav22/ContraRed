import { type PlaybookRule, type RuleDependency } from '@/api/client';
import { type UseMutationResult } from '@tanstack/react-query';
import { TRIGGER_CONDITIONS, EFFECTS, inputClass, labelClass } from './constants';
import { DependencyParamsEditor } from './DependencyParamsEditor';

export interface DependenciesTabProps {
    dependencies: RuleDependency[] | undefined;
    rules: PlaybookRule[];
    showAddDep: boolean;
    setShowAddDep: (v: boolean) => void;
    newDep: {
        source_rule_id: string;
        target_rule_id: string;
        trigger_condition: string;
        effect: string;
        effect_params: string;
        is_active: boolean;
    };
    setNewDep: React.Dispatch<React.SetStateAction<{
        source_rule_id: string;
        target_rule_id: string;
        trigger_condition: string;
        effect: string;
        effect_params: string;
        is_active: boolean;
    }>>;
    getRuleName: (ruleId: string) => string;
    createDepMutation: UseMutationResult<RuleDependency, Error, void>;
    deleteDepMutation: UseMutationResult<void, Error, string>;
}

export function DependenciesTab({
    dependencies, rules,
    showAddDep, setShowAddDep,
    newDep, setNewDep,
    getRuleName,
    createDepMutation, deleteDepMutation,
}: DependenciesTabProps) {
    return (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-[var(--text-primary)]">Dependencies ({dependencies?.length || 0})</h1>
                    <p className="text-sm text-[var(--text-muted)] mt-1">
                        Cross-clause dependency graph. Define how one rule's outcome affects another.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddDep(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-[var(--accent)] text-white text-sm font-semibold rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Add Dependency
                </button>
            </div>

            {/* Add Dependency Form */}
            {showAddDep && (
                <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] p-7 mb-6">
                    <h3 className="text-base font-bold text-[var(--text-primary)] mb-5">New Dependency</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className={labelClass}>Source Rule</label>
                            <select
                                value={newDep.source_rule_id}
                                onChange={(e) => setNewDep(prev => ({ ...prev, source_rule_id: e.target.value }))}
                                className={inputClass}
                            >
                                <option value="">Select source rule...</option>
                                {rules.map((r: PlaybookRule) => (
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
                                {rules.map((r: PlaybookRule) => (
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
                            <label className={labelClass}>Effect Parameters</label>
                            <DependencyParamsEditor
                                effect={newDep.effect}
                                value={newDep.effect_params}
                                onChange={(val) => setNewDep(prev => ({ ...prev, effect_params: val }))}
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-[var(--border)]">
                        <button
                            onClick={() => setShowAddDep(false)}
                            className="px-5 py-2.5 text-sm font-medium text-[var(--text-muted)] bg-transparent border border-[var(--border)] rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createDepMutation.mutate()}
                            disabled={!newDep.source_rule_id || !newDep.target_rule_id || createDepMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
                        >
                            {createDepMutation.isPending ? 'Creating...' : 'Create Dependency'}
                        </button>
                    </div>
                </div>
            )}

            {/* Dependencies List */}
            {dependencies && dependencies.length > 0 ? (
                <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] overflow-hidden">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-[var(--bg-surface)] border-b border-[var(--border)]">
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Source Rule</th>
                                <th scope="col" className="text-center px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide"></th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Target Rule</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Trigger</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Effect</th>
                                <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dependencies.map((dep: RuleDependency) => (
                                <tr key={dep.id} className="border-b border-[var(--border)]">
                                    <td className="px-6 py-4">
                                        <span className="font-semibold text-sm text-[var(--text-primary)]">{getRuleName(dep.source_rule_id)}</span>
                                    </td>
                                    <td className="px-2 py-4 text-center">
                                        <svg width="20" height="20" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                        </svg>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="font-semibold text-sm text-[var(--text-primary)]">{getRuleName(dep.target_rule_id)}</span>
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
                <div className="text-center py-16 px-8 bg-[var(--bg-surface)] rounded-xl border border-[var(--border)]">
                    <svg width="48" height="48" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">No dependencies yet</h3>
                    <p className="text-sm text-[var(--text-muted)] mb-6">Define cross-clause dependencies to link related rules together.</p>
                    <button
                        onClick={() => setShowAddDep(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                    >
                        Add Dependency
                    </button>
                </div>
            )}
        </>
    );
}
