import { type ReactNode, type CSSProperties } from 'react';

type BadgeVariant =
  | 'critical' | 'high' | 'medium' | 'low'
  | 'info' | 'neutral'
  | 'saas' | 'nda' | 'dpa' | 'employment' | 'msa'
  | 'custom';

type BadgeSize = 'sm' | 'md';

interface BadgeProps {
  variant?: BadgeVariant;
  size?: BadgeSize;
  icon?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}

const colorMap: Record<Exclude<BadgeVariant, 'custom'>, { bg: string; border: string; text: string }> = {
  critical: { bg: 'var(--risk-critical-bg)', border: 'var(--risk-critical-border)', text: 'var(--risk-critical)' },
  high: { bg: 'var(--risk-high-bg)', border: 'var(--risk-high-border)', text: 'var(--risk-high)' },
  medium: { bg: 'var(--risk-medium-bg)', border: 'var(--risk-medium-border)', text: 'var(--risk-medium)' },
  low: { bg: 'var(--risk-low-bg)', border: 'var(--risk-low-border)', text: 'var(--risk-low)' },
  info: { bg: 'var(--info-bg)', border: 'rgba(59, 130, 246, 0.3)', text: 'var(--info)' },
  neutral: { bg: 'var(--bg-elevated)', border: 'var(--border-strong)', text: 'var(--text-secondary)' },
  saas: { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.3)', text: '#3B82F6' },
  nda: { bg: 'rgba(139, 92, 246, 0.15)', border: 'rgba(139, 92, 246, 0.3)', text: '#8B5CF6' },
  dpa: { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)', text: '#10B981' },
  employment: { bg: 'rgba(249, 115, 22, 0.15)', border: 'rgba(249, 115, 22, 0.3)', text: '#F97316' },
  msa: { bg: 'rgba(99, 102, 241, 0.15)', border: 'rgba(99, 102, 241, 0.3)', text: '#6366F1' },
};

const sizeStyles: Record<BadgeSize, CSSProperties> = {
  sm: { fontSize: 10, padding: '2px 6px', gap: 4 },
  md: { fontSize: 11, padding: '3px 8px', gap: 5 },
};

export function Badge({ variant = 'neutral', size = 'sm', icon, children, style }: BadgeProps) {
  const colors = variant !== 'custom' ? colorMap[variant] : undefined;

  const badgeStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    borderRadius: 'var(--radius-sm)',
    lineHeight: 1,
    whiteSpace: 'nowrap',
    ...(colors
      ? { backgroundColor: colors.bg, border: `1px solid ${colors.border}`, color: colors.text }
      : {}),
    ...sizeStyles[size],
    ...style,
  };

  return (
    <span style={badgeStyle}>
      {icon && <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>}
      {children}
    </span>
  );
}
