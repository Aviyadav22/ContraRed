import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type CSSProperties } from 'react';
import {
    generateAnalyticsReport,
    listAnalyticsReports,
    getAnalyticsReport,
    type GeneratedReport,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Download } from 'lucide-react';

const REPORT_TYPES = [
    { id: 'executive_summary', label: 'Executive Summary', desc: 'Board-ready 6 key metrics on one page', icon: 'E' },
    { id: 'gc_operations', label: 'GC Operations', desc: 'General Counsel operational overview with portfolio risk', icon: 'G' },
    { id: 'team_review', label: 'Team Review', desc: 'Per-reviewer performance breakdown and activity', icon: 'T' },
    { id: 'risk_audit', label: 'Risk Audit', desc: 'Detailed risk analysis across contract portfolio', icon: 'R' },
];

const SEVERITY_MAP: Record<string, 'critical' | 'high' | 'low' | 'neutral'> = {
    red: 'critical', RED: 'critical', critical: 'critical', high: 'critical',
    yellow: 'high', YELLOW: 'high', medium: 'high', warning: 'high',
    green: 'low', GREEN: 'low', low: 'low', safe: 'low',
};

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '8px 12px', fontWeight: 500, fontSize: 12,
    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em',
};
const tdStyle: CSSProperties = { padding: '8px 12px' };

function MetricCard({ label, value }: { label: string; value: string | number }) {
    return (
        <Card padding="compact">
            <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>{value}</div>
        </Card>
    );
}

