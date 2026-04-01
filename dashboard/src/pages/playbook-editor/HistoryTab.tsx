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
                    <svg width="48" height="48" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-4">
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
}
