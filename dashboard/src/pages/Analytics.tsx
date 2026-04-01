import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type CSSProperties } from 'react';
import {
    getAnalyticsOverview,
    getAnalyticsRisks,
    getAnalyticsUsers,
    getAnalyticsTrends,
    analyticsExportBlob,
    getAnalyticsROI,
    getPortfolioRisk,
    getTeamPerformance,
    getClauseAnalytics,
    generateAnalyticsReport,
    listAnalyticsReports,
    type RiskBreakdownItem,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Download, X } from 'lucide-react';

const PERIOD_OPTIONS = [
    { value: 7, label: '7 days' },
    { value: 30, label: '30 days' },
    { value: 90, label: '90 days' },
    { value: 365, label: '1 year' },
];

const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'team', label: 'Team' },
    { id: 'reports', label: 'Reports' },
] as const;

type TabId = (typeof TABS)[number]['id'];

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '8px 12px', fontWeight: 500, fontSize: 12,
    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em',
};
const tdStyle: CSSProperties = { padding: '8px 12px' };

function StatCard({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
    return (
        <Card style={highlight ? { borderColor: 'var(--risk-critical-border)', backgroundColor: 'var(--risk-critical-bg)' } : {}}>
            <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4, color: highlight ? 'var(--risk-critical)' : 'var(--text-primary)' }}>{value}</div>
            {sub && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>}
        </Card>
    );
}

function RiskBar({ item }: { item: RiskBreakdownItem }) {
    const max = Math.max(item.total, 1);
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0' }}>
            <div style={{ width: 160, fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.risk_level}>
                {item.risk_level}
            </div>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 2, height: 24 }}>
                {item.red > 0 && <div style={{ backgroundColor: 'var(--risk-critical)', height: '100%', borderRadius: '4px 0 0 4px', width: `${(item.red / max) * 100}%`, minWidth: 4 }} title={`${item.red} RED`} />}
                {item.yellow > 0 && <div style={{ backgroundColor: 'var(--risk-high)', height: '100%', width: `${(item.yellow / max) * 100}%`, minWidth: 4 }} title={`${item.yellow} YELLOW`} />}
                {item.green > 0 && <div style={{ backgroundColor: 'var(--risk-low)', height: '100%', borderRadius: '0 4px 4px 0', width: `${(item.green / max) * 100}%`, minWidth: 4 }} title={`${item.green} GREEN`} />}
            </div>
            <div style={{ width: 40, textAlign: 'right', fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>{item.total}</div>
        </div>
    );
}

function formatCurrency(value: number, currency: string = 'INR'): string {
    if (currency === 'INR') {
        if (value >= 10000000) return `\u20b9${(value / 10000000).toFixed(1)}Cr`;
        if (value >= 100000) return `\u20b9${(value / 100000).toFixed(1)}L`;
        if (value >= 1000) return `\u20b9${(value / 1000).toFixed(1)}K`;
        return `\u20b9${value.toFixed(0)}`;
    }
    return `$${value.toLocaleString()}`;
}

