import { Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getStoredUser, logout, isAdmin, type User } from '@/api/client';

interface AppHeaderProps {
    /** Override the active page key (e.g. 'dashboard', 'playbooks', 'audit-logs', 'team', 'billing') */
    activePage?: string;
}

const NAV_ITEMS = [
    { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
    { key: 'drafting', label: 'Draft', path: '/drafting' },
    { key: 'playbooks', label: 'Playbooks', path: '/playbooks' },
    { key: 'clauses', label: 'Clauses', path: '/clause-library' },
    { key: 'templates', label: 'Templates', path: '/templates' },
    { key: 'compare', label: 'Compare', path: '/compare' },
    { key: 'batch', label: 'Batch', path: '/batch-upload' },
    { key: 'marketplace', label: 'Marketplace', path: '/marketplace' },
    { key: 'audit-logs', label: 'Audit Logs', path: '/audit-logs' },
];

const ADMIN_NAV_ITEMS = [
    { key: 'analytics', label: 'Analytics', path: '/analytics' },
    { key: 'executive', label: 'Executive', path: '/executive' },
    { key: 'reports', label: 'Reports', path: '/reports' },
    { key: 'team', label: 'Team', path: '/team' },
    { key: 'billing', label: 'Billing', path: '/billing' },
];

export default function AppHeader({ activePage }: AppHeaderProps) {
    const [user, setUser] = useState<User | null>(null);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();
    const admin = isAdmin();

    useEffect(() => {
        setUser(getStoredUser());
    }, []);

    const getActiveKey = (): string => {
        if (activePage) return activePage;
        const path = location.pathname;
        if (path.startsWith('/drafting')) return 'drafting';
        if (path.startsWith('/playbooks')) return 'playbooks';
        if (path.startsWith('/clause-library')) return 'clauses';
        if (path.startsWith('/templates')) return 'templates';
        if (path.startsWith('/compare')) return 'compare';
        if (path.startsWith('/batch-upload')) return 'batch';
        if (path.startsWith('/marketplace')) return 'marketplace';
        if (path.startsWith('/audit-logs')) return 'audit-logs';
        if (path.startsWith('/analytics')) return 'analytics';
        if (path.startsWith('/executive')) return 'executive';
        if (path.startsWith('/reports')) return 'reports';
        if (path.startsWith('/team')) return 'team';
        if (path.startsWith('/billing')) return 'billing';
        return 'dashboard';
    };

    const activeKey = getActiveKey();
    const allItems = [...NAV_ITEMS, ...(admin ? ADMIN_NAV_ITEMS : [])];
    const initials = user?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || '?';

    return (
        <header
            className="sticky top-0 z-50 backdrop-blur-md"
            style={{
                background: 'hsla(40, 20%, 98.4%, 0.85)',
                borderBottom: '1px solid hsl(36, 10%, 89%)',
            }}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-14">
                    <Link to="/dashboard" className="flex items-center gap-2 group">
                        <img src="/logo.png" alt="ContraRed" className="h-6" />
                    </Link>

                    {/* Desktop nav */}
                    <nav aria-label="Main navigation" className="hidden md:flex items-center gap-1">
                        {allItems.map((item) => {
                            const isActive = activeKey === item.key;
                            return (
                                <Link
                                    key={item.key}
                                    to={item.path}
                                    className={`relative px-3 py-1.5 text-[13px] font-medium rounded-md transition-colors ${isActive ? '' : 'hover:text-[#1A1A19]'}`}
                                    style={{
                                        color: isActive ? '#1A1A19' : '#8A8885',
                                        background: isActive ? 'hsl(36, 10%, 91%)' : 'transparent',
                                    }}
                                >
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="flex items-center gap-3">
                        <div className="hidden md:flex items-center gap-2">
                            <div
                                className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold"
                                style={{ background: '#F0EDE8', color: '#6B6966' }}
                            >
                                {initials}
                            </div>
                            <span className="text-[13px] font-medium" style={{ color: '#6B6966' }}>
                                {user?.name}
                            </span>
                        </div>
                        <div className="hidden md:block w-px h-4" style={{ background: '#E8E5E0' }} />
                        <button
                            type="button"
                            onClick={logout}
                            className="hidden md:block text-[13px] font-medium transition-colors cursor-pointer text-[#A09D98] hover:text-[#C0392B]"
                        >
                            Logout
                        </button>

                        {/* Hamburger button (mobile) */}
                        <button
                            type="button"
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="md:hidden p-1.5 rounded-md hover:bg-slate-100 transition-colors"
                            aria-label="Toggle menu"
                        >
                            <svg width="22" height="22" fill="none" stroke="#6B6966" viewBox="0 0 24 24">
                                {mobileMenuOpen ? (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                ) : (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                                )}
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Mobile dropdown menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden border-t" style={{ borderColor: 'hsl(36, 10%, 89%)' }}>
                        <nav className="flex flex-col py-2 px-4 gap-1">
                            {allItems.map((item) => {
                                const isActive = activeKey === item.key;
                                return (
                                    <Link
                                        key={item.key}
                                        to={item.path}
                                        onClick={() => setMobileMenuOpen(false)}
                                        className={`px-3 py-2 text-[13px] font-medium rounded-md transition-colors ${isActive ? '' : 'hover:text-[#1A1A19]'}`}
                                        style={{
                                            color: isActive ? '#1A1A19' : '#8A8885',
                                            background: isActive ? 'hsl(36, 10%, 91%)' : 'transparent',
                                        }}
                                    >
                                        {item.label}
                                    </Link>
                                );
                            })}
                            <div className="border-t my-1" style={{ borderColor: 'hsl(36, 10%, 89%)' }} />
                            <div className="flex items-center gap-2 px-3 py-2">
                                <div
                                    className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold"
                                    style={{ background: '#F0EDE8', color: '#6B6966' }}
                                >
                                    {initials}
                                </div>
                                <span className="text-[13px] font-medium" style={{ color: '#6B6966' }}>
                                    {user?.name}
                                </span>
                            </div>
                            <button
                                type="button"
                                onClick={logout}
                                className="text-left px-3 py-2 text-[13px] font-medium transition-colors cursor-pointer text-[#A09D98] hover:text-[#C0392B]"
                            >
                                Logout
                            </button>
                        </nav>
                    </div>
                )}
            </div>
        </header>
    );
}
