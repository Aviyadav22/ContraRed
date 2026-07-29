import { type CSSProperties, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import { Badge, Button } from '@/components/ui';
import {
    Shield, AlertTriangle, CheckCircle, Clock, FileText,
    Search, ClipboardList, Wrench, Bell, Scale,
    ChevronDown, ChevronRight, Download, ArrowRight,
} from 'lucide-react';
import {
    dpdpGetDashboard, dpdpScanContract, dpdpGetTemplates, dpdpRemediate,
    dpdpGenerateReport, dpdpGetReportHistory, dpdpSearchRegulation,
    dpdpGetAssessmentQuestions, dpdpRunAssessment,
    type DPDPDashboard, type DPDPScanResult, type DPDPContractFinding,
    type DPDPRemediationOutput, type DPDPDeadline, type DPDPAlert,
    type DPDPAssessmentQuestion, type DPDPGapAssessment, type DPDPGeneratedReport,
} from '@/api/client';

type Tab = 'overview' | 'scan' | 'assess' | 'remediate' | 'report';

const tabItems: { id: Tab; label: string; icon: typeof Shield }[] = [
    { id: 'overview', label: 'Command Center', icon: Shield },
    { id: 'scan', label: 'Contract Scanner', icon: Search },
    { id: 'assess', label: 'Gap Assessment', icon: ClipboardList },
    { id: 'remediate', label: 'Generate Documents', icon: Wrench },
    { id: 'report', label: 'Reports', icon: FileText },
];

export default function DPDPCommandCenter() {
    const [activeTab, setActiveTab] = useState<Tab>('overview');

    return (
        <AppLayout>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <Shield size={24} style={{ color: 'var(--accent)' }} />
                <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                    DPDP Compliance Center
                </h1>
                <Badge variant="critical">NEW</Badge>
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 24 }}>
                AI-powered compliance engine for India's Digital Personal Data Protection Act 2023.
                Scan contracts, assess gaps, generate drafts for legal review, and track deadlines.
            </p>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
                {tabItems.map(tab => {
                    const Icon = tab.icon;
                    const active = activeTab === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 8,
                                padding: '10px 16px', border: 'none', cursor: 'pointer',
                                backgroundColor: 'transparent',
                                color: active ? 'var(--accent)' : 'var(--text-muted)',
                                borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                                fontWeight: active ? 600 : 400, fontSize: 13,
                                fontFamily: 'var(--font-sans)', transition: 'all var(--transition-fast)',
                                marginBottom: -1,
                            }}
                        >
                            <Icon size={16} />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {activeTab === 'overview' && <OverviewTab />}
            {activeTab === 'scan' && <ScanTab />}
            {activeTab === 'assess' && <AssessTab />}
            {activeTab === 'remediate' && <RemediateTab />}
            {activeTab === 'report' && <ReportTab />}
        </AppLayout>
    );
}

/* =========================================================================
   OVERVIEW TAB — Dashboard + Deadlines + Alerts
   ========================================================================= */

