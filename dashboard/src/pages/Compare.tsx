import { useState, useMemo } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { compareContracts, listPlaybooks, type CompareResponse, type DiffChange, type Playbook } from '@/api/client';
import AppHeader from '@/components/AppHeader';

const CHANGE_COLORS: Record<string, { bg: string; border: string; label: string; textColor: string }> = {
    added: { bg: 'bg-green-50', border: 'border-green-300', label: 'Added', textColor: 'text-green-800' },
    removed: { bg: 'bg-red-50', border: 'border-red-300', label: 'Removed', textColor: 'text-red-800' },
    modified: { bg: 'bg-yellow-50', border: 'border-yellow-300', label: 'Modified', textColor: 'text-yellow-800' },
};

const ASSESSMENT_COLORS: Record<string, string> = {
    favors_us: 'bg-green-100 text-green-700',
    favors_them: 'bg-red-100 text-red-700',
    neutral: 'bg-slate-100 text-slate-700',
};

function parseAssessment(ai: string | null): { type: string; explanation: string } {
    if (!ai) return { type: 'neutral', explanation: '' };
    const parts = ai.split(': ', 2);
    return { type: parts[0] || 'neutral', explanation: parts[1] || ai };
}

function ChangeCard({ change }: { change: DiffChange }) {
    const colors = CHANGE_COLORS[change.change_type] || CHANGE_COLORS.modified;
    const assessment = parseAssessment(change.ai_assessment);
    const assessmentColor = ASSESSMENT_COLORS[assessment.type] || ASSESSMENT_COLORS.neutral;

    return (
        <div className={`rounded-lg border ${colors.border} ${colors.bg} p-4 mb-3`}>
            <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colors.bg} ${colors.textColor} border ${colors.border}`}>
                    {colors.label}
                </span>
                {change.change_type === 'modified' && (
                    <span className="text-xs text-slate-400">
                        {Math.round(change.similarity * 100)}% similar
                    </span>
                )}
            </div>

            {change.text_a && (
                <div className="mb-2">
                    <div className="text-xs font-medium text-slate-500 mb-1">Version A:</div>
                    <div className={`text-sm ${change.change_type === 'removed' ? 'line-through text-red-600' : 'text-slate-700'} bg-white rounded p-2 border border-slate-200`}>
                        {change.text_a.length > 500 ? change.text_a.slice(0, 500) + '...' : change.text_a}
                    </div>
                </div>
            )}

            {change.text_b && (
                <div className="mb-2">
                    <div className="text-xs font-medium text-slate-500 mb-1">Version B:</div>
                    <div className={`text-sm ${change.change_type === 'added' ? 'text-green-700' : 'text-slate-700'} bg-white rounded p-2 border border-slate-200`}>
                        {change.text_b.length > 500 ? change.text_b.slice(0, 500) + '...' : change.text_b}
                    </div>
                </div>
            )}

            {change.ai_assessment && (
                <div className={`text-xs px-2 py-1 rounded mt-2 ${assessmentColor}`}>
                    <span className="font-medium">{assessment.type.replace('_', ' ').toUpperCase()}:</span>{' '}
                    {assessment.explanation}
                </div>
            )}
        </div>
    );
}

export default function Compare() {
    const [textA, setTextA] = useState('');
    const [textB, setTextB] = useState('');
    const [playbookId, setPlaybookId] = useState('');
    const [result, setResult] = useState<CompareResponse | null>(null);
    const [filterType, setFilterType] = useState<string>('all');
    const [error, setError] = useState<string | null>(null);

    const { data: playbooks } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    const compareMutation = useMutation({
        mutationFn: () => compareContracts(textA, textB, playbookId || undefined),
        onSuccess: (data) => { setResult(data); setError(null); },
        onError: (err) => setError(err instanceof Error ? err.message : 'Comparison failed'),
    });

    const filteredChanges = useMemo(() => result?.changes.filter(c =>
        filterType === 'all' || c.change_type === filterType
    ) || [], [result, filterType]);

    const addedCount = useMemo(() => result?.changes.filter(c => c.change_type === 'added').length || 0, [result]);
    const removedCount = useMemo(() => result?.changes.filter(c => c.change_type === 'removed').length || 0, [result]);
    const modifiedCount = useMemo(() => result?.changes.filter(c => c.change_type === 'modified').length || 0, [result]);

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-slate-900">Contract Comparison</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Compare two contract versions side-by-side with AI-powered change assessment
                    </p>
                </div>

                {/* Input Section */}
                {!result && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Version A (Original)</label>
                                <textarea
                                    value={textA}
                                    onChange={(e) => setTextA(e.target.value)}
                                    placeholder="Paste the original contract text here..."
                                    className="w-full h-64 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none font-mono"
                                />
                                <div className="text-xs text-slate-400 mt-1">{textA.length} chars</div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Version B (Revised)</label>
                                <textarea
                                    value={textB}
                                    onChange={(e) => setTextB(e.target.value)}
                                    placeholder="Paste the revised contract text here..."
                                    className="w-full h-64 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none font-mono"
                                />
                                <div className="text-xs text-slate-400 mt-1">{textB.length} chars</div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="flex-1 max-w-xs">
                                <label className="block text-xs font-medium text-slate-500 mb-1">Playbook (optional)</label>
                                <select
                                    value={playbookId}
                                    onChange={(e) => setPlaybookId(e.target.value)}
                                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                >
                                    <option value="">No playbook</option>
                                    {playbooks?.map((p: Playbook) => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={() => compareMutation.mutate()}
                                disabled={!textA.trim() || !textB.trim() || compareMutation.isPending}
                                className="mt-5 px-6 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {compareMutation.isPending ? 'Comparing...' : 'Compare'}
                            </button>
                        </div>
                        {error && (
                            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                                {error}
                            </div>
                        )}
                    </div>
                )}

                {/* Results Section */}
                {result && (
                    <div>
                        {/* Summary Bar */}
                        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <span className="text-sm font-medium text-slate-700">{result.summary}</span>
                                    <div className="flex items-center gap-3 mt-2">
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">{addedCount} added</span>
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">{removedCount} removed</span>
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">{modifiedCount} modified</span>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <select
                                        value={filterType}
                                        onChange={(e) => setFilterType(e.target.value)}
                                        className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                                    >
                                        <option value="all">All Changes ({result.total_changes})</option>
                                        <option value="added">Added ({addedCount})</option>
                                        <option value="removed">Removed ({removedCount})</option>
                                        <option value="modified">Modified ({modifiedCount})</option>
                                    </select>
                                    <button
                                        onClick={() => { setResult(null); setTextA(''); setTextB(''); setError(null); }}
                                        className="px-3 py-1.5 text-xs text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50"
                                    >
                                        New Comparison
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Changes List */}
                        {filteredChanges.length === 0 ? (
                            <div className="text-center py-12 text-slate-400">
                                {result.total_changes === 0 ? 'No differences found between the two versions.' : 'No changes match the selected filter.'}
                            </div>
                        ) : (
                            <div>
                                {filteredChanges.map((change) => (
                                    <ChangeCard key={`${change.change_type}-${change.position}`} change={change} />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
