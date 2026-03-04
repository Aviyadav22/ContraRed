import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getStoredUser, getTeamMembers, changeTeamMemberRole, removeTeamMember, type TeamMember } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function Team() {
    const user = getStoredUser();
    const queryClient = useQueryClient();

    const { data: members, isLoading } = useQuery<TeamMember[]>({
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
        if (confirm(`Change this member's role to ${newRole}?`)) {
            roleMutation.mutate({ userId: memberId, role: newRole });
        }
    };

    const handleRemove = (member: TeamMember) => {
        if (confirm(`Remove ${member.name} (${member.email}) from the organization?`)) {
            removeMutation.mutate(member.id);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-2xl font-bold text-slate-900 mb-6">Team Management</h1>

                {(roleMutation.isError || removeMutation.isError) && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                        {(roleMutation.error as Error)?.message || (removeMutation.error as Error)?.message}
                    </div>
                )}

                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium text-slate-600">Name</th>
                                <th className="text-left px-4 py-3 font-medium text-slate-600">Email</th>
                                <th className="text-left px-4 py-3 font-medium text-slate-600">Role</th>
                                <th className="text-left px-4 py-3 font-medium text-slate-600">Last Login</th>
                                <th className="text-left px-4 py-3 font-medium text-slate-600">Actions</th>
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
                                                <button
                                                    onClick={() => handleRemove(member)}
                                                    disabled={removeMutation.isPending}
                                                    className="text-xs text-red-600 hover:text-red-800 font-medium"
                                                >
                                                    Remove
                                                </button>
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
