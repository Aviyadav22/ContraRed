import { useLocation } from 'react-router-dom';
import type { CSSProperties } from 'react';

interface TopBarProps {
  sidebarWidth: number;
}

const routeNames: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/redline': 'AI Redlining',
  '/drafting': 'Drafting',
  '/playbooks': 'Playbooks',
  '/clause-library': 'Clause Library',
  '/compare': 'Compare',
  '/batch-upload': 'Documents',
  '/audit-logs': 'Audit Logs',
  '/analytics': 'Analytics',
  '/executive': 'Executive',
  '/reports': 'Reports',
  '/team': 'Team',
  '/billing': 'Billing',
  '/marketplace': 'Marketplace',
  '/dpdp': 'DPDP Center',
  '/compliance': 'Compliance',
  '/settings/privacy': 'Privacy Settings',
  '/settings/data-rights': 'Data Rights',
};

function resolvePageName(pathname: string): string {
  if (routeNames[pathname]) return routeNames[pathname];
  // Dynamic routes
  if (pathname.startsWith('/playbooks/') && pathname.split('/').length > 2) {
    return 'Playbook Editor';
  }
  return 'Page';
}

export function TopBar({ sidebarWidth }: TopBarProps) {
  const location = useLocation();
  const pageName = resolvePageName(location.pathname);

  const barStyle: CSSProperties = {
    position: 'fixed',
    top: 0,
    left: sidebarWidth,
    right: 0,
    height: 48,
    backgroundColor: 'var(--bg-surface)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 20px',
    zIndex: 50,
    transition: `left var(--transition-normal)`,
  };

  const breadcrumbStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 13,
    color: 'var(--text-secondary)',
    whiteSpace: 'nowrap',
  };

  return (
    <header style={barStyle}>
      {/* Left: breadcrumb */}
      <div style={breadcrumbStyle}>
        <span style={{ color: 'var(--text-muted)' }}>ContraRed</span>
        <span style={{ color: 'var(--text-muted)' }}>/</span>
        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
          {pageName}
        </span>
      </div>
    </header>
  );
}