// ============================================================================
// Overview Tab
// ============================================================================
function OverviewTab({ days }: { days: number }) {
    const { data: overview, isLoading, error } = useQuery({ queryKey: ['analytics-overview', days], queryFn: () => getAnalyticsOverview(days) });
    const { data: roi } = useQuery({ queryKey: ['analytics-roi', days], queryFn: () => getAnalyticsROI(days) });
    const { data: risks } = useQuery({ queryKey: ['analytics-risks', days], queryFn: () => getAnalyticsRisks(days) });
    const { data: trends } = useQuery({ queryKey: ['analytics-trends', days], queryFn: () => getAnalyticsTrends('weekly', Math.ceil(days / 7)) });
    const { data: users } = useQuery({ queryKey: ['analytics-users', days], queryFn: () => getAnalyticsUsers(days) });

    if (isLoading) return <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading analytics...</div>;
    if (error) return <div style={{ color: 'var(--risk-critical)', padding: 16 }}>Failed to load data. Please try again.</div>;
    if (!overview) return null;

    const hoursSaved = roi?.time_savings?.hours_saved ?? null;
    const roiValue = roi?.total_roi_value;
    const roiMultiplier = roi?.roi_multiplier;
    const methodology = roi?.methodology;

    return (
        <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 32 }}>
                <StatCard label="Documents Analyzed" value={overview.documents_analyzed} sub={`Last ${days} days`} />
                <StatCard label="Total Risks" value={overview.total_risks} sub={`${overview.red_risks} red, ${overview.yellow_risks} yellow`} />
                <StatCard label="Critical Risks" value={overview.red_risks} sub="Deal-breakers" highlight={overview.red_risks > 0} />
                <StatCard label="Active Users" value={overview.active_users} />
                <StatCard label="Hours Saved" value={hoursSaved != null ? hoursSaved.toFixed(1) : 'N/A'} sub={methodology ? `${methodology.pages_per_hour} pages/hr benchmark` : 'Awaiting ROI data'} />
                {roiValue != null && <StatCard label="ROI" value={roiMultiplier || '\u2014'} sub={`${formatCurrency(roiValue, roi?.time_savings?.currency)} value`} highlight />}
            </div>

            {roi && (
                <Card style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>ROI Breakdown</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
                        <div>
                            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>Time Savings</div>
                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>{formatCurrency(roi.time_savings.monetary_value, roi.time_savings.currency)}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{roi.time_savings.estimated_manual_hours}h manual &rarr; {roi.time_savings.actual_ai_hours}h AI</div>
                        </div>
                        <div>
                            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>Risk Value Protected</div>
                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>{formatCurrency(roi.risk_value.total_risk_value_protected, roi.risk_value.currency)}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{roi.red_risks} red &times; {formatCurrency(roi.methodology.risk_value_per_red)} + {roi.yellow_risks} yellow</div>
                        </div>
                        <div>
                            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>Total ROI</div>
                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent)' }}>{formatCurrency(roi.total_roi_value, roi.time_savings.currency)}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{roi.roi_multiplier} return</div>
                        </div>
                    </div>
                    {methodology?.note && (
                        <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                            Methodology: {methodology.note}
                        </div>
                    )}
                </Card>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
                <Card>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Risk Breakdown</h2>
                    {risks && risks.length > 0 ? (
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 12, height: 12, backgroundColor: 'var(--risk-critical)', borderRadius: 2, display: 'inline-block' }} /> Red</span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 12, height: 12, backgroundColor: 'var(--risk-high)', borderRadius: 2, display: 'inline-block' }} /> Yellow</span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 12, height: 12, backgroundColor: 'var(--risk-low)', borderRadius: 2, display: 'inline-block' }} /> Green</span>
                            </div>
                            {risks.map((r) => <RiskBar key={r.risk_level} item={r} />)}
                        </div>
                    ) : (
                        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No risk data available.</p>
                    )}
                </Card>

                <Card>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Usage Trends</h2>
                    {trends && trends.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {(() => {
                                const maxScans = Math.max(...trends.map(x => x.scans), 1);
                                return trends.map((t) => {
                                    const weekLabel = new Date(t.period).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                    return (
                                        <div key={t.period} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                            <div style={{ width: 64, fontSize: 12, color: 'var(--text-muted)' }}>{weekLabel}</div>
                                            <div style={{ flex: 1, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', height: 20, overflow: 'hidden' }}>
                                                <div style={{ backgroundColor: 'var(--accent)', height: '100%', borderRadius: 'var(--radius-sm)', transition: 'width 0.3s ease', width: `${(t.scans / maxScans) * 100}%`, minWidth: t.scans > 0 ? 8 : 0 }} />
                                            </div>
                                            <div style={{ width: 80, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'right' }}>{t.scans} / {t.risks}</div>
                                        </div>
                                    );
                                });
                            })()}
                        </div>
                    ) : (
                        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No trend data available.</p>
                    )}
                </Card>
            </div>

            <Card>
                <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>User Activity</h2>
                {users && users.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Name</th>
                                    <th scope="col" style={thStyle}>Email</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Scans</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risks</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Last Scan</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u) => (
                                    <tr key={u.user_id} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                        <td style={{ ...tdStyle, fontWeight: 500, color: 'var(--text-primary)' }}>{u.name}</td>
                                        <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{u.email}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{u.scan_count}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{u.risks_found}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-muted)' }}>
                                            {u.last_scan ? new Date(u.last_scan).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No user activity data.</p>
                )}
            </Card>
        </>
    );
}

