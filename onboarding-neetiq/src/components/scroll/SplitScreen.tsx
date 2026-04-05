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
    const el = ref.current
    if (!el) return

    const leftEl = el.querySelector('.split-left')
    const rightEl = el.querySelector('.split-right')
    let trigger: ScrollTrigger | null = null

    const raf = requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect()
      if (rect.top > window.innerHeight) {
        // Below the fold — hide and animate on scroll
        if (leftEl) gsap.set(leftEl, { x: -50, opacity: 0 })
        if (rightEl) gsap.set(rightEl, { x: 50, opacity: 0 })

        trigger = ScrollTrigger.create({
          trigger: el,
          start: 'top 75%',
          once: true,
          onEnter: () => {
            const tl = gsap.timeline()
            tl.to(leftEl, { x: 0, opacity: 1, duration: 0.6 })
            tl.to(rightEl, { x: 0, opacity: 1, duration: 0.6 }, '<0.2')
            if (leftFade) {
              tl.to(leftEl, { opacity: 0.3, scale: 0.95, duration: 0.8, delay: 0.5 })
            }
            if (rightGlow) {
              tl.to(rightEl, { boxShadow: '0 0 30px rgba(197,168,128,0.3)', borderColor: '#C5A880', duration: 0.8 }, '<')
            }
          },
        })
      }
    })

    return () => {
      cancelAnimationFrame(raf)
      trigger?.kill()
      if (leftEl) gsap.killTweensOf(leftEl)
      if (rightEl) gsap.killTweensOf(rightEl)
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
