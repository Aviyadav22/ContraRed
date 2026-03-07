import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { listClauses, createClause, deleteClause, type ClauseLibraryItem } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function ClauseLibrary() {
    const queryClient = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newType, setNewType] = useState('');
    const [newText, setNewText] = useState('');
    const [filterType, setFilterType] = useState('');

    const { data: clauses, isLoading } = useQuery({
        queryKey: ['clauses', filterType],
        queryFn: () => listClauses(filterType || undefined),
    });

    const createMutation = useMutation({
        mutationFn: (data: { clause_type: string; name: string; approved_text: string }) => createClause(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['clauses'] });
            setShowCreate(false);
            setNewName('');
            setNewType('');
            setNewText('');
        },
    });

    const deleteMutation = useMutation({
        mutationFn: deleteClause,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clauses'] }),
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        if (newName.trim() && newType.trim() && newText.trim()) {
            createMutation.mutate({ clause_type: newType, name: newName, approved_text: newText });
        }
    };

    // Group clauses by type
    const grouped = (clauses || []).reduce<Record<string, ClauseLibraryItem[]>>((acc, c) => {
        (acc[c.clause_type] = acc[c.clause_type] || []).push(c);
        return acc;
    }, {});

    const clauseTypes = Object.keys(grouped).sort();

    return (
        <div className="font-['Inter',system-ui,sans-serif] min-h-screen bg-slate-50">
            <AppHeader activePage="clauses" />

            <main className="max-w-5xl mx-auto px-6 py-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-semibold text-slate-800">Clause Library</h1>
                        <p className="text-sm text-slate-500 mt-1">Saved approved clause language for contract review</p>
                    </div>
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition-colors"
                    >
                        + New Clause
                    </button>
                </div>

                {/* Create Form */}
                {showCreate && (
                    <form onSubmit={handleCreate} className="bg-white border border-slate-200 rounded-xl p-6 mb-6 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Clause Type</label>
                                <input
                                    value={newType}
                                    onChange={(e) => setNewType(e.target.value)}
                                    placeholder="e.g. Indemnification"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                                <input
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                    placeholder="e.g. Standard Mutual Indemnification"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
                                    required
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Approved Text</label>
                            <textarea
                                value={newText}
                                onChange={(e) => setNewText(e.target.value)}
                                placeholder="Paste the approved clause language here..."
                                rows={4}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
                                required
                            />
                        </div>
                        <div className="flex gap-3">
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 disabled:opacity-50"
                            >
                                {createMutation.isPending ? 'Saving...' : 'Save Clause'}
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowCreate(false)}
                                className="px-4 py-2 text-slate-600 border border-slate-200 rounded-lg text-sm hover:bg-slate-50"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                )}

                {/* Filter by type */}
                {clauseTypes.length > 0 && (
                    <div className="flex gap-2 mb-6 flex-wrap">
                        <button
                            onClick={() => setFilterType('')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                !filterType ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                            }`}
                        >
                            All
                        </button>
                        {clauseTypes.map(type => (
                            <button
                                key={type}
                                onClick={() => setFilterType(type)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                    filterType === type ? 'bg-slate-800 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                                }`}
                            >
                                {type}
                            </button>
                        ))}
                    </div>
                )}

                {/* Content */}
                {isLoading ? (
                    <div className="text-center py-12 text-slate-400">Loading clauses...</div>
                ) : (clauses || []).length === 0 ? (
                    <div className="text-center py-16 bg-white border border-slate-200 rounded-xl">
                        <p className="text-slate-500 mb-2">No saved clauses yet</p>
                        <p className="text-sm text-slate-400">Create your first clause to get started</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {(clauses || []).map((clause) => (
                            <div key={clause.id} className="bg-white border border-slate-200 rounded-xl p-5 hover:border-slate-300 transition-colors">
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <h3 className="font-medium text-slate-800">{clause.name}</h3>
                                        <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs font-medium">
                                            {clause.clause_type}
                                        </span>
                                        {clause.is_mandatory && (
                                            <span className="inline-block ml-2 mt-1 px-2 py-0.5 bg-red-50 text-red-600 rounded text-xs font-medium">
                                                Mandatory
                                            </span>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => {
                                            if (confirm('Delete this clause?')) {
                                                deleteMutation.mutate(clause.id);
                                            }
                                        }}
                                        className="text-slate-400 hover:text-red-500 text-sm transition-colors"
                                    >
                                        Delete
                                    </button>
                                </div>
                                <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                                    {clause.approved_text.length > 300
                                        ? clause.approved_text.slice(0, 300) + '...'
                                        : clause.approved_text}
                                </p>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
