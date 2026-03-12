import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
    generateAnalyticsReport,
    listAnalyticsReports,
    getAnalyticsReport,
    type GeneratedReport,
} from '@/api/client';
import AppHeader from '@/components/AppHeader';

const REPORT_TYPES = [
    { id: 'executive_summary', label: 'Executive Summary', desc: 'Board-ready 6 key metrics on one page', icon: 'E' },
    { id: 'gc_operations', label: 'GC Operations', desc: 'General Counsel operational overview with portfolio risk', icon: 'G' },
    { id: 'team_review', label: 'Team Review', desc: 'Per-reviewer performance breakdown and activity', icon: 'T' },
    { id: 'risk_audit', label: 'Risk Audit', desc: 'Detailed risk analysis across contract portfolio', icon: 'R' },
];

const SEVERITY_COLORS: Record<string, string> = {
    red: 'bg-red-50 text-red-700',
    RED: 'bg-red-50 text-red-700',
    critical: 'bg-red-50 text-red-700',
    high: 'bg-red-50 text-red-700',
    yellow: 'bg-amber-50 text-amber-700',
    YELLOW: 'bg-amber-50 text-amber-700',
    medium: 'bg-amber-50 text-amber-700',
    warning: 'bg-amber-50 text-amber-700',
    green: 'bg-green-50 text-green-700',
    GREEN: 'bg-green-50 text-green-700',
    low: 'bg-green-50 text-green-700',
    safe: 'bg-green-50 text-green-700',
};

function MetricCard({ label, value }: { label: string; value: string | number }) {
    return (
        <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{value}</div>
        </div>
    );
}