// ============================================================================
// Portfolio Tab
// ============================================================================
function PortfolioTab({ days }: { days: number }) {
    const { data: portfolio, isLoading } = useQuery({ queryKey: ['analytics-portfolio', days], queryFn: () => getPortfolioRisk(days) });
    const { data: clauses } = useQuery({ queryKey: ['analytics-clauses', days], queryFn: () => getClauseAnalytics(days) });

    if (isLoading) return <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading portfolio...</div>;
    if (!portfolio) return null;

    const { summary, risk_distribution, by_contract_type, high_risk_documents } = portfolio;
    const totalRiskItems = risk_distribution.red + risk_distribution.yellow + risk_distribution.green;

    return (
        <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
                <StatCard label="Total Contracts" value={summary.total_documents} sub={`Last ${days} days`} />
                <StatCard label="Avg Risk Score" value={summary.avg_risk_score.toFixed(1)} sub="out of 10" />
                <StatCard label="Total Risks" value={summary.total_risks} />
                <StatCard label="Avg Risks/Doc" value={summary.avg_risks_per_document.toFixed(1)} />
            </div>

            <Card style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Risk Distribution</h2>
                {totalRiskItems > 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
                        <div style={{ flex: 1, height: 32, display: 'flex', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                            <div style={{ backgroundColor: 'var(--risk-critical)', transition: 'width 0.3s', width: `${(risk_distribution.red / totalRiskItems) * 100}%` }} />
                            <div style={{ backgroundColor: 'var(--risk-high)', transition: 'width 0.3s', width: `${(risk_distribution.yellow / totalRiskItems) * 100}%` }} />
                            <div style={{ backgroundColor: 'var(--risk-low)', transition: 'width 0.3s', width: `${(risk_distribution.green / totalRiskItems) * 100}%` }} />
                        </div>
                        <div style={{ display: 'flex', gap: 16, fontSize: 14 }}>
                            <span style={{ color: 'var(--risk-critical)', fontWeight: 600 }}>{risk_distribution.red} Red</span>
                            <span style={{ color: 'var(--risk-high)', fontWeight: 600 }}>{risk_distribution.yellow} Yellow</span>
                            <span style={{ color: 'var(--risk-low)', fontWeight: 600 }}>{risk_distribution.green} Green</span>
                        </div>
                    </div>
                ) : (
                    <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No risk data.</p>
                )}
            </Card>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
                <Card>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>By Contract Type</h2>
                    {by_contract_type.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {by_contract_type.map((ct) => (
                                <div key={ct.contract_type} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div>
                                        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)' }}>{ct.contract_type}</div>
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ct.document_count} docs, avg risk {ct.avg_risk_score}</div>
                                    </div>
                                    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>{ct.total_risks} risks</div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No data.</p>
                    )}
                </Card>

                <Card>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Clause Risk Analysis</h2>
                    {clauses && clauses.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {clauses.map((c) => (
                                <div key={c.risk_level} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div>
                                        <div style={{ fontSize: 14, fontWeight: 500, color: c.risk_level === 'red' ? 'var(--risk-critical)' : c.risk_level === 'yellow' ? 'var(--risk-high)' : 'var(--risk-low)' }}>
                                            {c.risk_level.toUpperCase()}
                                        </div>
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.resolution_rate}% resolved</div>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ width: 96, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', height: 8, overflow: 'hidden' }}>
                                            <div style={{ backgroundColor: 'var(--risk-low)', height: '100%', borderRadius: 'var(--radius-sm)', width: `${c.resolution_rate}%` }} />
                                        </div>
                                        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', width: 40, textAlign: 'right' }}>{c.count}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No clause data.</p>
                    )}
                </Card>
            </div>

            {high_risk_documents.length > 0 && (
                <Card style={{ borderColor: 'var(--risk-critical-border)' }}>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--risk-critical)', marginBottom: 16 }}>High Risk Contracts (Score &ge; 7)</h2>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Filename</th>
                                    <th scope="col" style={thStyle}>Type</th>
                                    <th scope="col" style={thStyle}>Counterparty</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risk Score</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {high_risk_documents.map((doc) => (
                                    <tr key={doc.document_id} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--risk-critical-bg)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                        <td style={{ ...tdStyle, fontWeight: 500, color: 'var(--text-primary)' }}>{doc.filename}</td>
                                        <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{doc.contract_type || '\u2014'}</td>
                                        <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{doc.counterparty || '\u2014'}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: 'var(--risk-critical)' }}>{doc.risk_score?.toFixed(1) ?? '\u2014'}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{doc.total_risks}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}
        </>
    );
}

// ============================================================================
// Team Tab
// ============================================================================
function TeamTab({ days }: { days: number }) {
    const { data: team, isLoading } = useQuery({ queryKey: ['analytics-team', days], queryFn: () => getTeamPerformance(days) });

    if (isLoading) return <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading team data...</div>;
    if (!team || team.length === 0) return <p style={{ fontSize: 14, color: 'var(--text-muted)', padding: '32px 0', textAlign: 'center' }}>No team data available.</p>;

    const maxDocs = Math.max(...team.map(t => t.documents_reviewed), 1);

    return (
        <Card>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Team Performance</h2>
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)' }}>
                            <th scope="col" style={thStyle}>Name</th>
                            <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Docs Reviewed</th>
                            <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Risks Found</th>
                            <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Avg Risks/Doc</th>
                            <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Words Reviewed</th>
                            <th scope="col" style={{ ...thStyle, width: 160 }}>Activity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {team.map((m) => (
                            <tr key={m.user_id} style={{ borderBottom: '1px solid var(--border)' }} onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }} onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; }}>
                                <td style={tdStyle}>
                                    <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{m.name}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.email}</div>
                                </td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{m.documents_reviewed}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{m.total_risks_found}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>{m.avg_risks_per_doc}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-muted)' }}>{m.total_words_reviewed.toLocaleString()}</td>
                                <td style={tdStyle}>
                                    <div style={{ backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', height: 8, overflow: 'hidden' }}>
                                        <div style={{ backgroundColor: 'var(--accent)', height: '100%', borderRadius: 'var(--radius-sm)', width: `${(m.documents_reviewed / maxDocs) * 100}%` }} />
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </Card>
    );
}

