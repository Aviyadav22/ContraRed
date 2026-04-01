import { type ReactNode, type CSSProperties } from 'react';

type CardVariant = 'default' | 'elevated' | 'interactive';
type CardPadding = 'compact' | 'standard' | 'spacious';

interface CardProps {
  variant?: CardVariant;
  padding?: CardPadding;
  header?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
}

const paddingMap: Record<CardPadding, string> = {
  compact: '12px 16px',
  standard: '16px 20px',
  spacious: '20px 24px',
};

const variantBaseStyles: Record<CardVariant, CSSProperties> = {
  default: {},
  elevated: { boxShadow: 'var(--shadow-md)' },
  interactive: {},
};

export function Card({ variant = 'default', padding = 'standard', header, footer, children, style, className }: CardProps) {
  const isInteractive = variant === 'interactive';

  const containerStyle: CSSProperties = {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
    transition: 'all var(--transition-fast)',
    ...variantBaseStyles[variant],
    ...style,
  };

  const handleMouseEnter = isInteractive
    ? (e: React.MouseEvent<HTMLDivElement>) => {
        e.currentTarget.style.borderColor = 'var(--accent)';
        e.currentTarget.style.boxShadow = '0 0 12px var(--accent-glow)';
      }
    : undefined;

  const handleMouseLeave = isInteractive
    ? (e: React.MouseEvent<HTMLDivElement>) => {
        e.currentTarget.style.borderColor = 'var(--border)';
        e.currentTarget.style.boxShadow = '';
      }
    : undefined;

  const pad = paddingMap[padding];

  return (
    <div
      style={containerStyle}
      className={className}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {header && (
        <div style={{ padding: pad, borderBottom: '1px solid var(--border)' }}>
          {header}
        </div>
      )}
      <div style={{ padding: pad }}>{children}</div>
      {footer && (
        <div style={{ padding: pad, borderTop: '1px solid var(--border)' }}>
          {footer}
        </div>
      )}
    </div>
  );
}
