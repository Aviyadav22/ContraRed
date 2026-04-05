import { type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import { Card, Badge } from '@/components/ui';
import { Shield, Users, Clock, AlertTriangle, CheckCircle, Globe, FileText } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

async function fetchComplianceStats() {
    // Aggregate from DPDP compliance command center + consent APIs
    const [dashboardRes, purposesRes, consentHealthRes] = await Promise.all([
        fetch(`${API_BASE_URL}/dpdp/dashboard`, { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${API_BASE_URL}/consent/purposes`, { credentials: 'include' }).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE_URL}/dpdp/consent-health`, { credentials: 'include' }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]);
    return {
        dashboard: dashboardRes,
        purposes: purposesRes,
        consentHealth: consentHealthRes,
    };
}

const statCardStyle: CSSProperties = {
    padding: 24,
    borderRadius: 12,
    border: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
};

const sectionStyle: CSSProperties = {
    marginBottom: 32,
};

export default function ComplianceDashboard() {
    const { data, isLoading } = useQuery({
        queryKey: ['compliance-stats'],
        queryFn: fetchComplianceStats,
        staleTime: 60000,
    });

    const dashboard = data?.dashboard;
    const purposes = data?.purposes || [];
    const consentHealthData = data?.consentHealth;

    // Use real data from DPDP dashboard when available
    const totalGrants = consentHealthData?.recent_events?.grants || 0;
    const totalWithdrawals = consentHealthData?.recent_events?.withdrawals || 0;
    const rightsRequests = dashboard?.pending_rights_requests || consentHealthData?.recent_events?.rights_requests || 0;
    const grievances = dashboard?.pending_grievances || consentHealthData?.recent_events?.grievances || 0;
    const consentHealth = consentHealthData?.health_score || 0;
    const overallScore = dashboard?.overall_score || consentHealth;
    const contractsScanned = dashboard?.contracts_scanned || 0;

    if (isLoading) {
        return (
            <AppLayout>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
                    <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                </div>
            </AppLayout>
        );
    }

    return (
        <AppLayout>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <Shield size={24} style={{ color: 'var(--accent)' }} />
                <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                    DPDP Compliance Dashboard
                </h1>
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 32 }}>
                Monitor consent health, rights requests, and compliance status for India's DPDP Act.
            </p>

            {/* Stats Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, ...sectionStyle }}>
                <div style={statCardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <CheckCircle size={18} style={{ color: 'var(--green)' }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Consent Health
                        </span>
                    </div>
                    <span style={{ fontSize: 32, fontWeight: 700, color: overallScore > 70 ? 'var(--green)' : overallScore > 40 ? 'var(--accent)' : 'var(--red)' }}>
                        {overallScore}%
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Consent: {consentHealth}% | {totalGrants} grants / {totalWithdrawals} withdrawals
                    </span>
                </div>

                <div style={statCardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Users size={18} style={{ color: 'var(--accent)' }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Total Events
                        </span>
                    </div>
                    <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {contractsScanned}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Contracts scanned for DPDP</span>
                </div>

                <div style={statCardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileText size={18} style={{ color: 'var(--accent)' }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Rights Requests
                        </span>
                    </div>
                    <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {rightsRequests}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>90-day SLA tracked</span>
                </div>

                <div style={statCardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <AlertTriangle size={18} style={{ color: grievances > 0 ? 'var(--red)' : 'var(--text-muted)' }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Grievances
                        </span>
                    </div>
                    <span style={{ fontSize: 32, fontWeight: 700, color: grievances > 0 ? 'var(--red)' : 'var(--text-primary)' }}>
                        {grievances}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Filed by users</span>
                </div>
            </div>

            {/* Purposes Overview */}
            <div style={sectionStyle}>
                <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                    Registered Consent Purposes
                </h2>
                <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ backgroundColor: 'var(--bg-tertiary)' }}>
                                <th style={thStyle}>Purpose</th>
                                <th style={thStyle}>Data Categories</th>
                                <th style={thStyle}>Third Parties</th>
                                <th style={thStyle}>Required</th>
                                <th style={thStyle}>Retention</th>
                            </tr>
                        </thead>
                        <tbody>
                            {purposes.map((p: any) => (
                                <tr key={p.code} style={{ borderBottom: '1px solid var(--border)' }}>
                                    <td style={tdStyle}>
                                        <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{p.name}</span>
                                        <br />
                                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{p.code}</span>
                                    </td>
                                    <td style={tdStyle}>
                                        {(p.personal_data_categories || []).map((c: string) => (
                                            <span key={c} style={{ display: 'inline-block', padding: '2px 6px', margin: 2, borderRadius: 4, fontSize: 11, backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>{c}</span>
                                        ))}
                                    </td>
                                    <td style={tdStyle}>
                                        {(p.third_parties || []).length > 0 ? (
                                            p.third_parties.map((t: string) => (
                                                <span key={t} style={{ display: 'inline-block', padding: '2px 6px', margin: 2, borderRadius: 4, fontSize: 11, backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>
                                                    <Globe size={10} style={{ display: 'inline', marginRight: 4 }} />{t}
                                                </span>
                                            ))
                                        ) : (
                                            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>None</span>
                                        )}
                                    </td>
                                    <td style={tdStyle}>
                                        <Badge variant={p.is_required ? 'critical' : 'neutral'}>
                                            {p.is_required ? 'Required' : 'Optional'}
                                        </Badge>
                                    </td>
                                    <td style={{ ...tdStyle, fontSize: 12, color: 'var(--text-muted)' }}>
                                        {p.retention_period || '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Alerts & Deadlines */}
            {dashboard?.recent_alerts && dashboard.recent_alerts.length > 0 && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                        Compliance Alerts
                    </h2>
                    <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                        {dashboard.recent_alerts.map((alert: any, i: number) => (
                            <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: 12,
                                padding: '12px 16px', borderBottom: '1px solid var(--border)',
                                backgroundColor: 'var(--bg-secondary)',
                            }}>
                                <AlertTriangle size={16} style={{
                                    color: alert.severity === 'critical' ? 'var(--red)' :
                                        alert.severity === 'warning' ? 'orange' : 'var(--accent)',
                                    flexShrink: 0,
                                }} />
                                <div style={{ flex: 1 }}>
                                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                                        {alert.title}
                                    </span>
                                    <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                                        {alert.description}
                                    </p>
                                </div>
                                <Badge variant={alert.severity === 'critical' ? 'critical' : 'neutral'}>
                                    {alert.severity}
                                </Badge>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upcoming Deadlines */}
            {dashboard?.upcoming_deadlines && dashboard.upcoming_deadlines.length > 0 && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                        DPDP Deadlines
                    </h2>
                    <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                        {dashboard.upcoming_deadlines.map((deadline: any, i: number) => (
                            <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: 12,
                                padding: '12px 16px', borderBottom: '1px solid var(--border)',
                                backgroundColor: 'var(--bg-secondary)',
                            }}>
                                <Clock size={16} style={{
                                    color: deadline.days_remaining < 90 ? 'var(--red)' :
                                        deadline.days_remaining < 365 ? 'orange' : 'var(--text-muted)',
                                    flexShrink: 0,
                                }} />
                                <div style={{ flex: 1 }}>
                                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                                        {deadline.title}
                                    </span>
                                </div>
                                <span style={{ fontSize: 12, color: deadline.days_remaining < 90 ? 'var(--red)' : 'var(--text-muted)', fontWeight: 600 }}>
                                    {deadline.days_remaining} days
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Compliance Checklist */}
            <div style={sectionStyle}>
                <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                    DPDP Compliance Checklist
                </h2>
                <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 20, backgroundColor: 'var(--bg-secondary)' }}>
                    {[
                        { label: 'Consent collection at registration', done: true },
                        { label: 'Purpose-specific toggles (no bundling)', done: true },
                        { label: 'Withdrawal as easy as granting', done: true },
                        { label: 'ISO 27560 machine-readable receipts', done: true },
                        { label: 'Immutable hash-chained audit trail', done: true },
                        { label: 'Right to Access (data export)', done: true },
                        { label: 'Right to Correction', done: true },
                        { label: 'Right to Erasure', done: true },
                        { label: 'Right to Nomination (Section 14)', done: true },
                        { label: 'Grievance redressal (90-day SLA)', done: true },
                        { label: 'Cross-border transfer tracking', done: true },
                        { label: 'Breach notification (72-hour)', done: true },
                        { label: 'Multilingual notices (Hindi + English)', done: true },
                        { label: 'AES-256 encryption at rest', done: true },
                        { label: 'Children consent (under-18)', done: false },
                        { label: 'Consent Manager registration', done: false },
                    ].map((item) => (
                        <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                            {item.done ? (
                                <CheckCircle size={16} style={{ color: 'var(--green)', flexShrink: 0 }} />
                            ) : (
                                <Clock size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                            )}
                            <span style={{ fontSize: 13, color: item.done ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                                {item.label}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </AppLayout>
    );
}

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '10px 16px', fontWeight: 500,
    fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

const tdStyle: CSSProperties = {
    padding: '10px 16px', fontSize: 13,
};
