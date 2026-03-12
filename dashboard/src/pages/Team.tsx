import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { getStoredUser, getTeamMembers, changeTeamMemberRole, removeTeamMember, type TeamMember } from '@/api/client';
import AppHeader from '@/components/AppHeader';

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
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-2xl font-bold text-slate-900 mb-6">Team Management</h1>

                {/* Invite Member */}
                <div className="bg-white border border-slate-200 rounded-lg p-5 mb-6">
                    <h2 className="text-sm font-semibold text-slate-800 mb-3">Invite Member</h2>
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            setInviteMessage('Team invitation feature coming soon');
                            setTimeout(() => setInviteMessage(null), 4000);
                        }}
                        className="flex items-end gap-3"
                    >
                        <div className="flex-1 max-w-xs">
                            <label htmlFor="invite-email" className="block text-xs font-medium text-slate-500 mb-1">Email</label>
                            <input
                                id="invite-email"
                                type="email"
                                required
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                placeholder="colleague@company.com"
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-slate-300"
                            />
                        </div>
                        <div>
                            <label htmlFor="invite-role" className="block text-xs font-medium text-slate-500 mb-1">Role</label>
                            <select
                                id="invite-role"
                                value={inviteRole}
                                onChange={(e) => setInviteRole(e.target.value)}
                                className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                            >
                                <option value="analyst">Analyst</option>
                                <option value="admin">Admin</option>
                            </select>
                        </div>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-slate-800 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition-colors"
                        >
                            Send Invite
                        </button>
                    </form>
                    {inviteMessage && (
                        <div className="mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg">
                            {inviteMessage}
                        </div>
                    )}
                </div>

                {error && <div className="text-red-600 p-4">Failed to load data. Please try again.</div>}

                {(roleMutation.isError || removeMutation.isError) && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                        {(roleMutation.error as Error)?.message || (removeMutation.error as Error)?.message}
                    </div>
                )}

                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Name</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Email</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Role</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Last Login</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading ? (
                                <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
                            ) : members?.length === 0 ? (
                                <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">No team members found. Users need to be assigned to your organization.</td></tr>
                            ) : (
                                members?.map((member) => (
                                    <tr key={member.id} className="border-b border-slate-100 hover:bg-slate-50">
                                        <td className="px-4 py-3 text-slate-900 font-medium">{member.name}</td>
                                        <td className="px-4 py-3 text-slate-600">{member.email}</td>
                                        <td className="px-4 py-3">
                                            {member.id === user?.id ? (
                                                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">{member.role} (you)</span>
                                            ) : confirmRoleChange?.id === member.id ? (
                                                <span className="inline-flex items-center gap-1.5">
                                                    <span className="text-[12px] text-slate-500">Change to {confirmRoleChange.role}?</span>
                                                    <button onClick={() => { roleMutation.mutate({ userId: confirmRoleChange.id, role: confirmRoleChange.role }); setConfirmRoleChange(null); }} className="text-[12px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded hover:bg-red-100">Yes</button>
                                                    <button onClick={() => setConfirmRoleChange(null)} className="text-[12px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded hover:bg-slate-200">No</button>
                                                </span>
                                            ) : (
                                                <select
                                                    value={member.role === 'user' ? 'analyst' : member.role}
                                                    onChange={(e) => handleRoleChange(member.id, e.target.value)}
                                                    className="text-xs border border-slate-200 rounded px-2 py-1 bg-white"
                                                    disabled={roleMutation.isPending}
                                                >
                                                    <option value="analyst">Analyst</option>
                                                    <option value="admin">Admin</option>
                                                </select>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400 text-xs">
                                            {member.last_login ? new Date(member.last_login).toLocaleString() : 'Never'}
                                        </td>
                                        <td className="px-4 py-3">
                                            {member.id !== user?.id && (
                                                confirmRemoveId === member.id ? (
                                                    <span className="inline-flex items-center gap-1.5">
                                                        <span className="text-[12px] text-slate-500">Remove?</span>
                                                        <button onClick={() => { removeMutation.mutate(member.id); setConfirmRemoveId(null); }} className="text-[12px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded hover:bg-red-100">Yes</button>
                                                        <button onClick={() => setConfirmRemoveId(null)} className="text-[12px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded hover:bg-slate-200">No</button>
                                                    </span>
                                                ) : (
                                                    <button
                                                        onClick={() => handleRemove(member)}
                                                        disabled={removeMutation.isPending}
                                                        className="text-xs text-red-600 hover:text-red-800 font-medium"
                                                    >
                                                        Remove
                                                    </button>
                                                )
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </main>
        </div>
    );
}
