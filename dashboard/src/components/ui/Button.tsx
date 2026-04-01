import { forwardRef, type ButtonHTMLAttributes, type ReactNode, type CSSProperties } from 'react';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
}

const sizeStyles: Record<ButtonSize, CSSProperties> = {
  sm: { height: 32, padding: '0 12px', fontSize: 13, gap: 6 },
  md: { height: 36, padding: '0 16px', fontSize: 14, gap: 8 },
  lg: { height: 40, padding: '0 20px', fontSize: 14, gap: 8 },
};

const variantStyles: Record<ButtonVariant, CSSProperties> = {
  primary: {
    backgroundColor: 'var(--accent)',
    color: '#FFFFFF',
    border: '1px solid transparent',
  },
  secondary: {
    backgroundColor: 'transparent',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-strong)',
  },
  ghost: {
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid transparent',
  },
  danger: {
    backgroundColor: 'transparent',
    color: 'var(--risk-critical)',
    border: '1px solid var(--risk-critical-border)',
  },
};

const variantHoverStyles: Record<ButtonVariant, CSSProperties> = {
  primary: {
    backgroundColor: 'var(--accent-hover)',
    boxShadow: '0 0 12px var(--accent-glow)',
  },
  secondary: { backgroundColor: 'var(--bg-hover)' },
  ghost: { backgroundColor: 'var(--bg-hover)' },
  danger: { backgroundColor: 'var(--risk-critical-bg)' },
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, disabled, children, style, onMouseEnter, onMouseLeave, ...rest }, ref) => {
    const isDisabled = disabled || loading;

    const baseStyle: CSSProperties = {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 500,
      borderRadius: 'var(--radius-sm)',
      cursor: isDisabled ? 'not-allowed' : 'pointer',
      opacity: isDisabled ? 0.5 : 1,
      transition: 'all var(--transition-fast)',
      whiteSpace: 'nowrap',
      fontFamily: 'var(--font-sans)',
      lineHeight: 1,
      userSelect: 'none',
      ...sizeStyles[size],
      ...variantStyles[variant],
      ...style,
    };

    const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!isDisabled) {
        const hoverS = variantHoverStyles[variant];
        Object.assign(e.currentTarget.style, hoverS);
      }
      onMouseEnter?.(e);
    };

    const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
      // Reset hover styles
      const base = variantStyles[variant];
      e.currentTarget.style.backgroundColor = (base.backgroundColor as string) || '';
      e.currentTarget.style.boxShadow = '';
      onMouseLeave?.(e);
    };

    const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (!isDisabled) {
        e.currentTarget.style.transform = 'scale(0.98)';
      }
    };

    const handleMouseUp = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.currentTarget.style.transform = '';
    };

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        style={baseStyle}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        {...rest}
      >
        {loading ? (
          <Loader2 size={size === 'sm' ? 14 : 16} style={{ animation: 'spin 1s linear infinite' }} />
        ) : icon ? (
          icon
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
