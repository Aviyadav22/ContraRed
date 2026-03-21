import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import { listPlaybooks, createPlaybook, deletePlaybook, togglePlaybookPublish, isAdmin, type Playbook } from '@/api/client';
import AppHeader from '@/components/AppHeader';

function InlineConfirm({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
    return (
        <span className="inline-flex items-center gap-1.5 ml-2">
            <span className="text-[12px] text-slate-500">{message}</span>
            <button onClick={onConfirm} className="text-[12px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded hover:bg-red-100 transition-colors">Yes</button>
            <button onClick={onCancel} className="text-[12px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded hover:bg-slate-200 transition-colors">No</button>
        </span>
    );
}

const categoryStyles: Record<string, string> = {
    saas: 'bg-blue-50 text-blue-600',
    nda: 'bg-purple-50 text-purple-600',
    dpa: 'bg-green-50 text-green-600',
    employment: 'bg-orange-50 text-orange-600',
    msa: 'bg-indigo-50 text-indigo-600',
    custom: 'bg-slate-100 text-slate-600',
};

export default function Playbooks() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const admin = isAdmin();
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const modalRef = useFocusTrap(showCreate);

    const { data: playbooks, isLoading, error } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    const createMutation = useMutation({
        mutationFn: (data: { name: string; description?: string }) => createPlaybook(data),
        onSuccess: (newPlaybook) => {
            queryClient.invalidateQueries({ queryKey: ['playbooks'] });
            setShowCreate(false);
            setNewName('');
            setNewDescription('');
            navigate(`/playbooks/${newPlaybook.id}`);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: deletePlaybook,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
    });

    const publishMutation = useMutation({
        mutationFn: togglePlaybookPublish,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        if (newName.trim()) {
            createMutation.mutate({ name: newName, description: newDescription || undefined });
        }
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            {/* Main */}
            <main className="max-w-7xl mx-auto px-8 py-10">
                {/* Title row */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Playbooks</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            Define custom rule sets for different contract types.
                        </p>
                    </div>
                    {admin && (
                        <button
                            onClick={() => setShowCreate(true)}
                            className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
                        >
                            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                            New Playbook
                        </button>
                    )}
                </div>

                {/* Create Modal */}
                {showCreate && (
                    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="create-playbook-title" onKeyDown={(e) => { if (e.key === 'Escape') setShowCreate(false); }}>
                        <div ref={modalRef} className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl">
                            <h2 id="create-playbook-title" className="text-xl font-bold text-slate-900 mb-6">Create Playbook</h2>
                            <form onSubmit={handleCreate}>
                                <div className="mb-5">
                                    <label className="block text-[13px] font-semibold text-slate-700 mb-1.5">Name</label>
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                                        placeholder="e.g. SaaS Vendor Agreement"
                                        required
                                    />
                                </div>
                                <div className="mb-6">
                                    <label className="block text-[13px] font-semibold text-slate-700 mb-1.5">Description (optional)</label>
                                    <textarea
                                        value={newDescription}
                                        onChange={(e) => setNewDescription(e.target.value)}
                                        className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 outline-none resize-y min-h-[80px] focus:ring-2 focus:ring-slate-900 focus:border-transparent"
                                        placeholder="Rules for reviewing SaaS vendor contracts..."
                                    />
                                </div>
                                <div className="flex justify-end gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setShowCreate(false)}
                                        className="px-5 py-2.5 text-sm font-medium text-slate-500 bg-transparent border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-60"
                                    >
                                        {createMutation.isPending ? 'Creating...' : 'Create'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Loading */}
                {isLoading && (
                    <div className="text-center py-16">
                        <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto" />
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="bg-red-50 text-red-600 px-5 py-4 rounded-lg text-sm border border-red-200">
                        Error loading playbooks: {error instanceof Error ? error.message : 'Unknown error'}
                    </div>
                )}

                {/* Table */}
                {playbooks && playbooks.length > 0 && (
                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr className="bg-slate-50 border-b border-slate-200">
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Category</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Rules</th>
                                    <th scope="col" className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                                    <th scope="col" className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {playbooks.map((playbook: Playbook) => {
                                    const cat = categoryStyles[playbook.category] || categoryStyles.custom;
                                    return (
                                        <tr key={playbook.id} className="border-b border-slate-100">
                                            <td className="px-6 py-4">
                                                <Link to={`/playbooks/${playbook.id}`} className="font-semibold text-slate-900 no-underline text-sm hover:text-slate-700">
                                                    {playbook.name}
                                                </Link>
                                                {playbook.description && (
                                                    <p className="text-[13px] text-slate-400 mt-0.5 max-w-xs overflow-hidden text-ellipsis whitespace-nowrap">
                                                        {playbook.description}
                                                    </p>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2.5 py-1 text-xs font-semibold rounded-md ${cat}`}>
                                                    {playbook.category}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-slate-500">
                                                {playbook.rules_count} rules
                                            </td>
                                            <td className="px-6 py-4">
                                                {admin ? (
                                                    <button
                                                        onClick={() => publishMutation.mutate(playbook.id)}
                                                        className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md ${
                                                            playbook.is_public
                                                                ? 'bg-green-50 text-green-600'
                                                                : 'bg-slate-100 text-slate-500'
                                                        }`}
                                                    >
                                                        <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            {playbook.is_public
                                                                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                                            }
                                                        </svg>
                                                        {playbook.is_public ? 'Public' : 'Private'}
                                                    </button>
                                                ) : (
                                                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md ${
                                                        playbook.is_public
                                                            ? 'bg-green-50 text-green-600'
                                                            : 'bg-slate-100 text-slate-500'
                                                    }`}>
                                                        {playbook.is_public ? 'Public' : 'Private'}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                {admin ? (
                                                    <>
                                                        <Link
                                                            to={`/playbooks/${playbook.id}`}
                                                            className="text-[13px] font-semibold text-blue-600 no-underline mr-4 hover:text-blue-700"
                                                        >
                                                            Edit
                                                        </Link>
                                                        {confirmDeleteId === playbook.id ? (
                                                            <InlineConfirm
                                                                message="Delete?"
                                                                onConfirm={() => { deleteMutation.mutate(playbook.id); setConfirmDeleteId(null); }}
                                                                onCancel={() => setConfirmDeleteId(null)}
                                                            />
                                                        ) : (
                                                            <button
                                                                onClick={() => setConfirmDeleteId(playbook.id)}
                                                                className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
                                                            >
                                                                Delete
                                                            </button>
                                                        )}
                                                    </>
                                                ) : (
                                                    <span className="text-[13px] text-slate-400">View only</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Empty State */}
                {playbooks && playbooks.length === 0 && (
                    <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                        <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <h3 className="text-lg font-semibold text-slate-900 mb-2">No playbooks yet</h3>
                        <p className="text-sm text-slate-500 mb-6">
                            {admin
                                ? 'Create your first playbook to start detecting contract risks.'
                                : 'No playbooks are available yet. Ask your admin to create one.'}
                        </p>
                        {admin && (
                            <button
                                onClick={() => setShowCreate(true)}
                                className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors"
                            >
                                Create Playbook
                            </button>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
