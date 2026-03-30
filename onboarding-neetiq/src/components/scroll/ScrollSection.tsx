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

  useEffect(() => {
    if (!ref.current) return

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 80%',
      end: pin ? '+=100%' : 'bottom 20%',
      pin: pin ? ref.current : false,
      scrub: scrub,
      onEnter,
      onLeave,
    })

    // Animate children in
    const revealChildren = ref.current.querySelectorAll('.reveal-child')
    if (revealChildren.length > 0) {
      gsap.fromTo(
        revealChildren,
        { opacity: 0, y: 30 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.12,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: ref.current,
            start: 'top 80%',
          },
        }
      )
    }

    return () => {
      trigger.kill()
    }
  }, [pin, scrub, onEnter, onLeave])

  return (
    <div ref={ref} className={`min-h-[50vh] ${className}`}>
      {children}
    </div>
  )
}