function OverviewTab() {
    const { data: dashboard, isLoading } = useQuery<DPDPDashboard>({
        queryKey: ['dpdp-dashboard'],
        queryFn: dpdpGetDashboard,
        staleTime: 60000,
    });

    if (isLoading) return <LoadingSpinner />;

    const deadlines = dashboard?.upcoming_deadlines || [];
    const alerts = dashboard?.recent_alerts || [];

    return (
        <div>
            {/* Stats Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
                <StatCard
                    icon={<Shield size={18} />}
                    label="Compliance Score"
                    value={`${dashboard?.overall_score || 0}%`}
                    color={scoreColor(dashboard?.overall_score || 0)}
                    sub={dashboard?.status?.replace(/_/g, ' ') || 'Not assessed'}
                />
                <StatCard
                    icon={<FileText size={18} />}
                    label="Contracts Scanned"
                    value={String(dashboard?.contracts_scanned || 0)}
                    color="var(--text-primary)"
                    sub="Total analyzed"
                />
                <StatCard
                    icon={<ClipboardList size={18} />}
                    label="Rights Requests"
                    value={String(dashboard?.pending_rights_requests || 0)}
                    color="var(--accent)"
                    sub="Tracked to service target"
                />
                <StatCard
                    icon={<AlertTriangle size={18} />}
                    label="Grievances"
                    value={String(dashboard?.pending_grievances || 0)}
                    color={(dashboard?.pending_grievances || 0) > 0 ? 'var(--risk-critical)' : 'var(--text-primary)'}
                    sub="Open complaints"
                />
            </div>

            {/* Deadlines */}
            <SectionHeader icon={<Clock size={18} />} title="DPDP Deadlines" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 32 }}>
                {deadlines.map((d, i) => (
                    <DeadlineCard key={i} deadline={d} />
                ))}
                {deadlines.length === 0 && <EmptyState text="No deadlines loaded" />}
            </div>

            {/* Alerts */}
            <SectionHeader icon={<Bell size={18} />} title="Compliance Alerts" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 32 }}>
                {alerts.map((a, i) => (
                    <AlertCard key={i} alert={a} />
                ))}
                {alerts.length === 0 && <EmptyState text="No alerts" />}
            </div>

            {/* Quick Actions */}
            <SectionHeader icon={<ArrowRight size={18} />} title="Quick Actions" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                <QuickAction
                    icon={<Search size={20} />}
                    title="Scan a Contract"
                    description="Check any contract for DPDP compliance gaps against 18 rules"
                    color="var(--accent)"
                />
                <QuickAction
                    icon={<Wrench size={20} />}
                    title="Generate DPA"
                    description="Create a DPDP-oriented agreement draft for legal review"
                    color="var(--info)"
                />
                <QuickAction
                    icon={<Scale size={20} />}
                    title="Privacy Notice"
                    description="Generate a Section 5 / Rule 3 notice draft for legal review"
                    color="var(--green, #22C55E)"
                />
            </div>
        </div>
    );
}

/* =========================================================================
   SCAN TAB — Contract Scanner
   ========================================================================= */

