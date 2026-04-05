import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface CounterRevealProps {
  target: number
  prefix?: string
  suffix?: string
  duration?: number
  className?: string
}

export default function CounterReveal({
  target,
  prefix = '',
  suffix = '',
  duration = 2,
  className = '',
}: CounterRevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [value, setValue] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const obj = { val: 0 }
    let trigger: ScrollTrigger | null = null

    function startCount() {
      gsap.to(obj, {
        val: target,
        duration,
        ease: 'expo.out',
        onUpdate: () => setValue(Math.round(obj.val)),
      })
    }

    const raf = requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect()
      if (rect.top > window.innerHeight) {
        // Below fold — animate on scroll
        trigger = ScrollTrigger.create({
          trigger: el,
          start: 'top 85%',
          onEnter: startCount,
          once: true,
        })
      } else {
        // Already visible — start counting immediately
        startCount()
      }
    })

    return () => {
      cancelAnimationFrame(raf)
      trigger?.kill()
      gsap.killTweensOf(obj)
    }
  }, [target, duration])

  return (
    <div ref={ref} className={`font-mono text-gold ${className}`}>
      <span className="text-text-muted text-sm">{prefix}</span>
      <span className="text-5xl font-bold tabular-nums">{value.toLocaleString()}</span>
      <span className="text-text-muted text-sm">{suffix}</span>
    </div>
  )
}
