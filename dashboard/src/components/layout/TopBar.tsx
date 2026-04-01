import { useLocation } from 'react-router-dom';
import { Search, Bell } from 'lucide-react';
import type { CSSProperties } from 'react';

interface TopBarProps {
  sidebarWidth: number;
}

const routeNames: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/drafting': 'Drafting',
  '/playbooks': 'Playbooks',
  '/clause-library': 'Clause Library',
  '/templates': 'Templates',
  '/compare': 'Compare',
  '/batch-upload': 'Documents',
  '/audit-logs': 'Audit Logs',
  '/analytics': 'Analytics',
  '/executive': 'Executive',
  '/reports': 'Reports',
  '/team': 'Team',
  '/billing': 'Billing',
  '/marketplace': 'Marketplace',
};

export function TopBar({ sidebarWidth }: TopBarProps) {
  const location = useLocation();
  const pageName = routeNames[location.pathname] || 'Page';

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

  const searchPillStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 14px',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    color: 'var(--text-muted)',
    fontSize: 13,
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
  };

  const kbdStyle: CSSProperties = {
    fontSize: 11,
    fontFamily: 'var(--font-mono)',
    padding: '1px 5px',
    borderRadius: 4,
    backgroundColor: 'var(--bg-hover)',
    border: '1px solid var(--border)',
    color: 'var(--text-muted)',
    lineHeight: '16px',
  };

  const iconBtnStyle: CSSProperties = {
    background: 'none',
    border: 'none',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    padding: 6,
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
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

      {/* Center: search pill */}
      <div style={searchPillStyle}>
        <Search size={14} />
        <span>Search...</span>
        <kbd style={kbdStyle}>Ctrl+K</kbd>
      </div>

      {/* Right: notification bell */}
      <button style={iconBtnStyle} aria-label="Notifications">
        <Bell size={18} />
      </button>
    </header>
  );
}