function ScanTab() {
    const [text, setText] = useState('');
    const [name, setName] = useState('');
    const [result, setResult] = useState<DPDPScanResult | null>(null);
    const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

    const scanMutation = useMutation({
        mutationFn: () => dpdpScanContract(text, name || 'Untitled Contract'),
        onSuccess: (data) => setResult(data),
    });

    return (
        <div>
            {!result ? (
                <>
                    <div style={{ marginBottom: 16 }}>
                        <label style={labelStyle}>Contract Name</label>
                        <input
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="e.g., Vendor DPA - Acme Corp"
                            style={inputStyle}
                        />
                    </div>
                    <div style={{ marginBottom: 16 }}>
                        <label style={labelStyle}>Contract Text</label>
                        <textarea
                            value={text}
                            onChange={e => setText(e.target.value)}
                            placeholder="Paste your contract text here. The AI will scan it against all 18 DPDP Act rules..."
                            rows={12}
                            style={{ ...inputStyle, resize: 'vertical', fontFamily: 'var(--font-mono)', fontSize: 12 }}
                        />
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                            {text.length > 0 ? `${text.split(/\s+/).length} words` : 'Minimum 50 characters required'}
                        </span>
                    </div>
                    <Button
                        variant="primary"
                        onClick={() => scanMutation.mutate()}
                        loading={scanMutation.isPending}
                        disabled={text.length < 50}
                        icon={<Search size={16} />}
                    >
                        Scan for DPDP Compliance
                    </Button>
                </>
            ) : (
                <>
                    {/* Results Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                        <div>
                            <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                                {result.contract_name}
                            </h2>
                            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                Scanned {new Date(result.scanned_at).toLocaleString('en-IN')}
                            </span>
                        </div>
                        <Button variant="secondary" onClick={() => { setResult(null); setText(''); setName(''); }}>
                            Scan Another
                        </Button>
                    </div>

                    {/* Score + Stats */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
                        <StatCard icon={<Shield size={16} />} label="Score" value={`${result.compliance_score}%`} color={scoreColor(result.compliance_score)} sub="" />
                        <StatCard icon={<AlertTriangle size={16} />} label="Red" value={String(result.red_findings)} color="var(--risk-critical)" sub="Critical" />
                        <StatCard icon={<Clock size={16} />} label="Yellow" value={String(result.yellow_findings)} color="var(--risk-high, orange)" sub="Warnings" />
                        <StatCard icon={<CheckCircle size={16} />} label="Green" value={String(result.green_findings)} color="var(--risk-low, #22C55E)" sub="Compliant" />
                        <StatCard icon={<Scale size={16} />} label="Deal Breakers" value={String(result.deal_breakers)} color={result.deal_breakers > 0 ? 'var(--risk-critical)' : 'var(--text-primary)'} sub="" />
                    </div>

                    {/* Findings */}
                    <SectionHeader icon={<FileText size={18} />} title={`Findings (${result.total_findings})`} />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {result.findings.map((f, i) => (
                            <FindingCard
                                key={i}
                                finding={f}
                                expanded={expandedFinding === f.rule_id}
                                onToggle={() => setExpandedFinding(expandedFinding === f.rule_id ? null : f.rule_id)}
                            />
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}

/* =========================================================================
   REMEDIATE TAB — Generate Documents
   ========================================================================= */

function RemediateTab() {
    const [selectedType, setSelectedType] = useState<string | null>(null);
    const [output, setOutput] = useState<DPDPRemediationOutput | null>(null);
    const [party1, setParty1] = useState('');
    const [party2, setParty2] = useState('');

    const { data: templatesData } = useQuery({
        queryKey: ['dpdp-templates'],
        queryFn: dpdpGetTemplates,
        staleTime: 300000,
    });

    const generateMutation = useMutation({
        mutationFn: () => dpdpRemediate({
            remediation_type: selectedType,
            party_1_name: party1,
            party_2_name: party2,
            jurisdiction: 'IN',
            language: 'en',
            gaps_to_address: [],
            context: {},
        }),
        onSuccess: (data) => setOutput(data),
    });

    const templates = templatesData?.templates || [];

    if (output) {
        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                        {output.title}
                    </h2>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <Button variant="secondary" onClick={() => { setOutput(null); setSelectedType(null); }}>
                            Back
                        </Button>
                        <Button variant="primary" icon={<Download size={16} />} onClick={() => {
                            const blob = new Blob([output.content], { type: 'text/plain' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${output.title.replace(/\s+/g, '_')}.txt`;
                            a.click();
                            URL.revokeObjectURL(url);
                        }}>
                            Download
                        </Button>
                    </div>
                </div>

                {output.notes.length > 0 && (
                    <div style={{ padding: 12, borderRadius: 8, backgroundColor: 'var(--info-bg, rgba(59,130,246,0.1))', border: '1px solid var(--info, #3B82F6)', marginBottom: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
                        {output.notes.map((n, i) => <div key={i}>{n}</div>)}
                    </div>
                )}

                <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                    {output.sections.map((s, i) => (
                        <div key={i} style={{ padding: 20, borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--accent)', marginBottom: 8, margin: 0 }}>
                                {s.heading}
                            </h3>
                            <pre style={{ fontSize: 13, color: 'var(--text-primary)', whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'var(--font-sans)', lineHeight: 1.6 }}>
                                {s.content}
                            </pre>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div>
            {!selectedType ? (
                <>
                    <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 20 }}>
                        Generate DPDP-oriented drafts for legal and factual review. Select a template to get started.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                        {templates.map(t => (
                            <div
                                key={t.type}
                                onClick={() => setSelectedType(t.type)}
                                style={{
                                    padding: 20, borderRadius: 12,
                                    border: '1px solid var(--border)',
                                    backgroundColor: 'var(--bg-secondary)',
                                    cursor: 'pointer',
                                    transition: 'all var(--transition-fast)',
                                }}
                                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'; }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                    <Wrench size={16} style={{ color: 'var(--accent)' }} />
                                    <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{t.name}</span>
                                </div>
                                <span style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{t.description}</span>
                            </div>
                        ))}
                    </div>
                </>
            ) : (
                <>
                    <Button variant="ghost" onClick={() => setSelectedType(null)} style={{ marginBottom: 16 }}>
                        Back to templates
                    </Button>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                        Generate: {selectedType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                        <div>
                            <label style={labelStyle}>Party 1 (Data Fiduciary)</label>
                            <input value={party1} onChange={e => setParty1(e.target.value)} placeholder="Your company name" style={inputStyle} />
                        </div>
                        <div>
                            <label style={labelStyle}>Party 2 (Data Processor / Counterparty)</label>
                            <input value={party2} onChange={e => setParty2(e.target.value)} placeholder="Vendor / partner name" style={inputStyle} />
                        </div>
                    </div>
                    <Button
                        variant="primary"
                        onClick={() => generateMutation.mutate()}
                        loading={generateMutation.isPending}
                        icon={<Wrench size={16} />}
                    >
                        Generate Document
                    </Button>
                </>
            )}
        </div>
    );
}

/* =========================================================================
   SHARED COMPONENTS
   ========================================================================= */

function StatCard({ icon, label, value, color, sub }: { icon: React.ReactNode; label: string; value: string; color: string; sub: string }) {
    return (
        <div style={statCardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: 'var(--text-muted)' }}>{icon}</span>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
            </div>
            <span style={{ fontSize: 28, fontWeight: 700, color }}>{value}</span>
            {sub && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</span>}
        </div>
    );
}

function DeadlineCard({ deadline }: { deadline: DPDPDeadline }) {
    const statusColors: Record<string, string> = {
        overdue: 'var(--risk-critical)',
        due_soon: 'var(--risk-high, orange)',
        upcoming: 'var(--text-muted)',
        completed: 'var(--risk-low, #22C55E)',
    };
    const color = statusColors[deadline.status] || 'var(--text-muted)';

    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: 16, padding: '12px 16px',
            border: '1px solid var(--border)', borderRadius: 8, backgroundColor: 'var(--bg-secondary)',
        }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: color, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>{deadline.title}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{deadline.description}</div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color }}>{new Date(deadline.deadline).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {deadline.status === 'completed' ? 'Done' : deadline.status === 'overdue' ? 'OVERDUE' : `${deadline.days_remaining} days left`}
                </div>
            </div>
        </div>
    );
}

function AlertCard({ alert }: { alert: DPDPAlert }) {
    const severityColors: Record<string, string> = {
        critical: 'var(--risk-critical)',
        warning: 'var(--risk-high, orange)',
        info: 'var(--info, #3B82F6)',
    };
    const color = severityColors[alert.severity] || 'var(--text-muted)';

    return (
        <div style={{
            padding: '12px 16px', border: '1px solid var(--border)', borderRadius: 8,
            backgroundColor: 'var(--bg-secondary)', borderLeft: `3px solid ${color}`,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Badge variant={alert.severity === 'critical' ? 'critical' : alert.severity === 'warning' ? 'high' : 'info'}>
                    {alert.severity.toUpperCase()}
                </Badge>
                <span style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>{alert.title}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{alert.description}</div>
            {alert.action_required && (
                <div style={{ fontSize: 12, color, marginTop: 6, fontWeight: 500 }}>{alert.action_required}</div>
            )}
        </div>
    );
}

function FindingCard({ finding, expanded, onToggle }: { finding: DPDPContractFinding; expanded: boolean; onToggle: () => void }) {
    const riskColors: Record<string, string> = {
        RED: 'var(--risk-critical)',
        YELLOW: 'var(--risk-high, orange)',
        GREEN: 'var(--risk-low, #22C55E)',
    };
    const color = riskColors[finding.risk_level] || 'var(--text-muted)';

    return (
        <div style={{
            border: '1px solid var(--border)', borderRadius: 8,
            backgroundColor: 'var(--bg-secondary)', borderLeft: `3px solid ${color}`,
            overflow: 'hidden',
        }}>
            <div
                onClick={onToggle}
                style={{
                    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                    cursor: 'pointer', transition: 'background var(--transition-fast)',
                }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--bg-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
                {expanded ? <ChevronDown size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronRight size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                <Badge variant={finding.risk_level === 'RED' ? 'critical' : finding.risk_level === 'YELLOW' ? 'high' : 'low'}>
                    {finding.risk_level}
                </Badge>
                {finding.is_deal_breaker && <Badge variant="critical">DEAL BREAKER</Badge>}
                <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{finding.title}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
                    {finding.section.replace('section_', 'S.')}
                </span>
            </div>
            {expanded && (
                <div style={{ padding: '0 16px 16px 42px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{finding.description}</div>
                    {finding.clause_text && (
                        <div style={{ padding: 10, borderRadius: 6, backgroundColor: 'var(--bg-tertiary, rgba(255,255,255,0.03))', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', borderLeft: '2px solid var(--border)' }}>
                            "{finding.clause_text}"
                        </div>
                    )}
                    {finding.suggested_fix && (
                        <div style={{ padding: 10, borderRadius: 6, backgroundColor: 'rgba(34,197,94,0.06)', fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5 }}>
                            <span style={{ fontWeight: 600, color: 'var(--risk-low, #22C55E)' }}>Suggested Fix: </span>
                            {finding.suggested_fix}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function QuickAction({ icon, title, description, color }: { icon: React.ReactNode; title: string; description: string; color: string }) {
    return (
        <div style={{
            padding: 20, borderRadius: 12, border: '1px solid var(--border)',
            backgroundColor: 'var(--bg-secondary)', cursor: 'pointer',
            transition: 'all var(--transition-fast)',
        }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = color; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
        >
            <div style={{ color, marginBottom: 12 }}>{icon}</div>
            <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', marginBottom: 4 }}>{title}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{description}</div>
        </div>
    );
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ color: 'var(--accent)' }}>{icon}</span>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{title}</h2>
        </div>
    );
}

function LoadingSpinner() {
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
            <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
        </div>
    );
}

function EmptyState({ text }: { text: string }) {
    return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>{text}</div>;
}

function scoreColor(score: number): string {
    if (score >= 80) return 'var(--risk-low, #22C55E)';
    if (score >= 50) return 'var(--risk-high, orange)';
    return 'var(--risk-critical)';
}

/* ---- Shared Styles ---- */

const statCardStyle: CSSProperties = {
    padding: 20, borderRadius: 12, border: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)', display: 'flex', flexDirection: 'column', gap: 6,
};

const labelStyle: CSSProperties = {
    display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-muted)',
    marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em',
};

const inputStyle: CSSProperties = {
    width: '100%', padding: '10px 12px', borderRadius: 8,
    border: '1px solid var(--border)', backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-primary)', fontSize: 13, fontFamily: 'var(--font-sans)',
    outline: 'none', boxSizing: 'border-box',
};


/* =========================================================================
   ASSESS TAB — Gap Assessment Questionnaire
   ========================================================================= */

function AssessTab() {
    const [orgName, setOrgName] = useState('');
    const [industry, setIndustry] = useState('');
    const [childrenData, setChildrenData] = useState(false);
    const [sdf, setSdf] = useState(false);
    const [crossBorder, setCrossBorder] = useState(false);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [result, setResult] = useState<DPDPGapAssessment | null>(null);

    const { data: questions, isLoading } = useQuery({
        queryKey: ['dpdp-questions', childrenData, sdf, crossBorder],
        queryFn: () => dpdpGetAssessmentQuestions({
            processes_children_data: childrenData,
            is_significant_fiduciary: sdf,
            has_cross_border: crossBorder,
        }),
    });

    const assessMut = useMutation({
        mutationFn: () => dpdpRunAssessment({
            organization_name: orgName || 'My Organization',
            industry: industry || undefined,
            answers: Object.entries(answers).map(([qid, ans]) => ({
                question_id: qid,
                answer: ans,
            })),
            processes_children_data: childrenData,
            is_significant_fiduciary: sdf,
            has_cross_border_transfers: crossBorder,
        }),
        onSuccess: (data) => setResult(data),
    });

    if (result) {
        return (
            <div>
                {/* Assessment Result */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
                    <div style={{
                        width: 80, height: 80, borderRadius: '50%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        border: `3px solid ${scoreColor(result.overall_score)}`,
                        fontSize: 24, fontWeight: 700, color: scoreColor(result.overall_score),
                    }}>
                        {result.overall_score}
                    </div>
                    <div>
                        <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                            {result.overall_status?.replace('_', ' ').toUpperCase()}
                        </h2>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                            {result.deadline_risk}
                        </p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setResult(null)} style={{ marginLeft: 'auto' }}>
                        Run New Assessment
                    </Button>
                </div>

                {/* Critical Gaps */}
                {result.critical_gaps?.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--red)', marginBottom: 12 }}>
                            Critical Gaps ({result.critical_gaps.length})
                        </h3>
                        {result.critical_gaps.map((gap, i) => (
                            <div key={i} style={{ padding: 12, borderRadius: 8, border: '1px solid var(--red)', backgroundColor: 'rgba(239,68,68,0.05)', marginBottom: 8, fontSize: 13 }}>
                                {gap}
                            </div>
                        ))}
                    </div>
                )}

                {/* Action Items */}
                {result.action_items?.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>
                            Recommended Actions
                        </h3>
                        {result.action_items.map((item, i) => (
                            <div key={i} style={{ display: 'flex', gap: 8, padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                                <span style={{ color: 'var(--accent)', fontWeight: 600, flexShrink: 0 }}>{i + 1}.</span>
                                <span style={{ color: 'var(--text-primary)' }}>{item}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Section Scores */}
                {result.section_scores?.length > 0 && (
                    <div>
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>
                            Section-by-Section Scores
                        </h3>
                        <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                            {result.section_scores.map((s, i) => (
                                <div key={i} style={{
                                    display: 'flex', alignItems: 'center', gap: 12,
                                    padding: '10px 16px', borderBottom: '1px solid var(--border)',
                                    backgroundColor: 'var(--bg-secondary)',
                                }}>
                                    <div style={{
                                        width: 8, height: 8, borderRadius: '50%',
                                        backgroundColor: scoreColor(s.score || 0),
                                    }} />
                                    <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                                        {s.section_name || s.section}
                                    </span>
                                    <span style={{ fontSize: 13, fontWeight: 600, color: scoreColor(s.score || 0) }}>
                                        {s.score || 0}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 20 }}>
                Answer questions about your organization's DPDP compliance posture.
                Consent-related questions are auto-filled from your consent management system.
            </p>

            {/* Org Profile */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                    <label style={labelStyle}>Organization Name</label>
                    <input style={inputStyle} value={orgName} onChange={e => setOrgName(e.target.value)} placeholder="Your company name" />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                    <label style={labelStyle}>Industry</label>
                    <input style={inputStyle} value={industry} onChange={e => setIndustry(e.target.value)} placeholder="e.g., Technology, Finance" />
                </div>
            </div>

            {/* Toggles */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
                {[
                    { label: 'Processes children\'s data (under 18)', value: childrenData, set: setChildrenData },
                    { label: 'Significant Data Fiduciary', value: sdf, set: setSdf },
                    { label: 'Cross-border data transfers', value: crossBorder, set: setCrossBorder },
                ].map(toggle => (
                    <label key={toggle.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer' }}>
                        <input type="checkbox" checked={toggle.value} onChange={e => toggle.set(e.target.checked)} />
                        {toggle.label}
                    </label>
                ))}
            </div>

            {/* Questions */}
            {isLoading ? (
                <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading assessment questions...</div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
                    {(questions || []).map((q: DPDPAssessmentQuestion) => (
                        <div key={q.id} style={{
                            padding: 16, borderRadius: 10, border: '1px solid var(--border)',
                            backgroundColor: 'var(--bg-secondary)',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                                <div style={{ flex: 1 }}>
                                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                                        {q.question}
                                    </span>
                                    {q.is_critical && <Badge variant="critical" style={{ marginLeft: 8 }}>Critical</Badge>}
                                    {q.guidance && (
                                        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0 0' }}>{q.guidance}</p>
                                    )}
                                </div>
                                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                                    {['yes', 'partial', 'no'].map(ans => (
                                        <button
                                            key={ans}
                                            onClick={() => setAnswers(prev => ({ ...prev, [q.id]: ans }))}
                                            style={{
                                                padding: '4px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                                                border: answers[q.id] === ans ? '2px solid var(--accent)' : '1px solid var(--border)',
                                                backgroundColor: answers[q.id] === ans ? 'var(--accent)' : 'transparent',
                                                color: answers[q.id] === ans ? '#fff' : 'var(--text-muted)',
                                            }}
                                        >
                                            {ans.charAt(0).toUpperCase() + ans.slice(1)}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <Button
                variant="primary"
                onClick={() => assessMut.mutate()}
                disabled={assessMut.isPending || Object.keys(answers).length === 0}
            >
                {assessMut.isPending ? 'Analyzing...' : 'Run Assessment'}
            </Button>
        </div>
    );
}


/* =========================================================================
   REPORT TAB — Generate & View Compliance Reports
   ========================================================================= */

function ReportTab() {
    const [generatedReport, setGeneratedReport] = useState<DPDPGeneratedReport | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    const { data: reportHistory } = useQuery({
        queryKey: ['dpdp-report-history'],
        queryFn: dpdpGetReportHistory,
    });

    const { data: searchResults } = useQuery({
        queryKey: ['dpdp-search', searchQuery],
        queryFn: () => dpdpSearchRegulation(searchQuery),
        enabled: searchQuery.length >= 2,
    });

    const generateMut = useMutation({
        mutationFn: dpdpGenerateReport,
        onSuccess: (data) => setGeneratedReport(data),
    });

    return (
        <div>
            {/* Generate Report */}
            <div style={{ marginBottom: 32 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>
                    Generate Compliance Report
                </h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                    Generate a comprehensive DPDP compliance report aggregating contract scans,
                    gap assessments, and consent health for audit readiness.
                </p>
                <Button
                    variant="primary"
                    onClick={() => generateMut.mutate()}
                    disabled={generateMut.isPending}
                >
                    {generateMut.isPending ? 'Generating Report...' : 'Generate Full Report'}
                </Button>

                {generatedReport && (
                    <div style={{ marginTop: 16, padding: 20, borderRadius: 12, border: '1px solid var(--accent)', backgroundColor: 'var(--bg-secondary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                            <CheckCircle size={20} style={{ color: 'var(--green)' }} />
                            <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                                {generatedReport.title}
                            </span>
                            <span style={{ fontSize: 24, fontWeight: 700, color: scoreColor(generatedReport.compliance_score), marginLeft: 'auto' }}>
                                {generatedReport.compliance_score}/100
                            </span>
                        </div>
                        <pre style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'pre-wrap', margin: 0, lineHeight: 1.6 }}>
                            {generatedReport.summary}
                        </pre>
                        <Button
                            variant="ghost" size="sm"
                            onClick={() => {
                                const blob = new Blob([JSON.stringify(generatedReport.content, null, 2)], { type: 'application/json' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `dpdp-compliance-report-${generatedReport.report_id}.json`;
                                a.click();
                                URL.revokeObjectURL(url);
                            }}
                            style={{ marginTop: 12 }}
                        >
                            <Download size={14} /> Download Full Report (JSON)
                        </Button>
                    </div>
                )}
            </div>

            {/* Knowledge Base Search */}
            <div style={{ marginBottom: 32 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>
                    Search DPDP Act & Rules
                </h3>
                <input
                    style={inputStyle}
                    placeholder="Search for provisions... (e.g., 'consent withdrawal', 'breach notification', 'children data')"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                />
                {searchResults && searchResults.length > 0 && (
                    <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {searchResults.map((s, i) => (
                            <div key={i} style={{
                                padding: 16, borderRadius: 10, border: '1px solid var(--border)',
                                backgroundColor: 'var(--bg-secondary)',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                                    <Scale size={14} style={{ color: 'var(--accent)' }} />
                                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                                        {s.source} — {s.section}: {s.title}
                                    </span>
                                </div>
                                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px' }}>{s.summary}</p>
                                <pre style={{ fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0, padding: 12, borderRadius: 6, backgroundColor: 'var(--bg-tertiary)', maxHeight: 200, overflowY: 'auto' }}>
                                    {s.full_text}
                                </pre>
                                {(s.penalties || s.deadline) && (
                                    <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                                        {s.penalties && <Badge variant="critical">{s.penalties}</Badge>}
                                        {s.deadline && <Badge variant="neutral">Deadline: {s.deadline}</Badge>}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Report History */}
            {reportHistory && reportHistory.length > 0 && (
                <div>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>
                        Previous Reports
                    </h3>
                    <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                        {reportHistory.map((r) => (
                            <div key={r.id} style={{
                                display: 'flex', alignItems: 'center', gap: 12,
                                padding: '12px 16px', borderBottom: '1px solid var(--border)',
                                backgroundColor: 'var(--bg-secondary)',
                            }}>
                                <FileText size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                                <div style={{ flex: 1 }}>
                                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                                        {r.title}
                                    </span>
                                    <br />
                                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                        {new Date(r.generated_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                                    </span>
                                </div>
                                <span style={{ fontSize: 16, fontWeight: 700, color: scoreColor(r.compliance_score) }}>
                                    {r.compliance_score}%
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
