import { useState, useMemo, type CSSProperties } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { compareContracts, listPlaybooks, type CompareResponse, type DiffChange, type Playbook } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Badge, SelectInput, TextareaInput } from '@/components/ui';
import { ArrowLeftRight, RotateCcw, X } from 'lucide-react';

const CHANGE_STYLES: Record<string, { bg: string; border: string; badgeVariant: 'low' | 'critical' | 'high' }> = {
    added: { bg: 'var(--risk-low-bg)', border: 'var(--risk-low-border)', badgeVariant: 'low' },
    removed: { bg: 'var(--risk-critical-bg)', border: 'var(--risk-critical-border)', badgeVariant: 'critical' },
    modified: { bg: 'var(--risk-high-bg)', border: 'var(--risk-high-border)', badgeVariant: 'high' },
};

const ASSESSMENT_MAP: Record<string, 'low' | 'critical' | 'neutral'> = {
    favors_us: 'low',
    favors_them: 'critical',
    neutral: 'neutral',
};

function parseAssessment(ai: string | null): { type: string; explanation: string } {
    if (!ai) return { type: 'neutral', explanation: '' };
    const parts = ai.split(': ', 2);
    return { type: parts[0] || 'neutral', explanation: parts[1] || ai };
}

function ChangeCard({ change }: { change: DiffChange }) {
    const cs = CHANGE_STYLES[change.change_type] || CHANGE_STYLES.modified;
    const assessment = parseAssessment(change.ai_assessment);
    const badgeVariant = ASSESSMENT_MAP[assessment.type] || 'neutral';

    const textBoxStyle: CSSProperties = {
        fontSize: 14, padding: 8, borderRadius: 'var(--radius-sm)',
        backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)',
        color: 'var(--text-secondary)',
    };

    return (
        <div style={{
            borderRadius: 'var(--radius-md)', border: `1px solid ${cs.border}`,
            backgroundColor: cs.bg, padding: 16, marginBottom: 12,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Badge variant={cs.badgeVariant}>
                    {change.change_type === 'added' ? 'Added' : change.change_type === 'removed' ? 'Removed' : 'Modified'}
                </Badge>
                {change.change_type === 'modified' && (
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {Math.round(change.similarity * 100)}% similar
                    </span>
                )}
            </div>

            {change.text_a && (
                <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>Version A:</div>
                    <div style={{
                        ...textBoxStyle,
                        textDecoration: change.change_type === 'removed' ? 'line-through' : 'none',
                        color: change.change_type === 'removed' ? 'var(--risk-critical)' : 'var(--text-secondary)',
                    }}>
                        {change.text_a.length > 500 ? change.text_a.slice(0, 500) + '...' : change.text_a}
                    </div>
                </div>
            )}

            {change.text_b && (
                <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 4 }}>Version B:</div>
                    <div style={{
                        ...textBoxStyle,
                        color: change.change_type === 'added' ? 'var(--risk-low)' : 'var(--text-secondary)',
                    }}>
                        {change.text_b.length > 500 ? change.text_b.slice(0, 500) + '...' : change.text_b}
                    </div>
                </div>
            )}

            {change.ai_assessment && (
                <div style={{ marginTop: 8 }}>
                    <Badge variant={badgeVariant} size="md">
                        {assessment.type.replace('_', ' ').toUpperCase()}: {assessment.explanation}
                    </Badge>
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

    const { data: playbooks = [] } = useQuery({
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
        <AppLayout>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Contract Comparison</h1>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
                    Compare two contract versions side-by-side with AI-powered change assessment
                </p>
            </div>

            {/* Input Section */}
            {!result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <div>
                            <TextareaInput
                                label="Version A (Original)"
                                value={textA}
                                onChange={(e) => setTextA(e.target.value)}
                                placeholder="Paste the original contract text here..."
                                style={{ minHeight: 256, fontFamily: 'var(--font-mono)', resize: 'none' }}
                            />
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{textA.length} chars</div>
                        </div>
                        <div>
                            <TextareaInput
                                label="Version B (Revised)"
                                value={textB}
                                onChange={(e) => setTextB(e.target.value)}
                                placeholder="Paste the revised contract text here..."
                                style={{ minHeight: 256, fontFamily: 'var(--font-mono)', resize: 'none' }}
                            />
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{textB.length} chars</div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
                        <div style={{ flex: 1, maxWidth: 280 }}>
                            <SelectInput label="Playbook (optional)" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)}>
                                <option value="">No playbook</option>
                                {playbooks?.map((p: Playbook) => (
                                    <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                            </SelectInput>
                        </div>
                        <Button
                            onClick={() => compareMutation.mutate()}
                            disabled={!textA.trim() || !textB.trim() || compareMutation.isPending}
                            loading={compareMutation.isPending}
                            icon={<ArrowLeftRight size={16} />}
                        >
                            {compareMutation.isPending ? 'Comparing...' : 'Compare'}
                        </Button>
                    </div>
                    {error && (
                        <div style={{
                            padding: 12, background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)',
                            borderRadius: 'var(--radius-md)', fontSize: 14, color: 'var(--risk-critical)',
                        }}>
                            {error}
                        </div>
                    )}
                </div>
            )}

            {/* Results Section */}
            {result && (
                <div>
                    {/* Summary Bar */}
                    <div style={{
                        backgroundColor: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--border)', padding: 16, marginBottom: 24,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                                <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{result.summary}</span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
                                    <Badge variant="low">{addedCount} added</Badge>
                                    <Badge variant="critical">{removedCount} removed</Badge>
                                    <Badge variant="high">{modifiedCount} modified</Badge>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <SelectInput value={filterType} onChange={(e) => setFilterType(e.target.value)} style={{ height: 32, fontSize: 12, padding: '0 8px' }}>
                                    <option value="all">All Changes ({result.total_changes})</option>
                                    <option value="added">Added ({addedCount})</option>
                                    <option value="removed">Removed ({removedCount})</option>
                                    <option value="modified">Modified ({modifiedCount})</option>
                                </SelectInput>
                                <Button variant="secondary" size="sm" onClick={() => { setResult(null); setTextA(''); setTextB(''); setError(null); }} icon={<RotateCcw size={14} />}>
                                    New Comparison
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* Changes List */}
                    {filteredChanges.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
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
        </AppLayout>
    );
}
