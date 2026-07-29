import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState, type CSSProperties } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import {
    listPlaybooks,
    createPlaybook,
    deletePlaybook,
    togglePlaybookPublish,
    type CreatePlaybookData,
    type Playbook,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Badge, Modal, SelectInput, TextInput, TextareaInput } from '@/components/ui';
import { Plus, Globe, Lock, FileText } from 'lucide-react';

function InlineConfirm({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginLeft: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{message}</span>
            <button
                onClick={onConfirm}
                style={{
                    fontSize: 12, fontWeight: 600, color: 'var(--risk-critical)', background: 'var(--risk-critical-bg)',
                    padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
                }}
            >
                Yes
            </button>
            <button
                onClick={onCancel}
                style={{
                    fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', background: 'var(--bg-elevated)',
                    padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
                }}
            >
                No
            </button>
        </span>
    );
}

const categoryToBadge: Record<string, 'saas' | 'nda' | 'dpa' | 'employment' | 'msa' | 'neutral'> = {
    saas: 'saas',
    nda: 'nda',
    dpa: 'dpa',
    employment: 'employment',
    msa: 'msa',
    custom: 'neutral',
};

const tableHeaderStyle: CSSProperties = {
    textAlign: 'left',
    padding: '10px 20px',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const tableCellStyle: CSSProperties = {
    padding: '14px 20px',
};

export default function Playbooks() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const [newPartySide, setNewPartySide] = useState<'buyer' | 'seller' | 'neutral'>('neutral');
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
    const modalRef = useFocusTrap(showCreate);

    const { data: playbooks, isLoading, error } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    const createMutation = useMutation({
        mutationFn: (data: CreatePlaybookData) => createPlaybook(data),
        onSuccess: (newPlaybook) => {
            queryClient.invalidateQueries({ queryKey: ['playbooks'] });
            setShowCreate(false);
            setNewName('');
            setNewDescription('');
            setNewPartySide('neutral');
            navigate(`/playbooks/${newPlaybook.id}`);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: deletePlaybook,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        onError: (err: Error) => {
            console.error('Delete failed:', err.message);
            // Don't let delete errors cascade to logout
        },
    });

    const publishMutation = useMutation({
        mutationFn: togglePlaybookPublish,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['playbooks'] }),
        onError: (err: Error) => alert(err.message || 'Unable to publish this playbook.'),
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        if (newName.trim()) {
            createMutation.mutate({
                name: newName,
                description: newDescription || undefined,
                party_side: newPartySide,
            });
        }
    };

    return (
        <AppLayout>
            {/* Title row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Playbooks</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
                        Define custom rule sets for different contract types.
                    </p>
                </div>
                <Button onClick={() => setShowCreate(true)} icon={<Plus size={16} />}>
                    New Playbook
                </Button>
            </div>

            {/* Create Modal */}
            <Modal
                open={showCreate}
                onClose={() => setShowCreate(false)}
                title="Create Playbook"
                footer={
                    <>
                        <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
                        <Button
                            onClick={handleCreate}
                            loading={createMutation.isPending}
                        >
                            {createMutation.isPending ? 'Creating...' : 'Create'}
                        </Button>
                    </>
                }
            >
                <div ref={modalRef}>
                    <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <TextInput
                            label="Name"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            placeholder="e.g. SaaS Vendor Agreement"
                            required
                        />
                        <TextareaInput
                            label="Description (optional)"
                            value={newDescription}
                            onChange={(e) => setNewDescription(e.target.value)}
                            placeholder="Rules for reviewing SaaS vendor contracts..."
                        />
                        <SelectInput
                            label="Review perspective"
                            value={newPartySide}
                            onChange={(e) => setNewPartySide(e.target.value as 'buyer' | 'seller' | 'neutral')}
                        >
                            <option value="neutral">Neutral issue-spotting</option>
                            <option value="buyer">Representing buyer / customer</option>
                            <option value="seller">Representing seller / vendor</option>
                        </SelectInput>
                    </form>
                </div>
            </Modal>

            {/* Loading */}
            {isLoading && (
                <div style={{ textAlign: 'center', padding: '64px 0' }}>
                    <div style={{
                        width: 32, height: 32,
                        border: '2px solid var(--border)',
                        borderTopColor: 'var(--accent)',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite',
                        margin: '0 auto',
                    }} />
                </div>
            )}

            {/* Error */}
            {error && (
                <div style={{
                    background: 'var(--risk-critical-bg)', color: 'var(--risk-critical)',
                    padding: '12px 16px', borderRadius: 'var(--radius-md)',
                    fontSize: 14, border: '1px solid var(--risk-critical-border)',
                }}>
                    Error loading playbooks: {error instanceof Error ? error.message : 'Unknown error'}
                </div>
            )}

            {/* Table */}
            {playbooks && playbooks.length > 0 && (
                <div style={{
                    backgroundColor: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border)', overflow: 'hidden',
                }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-elevated)' }}>
                                <th scope="col" style={tableHeaderStyle}>Name</th>
                                <th scope="col" style={tableHeaderStyle}>Category</th>
                                <th scope="col" style={tableHeaderStyle}>Rules</th>
                                <th scope="col" style={tableHeaderStyle}>Status</th>
                                <th scope="col" style={{ ...tableHeaderStyle, textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {playbooks.map((playbook: Playbook) => {
                                const badgeVariant = categoryToBadge[playbook.category] || 'neutral';
                                return (
                                    <tr
                                        key={playbook.id}
                                        style={{ borderBottom: '1px solid var(--border)' }}
                                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}
                                    >
                                        <td style={tableCellStyle}>
                                            <Link to={`/playbooks/${playbook.id}`} style={{ fontWeight: 600, color: 'var(--text-primary)', textDecoration: 'none', fontSize: 14 }}>
                                                {playbook.name}
                                            </Link>
                                            {playbook.description && (
                                                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                    {playbook.description}
                                                </p>
                                            )}
                                        </td>
                                        <td style={tableCellStyle}>
                                            <Badge variant={badgeVariant}>{playbook.category}</Badge>
                                        </td>
                                        <td style={{ ...tableCellStyle, fontSize: 14, color: 'var(--text-secondary)' }}>
                                            {playbook.rules_count} rules
                                        </td>
                                        <td style={tableCellStyle}>
                                            {playbook.is_owner ? (
                                                <button
                                                    onClick={() => publishMutation.mutate(playbook.id)}
                                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                                                    title={playbook.is_public ? 'Click to unpublish' : 'Click to publish to your org'}
                                                >
                                                    <Badge
                                                        variant={playbook.is_public ? 'low' : 'neutral'}
                                                        icon={playbook.is_public ? <Globe size={12} /> : <Lock size={12} />}
                                                    >
                                                        {playbook.is_public ? 'Public' : 'Private'}
                                                    </Badge>
                                                </button>
                                            ) : (
                                                <Badge
                                                    variant={playbook.is_public ? 'low' : 'neutral'}
                                                    icon={playbook.is_public ? <Globe size={12} /> : <Lock size={12} />}
                                                >
                                                    {playbook.is_public ? 'Public' : 'Private'}
                                                </Badge>
                                            )}
                                        </td>
                                        <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                                            <Link
                                                to={`/playbooks/${playbook.id}`}
                                                style={{ fontSize: 13, fontWeight: 600, color: 'var(--info)', textDecoration: 'none', marginRight: 16 }}
                                            >
                                                {playbook.is_owner ? 'Edit' : 'View'}
                                            </Link>
                                            {playbook.is_owner && (
                                                confirmDeleteId === playbook.id ? (
                                                    <InlineConfirm
                                                        message="Delete?"
                                                        onConfirm={() => { deleteMutation.mutate(playbook.id); setConfirmDeleteId(null); }}
                                                        onCancel={() => setConfirmDeleteId(null)}
                                                    />
                                                ) : (
                                                    <button
                                                        onClick={() => setConfirmDeleteId(playbook.id)}
                                                        style={{ fontSize: 13, fontWeight: 600, color: 'var(--risk-critical)', background: 'none', border: 'none', cursor: 'pointer' }}
                                                    >
                                                        Delete
                                                    </button>
                                                )
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
                <div style={{
                    textAlign: 'center', padding: '64px 32px',
                    backgroundColor: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border)',
                }}>
                    <FileText size={48} style={{ color: 'var(--text-muted)', marginBottom: 16 }} />
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>No playbooks yet</h3>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 24 }}>
                        Create your first playbook to start detecting contract risks.
                    </p>
                    <Button onClick={() => setShowCreate(true)}>Create Playbook</Button>
                </div>
            )}
        </AppLayout>
    );
}
