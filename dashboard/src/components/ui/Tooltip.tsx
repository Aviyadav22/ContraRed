import { useState, useRef, useCallback, type ReactNode, type CSSProperties } from 'react';

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: string;
  position?: TooltipPosition;
  children: ReactNode;
}

const positionStyles: Record<TooltipPosition, CSSProperties> = {
  top: { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: 6 },
  bottom: { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 6 },
  left: { right: '100%', top: '50%', transform: 'translateY(-50%)', marginRight: 6 },
  right: { left: '100%', top: '50%', transform: 'translateY(-50%)', marginLeft: 6 },
};

export function Tooltip({ content, position = 'top', children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const show = useCallback(() => {
    timerRef.current = setTimeout(() => setVisible(true), 300);
  }, []);

  const hide = useCallback(() => {
    clearTimeout(timerRef.current);
    setVisible(false);
  }, []);

  const wrapperStyle: CSSProperties = {
    position: 'relative',
    display: 'inline-flex',
  };

  const tipStyle: CSSProperties = {
    position: 'absolute',
    padding: '6px 10px',
    fontSize: 12,
    fontWeight: 500,
    color: '#F8FAFC',
    backgroundColor: '#1E293B',
    borderRadius: 'var(--radius-sm)',
    boxShadow: 'var(--shadow-md)',
    animation: 'fadeIn 0.15s ease-out',
    zIndex: 1100,
    pointerEvents: 'none',
    whiteSpace: 'nowrap',
    ...positionStyles[position],
  };

  return (
    <div style={wrapperStyle} onMouseEnter={show} onMouseLeave={hide}>
      {children}
      {visible && <div style={tipStyle}>{content}</div>}
    </div>
  );
}
