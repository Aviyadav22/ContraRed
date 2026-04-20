import { useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '@/contexts/ThemeContext';
import { isAdmin } from '@/api/client';
import { Tooltip } from '@/components/ui/Tooltip';
import {
  LayoutDashboard,
  FileText,
  PenTool,
  BookOpen,
  Library,
  GitCompareArrows,
  Scissors,
  BarChart3,
  TrendingUp,
  FileBarChart,
  ScrollText,
  Users,
  CreditCard,
  Store,
  ShieldCheck,
  Sun,
  Moon,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  type LucideIcon,
} from 'lucide-react';
import type { CSSProperties } from 'react';

/* ---------- types ---------- */

interface SidebarProps {
  userName: string;
  userRole?: string;
  onLogout: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

interface NavItem {
  label: string;
  icon: LucideIcon;
  path: string;
  adminOnly?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

/* ---------- nav data ---------- */

const sections: NavSection[] = [
  {
    title: 'MAIN',
    items: [
      { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
      { label: 'AI Redlining', icon: Scissors, path: '/redline' },
      { label: 'Documents', icon: FileText, path: '/batch-upload' },
      { label: 'Drafting', icon: PenTool, path: '/drafting' },
    ],
  },
  {
    title: 'REVIEW',
    items: [
      { label: 'Playbooks', icon: BookOpen, path: '/playbooks' },
      { label: 'Clause Library', icon: Library, path: '/clause-library' },
      { label: 'Compare', icon: GitCompareArrows, path: '/compare' },
    ],
  },
  {
    title: 'COMPLIANCE',
    items: [
      { label: 'DPDP Center', icon: ShieldCheck, path: '/dpdp' },
    ],
  },
  {
    title: 'INSIGHTS',
    items: [
      { label: 'Analytics', icon: BarChart3, path: '/analytics', adminOnly: true },
      { label: 'Executive', icon: TrendingUp, path: '/executive', adminOnly: true },
      { label: 'Reports', icon: FileBarChart, path: '/reports', adminOnly: true },
      { label: 'Audit Logs', icon: ScrollText, path: '/audit-logs' },
    ],
  },
  {
    title: 'ADMIN',
    items: [
      { label: 'Team', icon: Users, path: '/team', adminOnly: true },
      { label: 'Billing', icon: CreditCard, path: '/billing', adminOnly: true },
      { label: 'Marketplace', icon: Store, path: '/marketplace' },
    ],
  },
];

/* ---------- helpers ---------- */

function getInitials(name: string): string {
  return name
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/* ---------- component ---------- */

export function Sidebar({
  userName,
  userRole,
  onLogout,
  collapsed,
  onToggleCollapse,
}: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const admin = isAdmin();

  const width = collapsed ? 64 : 240;

  /* ---- styles ---- */

  const sidebarStyle: CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    bottom: 0,
    width,
    backgroundColor: '#09090B',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 100,
    transition: `width var(--transition-normal)`,
    overflow: 'hidden',
  };

  const sectionLabelStyle: CSSProperties = {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    color: '#64748B',
    padding: collapsed ? '12px 0 4px' : '12px 16px 4px',
    textAlign: collapsed ? 'center' : 'left',
    whiteSpace: 'nowrap',
  };

  const dividerStyle: CSSProperties = {
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.06)',
    margin: '4px 12px',
  };

  /* ---- render helpers ---- */

  function renderFooterItem(icon: React.ReactNode, label: string, onClick: () => void) {
    const style: CSSProperties = {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: collapsed ? '10px 0' : '8px 16px',
      justifyContent: collapsed ? 'center' : 'flex-start',
      color: '#94A3B8',
      fontSize: 13,
      cursor: 'pointer',
      width: '100%',
      boxSizing: 'border-box' as const,
      minHeight: 38,
      transition: `background var(--transition-fast), color var(--transition-fast)`,
      backgroundColor: 'transparent',
      border: 'none',
      fontFamily: 'var(--font-sans)',
    };

    const inner = (
      <div
        style={style}
        onClick={onClick}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#CBD5E1'; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
      >
        {icon}
        {!collapsed && <span>{label}</span>}
      </div>
    );

    if (collapsed) {
      return <Tooltip key={label} content={label} position="right">{inner}</Tooltip>;
    }
    return inner;
  }

  function renderItem(item: NavItem) {
    if (item.adminOnly && !admin) return null;
    const active = location.pathname === item.path;
    const Icon = item.icon;

    const itemStyle: CSSProperties = {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: collapsed ? '10px 0' : '8px 16px',
      justifyContent: collapsed ? 'center' : 'flex-start',
      cursor: 'pointer',
      borderLeft: active ? '3px solid #C0392B' : '3px solid transparent',
      backgroundColor: active ? 'rgba(192,57,43,0.12)' : 'transparent',
      color: active ? '#FFFFFF' : '#94A3B8',
      fontSize: 13,
      fontWeight: active ? 600 : 400,
      whiteSpace: 'nowrap',
      transition: `background var(--transition-fast), color var(--transition-fast)`,
      borderRadius: 0,
      width: '100%',
      boxSizing: 'border-box' as const,
      minHeight: 38,
    };

    const hoverHandlers = active
      ? {}
      : {
          onMouseEnter: (e: React.MouseEvent<HTMLDivElement>) => {
            e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
            e.currentTarget.style.color = '#CBD5E1';
          },
          onMouseLeave: (e: React.MouseEvent<HTMLDivElement>) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = '#94A3B8';
          },
        };

    const inner = (
      <div
        key={item.path}
        style={itemStyle}
        onClick={() => navigate(item.path)}
        {...hoverHandlers}
      >
        <Icon size={18} style={{ flexShrink: 0 }} />
        {!collapsed && <span>{item.label}</span>}
      </div>
    );

    if (collapsed) {
      return (
        <Tooltip key={item.path} content={item.label} position="right">
          {inner}
        </Tooltip>
      );
    }

    return inner;
  }

  return (
    <aside style={sidebarStyle}>
      {/* Logo header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: collapsed ? '16px 0' : '16px',
          gap: 10,
          minHeight: 56,
        }}
      >
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 0, cursor: collapsed ? 'pointer' : 'default' }}
          onClick={collapsed ? onToggleCollapse : undefined}
          title={collapsed ? 'Expand sidebar' : undefined}
        >
          <span
            style={{
              color: '#F8FAFC',
              fontWeight: 700,
              fontSize: 18,
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ color: '#C0392B' }}>C</span>{!collapsed && 'ontraRed'}
          </span>
        </div>
        {!collapsed && (
          <button
            onClick={onToggleCollapse}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748B',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        )}
      </div>

      {/* Navigation sections */}
      <nav style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {sections.map((section, idx) => {
          const visibleItems = section.items.filter(
            i => !i.adminOnly || admin,
          );
          if (visibleItems.length === 0) return null;

          return (
            <div key={section.title} style={{ display: 'flex', flexDirection: 'column' }}>
              {idx > 0 && <div style={dividerStyle} />}
              {!collapsed && <div style={sectionLabelStyle}>{section.title}</div>}
              {collapsed && <div style={{ ...dividerStyle, margin: '6px 8px' }} />}
              {section.items.map(renderItem)}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          borderTop: '1px solid rgba(255,255,255,0.06)',
          padding: 8,
          display: 'flex',
          flexDirection: 'column',
          gap: 0,
        }}
      >
        {/* Theme toggle */}
        {renderFooterItem(
          theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />,
          theme === 'dark' ? 'Light mode' : 'Dark mode',
          toggleTheme,
        )}

        {/* Collapse toggle (shown in collapsed state) */}
        {collapsed && renderFooterItem(
          <PanelLeft size={18} />,
          'Expand sidebar',
          onToggleCollapse,
        )}

        {/* User */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 16px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            minHeight: 40,
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              backgroundColor: 'rgba(192,57,43,0.25)',
              color: '#F87171',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {getInitials(userName || 'U')}
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden' }}>
              <div
                style={{
                  color: '#F8FAFC',
                  fontSize: 13,
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                }}
              >
                {userName}
              </div>
              {userRole && (
                <div style={{ color: '#64748B', fontSize: 11 }}>{userRole}</div>
              )}
            </div>
          )}
        </div>

        {/* Logout */}
        {renderFooterItem(
          <LogOut size={18} />,
          'Logout',
          onLogout,
        )}
      </div>
    </aside>
  );
}
