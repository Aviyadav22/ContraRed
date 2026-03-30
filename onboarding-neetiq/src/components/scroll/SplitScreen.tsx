import { useEffect, useRef, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface SplitScreenProps {
  left: ReactNode
  right: ReactNode
  leftLabel?: string
  rightLabel?: string
  leftFade?: boolean
  rightGlow?: boolean
  className?: string
}

export default function SplitScreen({
  left,
  right,
  leftLabel,
  rightLabel,
  leftFade = false,
  rightGlow = false,
  className = '',
}: SplitScreenProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const leftEl = ref.current.querySelector('.split-left')
    const rightEl = ref.current.querySelector('.split-right')

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 75%',
      },
    })

    tl.fromTo(leftEl, { x: -50, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6 })
    tl.fromTo(rightEl, { x: 50, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6 }, '<0.2')

    if (leftFade) {
      tl.to(leftEl, { opacity: 0.3, scale: 0.95, duration: 0.8, delay: 0.5 })
    }
    if (rightGlow) {
      tl.to(rightEl, {
        boxShadow: '0 0 30px rgba(197, 168, 128, 0.3)',
        borderColor: '#C5A880',
        duration: 0.8,
      }, '<')
    }
  }, [leftFade, rightGlow])

  return (
    <div ref={ref} className={`grid grid-cols-2 gap-6 ${className}`}>
      <div className="split-left bg-surface border border-border rounded-lg p-6">
        {leftLabel && <div className="text-text-muted font-mono text-xs uppercase tracking-widest mb-3">{leftLabel}</div>}
        {left}
      </div>
      <div className="split-right bg-surface border border-border rounded-lg p-6">
        {rightLabel && <div className="text-gold font-mono text-xs uppercase tracking-widest mb-3">{rightLabel}</div>}
        {right}
      </div>
    </div>
  )
}