function ReportViewer({ report }: { report: GeneratedReport }) {
    if (!report.data) return <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No data available.</p>;

    const data = report.data as Record<string, unknown>;
    const title = (data.title as string) || report.title;
    const reportType = (data.report_type as string) || report.report_type;
    const generatedAt = (data.generated_at as string) || report.created_at;
    const periodDays = data.period_days as number | undefined;

    const overview = data.overview as Record<string, unknown> | undefined;
    const summary = data.summary as Record<string, unknown> | undefined;
    const metrics = data.metrics as Record<string, unknown> | undefined;
    const risks = data.risks as Array<Record<string, unknown>> | undefined;
    const findings = data.findings as Array<Record<string, unknown>> | undefined;
    const team = data.team as Array<Record<string, unknown>> | undefined;
    const teamPerformance = data.team_performance as Array<Record<string, unknown>> | undefined;
    const riskDistribution = data.risk_distribution as Record<string, number> | undefined;
    const highRiskDocuments = data.high_risk_documents as Array<Record<string, unknown>> | undefined;

    const metricsSource = overview || summary || metrics || {};
    const metricEntries = Object.entries(metricsSource).filter(([, v]) => typeof v === 'number' || typeof v === 'string');
    const riskItems = risks || findings || [];
    const teamItems = team || teamPerformance || [];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                    <h3 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>{title}</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
                        <Badge variant="critical">{reportType.replace(/_/g, ' ').toUpperCase()}</Badge>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            {new Date(generatedAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                        </span>
                        {periodDays && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>({periodDays} day period)</span>}
                    </div>
                </div>
            </div>

            {metricEntries.length > 0 && (
                <div>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Key Metrics</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
                        {metricEntries.map(([key, value]) => (
                            <MetricCard key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} value={typeof value === 'number' ? value.toLocaleString() : String(value)} />
                        ))}
                    </div>
                </div>
            )}

            {riskDistribution && (
                <Card>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Risk Distribution</h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        {Object.entries(riskDistribution).map(([level, count]) => (
                            <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Badge variant={SEVERITY_MAP[level] || 'neutral'}>{level.toUpperCase()}</Badge>
                                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{count}</span>
                            </div>
                        ))}
                    </div>
                </Card>
            )}

            {riskItems.length > 0 && (
                <Card>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Risk Findings</h4>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Item</th>
                                    <th scope="col" style={thStyle}>Severity</th>
                                    <th scope="col" style={thStyle}>Details</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {riskItems.map((item, idx) => {
                                    const name = (item.risk_level || item.clause_type || item.name || item.title || `Finding ${idx + 1}`) as string;
                                    const severity = (item.severity || item.risk_level || item.level || 'unknown') as string;
                                    const details = (item.description || item.details || item.text || '') as string;
                                    const count = (item.count || item.total || '') as string | number;
                                    return (
                                        <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                            <td style={{ ...tdStyle, fontWeight: 500, color: 'var(--text-primary)' }}>{String(name)}</td>
                                            <td style={tdStyle}><Badge variant={SEVERITY_MAP[String(severity).toLowerCase()] || 'neutral'}>{String(severity).toUpperCase()}</Badge></td>
                                            <td style={{ ...tdStyle, color: 'var(--text-muted)', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(details)}</td>
                                            <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)', fontWeight: 500 }}>{count !== '' ? String(count) : '--'}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {teamItems.length > 0 && (
                <Card>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>Team Performance</h4>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Name</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Docs Reviewed</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risks Found</th>
                                </tr>
                            </thead>
                            <tbody>
                                {teamItems.map((member, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                        <td style={{ ...tdStyle, fontWeight: 500, color: 'var(--text-primary)' }}>{String(member.name || member.email || `User ${idx + 1}`)}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{String(member.documents_reviewed || member.scan_count || '--')}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{String(member.total_risks_found || member.risks_found || '--')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {highRiskDocuments && highRiskDocuments.length > 0 && (
                <Card style={{ borderColor: 'var(--risk-critical-border)' }}>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--risk-critical)', marginBottom: 12 }}>High Risk Documents</h4>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Filename</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risk Score</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {highRiskDocuments.map((doc, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--risk-critical-bg)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                        <td style={{ ...tdStyle, fontWeight: 500, color: 'var(--text-primary)' }}>{String(doc.filename)}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: 'var(--risk-critical)' }}>{doc.risk_score != null ? Number(doc.risk_score).toFixed(1) : '--'}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{String(doc.total_risks || '--')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {metricEntries.length === 0 && riskItems.length === 0 && teamItems.length === 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {Object.entries(data).filter(([k]) => !['title', 'report_type', 'generated_at', 'period_days'].includes(k)).map(([key, value]) => (
                        <Card key={key}>
                            <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                                {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                            </h4>
                            {typeof value === 'object' && value !== null ? (
                                <div style={{ fontSize: 14, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                                        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                                            <span style={{ color: 'var(--text-muted)' }}>{k.replace(/_/g, ' ')}</span>
                                            <span style={{ fontWeight: 500 }}>{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{String(value)}</p>
                            )}
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Reports() {
    const queryClient = useQueryClient();
    const [days, setDays] = useState(30);
    const [generating, setGenerating] = useState<string | null>(null);
    const [selectedReport, setSelectedReport] = useState<GeneratedReport | null>(null);
    const [loadingReport, setLoadingReport] = useState(false);
    const [error, setError] = useState('');

    const { data: reports, isLoading } = useQuery({
        queryKey: ['analytics-reports'],
        queryFn: () => listAnalyticsReports(undefined, 50),
    });

    const generateMutation = useMutation({
        mutationFn: (type: string) => generateAnalyticsReport(type, days),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['analytics-reports'] });
            setGenerating(null);
            setSelectedReport(data);
            setError('');
        },
        onError: (err) => {
            setGenerating(null);
            setError(err instanceof Error ? err.message : 'Failed to generate report');
        },
    });

    const handleViewReport = async (reportId: string) => {
        setLoadingReport(true);
        setError('');
        try {
            const full = await getAnalyticsReport(reportId);
            setSelectedReport(full);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load report');
        } finally {
            setLoadingReport(false);
        }
    };

    const handleDownloadJSON = () => {
        if (!selectedReport?.data) return;
        const blob = new Blob([JSON.stringify(selectedReport.data, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${selectedReport.title.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
        link.click();
        URL.revokeObjectURL(link.href);
    };

    return (
        <AppLayout>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Reports</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Generate and view analytics reports</p>
                </div>
                <div style={{ width: 140 }}>
                    <SelectInput value={days} onChange={(e) => setDays(Number(e.target.value))}>
                        <option value={7}>7 days</option>
                        <option value={30}>30 days</option>
                        <option value={90}>90 days</option>
                        <option value={365}>1 year</option>
                    </SelectInput>
                </div>
            </div>

            {error && (
                <div style={{ background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)', color: 'var(--risk-critical)', padding: '10px 16px', borderRadius: 'var(--radius-md)', marginBottom: 16, fontSize: 14 }}>
                    {error}
                </div>
            )}

            {/* Generate Reports */}
            <Card style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Generate New Report</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                    {REPORT_TYPES.map((rt) => (
                        <button
                            key={rt.id}
                            onClick={() => { setGenerating(rt.id); generateMutation.mutate(rt.id); }}
                            disabled={generating !== null}
                            style={{
                                textAlign: 'left', padding: 20, border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-lg)', cursor: generating ? 'not-allowed' : 'pointer',
                                backgroundColor: 'var(--bg-surface)', opacity: generating !== null && generating !== rt.id ? 0.5 : 1,
                                transition: 'all var(--transition-fast)',
                            }}
                            onMouseEnter={(e) => { if (!generating) { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; } }}
                            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.backgroundColor = 'var(--bg-surface)'; }}
                        >
                            <div style={{
                                width: 40, height: 40, backgroundColor: 'var(--accent-glow)',
                                color: 'var(--accent)', fontWeight: 700, borderRadius: 'var(--radius-md)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12,
                            }}>
                                {rt.icon}
                            </div>
                            <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{rt.label}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{rt.desc}</div>
                            {generating === rt.id && <div style={{ fontSize: 12, color: 'var(--accent)', marginTop: 8, fontWeight: 500 }}>Generating...</div>}
                        </button>
                    ))}
                </div>
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
                {/* Report List */}
                <Card>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Report History</h2>
                    {isLoading ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: '16px 0' }}>Loading...</div>
                    ) : reports && reports.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 600, overflowY: 'auto' }}>
                            {reports.map((r) => (
                                <button
                                    key={r.id}
                                    onClick={() => handleViewReport(r.id)}
                                    style={{
                                        width: '100%', textAlign: 'left', padding: 12, borderRadius: 'var(--radius-md)',
                                        border: `1px solid ${selectedReport?.id === r.id ? 'var(--accent)' : 'var(--border)'}`,
                                        backgroundColor: selectedReport?.id === r.id ? 'var(--bg-hover)' : 'transparent',
                                        cursor: 'pointer', transition: 'all var(--transition-fast)',
                                    }}
                                    onMouseEnter={(e) => { if (selectedReport?.id !== r.id) e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                                    onMouseLeave={(e) => { if (selectedReport?.id !== r.id) e.currentTarget.style.backgroundColor = 'transparent'; }}
                                >
                                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.title}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                                        {r.report_type.replace(/_/g, ' ')} &mdash; {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                    </div>
                                </button>
                            ))}
                        </div>
                    ) : (
                        <p style={{ fontSize: 14, color: 'var(--text-muted)', padding: '16px 0' }}>No reports generated yet. Use the cards above to create one.</p>
                    )}
                </Card>

                {/* Report Viewer */}
                <Card>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                            {selectedReport ? selectedReport.title : 'Select a Report'}
                        </h2>
                        {selectedReport?.data && (
                            <Button variant="secondary" size="sm" onClick={handleDownloadJSON} icon={<Download size={14} />}>
                                Download JSON
                            </Button>
                        )}
                    </div>
                    {loadingReport ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: '32px 0', textAlign: 'center' }}>Loading report...</div>
                    ) : selectedReport ? (
                        <ReportViewer report={selectedReport} />
                    ) : (
                        <div style={{ color: 'var(--text-muted)', fontSize: 14, padding: '32px 0', textAlign: 'center' }}>
                            Select a report from the list or generate a new one.
                        </div>
                    )}
                </Card>
            </div>
        </AppLayout>
    );
}
