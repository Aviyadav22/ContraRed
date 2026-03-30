import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface ScoreCardProps {
  className?: string
}

const scores = [
  { label: 'Technical', value: 7.5, max: 10 },
  { label: 'Business', value: 7, max: 10 },
  { label: 'Legal', value: 6, max: 10 },
]

export default function ScoreCard({ className = '' }: ScoreCardProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const barsRef = useRef<(HTMLDivElement | null)[]>([])
  const valuesRef = useRef<(HTMLSpanElement | null)[]>([])
  const verdictRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const verdict = verdictRef.current
    if (!container || !verdict) return

    // Set initial states
    barsRef.current.forEach((bar) => {
      if (bar) gsap.set(bar, { width: '0%' })
    })
    valuesRef.current.forEach((val) => {
      if (val) gsap.set(val, { opacity: 0 })
    })
    gsap.set(verdict, { opacity: 0 })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 75%',
      },
    })

    // Animate bars
    scores.forEach((score, i) => {
      const bar = barsRef.current[i]
      const val = valuesRef.current[i]
      const pct = (score.value / score.max) * 100

      if (bar) {
        tl.to(
          bar,
          { width: `${pct}%`, duration: 0.8, ease: 'power2.out' },
          i * 0.2
        )
      }
      if (val) {
        tl.to(val, { opacity: 1, duration: 0.3 }, i * 0.2 + 0.5)
      }
    })

    // Typewriter verdict
    tl.call(
      () => {
        gsap.set(verdict, { opacity: 1 })
        const text = 'CONDITIONAL GO'
        let charIndex = 0
        const type = () => {
          if (charIndex <= text.length) {
            verdict.textContent = text.slice(0, charIndex)
            charIndex++
            setTimeout(type, 60)
          }
        }
        type()
      },
      undefined,
      '+=0.3'
    )

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`${className}`}>
      <div
        className="rounded-lg border p-6"
        style={{ backgroundColor: '#111111', borderColor: '#1E1E1E' }}
      >
        <div className="space-y-4">
          {scores.map((score, i) => (
            <div key={score.label} className="flex items-center gap-4">
              {/* Label */}
              <div
                className="w-20 text-xs font-mono shrink-0"
                style={{ color: '#6B6B6B' }}
              >
                {score.label}
              </div>

              {/* Bar track */}
              <div
                className="flex-1 h-6 rounded-sm overflow-hidden"
                style={{ backgroundColor: '#1A1A1A' }}
              >
                <div
                  ref={(el) => { barsRef.current[i] = el }}
                  className="h-full rounded-sm"
                  style={{ backgroundColor: '#C5A880' }}
                />
              </div>

              {/* Value */}
              <span
                ref={(el) => { valuesRef.current[i] = el }}
                className="w-12 text-right text-sm font-mono"
                style={{ color: '#C5A880' }}
              >
                {score.value}/{score.max}
              </span>
            </div>
          ))}
        </div>

        {/* Verdict */}
        <div className="mt-6 pt-4 border-t" style={{ borderColor: '#1E1E1E' }}>
          <div
            ref={verdictRef}
            className="text-lg font-mono tracking-widest text-center"
            style={{ color: '#EAB308', minHeight: '1.75rem' }}
          />
        </div>
      </div>
    </div>
  )
}
