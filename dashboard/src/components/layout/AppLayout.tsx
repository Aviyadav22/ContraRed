import { useState, type ReactNode, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout } from '@/api/client';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface AppLayoutProps {
  children: ReactNode;
}

function getUserProfile(): { name: string; role?: string } {
  try {
    const raw = sessionStorage.getItem('user_profile');
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        name: parsed.full_name || parsed.name || parsed.email || 'User',
        role: parsed.role,
      };
    }
  } catch { /* ignore */ }
  return { name: 'User' };
}

export function AppLayout({ children }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const user = getUserProfile();

  const sidebarWidth = collapsed ? 64 : 240;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const mainStyle: CSSProperties = {
    marginLeft: sidebarWidth,
    paddingTop: 48,
    minHeight: '100vh',
    backgroundColor: 'var(--bg-app)',
    transition: `margin-left var(--transition-normal)`,
  };

  const innerStyle: CSSProperties = {
    maxWidth: 1280,
    margin: '0 auto',
    padding: '32px 24px',
  };

  return (
    <>
      <Sidebar
        userName={user.name}
        userRole={user.role}
        onLogout={handleLogout}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(c => !c)}
      />
      <TopBar sidebarWidth={sidebarWidth} />
      <main style={mainStyle}>
        <div style={innerStyle}>{children}</div>
      </main>
    </>
  );
}
