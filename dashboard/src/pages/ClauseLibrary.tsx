import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useMemo, type CSSProperties } from 'react';
import { listClauses, createClause, updateClause, deleteClause, type ClauseLibraryItem } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, TextInput, TextareaInput } from '@/components/ui';
import { Plus, Pencil, Trash2 } from 'lucide-react';

function InlineConfirm({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{message}</span>
            <button onClick={onConfirm} style={{ fontSize: 12, fontWeight: 600, color: 'var(--risk-critical)', background: 'var(--risk-critical-bg)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer' }}>Yes</button>
            <button onClick={onCancel} style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', background: 'var(--bg-elevated)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer' }}>No</button>
        </span>
    );
}

export default function ClauseLibrary() {
    const queryClient = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [newName, setNewName] = useState('');
    const [newType, setNewType] = useState('');
    const [newText, setNewText] = useState('');
    const [filterType, setFilterType] = useState('');
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

    const { data: clauses, isLoading, error } = useQuery({
        queryKey: ['clauses', filterType],
        queryFn: () => listClauses(filterType || undefined),
    });

    const resetForm = () => {
        setShowCreate(false);
        setEditingId(null);
        setNewName('');
        setNewType('');
        setNewText('');
    };

    const createMutation = useMutation({
        mutationFn: (data: { clause_type: string; name: string; approved_text: string }) => createClause(data),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['clauses'] }); resetForm(); },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: { clause_type: string; name: string; approved_text: string } }) => updateClause(id, data),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['clauses'] }); resetForm(); },
    });

    const deleteMutation = useMutation({
        mutationFn: deleteClause,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clauses'] }),
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (newName.trim() && newType.trim() && newText.trim()) {
            const payload = { clause_type: newType, name: newName, approved_text: newText };
            if (editingId) {
                updateMutation.mutate({ id: editingId, data: payload });
            } else {
                createMutation.mutate(payload);
            }
        }
    };

    const handleEdit = (clause: ClauseLibraryItem) => {
        setEditingId(clause.id);
        setNewName(clause.name);
        setNewType(clause.clause_type);
        setNewText(clause.approved_text);
        setShowCreate(true);
    };

    const grouped = useMemo(() => (clauses || []).reduce<Record<string, ClauseLibraryItem[]>>((acc, c) => {
        (acc[c.clause_type] = acc[c.clause_type] || []).push(c);
        return acc;
    }, {}), [clauses]);

    const clauseTypes = useMemo(() => Object.keys(grouped).sort(), [grouped]);

    const filterBtnStyle = (active: boolean): CSSProperties => ({
        padding: '6px 12px', borderRadius: 'var(--radius-sm)', fontSize: 12, fontWeight: 500,
        cursor: 'pointer', border: active ? 'none' : '1px solid var(--border)',
        backgroundColor: active ? 'var(--accent)' : 'transparent',
        color: active ? '#fff' : 'var(--text-secondary)',
        transition: 'all var(--transition-fast)',
    });

    return (
        <AppLayout>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Clause Library</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Saved approved clause language for contract review</p>
                </div>
                <Button onClick={() => { if (showCreate) { resetForm(); } else { setShowCreate(true); } }} icon={<Plus size={16} />}>
                    New Clause
                </Button>
            </div>

            {/* Create/Edit Form */}
            {showCreate && (
                <Card style={{ marginBottom: 24 }}>
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <TextInput label="Clause Type" value={newType} onChange={(e) => setNewType(e.target.value)} placeholder="e.g. Indemnification" required />
                            <TextInput label="Name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Standard Mutual Indemnification" required />
                        </div>
                        <TextareaInput label="Approved Text" value={newText} onChange={(e) => setNewText(e.target.value)} placeholder="Paste the approved clause language here..." style={{ minHeight: 100 }} required />
                        <div style={{ display: 'flex', gap: 12 }}>
                            <Button type="submit" loading={createMutation.isPending || updateMutation.isPending}>
                                {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : editingId ? 'Update Clause' : 'Save Clause'}
                            </Button>
                            <Button variant="secondary" type="button" onClick={resetForm}>Cancel</Button>
                        </div>
                    </form>
                </Card>
            )}

            {/* Filter by type */}
            {clauseTypes.length > 0 && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
                    <button onClick={() => setFilterType('')} style={filterBtnStyle(!filterType)}>All</button>
                    {clauseTypes.map(type => (
                        <button key={type} onClick={() => setFilterType(type)} style={filterBtnStyle(filterType === type)}>{type}</button>
                    ))}
                </div>
            )}

            {error && (
                <div style={{ color: 'var(--risk-critical)', padding: 16, background: 'var(--risk-critical-bg)', borderRadius: 'var(--radius-md)', border: '1px solid var(--risk-critical-border)' }}>
                    Failed to load data. Please try again.
                </div>
            )}

            {/* Content */}
            {isLoading ? (
                <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading clauses...</div>
            ) : (clauses || []).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '64px 32px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)' }}>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>No saved clauses yet</p>
                    <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Create your first clause to get started</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {(clauses || []).map((clause) => (
                        <Card key={clause.id} variant="interactive">
                            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                                <div>
                                    <h3 style={{ fontWeight: 500, color: 'var(--text-primary)', margin: 0 }}>{clause.name}</h3>
                                    <div style={{ marginTop: 6, display: 'flex', gap: 8 }}>
                                        <Badge variant="neutral">{clause.clause_type}</Badge>
                                        {clause.is_mandatory && <Badge variant="critical">Mandatory</Badge>}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <Button variant="ghost" size="sm" onClick={() => handleEdit(clause)} icon={<Pencil size={14} />}>Edit</Button>
                                    {confirmDeleteId === clause.id ? (
                                        <InlineConfirm
                                            message="Delete?"
                                            onConfirm={() => { deleteMutation.mutate(clause.id); setConfirmDeleteId(null); }}
                                            onCancel={() => setConfirmDeleteId(null)}
                                        />
                                    ) : (
                                        <Button variant="danger" size="sm" onClick={() => setConfirmDeleteId(clause.id)} icon={<Trash2 size={14} />}>Delete</Button>
                                    )}
                                </div>
                            </div>
                            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                                {clause.approved_text.length > 300
                                    ? clause.approved_text.slice(0, 300) + '...'
                                    : clause.approved_text}
                            </p>
                        </Card>
                    ))}
                </div>
            )}
        </AppLayout>
    );
}
