import { type CSSProperties } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToast, type ToastVariant } from '@/contexts/ToastContext';

const iconMap: Record<ToastVariant, { Icon: typeof Info; color: string }> = {
  success: { Icon: CheckCircle, color: 'var(--risk-low)' },
  error: { Icon: XCircle, color: 'var(--risk-critical)' },
  warning: { Icon: AlertTriangle, color: 'var(--risk-high)' },
  info: { Icon: Info, color: 'var(--info)' },
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  const containerStyle: CSSProperties = {
    position: 'fixed',
    bottom: 20,
    right: 20,
    zIndex: 2000,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    pointerEvents: 'none',
  };

  return (
    <div style={containerStyle}>
      {toasts.map((toast) => {
        const { Icon, color } = iconMap[toast.variant];
        const toastStyle: CSSProperties = {
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 16px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          animation: 'slideUp 0.3s ease-out',
          minWidth: 280,
          maxWidth: 400,
          pointerEvents: 'auto',
        };

        const closeBtnStyle: CSSProperties = {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 20,
          height: 20,
          border: 'none',
          backgroundColor: 'transparent',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          borderRadius: 'var(--radius-sm)',
          marginLeft: 'auto',
          flexShrink: 0,
        };

        return (
          <div key={toast.id} style={toastStyle}>
            <Icon size={18} style={{ color, flexShrink: 0 }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', flex: 1 }}>
              {toast.message}
            </span>
            <button style={closeBtnStyle} onClick={() => removeToast(toast.id)} aria-label="Dismiss">
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
