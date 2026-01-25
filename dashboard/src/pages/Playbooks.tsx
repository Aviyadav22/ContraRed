import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { listPlaybooks, createPlaybook, deletePlaybook, togglePlaybookPublish, type Playbook } from '@/api/client';

export default function Playbooks() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');

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

    const categoryColors: Record<string, string> = {
        saas: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        nda: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
        dpa: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        employment: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
        msa: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
        custom: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <Link to="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <span className="text-xl font-bold text-slate-900 dark:text-white">Contra<span className="text-red-500">Red</span></span>
                        </Link>

                        <nav className="flex items-center gap-6">
                            <Link to="/" className="text-slate-600 dark:text-slate-300 hover:text-blue-600 font-medium">Dashboard</Link>
                            <Link to="/playbooks" className="text-blue-600 dark:text-blue-400 font-semibold">Playbooks</Link>
                            <Link to="/billing" className="text-slate-600 dark:text-slate-300 hover:text-blue-600 font-medium">Billing</Link>
                        </nav>
                    </div>
                </div>
            </header>

            {/* Main */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Playbooks</h1>
                    <button
                        onClick={() => setShowCreate(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition flex items-center gap-2"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        New Playbook
                    </button>
                </div>

                {/* Create Modal */}
                {showCreate && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl p-6 w-full max-w-md">
                            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Create Playbook</h2>
                            <form onSubmit={handleCreate} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Name</label>
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                        placeholder="My SaaS Playbook"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Description</label>
                                    <textarea
                                        value={newDescription}
                                        onChange={(e) => setNewDescription(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                                        rows={3}
                                        placeholder="Rules for reviewing SaaS vendor contracts..."
                                    />
                                </div>
                                <div className="flex justify-end gap-3 pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowCreate(false)}
                                        className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition disabled:opacity-50"
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
                    <div className="text-center py-12">
                        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-4 rounded-lg">
                        Error loading playbooks: {(error as Error).message}
                    </div>
                )}

                {/* Table */}
                {playbooks && playbooks.length > 0 && (
                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <table className="w-full">
                            <thead className="bg-slate-50 dark:bg-slate-700/50">
                                <tr>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Name</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Category</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Rules</th>
                                    <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                                    <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                                {playbooks.map((playbook: Playbook) => (
                                    <tr key={playbook.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                        <td className="px-6 py-4">
                                            <Link to={`/playbooks/${playbook.id}`} className="font-medium text-slate-900 dark:text-white hover:text-blue-600">
                                                {playbook.name}
                                            </Link>
                                            {playbook.description && (
                                                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 truncate max-w-xs">{playbook.description}</p>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${categoryColors[playbook.category] || categoryColors.custom}`}>
                                                {playbook.category}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                                            {playbook.rules_count} rules
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => publishMutation.mutate(playbook.id)}
                                                className={`text-xs font-medium px-2 py-1 rounded ${playbook.is_public ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'}`}
                                            >
                                                {playbook.is_public ? '🌐 Public' : '🔒 Private'}
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <Link
                                                to={`/playbooks/${playbook.id}`}
                                                className="text-blue-600 hover:text-blue-700 font-medium mr-4"
                                            >
                                                Edit
                                            </Link>
                                            <button
                                                onClick={() => {
                                                    if (confirm('Delete this playbook?')) {
                                                        deleteMutation.mutate(playbook.id);
                                                    }
                                                }}
                                                className="text-red-600 hover:text-red-700 font-medium"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Empty State */}
                {playbooks && playbooks.length === 0 && (
                    <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <svg className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No playbooks yet</h3>
                        <p className="text-slate-500 dark:text-slate-400 mb-4">Create your first playbook to start detecting contract risks.</p>
                        <button
                            onClick={() => setShowCreate(true)}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition"
                        >
                            Create Playbook
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
}
