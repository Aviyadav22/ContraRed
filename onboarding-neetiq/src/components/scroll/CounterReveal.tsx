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
    if (!ref.current) return

    const obj = { val: 0 }

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 85%',
      onEnter: () => {
        gsap.to(obj, {
          val: target,
          duration,
          ease: 'expo.out',
          onUpdate: () => setValue(Math.round(obj.val)),
        })
      },
      once: true,
    })

    return () => trigger.kill()
  }, [target, duration])

  return (
    <div ref={ref} className={`font-mono text-gold ${className}`}>
      <span className="text-text-muted text-sm">{prefix}</span>
      <span className="text-5xl font-bold tabular-nums">{value.toLocaleString()}</span>
      <span className="text-text-muted text-sm">{suffix}</span>
    </div>
  )
}
