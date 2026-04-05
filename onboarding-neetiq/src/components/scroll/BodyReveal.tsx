import { useEffect, useRef, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface BodyRevealProps {
  children: ReactNode
  className?: string
}

export default function BodyReveal({ children, className = '' }: BodyRevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    let trigger: ScrollTrigger | null = null

    // Wait one frame so layout is settled and getBoundingClientRect is accurate
    const raf = requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect()
      if (rect.top > window.innerHeight) {
        // Below the fold — hide and animate on scroll
        gsap.set(el, { opacity: 0, y: 30 })
        trigger = ScrollTrigger.create({
          trigger: el,
          start: 'top 90%',
          once: true,
          onEnter: () => gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }),
        })
      }
      // Already visible — leave it alone, no animation needed
    })

    return () => {
      cancelAnimationFrame(raf)
      trigger?.kill()
      gsap.killTweensOf(el)
    }
  }, [])

  return (
    <div ref={ref} className={`text-text-primary leading-relaxed ${className}`}>
      {children}
    </div>
  )
}
