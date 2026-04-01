import { Link } from 'react-router-dom';
import { Button } from '@/components/ui';
import { ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--bg-app)',
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: 64, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>404</h1>
        <p style={{ fontSize: 18, color: 'var(--text-secondary)', marginBottom: 32 }}>Page not found</p>
        <Link to="/dashboard" style={{ textDecoration: 'none' }}>
          <Button icon={<ArrowLeft size={16} />}>Back to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
