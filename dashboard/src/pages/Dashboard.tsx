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

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-2xl font-bold text-slate-900 mb-8">Dashboard</h1>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-white rounded-lg p-6 border border-slate-200">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-slate-900">
                                    {statsLoading ? (
                                        <span className="inline-block w-8 h-6 bg-slate-200 rounded animate-pulse" />
                                    ) : (
                                        stats?.documents_analyzed ?? 0
                                    )}
                                </p>
                                <p className="text-sm text-slate-500">Documents Analyzed</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg p-6 border border-slate-200">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-slate-900">
                                    {statsLoading ? (
                                        <span className="inline-block w-8 h-6 bg-slate-200 rounded animate-pulse" />
                                    ) : (
                                        stats?.total_risks_detected ?? 0
                                    )}
                                </p>
                                <p className="text-sm text-slate-500">Risks Detected</p>
                                {stats && !statsLoading && (stats.red_risks > 0 || stats.yellow_risks > 0) && (
                                    <div className="flex gap-2 mt-1">
                                        {stats.red_risks > 0 && (
                                            <span className="text-xs text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{stats.red_risks} critical</span>
                                        )}
                                        {stats.yellow_risks > 0 && (
                                            <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">{stats.yellow_risks} warning</span>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg p-6 border border-slate-200">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-slate-900">
                                    {statsLoading ? (
                                        <span className="inline-block w-8 h-6 bg-slate-200 rounded animate-pulse" />
                                    ) : (
                                        stats?.redlines_applied ?? 0
                                    )}
                                </p>
                                <p className="text-sm text-slate-500">Fixes Applied</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Quick Actions */}
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Link
                        to="/playbooks"
                        className="bg-white rounded-lg p-6 border border-slate-200 hover:border-slate-300 transition-colors group"
                    >
                        <h3 className="font-semibold text-slate-900 group-hover:text-slate-700 mb-2">
                            {admin ? 'Manage Playbooks' : 'View Playbooks'}
                        </h3>
                        <p className="text-sm text-slate-500">
                            {admin
                                ? 'Create and edit clause detection rules for your contracts.'
                                : 'Browse available clause detection playbooks.'}
                        </p>
                    </Link>

                    <Link
                        to="/audit-logs"
                        className="bg-white rounded-lg p-6 border border-slate-200 hover:border-slate-300 transition-colors group"
                    >
                        <h3 className="font-semibold text-slate-900 group-hover:text-slate-700 mb-2">
                            Audit Logs
                        </h3>
                        <p className="text-sm text-slate-500">
                            View activity history and compliance audit trail.
                        </p>
                    </Link>
                </div>
            </main>
        </div>
    );
}
