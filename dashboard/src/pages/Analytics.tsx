import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
    getAnalyticsOverview,
    getAnalyticsRisks,
    getAnalyticsUsers,
    getAnalyticsTrends,
    getAnalyticsExportUrl,
    getAnalyticsROI,
    getPortfolioRisk,
    getTeamPerformance,
    getClauseAnalytics,
    generateAnalyticsReport,
    listAnalyticsReports,
    type RiskBreakdownItem,
} from '@/api/client';
import AppHeader from '@/components/AppHeader';

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

function StatCard({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
    return (
        <div className={`rounded-xl border p-5 ${highlight ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
            <div className="text-sm font-medium text-slate-500">{label}</div>
            <div className={`text-3xl font-bold mt-1 ${highlight ? 'text-red-700' : 'text-slate-900'}`}>{value}</div>
            {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
        </div>
    );
}

function RiskBar({ item }: { item: RiskBreakdownItem }) {
    const max = Math.max(item.total, 1);
    return (
        <div className="flex items-center gap-3 py-2">
            <div className="w-40 text-sm font-medium text-slate-700 truncate" title={item.risk_level}>
                {item.risk_level}
            </div>
            <div className="flex-1 flex items-center gap-1 h-6">
                {item.red > 0 && (
                    <div className="bg-red-500 h-full rounded-l" style={{ width: `${(item.red / max) * 100}%`, minWidth: '4px' }} title={`${item.red} RED`} />
                )}
                {item.yellow > 0 && (
                    <div className="bg-amber-400 h-full" style={{ width: `${(item.yellow / max) * 100}%`, minWidth: '4px' }} title={`${item.yellow} YELLOW`} />
                )}
                {item.green > 0 && (
                    <div className="bg-green-400 h-full rounded-r" style={{ width: `${(item.green / max) * 100}%`, minWidth: '4px' }} title={`${item.green} GREEN`} />
                )}
            </div>
            <div className="w-10 text-right text-sm font-semibold text-slate-600">{item.total}</div>
        </div>
    );
}

function formatCurrency(value: number, currency: string = 'INR'): string {
    if (currency === 'INR') {
        if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
        if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
        if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
        return `₹${value.toFixed(0)}`;
    }
    return `$${value.toLocaleString()}`;
}

// ============================================================================
// Overview Tab
// ============================================================================
function OverviewTab({ days }: { days: number }) {
    const { data: overview, isLoading, error } = useQuery({
        queryKey: ['analytics-overview', days],
        queryFn: () => getAnalyticsOverview(days),
    });
    const { data: roi } = useQuery({
        queryKey: ['analytics-roi', days],
        queryFn: () => getAnalyticsROI(days),
    });
    const { data: risks } = useQuery({
        queryKey: ['analytics-risks', days],
        queryFn: () => getAnalyticsRisks(days),
    });
    const { data: trends } = useQuery({
        queryKey: ['analytics-trends', days],
        queryFn: () => getAnalyticsTrends('weekly', Math.ceil(days / 7)),
    });
    const { data: users } = useQuery({
        queryKey: ['analytics-users', days],
        queryFn: () => getAnalyticsUsers(days),
    });

    if (isLoading) return <div className="text-center py-12 text-slate-400">Loading analytics...</div>;
    if (error) return <div className="text-red-600 p-4">Failed to load data. Please try again.</div>;
    if (!overview) return null;

    const hoursSaved = roi?.time_savings?.hours_saved ?? null;
    const roiValue = roi?.total_roi_value;
    const roiMultiplier = roi?.roi_multiplier;
    const methodology = roi?.methodology;

    return (
        <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
                <StatCard label="Documents Analyzed" value={overview.documents_analyzed} sub={`Last ${days} days`} />
                <StatCard label="Total Risks" value={overview.total_risks} sub={`${overview.red_risks} red, ${overview.yellow_risks} yellow`} />
                <StatCard label="Critical Risks" value={overview.red_risks} sub="Deal-breakers" highlight={overview.red_risks > 0} />
                <StatCard label="Active Users" value={overview.active_users} />
                <StatCard
                    label="Hours Saved"
                    value={hoursSaved != null ? hoursSaved.toFixed(1) : 'N/A'}
                    sub={methodology ? `${methodology.pages_per_hour} pages/hr benchmark` : 'Awaiting ROI data'}
                />
                {roiValue != null && (
                    <StatCard
                        label="ROI"
                        value={roiMultiplier || '—'}
                        sub={`${formatCurrency(roiValue, roi?.time_savings?.currency)} value`}
                        highlight
                    />
                )}
            </div>

            {/* ROI Breakdown */}
            {roi && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">ROI Breakdown</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                            <div className="text-sm text-slate-500 mb-1">Time Savings</div>
                            <div className="text-2xl font-bold text-slate-900">
                                {formatCurrency(roi.time_savings.monetary_value, roi.time_savings.currency)}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">
                                {roi.time_savings.estimated_manual_hours}h manual → {roi.time_savings.actual_ai_hours}h AI
                            </div>
                        </div>
                        <div>
                            <div className="text-sm text-slate-500 mb-1">Risk Value Protected</div>
                            <div className="text-2xl font-bold text-slate-900">
                                {formatCurrency(roi.risk_value.total_risk_value_protected, roi.risk_value.currency)}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">
                                {roi.red_risks} red × {formatCurrency(roi.methodology.risk_value_per_red)} + {roi.yellow_risks} yellow
                            </div>
                        </div>
                        <div>
                            <div className="text-sm text-slate-500 mb-1">Total ROI</div>
                            <div className="text-2xl font-bold text-red-700">
                                {formatCurrency(roi.total_roi_value, roi.time_savings.currency)}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">{roi.roi_multiplier} return</div>
                        </div>
                    </div>
                    {methodology?.note && (
                        <div className="mt-4 text-xs text-slate-400 border-t border-slate-100 pt-3">
                            Methodology: {methodology.note}
                        </div>
                    )}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Risk Breakdown */}
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Breakdown</h2>
                    {risks && risks.length > 0 ? (
                        <div>
                            <div className="flex items-center gap-4 mb-3 text-xs text-slate-400">
                                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500 rounded-sm inline-block" /> Red</span>
                                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-400 rounded-sm inline-block" /> Yellow</span>
                                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-400 rounded-sm inline-block" /> Green</span>
                            </div>
                            {risks.map((r) => <RiskBar key={r.risk_level} item={r} />)}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400">No risk data available.</p>
                    )}
                </div>

                {/* Trends */}
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">Usage Trends</h2>
                    {trends && trends.length > 0 ? (
                        <div className="space-y-2">
                            {(() => {
                                const maxScans = Math.max(...trends.map(x => x.scans), 1);
                                return trends.map((t) => {
                                    const weekLabel = new Date(t.period).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                    return (
                                        <div key={t.period} className="flex items-center gap-3">
                                            <div className="w-16 text-xs text-slate-500">{weekLabel}</div>
                                            <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden">
                                                <div
                                                    className="bg-red-500 h-full rounded-full transition-all"
                                                    style={{ width: `${(t.scans / maxScans) * 100}%`, minWidth: t.scans > 0 ? '8px' : '0' }}
                                                />
                                            </div>
                                            <div className="w-20 text-xs text-slate-600 text-right">{t.scans} / {t.risks}</div>
                                        </div>
                                    );
                                });
                            })()}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400">No trend data available.</p>
                    )}
                </div>
            </div>

            {/* User Activity */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">User Activity</h2>
                {users && users.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Name</th>
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Email</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Scans</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risks</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Last Scan</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((u) => (
                                    <tr key={u.user_id} className="border-b border-slate-100 hover:bg-slate-50">
                                        <td className="py-2 px-3 font-medium text-slate-900">{u.name}</td>
                                        <td className="py-2 px-3 text-slate-500">{u.email}</td>
                                        <td className="py-2 px-3 text-right text-slate-700">{u.scan_count}</td>
                                        <td className="py-2 px-3 text-right text-slate-700">{u.risks_found}</td>
                                        <td className="py-2 px-3 text-right text-slate-400">
                                            {u.last_scan ? new Date(u.last_scan).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-sm text-slate-400">No user activity data.</p>
                )}
            </div>
        </>
    );
}

// ============================================================================
// Portfolio Tab
// ============================================================================
function PortfolioTab({ days }: { days: number }) {
    const { data: portfolio, isLoading } = useQuery({
        queryKey: ['analytics-portfolio', days],
        queryFn: () => getPortfolioRisk(days),
    });
    const { data: clauses } = useQuery({
        queryKey: ['analytics-clauses', days],
        queryFn: () => getClauseAnalytics(days),
    });

    if (isLoading) return <div className="text-center py-12 text-slate-400">Loading portfolio...</div>;
    if (!portfolio) return null;

    const { summary, risk_distribution, by_contract_type, high_risk_documents } = portfolio;
    const totalRiskItems = risk_distribution.red + risk_distribution.yellow + risk_distribution.green;

    return (
        <>
            {/* Summary */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <StatCard label="Total Contracts" value={summary.total_documents} sub={`Last ${days} days`} />
                <StatCard label="Avg Risk Score" value={summary.avg_risk_score.toFixed(1)} sub="out of 10" />
                <StatCard label="Total Risks" value={summary.total_risks} />
                <StatCard label="Avg Risks/Doc" value={summary.avg_risks_per_document.toFixed(1)} />
            </div>

            {/* Risk Distribution Pie (CSS) */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Distribution</h2>
                {totalRiskItems > 0 ? (
                    <div className="flex items-center gap-6">
                        <div className="flex-1 h-8 flex rounded-full overflow-hidden">
                            <div className="bg-red-500 transition-all" style={{ width: `${(risk_distribution.red / totalRiskItems) * 100}%` }} />
                            <div className="bg-amber-400 transition-all" style={{ width: `${(risk_distribution.yellow / totalRiskItems) * 100}%` }} />
                            <div className="bg-green-400 transition-all" style={{ width: `${(risk_distribution.green / totalRiskItems) * 100}%` }} />
                        </div>
                        <div className="flex gap-4 text-sm">
                            <span className="text-red-600 font-semibold">{risk_distribution.red} Red</span>
                            <span className="text-amber-600 font-semibold">{risk_distribution.yellow} Yellow</span>
                            <span className="text-green-600 font-semibold">{risk_distribution.green} Green</span>
                        </div>
                    </div>
                ) : (
                    <p className="text-sm text-slate-400">No risk data.</p>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* By Contract Type */}
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">By Contract Type</h2>
                    {by_contract_type.length > 0 ? (
                        <div className="space-y-3">
                            {by_contract_type.map((ct) => (
                                <div key={ct.contract_type} className="flex items-center justify-between">
                                    <div>
                                        <div className="text-sm font-medium text-slate-700">{ct.contract_type}</div>
                                        <div className="text-xs text-slate-400">{ct.document_count} docs, avg risk {ct.avg_risk_score}</div>
                                    </div>
                                    <div className="text-sm font-semibold text-slate-600">{ct.total_risks} risks</div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400">No data.</p>
                    )}
                </div>

                {/* Clause Risk Analysis */}
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">Clause Risk Analysis</h2>
                    {clauses && clauses.length > 0 ? (
                        <div className="space-y-3">
                            {clauses.map((c) => (
                                <div key={c.risk_level} className="flex items-center justify-between">
                                    <div>
                                        <div className={`text-sm font-medium ${c.risk_level === 'red' ? 'text-red-600' : c.risk_level === 'yellow' ? 'text-amber-600' : 'text-green-600'}`}>
                                            {c.risk_level.toUpperCase()}
                                        </div>
                                        <div className="text-xs text-slate-400">{c.resolution_rate}% resolved</div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="w-24 bg-slate-100 rounded-full h-2 overflow-hidden">
                                            <div
                                                className="bg-green-500 h-full rounded-full"
                                                style={{ width: `${c.resolution_rate}%` }}
                                            />
                                        </div>
                                        <div className="text-sm font-semibold text-slate-600 w-10 text-right">{c.count}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400">No clause data.</p>
                    )}
                </div>
            </div>

            {/* High Risk Documents */}
            {high_risk_documents.length > 0 && (
                <div className="bg-white rounded-xl border border-red-200 p-5">
                    <h2 className="text-lg font-semibold text-red-700 mb-4">High Risk Contracts (Score ≥ 7)</h2>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Filename</th>
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Type</th>
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Counterparty</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risk Score</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {high_risk_documents.map((doc) => (
                                    <tr key={doc.document_id} className="border-b border-slate-100 hover:bg-red-50">
                                        <td className="py-2 px-3 font-medium text-slate-900">{doc.filename}</td>
                                        <td className="py-2 px-3 text-slate-500">{doc.contract_type || '—'}</td>
                                        <td className="py-2 px-3 text-slate-500">{doc.counterparty || '—'}</td>
                                        <td className="py-2 px-3 text-right font-bold text-red-600">{doc.risk_score?.toFixed(1) ?? '—'}</td>
                                        <td className="py-2 px-3 text-right text-slate-700">{doc.total_risks}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </>
    );
}

// ============================================================================
// Team Tab
// ============================================================================
function TeamTab({ days }: { days: number }) {
    const { data: team, isLoading } = useQuery({
        queryKey: ['analytics-team', days],
        queryFn: () => getTeamPerformance(days),
    });

    if (isLoading) return <div className="text-center py-12 text-slate-400">Loading team data...</div>;
    if (!team || team.length === 0) return <p className="text-sm text-slate-400 py-8 text-center">No team data available.</p>;

    const maxDocs = Math.max(...team.map(t => t.documents_reviewed), 1);

    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Team Performance</h2>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-slate-200">
                            <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Name</th>
                            <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Docs Reviewed</th>
                            <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risks Found</th>
                            <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Avg Risks/Doc</th>
                            <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Words Reviewed</th>
                            <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500 w-40">Activity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {team.map((m) => (
                            <tr key={m.user_id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="py-2 px-3">
                                    <div className="font-medium text-slate-900">{m.name}</div>
                                    <div className="text-xs text-slate-400">{m.email}</div>
                                </td>
                                <td className="py-2 px-3 text-right text-slate-700">{m.documents_reviewed}</td>
                                <td className="py-2 px-3 text-right text-slate-700">{m.total_risks_found}</td>
                                <td className="py-2 px-3 text-right text-slate-700">{m.avg_risks_per_doc}</td>
                                <td className="py-2 px-3 text-right text-slate-400">{m.total_words_reviewed.toLocaleString()}</td>
                                <td className="py-2 px-3">
                                    <div className="bg-slate-100 rounded-full h-2 overflow-hidden">
                                        <div
                                            className="bg-red-500 h-full rounded-full"
                                            style={{ width: `${(m.documents_reviewed / maxDocs) * 100}%` }}
                                        />
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ============================================================================
// Reports Tab
// ============================================================================
function ReportsTab({ days }: { days: number }) {
    const queryClient = useQueryClient();
    const [generating, setGenerating] = useState<string | null>(null);

    const { data: reports, isLoading } = useQuery({
        queryKey: ['analytics-reports'],
        queryFn: () => listAnalyticsReports(undefined, 20),
    });

    const generateMutation = useMutation({
        mutationFn: (type: string) => generateAnalyticsReport(type, days),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['analytics-reports'] });
            setGenerating(null);
        },
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
            {/* Generate Reports */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Generate Report</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {reportTypes.map((rt) => (
                        <button
                            key={rt.id}
                            onClick={() => { setGenerating(rt.id); generateMutation.mutate(rt.id); }}
                            disabled={generating !== null}
                            className="text-left p-4 border border-slate-200 rounded-lg hover:border-red-300 hover:bg-red-50 transition-colors disabled:opacity-50"
                        >
                            <div className="font-medium text-slate-900">{rt.label}</div>
                            <div className="text-xs text-slate-400 mt-1">{rt.desc}</div>
                            {generating === rt.id && <div className="text-xs text-red-600 mt-2">Generating...</div>}
                        </button>
                    ))}
                </div>
            </div>

            {/* Report History */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Report History</h2>
                {isLoading ? (
                    <div className="text-slate-400 text-sm">Loading...</div>
                ) : reports && reports.length > 0 ? (
                    <div className="space-y-3">
                        {reports.map((r) => (
                            <div key={r.id} className="flex items-center justify-between py-2 border-b border-slate-100">
                                <div>
                                    <div className="text-sm font-medium text-slate-900">{r.title}</div>
                                    <div className="text-xs text-slate-400">
                                        {r.report_type.replace('_', ' ')} — {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                    </div>
                                </div>
                                <span className="px-2 py-1 text-xs rounded bg-slate-100 text-slate-600">{r.format}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-sm text-slate-400">No reports generated yet.</p>
                )}
            </div>
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
        const url = getAnalyticsExportUrl(days);
        try {
            const res = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Accept': 'text/csv',
                    'X-CSRF-Token': document.cookie.match(/csrf_token=([^;]+)/)?.[1] || '',
                },
            });
            if (!res.ok) throw new Error(`Export failed: ${res.status}`);
            const blob = await res.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `contrared_analytics_${days}d.csv`;
            link.click();
            URL.revokeObjectURL(link.href);
        } catch {
            setError('Export failed. Please try again.');
        }
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
                        <p className="text-sm text-slate-500 mt-1">Firm-wide contract review metrics and ROI</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <select
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        >
                            {PERIOD_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                        <button onClick={handleExport} className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Error banner */}
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg mb-4 text-sm flex items-center justify-between">
                        <span>{error}</span>
                        <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-600 font-bold">&times;</button>
                    </div>
                )}

                {/* Tabs */}
                <div className="flex gap-1 mb-6 bg-slate-200 rounded-lg p-1 w-fit">
                    {TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                                activeTab === tab.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                {activeTab === 'overview' && <OverviewTab days={days} />}
                {activeTab === 'portfolio' && <PortfolioTab days={days} />}
                {activeTab === 'team' && <TeamTab days={days} />}
                {activeTab === 'reports' && <ReportsTab days={days} />}
            </main>
        </div>
    );
}
