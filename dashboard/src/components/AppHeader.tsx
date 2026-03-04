import { Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getStoredUser, logout, isAdmin, type User } from '@/api/client';

interface AppHeaderProps {
    /** Override the active page key (e.g. 'dashboard', 'playbooks', 'audit-logs', 'team', 'billing') */
    activePage?: string;
}

const NAV_ITEMS = [
    { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
    { key: 'playbooks', label: 'Playbooks', path: '/playbooks' },
    { key: 'audit-logs', label: 'Audit Logs', path: '/audit-logs' },
];

const ADMIN_NAV_ITEMS = [
    { key: 'team', label: 'Team', path: '/team' },
    { key: 'billing', label: 'Billing', path: '/billing' },
];

export default function AppHeader({ activePage }: AppHeaderProps) {
    const [user, setUser] = useState<User | null>(null);
    const location = useLocation();
    const admin = isAdmin();

    useEffect(() => {
        setUser(getStoredUser());
    }, []);

    // Determine which nav item is active based on current path or explicit prop
    const getActiveKey = (): string => {
        if (activePage) return activePage;
        const path = location.pathname;
        if (path.startsWith('/playbooks')) return 'playbooks';
        if (path.startsWith('/audit-logs')) return 'audit-logs';
        if (path.startsWith('/team')) return 'team';
        if (path.startsWith('/billing')) return 'billing';
        return 'dashboard';
    };

    const activeKey = getActiveKey();

    const allItems = [...NAV_ITEMS, ...(admin ? ADMIN_NAV_ITEMS : [])];

    return (
        <header className="bg-white border-b border-slate-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    <Link to="/dashboard" className="flex items-center">
                        <img src="/logo.png" alt="ContraRed" className="h-7" />
                    </Link>

                    <nav className="flex items-center gap-6">
                        {allItems.map((item) => (
                            <Link
                                key={item.key}
                                to={item.path}
                                className={
                                    activeKey === item.key
                                        ? 'text-slate-900 font-medium text-sm'
                                        : 'text-slate-500 hover:text-slate-900 font-medium text-sm transition-colors'
                                }
                            >
                                {item.label}
                            </Link>
                        ))}
                    </nav>

                    <div className="flex items-center gap-4">
                        <span className="text-sm text-slate-500">
                            {user?.name}
                            {user?.role && (
                                <span className="ml-2 text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                    {user.role}
                                </span>
                            )}
                        </span>
                        <button
                            onClick={logout}
                            className="text-sm text-slate-400 hover:text-slate-600 font-medium transition-colors"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </header>
    );
}
