import type { CSSProperties } from 'react'

interface ParticleFlowProps {
  direction?: 'left' | 'right' | 'up' | 'down'
  count?: number
  className?: string
}

const directionMap: Record<string, { x1: string; y1: string; x2: string; y2: string }> = {
  right: { x1: '-10%', y1: '0%', x2: '110%', y2: '0%' },
  left:  { x1: '110%', y1: '0%', x2: '-10%', y2: '0%' },
  down:  { x1: '0%', y1: '-10%', x2: '0%', y2: '110%' },
  up:    { x1: '0%', y1: '110%', x2: '0%', y2: '-10%' },
}

export default function ParticleFlow({
  direction = 'right',
  count = 20,
  className = '',
}: ParticleFlowProps) {
  const dir = directionMap[direction]
  const isHorizontal = direction === 'left' || direction === 'right'

  const particles = Array.from({ length: count }, (_, i) => {
    const delay = (i / count) * 4
    const duration = 3 + Math.random() * 2
    const offset = Math.random() * 100
    const size = 2 + Math.random() * 3
    const opacity = 0.3 + Math.random() * 0.5

    const style: CSSProperties = {
      position: 'absolute',
      width: size,
      height: size,
      borderRadius: '50%',
      backgroundColor: '#C5A880',
      opacity,
      animation: `particle-flow-${direction} ${duration}s linear ${delay}s infinite`,
      ...(isHorizontal
        ? { top: `${offset}%`, left: dir.x1 }
        : { left: `${offset}%`, top: dir.y1 }),
    }

    return <div key={i} style={style} />
  })

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <style>{`
        @keyframes particle-flow-right {
          from { transform: translateX(0); opacity: 0; }
          10% { opacity: var(--particle-opacity, 0.5); }
          90% { opacity: var(--particle-opacity, 0.5); }
          to { transform: translateX(calc(110vw)); opacity: 0; }
        }
        @keyframes particle-flow-left {
          from { transform: translateX(0); opacity: 0; }
          10% { opacity: var(--particle-opacity, 0.5); }
          90% { opacity: var(--particle-opacity, 0.5); }
          to { transform: translateX(calc(-110vw)); opacity: 0; }
        }
        @keyframes particle-flow-down {
          from { transform: translateY(0); opacity: 0; }
          10% { opacity: var(--particle-opacity, 0.5); }
          90% { opacity: var(--particle-opacity, 0.5); }
          to { transform: translateY(110vh); opacity: 0; }
        }
        @keyframes particle-flow-up {
          from { transform: translateY(0); opacity: 0; }
          10% { opacity: var(--particle-opacity, 0.5); }
          90% { opacity: var(--particle-opacity, 0.5); }
          to { transform: translateY(-110vh); opacity: 0; }
        }
      `}</style>
      {particles}
    </div>
  )
}
