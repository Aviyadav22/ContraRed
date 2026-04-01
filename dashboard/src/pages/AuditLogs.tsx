import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLogs, type AuditLogPage } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Badge, TextInput, SelectInput } from '@/components/ui';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '10px 16px', fontWeight: 500,
    fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const tdStyle: CSSProperties = {
    padding: '10px 16px',
};

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

    function getActionBadgeVariant(action: string, status: string): 'critical' | 'high' | 'neutral' {
        if (action.includes('failed') || status === 'failure') return 'critical';
        if (action.includes('delete') || action.includes('removed')) return 'high';
        return 'neutral';
    }

    return (
        <AppLayout>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: 24 }}>Audit Logs</h1>

            {/* Filters */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ minWidth: 180 }}>
                    <SelectInput label="Action" value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}>
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
                    </SelectInput>
                </div>
                <div style={{ minWidth: 240 }}>
                    <TextInput label="Email" placeholder="Filter by email..." value={emailFilter} onChange={(e) => setEmailFilter(e.target.value)} />
                </div>
                <TextInput label="From" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} style={{ width: 160 }} />
                <TextInput label="To" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} style={{ width: 160 }} />
            </div>

            {error && (
                <div style={{ color: 'var(--risk-critical)', padding: 16, background: 'var(--risk-critical-bg)', borderRadius: 'var(--radius-md)', marginBottom: 16, border: '1px solid var(--risk-critical-border)' }}>
                    Failed to load data. Please try again.
                </div>
            )}

            {/* Table */}
            <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                    <thead style={{ backgroundColor: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                        <tr>
                            <th scope="col" style={thStyle}>Timestamp</th>
                            <th scope="col" style={thStyle}>User</th>
                            <th scope="col" style={thStyle}>Action</th>
                            <th scope="col" style={thStyle}>Resource</th>
                            <th scope="col" style={thStyle}>Status</th>
                            <th scope="col" style={thStyle}>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>Loading...</td></tr>
                        ) : data?.items.length === 0 ? (
                            <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>No audit logs found</td></tr>
                        ) : (
                            data?.items.map((log) => (
                                <tr
                                    key={log.id}
                                    style={{ borderBottom: '1px solid var(--border)' }}
                                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}
                                >
                                    <td style={{ ...tdStyle, color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: 13 }}>
                                        {new Date(log.timestamp).toLocaleString()}
                                    </td>
                                    <td style={{ ...tdStyle, color: 'var(--text-secondary)' }}>{log.user_email}</td>
                                    <td style={tdStyle}>
                                        <Badge variant={getActionBadgeVariant(log.action, log.status)}>
                                            {log.action.replace(/_/g, ' ')}
                                        </Badge>
                                    </td>
                                    <td style={{ ...tdStyle, color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {log.resource_name}
                                    </td>
                                    <td style={tdStyle}>
                                        <span style={{
                                            fontSize: 12, fontWeight: 500,
                                            color: log.status === 'success' ? 'var(--risk-low)' : log.status === 'failure' ? 'var(--risk-critical)' : 'var(--text-muted)',
                                        }}>
                                            {log.status}
                                        </span>
                                    </td>
                                    <td style={{ ...tdStyle, color: 'var(--text-muted)', fontSize: 12 }}>{log.ip_address || '-'}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
                    <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>
                        Page {page} of {totalPages} ({data?.total} total)
                    </span>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)} icon={<ChevronLeft size={14} />}>
                            Previous
                        </Button>
                        <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} icon={<ChevronRight size={14} />}>
                            Next
                        </Button>
                    </div>
                </div>
            )}
        </AppLayout>
    );
}
