import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
    getAnalyticsOverview,
    getAnalyticsRisks,
    getAnalyticsUsers,
    getAnalyticsTrends,
    getAnalyticsExportUrl,
    getStoredTokens,
    type AnalyticsOverview,
    type RiskBreakdownItem,
    type UserActivityItem,
    type TrendDataPoint,
} from '@/api/client';
import AppHeader from '@/components/AppHeader';

const PERIOD_OPTIONS = [
    { value: 7, label: '7 days' },
    { value: 30, label: '30 days' },
    { value: 90, label: '90 days' },
];

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
    return (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="text-sm font-medium text-slate-500">{label}</div>
            <div className="text-3xl font-bold text-slate-900 mt-1">{value}</div>
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
                    <div
                        className="bg-red-500 h-full rounded-l"
                        style={{ width: `${(item.red / max) * 100}%`, minWidth: '4px' }}
                        title={`${item.red} RED`}
                    />
                )}
                {item.yellow > 0 && (
                    <div
                        className="bg-amber-400 h-full"
                        style={{ width: `${(item.yellow / max) * 100}%`, minWidth: '4px' }}
                        title={`${item.yellow} YELLOW`}
                    />
                )}
                {item.green > 0 && (
                    <div
                        className="bg-green-400 h-full rounded-r"
                        style={{ width: `${(item.green / max) * 100}%`, minWidth: '4px' }}
                        title={`${item.green} GREEN`}
                    />
                )}
            </div>
            <div className="w-10 text-right text-sm font-semibold text-slate-600">{item.total}</div>
        </div>
    );
}

export default function Analytics() {
    const [days, setDays] = useState(30);

    const { data: overview, isLoading: loadingOverview } = useQuery({
        queryKey: ['analytics-overview', days],
        queryFn: () => getAnalyticsOverview(days),
    });

    const { data: risks } = useQuery({
        queryKey: ['analytics-risks', days],
        queryFn: () => getAnalyticsRisks(days),
    });

    const { data: users } = useQuery({
        queryKey: ['analytics-users', days],
        queryFn: () => getAnalyticsUsers(days),
    });

    const { data: trends } = useQuery({
        queryKey: ['analytics-trends', days],
        queryFn: () => getAnalyticsTrends('weekly', Math.ceil(days / 7)),
    });

    const handleExport = async () => {
        const url = getAnalyticsExportUrl(days);
        const tokens = getStoredTokens();
        try {
            const res = await fetch(url, {
                headers: { Authorization: `Bearer ${tokens?.access_token}` },
            });
            if (!res.ok) throw new Error(`Export failed: ${res.status}`);
            const blob = await res.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `contrared_analytics_${days}d.csv`;
            link.click();
            URL.revokeObjectURL(link.href);
        } catch {
            alert('Export failed');
        }
    };

    // Estimate hours saved (rough: 2 hours saved per scan)
    const hoursSaved = (overview?.documents_analyzed || 0) * 2;

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            Firm-wide contract review metrics and ROI
                        </p>
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
                        <button
                            onClick={handleExport}
                            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                        >
                            Export CSV
                        </button>
                    </div>
                </div>

                {/* Loading */}
                {loadingOverview && (
                    <div className="text-center py-12 text-slate-400">Loading analytics...</div>
                )}

                {overview && (
                    <>
                        {/* Summary Cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
                            <StatCard label="Documents Analyzed" value={overview.documents_analyzed} sub={`Last ${days} days`} />
                            <StatCard label="Total Risks Found" value={overview.total_risks} sub={`${overview.red_risks} red, ${overview.yellow_risks} yellow`} />
                            <StatCard label="Red Risks" value={overview.red_risks} sub="Deal-breakers" />
                            <StatCard label="Active Users" value={overview.active_users} />
                            <StatCard label="Est. Hours Saved" value={hoursSaved} sub="~2h per review" />
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                            {/* Risk Breakdown */}
                            <div className="bg-white rounded-xl border border-slate-200 p-5">
                                <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Breakdown by Clause Type</h2>
                                {risks && risks.length > 0 ? (
                                    <div>
                                        <div className="flex items-center gap-4 mb-3 text-xs text-slate-400">
                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500 rounded-sm inline-block" /> Red</span>
                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-400 rounded-sm inline-block" /> Yellow</span>
                                            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-400 rounded-sm inline-block" /> Green</span>
                                        </div>
                                        {risks.map((r) => (
                                            <RiskBar key={r.risk_level} item={r} />
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400">No risk data available for this period.</p>
                                )}
                            </div>

                            {/* Trend Chart (simple text-based for now) */}
                            <div className="bg-white rounded-xl border border-slate-200 p-5">
                                <h2 className="text-lg font-semibold text-slate-900 mb-4">Usage Trends (Weekly)</h2>
                                {trends && trends.length > 0 ? (
                                    <div className="space-y-2">
                                        {trends.map((t) => {
                                            const weekLabel = new Date(t.period).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                            const maxScans = Math.max(...trends.map(x => x.scans), 1);
                                            return (
                                                <div key={t.period} className="flex items-center gap-3">
                                                    <div className="w-16 text-xs text-slate-500">{weekLabel}</div>
                                                    <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden">
                                                        <div
                                                            className="bg-red-500 h-full rounded-full transition-all"
                                                            style={{ width: `${(t.scans / maxScans) * 100}%`, minWidth: t.scans > 0 ? '8px' : '0' }}
                                                        />
                                                    </div>
                                                    <div className="w-20 text-xs text-slate-600 text-right">
                                                        {t.scans} scans / {t.risks} risks
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400">No trend data available for this period.</p>
                                )}
                            </div>
                        </div>

                        {/* User Activity Table */}
                        <div className="bg-white rounded-xl border border-slate-200 p-5">
                            <h2 className="text-lg font-semibold text-slate-900 mb-4">User Activity</h2>
                            {users && users.length > 0 ? (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-slate-200">
                                                <th className="text-left py-2 px-3 font-medium text-slate-500">Name</th>
                                                <th className="text-left py-2 px-3 font-medium text-slate-500">Email</th>
                                                <th className="text-right py-2 px-3 font-medium text-slate-500">Scans</th>
                                                <th className="text-right py-2 px-3 font-medium text-slate-500">Risks Found</th>
                                                <th className="text-right py-2 px-3 font-medium text-slate-500">Last Scan</th>
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
                                                        {u.last_scan
                                                            ? new Date(u.last_scan).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                                                            : 'Never'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="text-sm text-slate-400">No user activity data available.</p>
                            )}
                        </div>
                    </>
                )}
            </main>
        </div>
    );
}
