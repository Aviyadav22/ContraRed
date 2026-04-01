import { type CSSProperties } from 'react';

type SkeletonVariant = 'text' | 'card' | 'stat' | 'row' | 'avatar';

interface SkeletonProps {
  variant?: SkeletonVariant;
  width?: number | string;
  height?: number | string;
  count?: number;
  style?: CSSProperties;
}

const variantDefaults: Record<SkeletonVariant, { height: number | string; width: number | string; borderRadius: string }> = {
  text: { height: 14, width: '100%', borderRadius: 'var(--radius-sm)' },
  card: { height: 120, width: '100%', borderRadius: 'var(--radius-lg)' },
  stat: { height: 88, width: '100%', borderRadius: 'var(--radius-lg)' },
  row: { height: 44, width: '100%', borderRadius: 'var(--radius-sm)' },
  avatar: { height: 36, width: 36, borderRadius: '50%' },
};

export function Skeleton({ variant = 'text', width, height, count, style }: SkeletonProps) {
  const defaults = variantDefaults[variant];

  const baseStyle: CSSProperties = {
    backgroundColor: 'var(--bg-elevated)',
    backgroundImage: 'linear-gradient(90deg, transparent 0%, var(--bg-hover) 50%, transparent 100%)',
    backgroundSize: '200px 100%',
    backgroundRepeat: 'no-repeat',
    animation: 'shimmer 1.4s infinite',
    height: height ?? defaults.height,
    width: width ?? defaults.width,
    borderRadius: defaults.borderRadius,
    ...style,
  };

  if (count && count > 1) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            style={{
              ...baseStyle,
              width: i === count - 1 ? '75%' : (width ?? defaults.width),
            }}
          />
        ))}
      </div>
    );
  }

  return <div style={baseStyle} />;
}
