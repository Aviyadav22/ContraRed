import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type CSSProperties } from 'react';
import { getStoredUser, getTeamMembers, changeTeamMemberRole, removeTeamMember, type TeamMember } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, TextInput, SelectInput, Badge } from '@/components/ui';
import { Send, UserMinus } from 'lucide-react';

function InlineConfirm({ message, onConfirm, onCancel }: { message: string; onConfirm: () => void; onCancel: () => void }) {
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{message}</span>
            <button onClick={onConfirm} style={{ fontSize: 12, fontWeight: 600, color: 'var(--risk-critical)', background: 'var(--risk-critical-bg)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer' }}>Yes</button>
            <button onClick={onCancel} style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', background: 'var(--bg-elevated)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer' }}>No</button>
        </span>
    );
}

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '10px 16px', fontWeight: 500,
    fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const tdStyle: CSSProperties = { padding: '10px 16px' };

export default function Team() {
    const user = getStoredUser();
    const queryClient = useQueryClient();
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('analyst');
    const [inviteMessage, setInviteMessage] = useState<string | null>(null);
    const [confirmRoleChange, setConfirmRoleChange] = useState<{ id: string; role: string } | null>(null);
    const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

    const { data: members, isLoading, error } = useQuery<TeamMember[]>({
        queryKey: ['team-members'],
        queryFn: getTeamMembers,
    });

    const roleMutation = useMutation({
        mutationFn: ({ userId, role }: { userId: string; role: string }) => changeTeamMemberRole(userId, role),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['team-members'] }),
    });

    const removeMutation = useMutation({
        mutationFn: (userId: string) => removeTeamMember(userId),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['team-members'] }),
    });

    const handleRoleChange = (memberId: string, newRole: string) => {
        setConfirmRoleChange({ id: memberId, role: newRole });
    };

    const handleRemove = (member: TeamMember) => {
        setConfirmRemoveId(member.id);
    };

    return (
        <AppLayout>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: 24 }}>Team Management</h1>

            {/* Invite Member */}
            <Card style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>Invite Member</h2>
                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        setInviteMessage('Team invitation feature coming soon');
                        setTimeout(() => setInviteMessage(null), 4000);
                    }}
                    style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}
                >
                    <div style={{ flex: 1, maxWidth: 280 }}>
                        <TextInput
                            label="Email"
                            type="email"
                            required
                            value={inviteEmail}
                            onChange={(e) => setInviteEmail(e.target.value)}
                            placeholder="colleague@company.com"
                        />
                    </div>
                    <div style={{ minWidth: 120 }}>
                        <SelectInput label="Role" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                            <option value="analyst">Analyst</option>
                            <option value="admin">Admin</option>
                        </SelectInput>
                    </div>
                    <Button type="submit" icon={<Send size={14} />}>Send Invite</Button>
                </form>
                {inviteMessage && (
                    <div style={{
                        marginTop: 12, fontSize: 14, color: 'var(--risk-high)',
                        background: 'var(--risk-high-bg)', border: '1px solid var(--risk-high-border)',
                        padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                    }}>
                        {inviteMessage}
                    </div>
                )}
            </Card>

            {error && (
                <div style={{ color: 'var(--risk-critical)', padding: 16, background: 'var(--risk-critical-bg)', borderRadius: 'var(--radius-md)', marginBottom: 16, border: '1px solid var(--risk-critical-border)' }}>
                    Failed to load data. Please try again.
                </div>
            )}

            {(roleMutation.isError || removeMutation.isError) && (
                <div style={{ marginBottom: 16, padding: 12, background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)', borderRadius: 'var(--radius-md)', fontSize: 14, color: 'var(--risk-critical)' }}>
                    {(roleMutation.error as Error)?.message || (removeMutation.error as Error)?.message}
                </div>
            )}

            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                    <thead style={{ backgroundColor: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                        <tr>
                            <th scope="col" style={thStyle}>Name</th>
                            <th scope="col" style={thStyle}>Email</th>
                            <th scope="col" style={thStyle}>Role</th>
                            <th scope="col" style={thStyle}>Last Login</th>
                            <th scope="col" style={thStyle}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>Loading...</td></tr>
                        ) : members?.length === 0 ? (
                            <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>No team members found. Users need to be assigned to your organization.</td></tr>
                        ) : (
                            members?.map((member) => (
                                <tr
                                    key={member.id}
                                    style={{ borderBottom: '1px solid var(--border)' }}
                                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}
                                >
                                    <td style={{ ...tdStyle, color: 'var(--text-primary)', fontWeight: 500 }}>{member.name}</td>
                                    <td style={{ ...tdStyle, color: 'var(--text-secondary)' }}>{member.email}</td>
                                    <td style={tdStyle}>
                                        {member.id === user?.id ? (
                                            <Badge variant="neutral">{member.role} (you)</Badge>
                                        ) : confirmRoleChange?.id === member.id ? (
                                            <InlineConfirm
                                                message={`Change to ${confirmRoleChange.role}?`}
                                                onConfirm={() => { roleMutation.mutate({ userId: confirmRoleChange.id, role: confirmRoleChange.role }); setConfirmRoleChange(null); }}
                                                onCancel={() => setConfirmRoleChange(null)}
                                            />
                                        ) : (
                                            <select
                                                value={member.role === 'user' ? 'analyst' : member.role}
                                                onChange={(e) => handleRoleChange(member.id, e.target.value)}
                                                disabled={roleMutation.isPending}
                                                style={{
                                                    fontSize: 12, border: '1px solid var(--border)',
                                                    borderRadius: 'var(--radius-sm)', padding: '4px 8px',
                                                    backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)',
                                                }}
                                            >
                                                <option value="analyst">Analyst</option>
                                                <option value="admin">Admin</option>
                                            </select>
                                        )}
                                    </td>
                                    <td style={{ ...tdStyle, color: 'var(--text-muted)', fontSize: 12 }}>
                                        {member.last_login ? new Date(member.last_login).toLocaleString() : 'Never'}
                                    </td>
                                    <td style={tdStyle}>
                                        {member.id !== user?.id && (
                                            confirmRemoveId === member.id ? (
                                                <InlineConfirm
                                                    message="Remove?"
                                                    onConfirm={() => { removeMutation.mutate(member.id); setConfirmRemoveId(null); }}
                                                    onCancel={() => setConfirmRemoveId(null)}
                                                />
                                            ) : (
                                                <Button variant="danger" size="sm" onClick={() => handleRemove(member)} disabled={removeMutation.isPending} icon={<UserMinus size={14} />}>
                                                    Remove
                                                </Button>
                                            )
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </AppLayout>
    );
}
