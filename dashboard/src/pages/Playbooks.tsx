import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { listPlaybooks, createPlaybook, deletePlaybook, togglePlaybookPublish, getStoredUser, isAdmin, type Playbook } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function Playbooks() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const admin = isAdmin();

    const user = getStoredUser();

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

    const categoryStyles: Record<string, { bg: string; text: string }> = {
        saas: { bg: '#eff6ff', text: '#2563eb' },
        nda: { bg: '#faf5ff', text: '#7c3aed' },
        dpa: { bg: '#f0fdf4', text: '#16a34a' },
        employment: { bg: '#fff7ed', text: '#ea580c' },
        msa: { bg: '#eef2ff', text: '#4f46e5' },
        custom: { bg: '#f1f5f9', text: '#475569' },
    };

    return (
        <div style={{ fontFamily: "'Inter', system-ui, sans-serif", minHeight: '100vh', backgroundColor: '#f8fafc' }}>
            <AppHeader />

            {/* Main */}
            <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 32px' }}>
                {/* Title row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                    <div>
                        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', margin: 0 }}>Playbooks</h1>
                        <p style={{ fontSize: 14, color: '#64748b', margin: '4px 0 0' }}>
                            Define custom rule sets for different contract types.
                        </p>
                    </div>
                    {admin && (
                        <button
                            onClick={() => setShowCreate(true)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                padding: '10px 20px',
                                backgroundColor: '#0f172a',
                                color: '#ffffff',
                                fontSize: 14,
                                fontWeight: 600,
                                borderRadius: 8,
                                border: 'none',
                                cursor: 'pointer',
                            }}
                        >
                            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                            New Playbook
                        </button>
                    )}
                </div>

                {/* Create Modal */}
                {showCreate && (
                    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
                        <div style={{ backgroundColor: '#ffffff', borderRadius: 16, padding: 32, width: '100%', maxWidth: 480, boxShadow: '0 24px 48px rgba(0,0,0,0.12)' }}>
                            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', margin: '0 0 24px' }}>Create Playbook</h2>
                            <form onSubmit={handleCreate}>
                                <div style={{ marginBottom: 20 }}>
                                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#334155', marginBottom: 6 }}>Name</label>
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '10px 14px',
                                            borderRadius: 8,
                                            border: '1px solid #e2e8f0',
                                            fontSize: 14,
                                            color: '#0f172a',
                                            outline: 'none',
                                            boxSizing: 'border-box',
                                        }}
                                        placeholder="e.g. SaaS Vendor Agreement"
                                        required
                                    />
                                </div>
                                <div style={{ marginBottom: 24 }}>
                                    <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#334155', marginBottom: 6 }}>Description (optional)</label>
                                    <textarea
                                        value={newDescription}
                                        onChange={(e) => setNewDescription(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '10px 14px',
                                            borderRadius: 8,
                                            border: '1px solid #e2e8f0',
                                            fontSize: 14,
                                            color: '#0f172a',
                                            outline: 'none',
                                            resize: 'vertical',
                                            minHeight: 80,
                                            boxSizing: 'border-box',
                                        }}
                                        placeholder="Rules for reviewing SaaS vendor contracts..."
                                    />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                                    <button
                                        type="button"
                                        onClick={() => setShowCreate(false)}
                                        style={{
                                            padding: '10px 20px',
                                            fontSize: 14,
                                            fontWeight: 500,
                                            color: '#64748b',
                                            backgroundColor: 'transparent',
                                            border: '1px solid #e2e8f0',
                                            borderRadius: 8,
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        style={{
                                            padding: '10px 20px',
                                            fontSize: 14,
                                            fontWeight: 600,
                                            color: '#ffffff',
                                            backgroundColor: '#0f172a',
                                            border: 'none',
                                            borderRadius: 8,
                                            cursor: 'pointer',
                                            opacity: createMutation.isPending ? 0.6 : 1,
                                        }}
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
                    <div style={{ textAlign: 'center', padding: '64px 0' }}>
                        <div style={{
                            width: 32, height: 32, border: '3px solid #e2e8f0', borderTopColor: '#0f172a',
                            borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto',
                        }} />
                        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div style={{ backgroundColor: '#fef2f2', color: '#dc2626', padding: '16px 20px', borderRadius: 10, fontSize: 14, border: '1px solid #fecaca' }}>
                        Error loading playbooks: {(error as Error).message}
                    </div>
                )}

                {/* Table */}
                {playbooks && playbooks.length > 0 && (
                    <div style={{ backgroundColor: '#ffffff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Name</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Category</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Rules</th>
                                    <th style={{ textAlign: 'left', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Status</th>
                                    <th style={{ textAlign: 'right', padding: '12px 24px', fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {playbooks.map((playbook: Playbook) => {
                                    const cat = categoryStyles[playbook.category] || categoryStyles.custom;
                                    return (
                                        <tr key={playbook.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '16px 24px' }}>
                                                <Link to={`/playbooks/${playbook.id}`} style={{ fontWeight: 600, color: '#0f172a', textDecoration: 'none', fontSize: 14 }}>
                                                    {playbook.name}
                                                </Link>
                                                {playbook.description && (
                                                    <p style={{ fontSize: 13, color: '#94a3b8', margin: '2px 0 0', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        {playbook.description}
                                                    </p>
                                                )}
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                <span style={{ padding: '4px 10px', fontSize: 12, fontWeight: 600, borderRadius: 6, backgroundColor: cat.bg, color: cat.text }}>
                                                    {playbook.category}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px 24px', fontSize: 14, color: '#64748b' }}>
                                                {playbook.rules_count} rules
                                            </td>
                                            <td style={{ padding: '16px 24px' }}>
                                                {admin ? (
                                                    <button
                                                        onClick={() => publishMutation.mutate(playbook.id)}
                                                        style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: 4,
                                                            padding: '4px 10px',
                                                            fontSize: 12,
                                                            fontWeight: 600,
                                                            borderRadius: 6,
                                                            border: 'none',
                                                            cursor: 'pointer',
                                                            backgroundColor: playbook.is_public ? '#f0fdf4' : '#f1f5f9',
                                                            color: playbook.is_public ? '#16a34a' : '#64748b',
                                                        }}
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
                                                    <span style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        gap: 4,
                                                        padding: '4px 10px',
                                                        fontSize: 12,
                                                        fontWeight: 600,
                                                        borderRadius: 6,
                                                        backgroundColor: playbook.is_public ? '#f0fdf4' : '#f1f5f9',
                                                        color: playbook.is_public ? '#16a34a' : '#64748b',
                                                    }}>
                                                        {playbook.is_public ? 'Public' : 'Private'}
                                                    </span>
                                                )}
                                            </td>
                                            <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                                {admin ? (
                                                    <>
                                                        <Link
                                                            to={`/playbooks/${playbook.id}`}
                                                            style={{ fontSize: 13, fontWeight: 600, color: '#2563eb', textDecoration: 'none', marginRight: 16 }}
                                                        >
                                                            Edit
                                                        </Link>
                                                        <button
                                                            onClick={() => {
                                                                if (confirm('Delete this playbook?')) {
                                                                    deleteMutation.mutate(playbook.id);
                                                                }
                                                            }}
                                                            style={{ fontSize: 13, fontWeight: 600, color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}
                                                        >
                                                            Delete
                                                        </button>
                                                    </>
                                                ) : (
                                                    <span style={{ fontSize: 13, color: '#94a3b8' }}>View only</span>
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
                    <div style={{ textAlign: 'center', padding: '64px 32px', backgroundColor: '#ffffff', borderRadius: 12, border: '1px solid #e2e8f0' }}>
                        <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" style={{ margin: '0 auto 16px' }}>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <h3 style={{ fontSize: 18, fontWeight: 600, color: '#0f172a', margin: '0 0 8px' }}>No playbooks yet</h3>
                        <p style={{ fontSize: 14, color: '#64748b', margin: '0 0 24px' }}>
                            {admin
                                ? 'Create your first playbook to start detecting contract risks.'
                                : 'No playbooks are available yet. Ask your admin to create one.'}
                        </p>
                        {admin && (
                            <button
                                onClick={() => setShowCreate(true)}
                                style={{
                                    padding: '10px 24px',
                                    fontSize: 14,
                                    fontWeight: 600,
                                    color: '#ffffff',
                                    backgroundColor: '#0f172a',
                                    border: 'none',
                                    borderRadius: 8,
                                    cursor: 'pointer',
                                }}
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