// ============================================================================
// Reports Tab
// ============================================================================
function ReportsTab({ days }: { days: number }) {
    const queryClient = useQueryClient();
    const [generating, setGenerating] = useState<string | null>(null);

    const { data: reports, isLoading } = useQuery({ queryKey: ['analytics-reports'], queryFn: () => listAnalyticsReports(undefined, 20) });

    const generateMutation = useMutation({
        mutationFn: (type: string) => generateAnalyticsReport(type, days),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['analytics-reports'] }); setGenerating(null); },
        onError: () => setGenerating(null),
    });

    const reportTypes = [
        { id: 'executive_summary', label: 'Executive Summary', desc: 'Board-ready 6 key metrics' },
        { id: 'gc_operations', label: 'GC Operations', desc: 'General Counsel operational overview' },
        { id: 'team_review', label: 'Team Review', desc: 'Per-reviewer performance breakdown' },
        { id: 'risk_audit', label: 'Risk Audit', desc: 'Detailed risk analysis across portfolio' },
    ];

    return (
        <>
            <Card style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Generate Report</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                    {reportTypes.map((rt) => (
                        <button
                            key={rt.id}
                            onClick={() => { setGenerating(rt.id); generateMutation.mutate(rt.id); }}
                            disabled={generating !== null}
                            style={{
                                textAlign: 'left', padding: 16, border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-md)', cursor: generating ? 'not-allowed' : 'pointer',
                                backgroundColor: 'var(--bg-surface)', opacity: generating !== null && generating !== rt.id ? 0.5 : 1,
                                transition: 'all var(--transition-fast)',
                            }}
                            onMouseEnter={(e) => { if (!generating) { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; } }}
                            onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.backgroundColor = 'var(--bg-surface)'; }}
                        >
                            <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{rt.label}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{rt.desc}</div>
                            {generating === rt.id && <div style={{ fontSize: 12, color: 'var(--accent)', marginTop: 8 }}>Generating...</div>}
                        </button>
                    ))}
                </div>
            </Card>

            <Card>
                <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Report History</h2>
                {isLoading ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading...</div>
                ) : reports && reports.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {reports.map((r) => (
                            <div key={r.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{r.title}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                        {r.report_type.replace('_', ' ')} &mdash; {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                    </div>
                                </div>
                                <Badge variant="neutral">{r.format}</Badge>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>No reports generated yet.</p>
                )}
            </Card>
        </>
    );
}

// ============================================================================
// Main Analytics Page
// ============================================================================
export default function Analytics() {
    const [days, setDays] = useState(30);
    const [activeTab, setActiveTab] = useState<TabId>('overview');
    const [error, setError] = useState('');

    const handleExport = async () => {
        try {
            const blob = await analyticsExportBlob(days);
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `contrared_analytics_${days}d.csv`;
            link.click();
            URL.revokeObjectURL(link.href);
        } catch {
            setError('Export failed. Please try again.');
        }
    };

    const tabStyle = (active: boolean): CSSProperties => ({
        padding: '8px 16px', fontSize: 14, fontWeight: 500, borderRadius: 'var(--radius-sm)', cursor: 'pointer',
        border: 'none', transition: 'all var(--transition-fast)',
        backgroundColor: active ? 'var(--bg-surface)' : 'transparent',
        color: active ? 'var(--text-primary)' : 'var(--text-muted)',
        boxShadow: active ? 'var(--shadow-sm)' : 'none',
    });

    return (
        <AppLayout>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Analytics</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Firm-wide contract review metrics and ROI</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 140 }}>
                        <SelectInput value={days} onChange={(e) => setDays(Number(e.target.value))}>
                            {PERIOD_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </SelectInput>
                    </div>
                    <Button onClick={handleExport} icon={<Download size={16} />}>Export CSV</Button>
                </div>
            </div>

            {error && (
                <div style={{
                    background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)',
                    color: 'var(--risk-critical)', padding: '10px 16px', borderRadius: 'var(--radius-md)',
                    marginBottom: 16, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                    <span>{error}</span>
                    <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--risk-critical)' }}>
                        <X size={16} />
                    </button>
                </div>
            )}

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 24, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', padding: 4, width: 'fit-content' }}>
                {TABS.map((tab) => (
                    <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={tabStyle(activeTab === tab.id)}>{tab.label}</button>
                ))}
            </div>

            {activeTab === 'overview' && <OverviewTab days={days} />}
            {activeTab === 'portfolio' && <PortfolioTab days={days} />}
            {activeTab === 'team' && <TeamTab days={days} />}
            {activeTab === 'reports' && <ReportsTab days={days} />}
        </AppLayout>
    );
}
