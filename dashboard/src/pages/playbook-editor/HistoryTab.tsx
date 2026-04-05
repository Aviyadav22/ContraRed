import { type PlaybookVersionSummary } from '@/api/client';
import { type UseMutationResult } from '@tanstack/react-query';
import { inputClass, labelClass } from './constants';

export interface HistoryTabProps {
    versions: PlaybookVersionSummary[] | undefined;
    showCreateSnapshot: boolean;
    setShowCreateSnapshot: (v: boolean) => void;
    snapshotSummary: string;
    setSnapshotSummary: (v: string) => void;
    createSnapshotMutation: UseMutationResult<PlaybookVersionSummary, Error, void>;
    rollbackMutation: UseMutationResult<void, Error, string>;
}

export function HistoryTab({
    versions,
    showCreateSnapshot, setShowCreateSnapshot,
    snapshotSummary, setSnapshotSummary,
    createSnapshotMutation, rollbackMutation,
}: HistoryTabProps) {
    return (
        <>
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-[var(--text-primary)]">Version History ({versions?.length || 0})</h1>
                    <p className="text-sm text-[var(--text-muted)] mt-1">
                        Track changes and rollback to previous versions of this playbook.
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateSnapshot(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-[var(--accent)] text-white text-sm font-semibold rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                >
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    Create Snapshot
                </button>
            </div>

            {/* Create Snapshot Form */}
            {showCreateSnapshot && (
                <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] p-7 mb-6">
                    <h3 className="text-base font-bold text-[var(--text-primary)] mb-5">Create Version Snapshot</h3>
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
                    <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-[var(--border)]">
                        <button
                            onClick={() => { setShowCreateSnapshot(false); setSnapshotSummary(''); }}
                            className="px-5 py-2.5 text-sm font-medium text-[var(--text-muted)] bg-transparent border border-[var(--border)] rounded-lg hover:bg-[var(--bg-surface)] transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => createSnapshotMutation.mutate()}
                            disabled={!snapshotSummary.trim() || createSnapshotMutation.isPending}
                            className="px-5 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
                        >
                            {createSnapshotMutation.isPending ? 'Creating...' : 'Save Snapshot'}
                        </button>
                    </div>
                </div>
            )}

            {/* Versions List */}
            {versions && versions.length > 0 ? (
                <div className="bg-[var(--bg-surface)] rounded-xl border border-[var(--border)] overflow-hidden">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-[var(--bg-surface)] border-b border-[var(--border)]">
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Version</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Summary</th>
                                <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Created</th>
                                <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {versions.map((version: PlaybookVersionSummary) => (
                                <tr key={version.id} className="border-b border-[var(--border)]">
                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[var(--bg-elevated)] text-sm font-bold text-[var(--text-primary)]">
                                            {version.version_number}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-sm text-[var(--text-primary)]">{version.change_summary || 'No summary'}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-[13px] text-[var(--text-muted)]">
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
                <div className="text-center py-16 px-8 bg-[var(--bg-surface)] rounded-xl border border-[var(--border)]">
                    <svg width="48" height="48" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-4">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">No version history</h3>
                    <p className="text-sm text-[var(--text-muted)] mb-6">Create a snapshot to save the current state of this playbook.</p>
                    <button
                        onClick={() => setShowCreateSnapshot(true)}
                        className="px-6 py-2.5 text-sm font-semibold text-white bg-[var(--accent)] rounded-lg hover:bg-[var(--accent-hover)] transition-colors"
                    >
                        Create Snapshot
                    </button>
                </div>
            )}
        </>
    );
}
