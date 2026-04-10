import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { getExecutiveDashboard } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Card, SelectInput } from '@/components/ui';

function formatCurrency(value: number, currency: string = 'INR'): string {
    if (currency === 'INR') {
        if (value >= 10000000) return `\u20b9${(value / 10000000).toFixed(1)}Cr`;
        if (value >= 100000) return `\u20b9${(value / 100000).toFixed(1)}L`;
        if (value >= 1000) return `\u20b9${(value / 1000).toFixed(1)}K`;
        return `\u20b9${value.toFixed(0)}`;
    }
    return `$${value.toLocaleString()}`;
}

function BigMetric({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
    return (
        <Card padding="spacious" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 48, fontWeight: 700, color: color || 'var(--text-primary)' }}>{value}</div>
            {sub && <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 8 }}>{sub}</div>}
        </Card>
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
        <AppLayout>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
                <div>
                    <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Executive Dashboard</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>Board-ready metrics at a glance</p>
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

            {error && <div style={{ color: 'var(--risk-critical)', padding: 16, marginBottom: 24 }}>Failed to load dashboard data.</div>}
            {isLoading && <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)', fontSize: 18 }}>Loading executive dashboard...</div>}

            {data && (
                <>
                    {/* 6 Key Metrics */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24, marginBottom: 40 }}>
                        <BigMetric label="Contracts Reviewed" value={data.documents_analyzed} sub={`Last ${days} days`} />
                        <BigMetric label="Risks Identified" value={data.total_risks} sub={`${data.red_risks} critical`} />
                        <BigMetric label="Critical Risks" value={data.red_risks} color="var(--risk-critical)" sub="Deal-breakers flagged" />
                        <BigMetric
                            label="Hours Saved"
                            value={roi ? roi.time_savings.hours_saved.toFixed(0) : '\u2014'}
                            sub={roi ? `vs ${roi.time_savings.estimated_manual_hours.toFixed(0)}h manual` : ''}
                        />
                        <BigMetric
                            label="ROI Value"
                            value={roi ? formatCurrency(roi.total_roi_value, roi.time_savings.currency) : '\u2014'}
                            color="var(--accent)"
                            sub="Time savings + risk protection"
                        />
                        <BigMetric
                            label="Return Multiple"
                            value={roi?.roi_multiplier || '\u2014'}
                            color="var(--risk-low)"
                            sub="vs subscription cost"
                        />
                    </div>

                    {/* ROI Detail */}
                    {roi && (
                        <Card padding="spacious" style={{ marginBottom: 40 }}>
                            <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 24 }}>Return on Investment</h2>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 12 }}>Time Savings</div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Estimated manual review</span>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{roi.time_savings.estimated_manual_hours.toFixed(1)} hours</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>AI processing time</span>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{roi.time_savings.actual_ai_hours.toFixed(2)} hours</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                                            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Net time saved</span>
                                            <span style={{ fontWeight: 700, color: 'var(--risk-low)' }}>{roi.time_savings.hours_saved.toFixed(1)} hours</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Monetary value</span>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{formatCurrency(roi.time_savings.monetary_value, roi.time_savings.currency)}</span>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 12 }}>Risk Protection Value</div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Red risks ({roi.red_risks})</span>
                                            <span style={{ fontWeight: 600, color: 'var(--risk-critical)' }}>{formatCurrency(roi.risk_value.red_risk_value, roi.risk_value.currency)}</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Yellow risks ({roi.yellow_risks})</span>
                                            <span style={{ fontWeight: 600, color: 'var(--risk-high)' }}>{formatCurrency(roi.risk_value.yellow_risk_value, roi.risk_value.currency)}</span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                                            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Total protected</span>
                                            <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{formatCurrency(roi.risk_value.total_risk_value_protected, roi.risk_value.currency)}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {roi.methodology?.note && (
                                <div style={{ marginTop: 24, fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: 16 }}>
                                    Methodology: {roi.methodology.note}
                                </div>
                            )}
                        </Card>
                    )}

                    {/* Weekly Trend */}
                    {trends && trends.length > 0 && (
                        <Card padding="spacious">
                            <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 24 }}>Weekly Activity</h2>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                {(() => {
                                    const maxScans = Math.max(...trends.map(t => t.scans), 1);
                                    return trends.map((t) => {
                                        const label = new Date(t.period).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                                        return (
                                            <div key={t.period} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                                <div style={{ width: 80, fontSize: 14, color: 'var(--text-muted)' }}>{label}</div>
                                                <div style={{ flex: 1, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', height: 24, overflow: 'hidden' }}>
                                                    <div
                                                        style={{
                                                            backgroundColor: 'var(--accent)', height: '100%',
                                                            borderRadius: 'var(--radius-sm)', transition: 'width 0.3s ease',
                                                            width: `${(t.scans / maxScans) * 100}%`,
                                                            minWidth: t.scans > 0 ? 8 : 0,
                                                        }}
                                                    />
                                                </div>
                                                <div style={{ width: 128, fontSize: 14, color: 'var(--text-secondary)', textAlign: 'right' }}>
                                                    {t.scans} scans / {t.risks} risks
                                                </div>
                                            </div>
                                        );
                                    });
                                })()}
                            </div>
                        </Card>
                    )}
                </>
            )}
        </AppLayout>
    );
}
