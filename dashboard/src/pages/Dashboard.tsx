import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { isAdmin, getDashboardStats, type DashboardStats } from '@/api/client';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import {
    FileText,
    ShieldAlert,
    Wrench,
    BookOpen,
    Library,
    GitCompareArrows,
    ClipboardList,
    BarChart3,
    FileBarChart,
    Scissors,
    PenTool,
    ArrowRight,
} from 'lucide-react';

export default function Dashboard() {
    const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
        queryKey: ['dashboard-stats'],
        queryFn: getDashboardStats,
    });

    const admin = isAdmin();

    const statCards = [
        {
            label: 'Documents Analyzed',
            value: stats?.documents_analyzed ?? 0,
            icon: <FileText size={20} />,
            iconColor: 'var(--text-secondary)',
            iconBg: 'var(--bg-elevated)',
        },
        {
            label: 'Risks Detected',
            value: stats?.total_risks_detected ?? 0,
            icon: <ShieldAlert size={20} />,
            iconColor: 'var(--risk-critical)',
            iconBg: 'var(--risk-critical-bg)',
            extra: stats && !statsLoading && (stats.red_risks > 0 || stats.yellow_risks > 0) ? (
                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                    {stats.red_risks > 0 && (
                        <Badge variant="critical" size="sm">{stats.red_risks} critical</Badge>
                    )}
                    {stats.yellow_risks > 0 && (
                        <Badge variant="high" size="sm">{stats.yellow_risks} warning</Badge>
                    )}
                </div>
            ) : null,
        },
        {
            label: 'Fixes Applied',
            value: stats?.redlines_applied ?? 0,
            icon: <Wrench size={20} />,
            iconColor: 'var(--risk-low)',
            iconBg: 'var(--risk-low-bg)',
        },
    ];

    // Primary actions — the flagship features (shown prominently)
    const primaryActions = [
        {
            to: '/redline',
            title: 'AI Redlining',
            desc: 'Upload a contract and get instant AI-powered risk analysis with suggested fixes.',
            icon: <Scissors size={20} />,
        },
        {
            to: '/drafting',
            title: 'Draft a Contract',
            desc: 'Generate an NDA or SaaS agreement in minutes using our multi-agent drafting system.',
            icon: <PenTool size={20} />,
        },
    ];

    // Secondary actions — tools a user may also need
    const secondaryActions = [
        {
            to: '/playbooks',
            title: 'Manage Playbooks',
            desc: 'Create and edit clause detection rules for your organization.',
            icon: <BookOpen size={18} />,
        },
        {
            to: '/clause-library',
            title: 'Clause Library',
            desc: 'Save and manage pre-approved contract language.',
            icon: <Library size={18} />,
        },
        {
            to: '/compare',
            title: 'Compare Contracts',
            desc: 'Side-by-side diff analysis of two contract versions.',
            icon: <GitCompareArrows size={18} />,
        },
        {
            to: '/audit-logs',
            title: 'Audit Logs',
            desc: 'Activity history and compliance audit trail.',
            icon: <ClipboardList size={18} />,
        },
        ...(admin
            ? [
                {
                    to: '/executive',
                    title: 'Executive Dashboard',
                    desc: 'High-level metrics and ROI insights for leadership.',
                    icon: <BarChart3 size={18} />,
                },
                {
                    to: '/reports',
                    title: 'Reports',
                    desc: 'Generate and download detailed contract analysis reports.',
                    icon: <FileBarChart size={18} />,
                },
            ]
            : []),
    ];

    return (
        <AppLayout>
            <h1
                style={{
                    fontSize: 24,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.02em',
                    marginBottom: 32,
                }}
            >
                Dashboard
            </h1>

            {/* Onboarding Welcome */}
            {stats?.documents_analyzed === 0 && (
                <Card
                    style={{
                        backgroundColor: 'var(--accent-subtle)',
                        border: '1px solid var(--accent-glow)',
                        textAlign: 'center',
                        marginBottom: 24,
                    }}
                    padding="spacious"
                >
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent-text)', marginBottom: 8 }}>
                        Welcome to ContraRed!
                    </h3>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                        Get started by scanning your first contract in the Word Add-in, or explore the features below.
                    </p>
                </Card>
            )}

            {/* Stats Cards */}
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: 20,
                    marginBottom: 40,
                }}
            >
                {statCards.map(card => (
                    <Card key={card.label} variant="default" padding="spacious">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                            <div
                                style={{
                                    width: 40,
                                    height: 40,
                                    borderRadius: 'var(--radius-md)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    backgroundColor: card.iconBg,
                                    color: card.iconColor,
                                    flexShrink: 0,
                                }}
                            >
                                {card.icon}
                            </div>
                            <div>
                                <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2 }}>
                                    {statsLoading ? (
                                        <Skeleton variant="text" width={48} height={24} />
                                    ) : card.value}
                                </div>
                                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
                                    {card.label}
                                </div>
                                {'extra' in card && card.extra}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Primary actions — flagship features */}
            <h2
                style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    marginBottom: 16,
                }}
            >
                Get Started
            </h2>
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                    gap: 16,
                    marginBottom: 40,
                }}
            >
                {primaryActions.map(action => (
                    <Link key={action.to} to={action.to} style={{ textDecoration: 'none', display: 'flex' }}>
                        <Card
                            variant="interactive"
                            padding="spacious"
                            style={{
                                flex: 1,
                                border: '1px solid var(--accent-glow)',
                                backgroundColor: 'var(--accent-subtle)',
                            }}
                        >
                            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                                <div
                                    style={{
                                        width: 40,
                                        height: 40,
                                        borderRadius: 'var(--radius-md)',
                                        backgroundColor: 'var(--accent)',
                                        color: '#FFFFFF',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        flexShrink: 0,
                                    }}
                                >
                                    {action.icon}
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                                        <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                                            {action.title}
                                        </h3>
                                        <ArrowRight size={14} style={{ color: 'var(--accent-text)' }} />
                                    </div>
                                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                        {action.desc}
                                    </p>
                                </div>
                            </div>
                        </Card>
                    </Link>
                ))}
            </div>

            {/* Secondary actions — tools */}
            <h2
                style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    marginBottom: 16,
                }}
            >
                Tools
            </h2>
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: 16,
                }}
            >
                {secondaryActions.map(action => (
                    <Link key={action.to} to={action.to} style={{ textDecoration: 'none', display: 'flex' }}>
                        <Card variant="interactive" padding="spacious" style={{ flex: 1 }}>
                            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                                <div style={{ color: 'var(--accent-text)', marginTop: 2, flexShrink: 0 }}>
                                    {action.icon}
                                </div>
                                <div>
                                    <h3 style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
                                        {action.title}
                                    </h3>
                                    <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                                        {action.desc}
                                    </p>
                                </div>
                            </div>
                        </Card>
                    </Link>
                ))}
            </div>
        </AppLayout>
    );
}
