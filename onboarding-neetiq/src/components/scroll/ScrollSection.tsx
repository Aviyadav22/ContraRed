import { useEffect, useRef, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface ScrollSectionProps {
  children: ReactNode
  pin?: boolean
  scrub?: boolean | number
  className?: string
  onEnter?: () => void
  onLeave?: () => void
}

export default function ScrollSection({
  children,
  pin = false,
  scrub = false,
  className = '',
  onEnter,
  onLeave,
}: ScrollSectionProps) {
  const ref = useRef<HTMLDivElement>(null)
  const onEnterRef = useRef(onEnter)
  const onLeaveRef = useRef(onLeave)
  onEnterRef.current = onEnter
  onLeaveRef.current = onLeave

  useEffect(() => {
    if (!ref.current) return

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 80%',
      end: pin ? '+=100%' : 'bottom 20%',
      pin: pin ? ref.current : false,
      scrub: scrub,
      onEnter: () => onEnterRef.current?.(),
      onLeave: () => onLeaveRef.current?.(),
    })

    // Animate .reveal-child elements (only if below the fold)
    const el = ref.current
    const revealChildren = el.querySelectorAll('.reveal-child')
    let revealTrigger: ScrollTrigger | null = null

    let raf: number | null = null
    if (revealChildren.length > 0) {
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect()
        if (rect.top > window.innerHeight) {
          gsap.set(revealChildren, { opacity: 0, y: 30 })
          revealTrigger = ScrollTrigger.create({
            trigger: el,
            start: 'top 80%',
            once: true,
            onEnter: () => {
              gsap.to(revealChildren, { opacity: 1, y: 0, duration: 0.6, stagger: 0.12, ease: 'power2.out' })
            },
          })
        }
      })
    }

    return () => {
      if (raf) cancelAnimationFrame(raf)
      trigger.kill()
      revealTrigger?.kill()
      revealChildren.forEach((c) => gsap.killTweensOf(c))
    }
  }, [pin, scrub])

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  )
}
