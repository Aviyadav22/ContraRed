import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLogs, type AuditLogPage } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function AuditLogs() {
    const [page, setPage] = useState(1);
    const [actionFilter, setActionFilter] = useState('');
    const [emailFilter, setEmailFilter] = useState('');
    const [debouncedEmail, setDebouncedEmail] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            setDebouncedEmail(emailFilter);
            setPage(1);
        }, 300);
        return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
    }, [emailFilter]);

    const { data, isLoading, error } = useQuery<AuditLogPage>({
        queryKey: ['audit-logs', page, actionFilter, debouncedEmail, dateFrom, dateTo],
        queryFn: () => getAuditLogs({
            page,
            page_size: 25,
            action: actionFilter || undefined,
            user_email: debouncedEmail || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
        }),
    });

    const totalPages = data ? Math.ceil(data.total / 25) : 0;

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-2xl font-bold text-slate-900 mb-6">Audit Logs</h1>

                {/* Filters */}
                <div className="flex gap-4 mb-6 flex-wrap items-end">
                    <select
                        value={actionFilter}
                        onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
                        className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                    >
                        <option value="">All Actions</option>
                        <option value="login_success">Login Success</option>
                        <option value="login_failed">Login Failed</option>
                        <option value="user_registered">User Registered</option>
                        <option value="analyze">Document Analyzed</option>
                        <option value="ai_full_analysis">AI Analysis</option>
                        <option value="redline_generated">Redline Generated</option>
                        <option value="summary_generated">Summary Generated</option>
                        <option value="playbook_created">Playbook Created</option>
                        <option value="playbook_updated">Playbook Updated</option>
                        <option value="playbook_deleted">Playbook Deleted</option>
                        <option value="role_changed">Role Changed</option>
                    </select>

                    <input
                        type="text"
                        placeholder="Filter by email..."
                        value={emailFilter}
                        onChange={(e) => setEmailFilter(e.target.value)}
                        className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white w-64"
                    />

                    <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-500">From</label>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                            className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-500">To</label>
                        <input
                            type="date"
                            value={dateTo}
                            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                            className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                        />
                    </div>
                </div>

                {error && <div className="text-red-600 p-4">Failed to load data. Please try again.</div>}

                {/* Table */}
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Timestamp</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">User</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Action</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Resource</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
                                <th scope="col" className="text-left px-4 py-3 font-medium text-slate-600">IP</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading ? (
                                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
                            ) : data?.items.length === 0 ? (
                                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">No audit logs found</td></tr>
                            ) : (
                                data?.items.map((log) => (
                                    <tr key={log.id} className="border-b border-slate-100 hover:bg-slate-50">
                                        <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                                            {new Date(log.timestamp).toLocaleString()}
                                        </td>
                                        <td className="px-4 py-3 text-slate-700">{log.user_email}</td>
                                        <td className="px-4 py-3">
                                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${log.action.includes('failed') || log.status === 'failure'
                                                ? 'bg-red-50 text-red-700'
                                                : log.action.includes('delete') || log.action.includes('removed')
                                                    ? 'bg-amber-50 text-amber-700'
                                                    : 'bg-slate-100 text-slate-700'
                                                }`}>
                                                {log.action.replace(/_/g, ' ')}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-slate-600 max-w-[200px] truncate">{log.resource_name}</td>
                                        <td className="px-4 py-3">
                                            <span className={`text-xs font-medium ${log.status === 'success' ? 'text-green-600' :
                                                log.status === 'failure' ? 'text-red-600' : 'text-slate-500'
                                                }`}>
                                                {log.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-slate-400 text-xs">{log.ip_address || '-'}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between mt-4">
                        <span className="text-sm text-slate-500">
                            Page {page} of {totalPages} ({data?.total} total)
                        </span>
                        <div className="flex gap-2">
                            <button
                                disabled={page <= 1}
                                onClick={() => setPage(p => p - 1)}
                                className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50"
                            >
                                Previous
                            </button>
                            <button
                                disabled={page >= totalPages}
                                onClick={() => setPage(p => p + 1)}
                                className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
