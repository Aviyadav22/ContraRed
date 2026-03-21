import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { getExecutiveDashboard } from '@/api/client';
import AppHeader from '@/components/AppHeader';

function formatCurrency(value: number, currency: string = 'INR'): string {
    if (currency === 'INR') {
        if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
        if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
        if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
        return `₹${value.toFixed(0)}`;
    }
    return `$${value.toLocaleString()}`;
}

function BigMetric({ label, value, sub, color = 'text-slate-900' }: { label: string; value: string | number; sub?: string; color?: string }) {
    return (
        <article className="bg-white rounded-2xl border border-slate-200 p-8 text-center">
            <div className="text-sm font-medium text-slate-500 mb-2">{label}</div>
            <div className={`text-5xl font-bold ${color}`}>{value}</div>
            {sub && <div className="text-sm text-slate-400 mt-2">{sub}</div>}
        </article>
    );
}

export default function Executive() {
    const [days, setDays] = useState(30);

    const { data, isLoading, error } = useQuery({
        queryKey: ['executive-dashboard', days],
        queryFn: () => getExecutiveDashboard(days),
    });

    const roi = data?.roi;
    const trends = data?.trends;

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
                {/* Header */}
                <div className="flex justify-between items-center mb-10">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Executive Dashboard</h1>
                        <p className="text-sm text-slate-500 mt-1">Board-ready metrics at a glance</p>
                    </div>
                    <label htmlFor="exec-time-range" className="sr-only">Time range</label>
                    <select
                        id="exec-time-range"
                        value={days}
                        onChange={(e) => setDays(Number(e.target.value))}
                        className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    >
                        <option value={7}>7 days</option>
                        <option value={30}>30 days</option>
                        <option value={90}>90 days</option>
                        <option value={365}>1 year</option>
                    </select>
                </div>

                {error && <div className="text-red-600 p-4 mb-6">Failed to load dashboard data.</div>}
                {isLoading && <div className="text-center py-20 text-slate-400 text-lg">Loading executive dashboard...</div>}

                {data && (
                    <>
                        {/* 6 Key Metrics — Large Font */}
                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
                            <BigMetric label="Contracts Reviewed" value={data.documents_analyzed} sub={`Last ${days} days`} />
                            <BigMetric label="Risks Identified" value={data.total_risks} sub={`${data.red_risks} critical`} />
                            <BigMetric label="Critical Risks" value={data.red_risks} color="text-red-600" sub="Deal-breakers flagged" />
                            <BigMetric
                                label="Hours Saved"
                                value={roi ? roi.time_savings.hours_saved.toFixed(0) : '—'}
                                sub={roi ? `vs ${roi.time_savings.estimated_manual_hours.toFixed(0)}h manual` : ''}
                            />
                            <BigMetric
                                label="ROI Value"
                                value={roi ? formatCurrency(roi.total_roi_value, roi.time_savings.currency) : '—'}
                                color="text-red-700"
                                sub="Time savings + risk protection"
                            />
                            <BigMetric
                                label="Return Multiple"
                                value={roi?.roi_multiplier || '—'}
                                color="text-green-700"
                                sub="vs subscription cost"
                            />
                        </div>

                        {/* ROI Detail */}
                        {roi && (
                            <div className="bg-white rounded-2xl border border-slate-200 p-8 mb-10">
                                <h2 className="text-xl font-semibold text-slate-900 mb-6">Return on Investment</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div>
                                        <div className="text-sm font-medium text-slate-500 mb-3">Time Savings</div>
                                        <div className="space-y-2">
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Estimated manual review</span>
                                                <span className="font-semibold">{roi.time_savings.estimated_manual_hours.toFixed(1)} hours</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">AI processing time</span>
                                                <span className="font-semibold">{roi.time_savings.actual_ai_hours.toFixed(2)} hours</span>
                                            </div>
                                            <div className="flex justify-between border-t pt-2">
                                                <span className="text-slate-900 font-medium">Net time saved</span>
                                                <span className="font-bold text-green-700">{roi.time_savings.hours_saved.toFixed(1)} hours</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Monetary value</span>
                                                <span className="font-semibold">{formatCurrency(roi.time_savings.monetary_value, roi.time_savings.currency)}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-slate-500 mb-3">Risk Protection Value</div>
                                        <div className="space-y-2">
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Red risks ({roi.red_risks})</span>
                                                <span className="font-semibold text-red-600">{formatCurrency(roi.risk_value.red_risk_value, roi.risk_value.currency)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Yellow risks ({roi.yellow_risks})</span>
                                                <span className="font-semibold text-amber-600">{formatCurrency(roi.risk_value.yellow_risk_value, roi.risk_value.currency)}</span>
                                            </div>
                                            <div className="flex justify-between border-t pt-2">
                                                <span className="text-slate-900 font-medium">Total protected</span>
                                                <span className="font-bold">{formatCurrency(roi.risk_value.total_risk_value_protected, roi.risk_value.currency)}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                {roi.methodology?.note && (
                                    <div className="mt-6 text-xs text-slate-400 border-t pt-4">
                                        Methodology: {roi.methodology.note}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Weekly Trend */}
                        {trends && trends.length > 0 && (
                            <div className="bg-white rounded-2xl border border-slate-200 p-8">
                                <h2 className="text-xl font-semibold text-slate-900 mb-6">Weekly Activity</h2>
                                <div className="space-y-3">
                                    {(() => {
                                        const maxScans = Math.max(...trends.map(t => t.scans), 1);
                                        return trends.map((t) => {
                                            const label = new Date(t.period).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                            return (
                                                <div key={t.period} className="flex items-center gap-4">
                                                    <div className="w-20 text-sm text-slate-500">{label}</div>
                                                    <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden">
                                                        <div
                                                            className="bg-red-500 h-full rounded-full transition-all"
                                                            style={{ width: `${(t.scans / maxScans) * 100}%`, minWidth: t.scans > 0 ? '8px' : '0' }}
                                                        />
                                                    </div>
                                                    <div className="w-32 text-sm text-slate-600 text-right">
                                                        {t.scans} scans / {t.risks} risks
                                                    </div>
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </main>
        </div>
    );
}