function ReportViewer({ report }: { report: GeneratedReport }) {
    if (!report.data) return <p className="text-sm text-slate-400">No data available.</p>;

    const data = report.data as Record<string, unknown>;

    // Extract common report fields
    const title = (data.title as string) || report.title;
    const reportType = (data.report_type as string) || report.report_type;
    const generatedAt = (data.generated_at as string) || report.created_at;
    const periodDays = data.period_days as number | undefined;

    // Try to extract metrics - common patterns across report types
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
    const metricEntries = Object.entries(metricsSource).filter(
        ([, v]) => typeof v === 'number' || typeof v === 'string'
    );
    const riskItems = risks || findings || [];
    const teamItems = team || teamPerformance || [];

    return (
        <div className="space-y-6">
            {/* Report Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h3 className="text-xl font-bold text-slate-900">{title}</h3>
                    <div className="flex items-center gap-3 mt-2">
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-md bg-red-50 text-red-700">
                            {reportType.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <span className="text-xs text-slate-400">
                            {new Date(generatedAt).toLocaleDateString('en-IN', {
                                day: 'numeric', month: 'long', year: 'numeric',
                            })}
                        </span>
                        {periodDays && (
                            <span className="text-xs text-slate-400">
                                ({periodDays} day period)
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Key Metrics Cards */}
            {metricEntries.length > 0 && (
                <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Key Metrics</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {metricEntries.map(([key, value]) => (
                            <MetricCard
                                key={key}
                                label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                value={typeof value === 'number' ? value.toLocaleString() : String(value)}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Risk Distribution */}
            {riskDistribution && (
                <div className="bg-white rounded-lg border border-slate-200 p-5">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Risk Distribution</h4>
                    <div className="flex items-center gap-4">
                        {Object.entries(riskDistribution).map(([level, count]) => (
                            <div key={level} className="flex items-center gap-2">
                                <span className={`px-2 py-0.5 text-xs font-semibold rounded ${SEVERITY_COLORS[level] || 'bg-slate-100 text-slate-600'}`}>
                                    {level.toUpperCase()}
                                </span>
                                <span className="text-sm font-bold text-slate-900">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Risk Findings Table */}
            {riskItems.length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 p-5">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Risk Findings</h4>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Item</th>
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Severity</th>
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Details</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {riskItems.map((item, idx) => {
                                    const name = (item.risk_level || item.clause_type || item.name || item.title || `Finding ${idx + 1}`) as string;
                                    const severity = (item.severity || item.risk_level || item.level || 'unknown') as string;
                                    const details = (item.description || item.details || item.text || '') as string;
                                    const count = (item.count || item.total || '') as string | number;
                                    return (
                                        <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                                            <td className="py-2 px-3 font-medium text-slate-900">{String(name)}</td>
                                            <td className="py-2 px-3">
                                                <span className={`px-2 py-0.5 text-xs font-semibold rounded ${SEVERITY_COLORS[String(severity).toLowerCase()] || 'bg-slate-100 text-slate-600'}`}>
                                                    {String(severity).toUpperCase()}
                                                </span>
                                            </td>
                                            <td className="py-2 px-3 text-slate-500 max-w-xs truncate">{String(details)}</td>
                                            <td className="py-2 px-3 text-right text-slate-700 font-medium">{count !== '' ? String(count) : '--'}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Team Performance Table */}
            {teamItems.length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 p-5">
                    <h4 className="text-sm font-semibold text-slate-700 mb-3">Team Performance</h4>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Name</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Docs Reviewed</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risks Found</th>
                                </tr>
                            </thead>
                            <tbody>
                                {teamItems.map((member, idx) => (
                                    <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                                        <td className="py-2 px-3 font-medium text-slate-900">
                                            {String(member.name || member.email || `User ${idx + 1}`)}
                                        </td>
                                        <td className="py-2 px-3 text-right text-slate-700">
                                            {String(member.documents_reviewed || member.scan_count || '--')}
                                        </td>
                                        <td className="py-2 px-3 text-right text-slate-700">
                                            {String(member.total_risks_found || member.risks_found || '--')}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* High Risk Documents */}
            {highRiskDocuments && highRiskDocuments.length > 0 && (
                <div className="bg-white rounded-lg border border-red-200 p-5">
                    <h4 className="text-sm font-semibold text-red-700 mb-3">High Risk Documents</h4>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200">
                                    <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Filename</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risk Score</th>
                                    <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Risks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {highRiskDocuments.map((doc, idx) => (
                                    <tr key={idx} className="border-b border-slate-100 hover:bg-red-50">
                                        <td className="py-2 px-3 font-medium text-slate-900">{String(doc.filename)}</td>
                                        <td className="py-2 px-3 text-right font-bold text-red-600">
                                            {doc.risk_score != null ? Number(doc.risk_score).toFixed(1) : '--'}
                                        </td>
                                        <td className="py-2 px-3 text-right text-slate-700">{String(doc.total_risks || '--')}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Fallback: show remaining data as formatted sections */}
            {metricEntries.length === 0 && riskItems.length === 0 && teamItems.length === 0 && (
                <div className="space-y-4">
                    {Object.entries(data).filter(([k]) => !['title', 'report_type', 'generated_at', 'period_days'].includes(k)).map(([key, value]) => (
                        <div key={key} className="bg-white rounded-lg border border-slate-200 p-5">
                            <h4 className="text-sm font-semibold text-slate-700 mb-2">
                                {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                            </h4>
                            {typeof value === 'object' && value !== null ? (
                                <div className="text-sm text-slate-600 space-y-1">
                                    {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                                        <div key={k} className="flex justify-between py-1 border-b border-slate-50">
                                            <span className="text-slate-500">{k.replace(/_/g, ' ')}</span>
                                            <span className="font-medium">{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-slate-600">{String(value)}</p>
                            )}
                        </div>
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
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
                        <p className="text-sm text-slate-500 mt-1">Generate and view analytics reports</p>
                    </div>
                    <select
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

                {/* Error display */}
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg mb-4 text-sm">
                        {error}
                    </div>
                )}

                {/* Generate Reports */}
                <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
                    <h2 className="text-lg font-semibold text-slate-900 mb-4">Generate New Report</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {REPORT_TYPES.map((rt) => (
                            <button
                                key={rt.id}
                                onClick={() => { setGenerating(rt.id); generateMutation.mutate(rt.id); }}
                                disabled={generating !== null}
                                className="text-left p-5 border border-slate-200 rounded-xl hover:border-red-300 hover:bg-red-50 transition-colors disabled:opacity-50"
                            >
                                <div className="w-10 h-10 bg-red-100 text-red-700 font-bold rounded-lg flex items-center justify-center mb-3">
                                    {rt.icon}
                                </div>
                                <div className="font-medium text-slate-900">{rt.label}</div>
                                <div className="text-xs text-slate-400 mt-1">{rt.desc}</div>
                                {generating === rt.id && (
                                    <div className="text-xs text-red-600 mt-2 font-medium">Generating...</div>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Report List */}
                    <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5">
                        <h2 className="text-lg font-semibold text-slate-900 mb-4">Report History</h2>
                        {isLoading ? (
                            <div className="text-slate-400 text-sm py-4">Loading...</div>
                        ) : reports && reports.length > 0 ? (
                            <div className="space-y-2 max-h-[600px] overflow-y-auto">
                                {reports.map((r) => (
                                    <button
                                        key={r.id}
                                        onClick={() => handleViewReport(r.id)}
                                        className={`w-full text-left p-3 rounded-lg border transition-colors ${
                                            selectedReport?.id === r.id
                                                ? 'border-red-300 bg-red-50'
                                                : 'border-slate-100 hover:border-slate-300 hover:bg-slate-50'
                                        }`}
                                    >
                                        <div className="text-sm font-medium text-slate-900 truncate">{r.title}</div>
                                        <div className="text-xs text-slate-400 mt-1">
                                            {r.report_type.replace(/_/g, ' ')} — {new Date(r.created_at).toLocaleDateString('en-IN', {
                                                day: 'numeric', month: 'short', year: 'numeric',
                                            })}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-400 py-4">No reports generated yet. Use the cards above to create one.</p>
                        )}
                    </div>

                    {/* Report Viewer */}
                    <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-lg font-semibold text-slate-900">
                                {selectedReport ? selectedReport.title : 'Select a Report'}
                            </h2>
                            {selectedReport?.data && (
                                <button
                                    onClick={handleDownloadJSON}
                                    className="px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                                >
                                    Download JSON
                                </button>
                            )}
                        </div>
                        {loadingReport ? (
                            <div className="text-slate-400 text-sm py-8 text-center">Loading report...</div>
                        ) : selectedReport ? (
                            <ReportViewer report={selectedReport} />
                        ) : (
                            <div className="text-slate-400 text-sm py-8 text-center">
                                Select a report from the list or generate a new one.
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
