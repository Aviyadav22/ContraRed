import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { isAdmin, getDashboardStats, type DashboardStats } from '@/api/client';
import AppHeader from '@/components/AppHeader';

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
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: '#6B6966' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            ),
            accent: '#F0EDE8',
        },
        {
            label: 'Risks Detected',
            value: stats?.total_risks_detected ?? 0,
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: '#C0392B' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
            ),
            accent: '#FDF2F1',
            extra: stats && !statsLoading && (stats.red_risks > 0 || stats.yellow_risks > 0) ? (
                <div className="flex gap-2 mt-1.5">
                    {stats.red_risks > 0 && (
                        <span className="text-xs font-medium px-1.5 py-0.5 rounded" style={{ color: '#C0392B', background: '#FDF2F1' }}>
                            {stats.red_risks} critical
                        </span>
                    )}
                    {stats.yellow_risks > 0 && (
                        <span className="text-xs font-medium px-1.5 py-0.5 rounded" style={{ color: '#B7770D', background: '#FEF9EC' }}>
                            {stats.yellow_risks} warning
                        </span>
                    )}
                </div>
            ) : null,
        },
        {
            label: 'Fixes Applied',
            value: stats?.redlines_applied ?? 0,
            icon: (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: '#1A7A4A' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
                </svg>
            ),
            accent: '#F0F9F4',
        },
    ];

    const quickActions = [
        {
            to: '/playbooks',
            title: admin ? 'Manage Playbooks' : 'View Playbooks',
            desc: admin
                ? 'Create and edit clause detection rules for your contracts.'
                : 'Browse available clause detection playbooks.',
        },
        {
            to: '/clause-library',
            title: 'Clause Library',
            desc: 'Save and manage pre-approved contract language.',
        },
        {
            to: '/compare',
            title: 'Compare Contracts',
            desc: 'Upload two contract versions for side-by-side diff analysis.',
        },
        {
            to: '/audit-logs',
            title: 'Audit Logs',
            desc: 'View activity history and compliance audit trail.',
        },
    ];

    return (
        <div className="min-h-screen" style={{ background: '#FAFAF9' }}>
            <AppHeader />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-2xl font-semibold mb-8" style={{ color: '#1A1A19', letterSpacing: '-0.02em' }}>
                    Dashboard
                </h1>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
                    {statCards.map(card => (
                        <div
                            key={card.label}
                            className="rounded-xl p-5 transition-shadow hover:shadow"
                            style={{ background: '#FFFFFF', border: '1px solid #E8E5E0' }}
                        >
                            <div className="flex items-center gap-4">
                                <div
                                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                                    style={{ background: card.accent }}
                                >
                                    {card.icon}
                                </div>
                                <div>
                                    <p className="text-2xl font-semibold" style={{ color: '#1A1A19' }}>
                                        {statsLoading ? (
                                            <span
                                                className="inline-block w-8 h-6 rounded animate-pulse"
                                                style={{ background: '#F0EDE8' }}
                                            />
                                        ) : card.value}
                                    </p>
                                    <p className="text-[13px]" style={{ color: '#8A8885' }}>{card.label}</p>
                                    {card.extra}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Quick Actions */}
                <h2 className="text-base font-semibold mb-4" style={{ color: '#1A1A19' }}>Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {quickActions.map(action => (
                        <Link
                            key={action.to}
                            to={action.to}
                            className="rounded-xl p-5 transition-all group"
                            style={{ background: '#FFFFFF', border: '1px solid #E8E5E0' }}
                            onMouseEnter={e => {
                                (e.currentTarget as HTMLElement).style.borderColor = '#C0392B40';
                                (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px rgba(192,57,43,0.06)';
                            }}
                            onMouseLeave={e => {
                                (e.currentTarget as HTMLElement).style.borderColor = '#E8E5E0';
                                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                            }}
                        >
                            <h3 className="font-medium mb-1" style={{ color: '#1A1A19' }}>{action.title}</h3>
                            <p className="text-[13px]" style={{ color: '#8A8885' }}>{action.desc}</p>
                        </Link>
                    ))}
                </div>
            </main>
        </div>
    );
}
