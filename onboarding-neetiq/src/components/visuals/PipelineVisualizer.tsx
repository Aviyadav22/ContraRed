import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface PipelineVisualizerProps {
  className?: string
}

const stages = [
  { name: 'EXTRACT', subtitle: 'parse', color: '#C5A880' },
  { name: 'CLASSIFY', subtitle: 'detect', color: '#8B7355' },
  { name: 'ASSESS', subtitle: 'AI', color: '#C5A880' },
  { name: 'VERIFY', subtitle: 'check', color: '#8B7355' },
  { name: 'ENRICH', subtitle: 'score', color: '#C5A880' },
]

export default function PipelineVisualizer({ className = '' }: PipelineVisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const orbRef = useRef<HTMLDivElement>(null)
  const labelsRef = useRef<(HTMLDivElement | null)[]>([])
  const particlesRef = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const container = containerRef.current
    const orb = orbRef.current
    if (!container || !orb) return

    // Hide labels and particles initially
    labelsRef.current.forEach((el) => {
      if (el) gsap.set(el, { opacity: 0, y: 10 })
    })
    particlesRef.current.forEach((el) => {
      if (el) gsap.set(el, { opacity: 0, scale: 0 })
    })

    // Calculate orb path
    const chambers = container.querySelectorAll<HTMLElement>('[data-chamber]')
    if (chambers.length === 0) return

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 60%',
        end: 'bottom 40%',
        scrub: 1,
      },
    })

    // Move orb through each chamber
    chambers.forEach((_, i) => {
      const position = i / (chambers.length - 1)
      const xPercent = position * 100

      tl.to(
        orb,
        {
          left: `${xPercent}%`,
          duration: 1,
          ease: 'none',
        },
        i * 1
      )

      // Show label when orb enters
      const label = labelsRef.current[i]
      if (label) {
        tl.to(
          label,
          { opacity: 1, y: 0, duration: 0.3 },
          i * 1 + 0.2
        )
      }

      // Show particles at boundary
      const particle = particlesRef.current[i]
      if (particle) {
        tl.to(
          particle,
          { opacity: 1, scale: 1, duration: 0.3 },
          i * 1 + 0.5
        )
        tl.to(
          particle,
          { opacity: 0, scale: 0.5, duration: 0.3 },
          i * 1 + 0.8
        )
      }
    })

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Pipeline track */}
      <div className="relative flex items-center gap-2 py-12">
        {/* Connection line */}
        <div
          className="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2"
          style={{ backgroundColor: '#1E1E1E' }}
        />

        {/* Glowing orb */}
        <div
          ref={orbRef}
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 rounded-full"
          style={{
            width: 20,
            height: 20,
            backgroundColor: '#C5A880',
            boxShadow: '0 0 20px rgba(197,168,128,0.6), 0 0 40px rgba(197,168,128,0.3)',
            left: '0%',
          }}
        />

        {/* Chambers */}
        {stages.map((stage, i) => (
          <div
            key={stage.name}
            data-chamber
            className="relative flex-1 flex flex-col items-center"
          >
            {/* Chamber box */}
            <div
              className="w-full rounded-lg border px-4 py-6 flex items-center justify-center"
              style={{
                borderColor: stage.color,
                backgroundColor: '#111111',
                minHeight: 80,
              }}
            >
              {/* Particles at boundary */}
              <div
                ref={(el) => { particlesRef.current[i] = el }}
                className="absolute -right-1 top-1/2 -translate-y-1/2"
              >
                {[0, 1, 2].map((p) => (
                  <div
                    key={p}
                    className="absolute rounded-full"
                    style={{
                      width: 4,
                      height: 4,
                      backgroundColor: stage.color,
                      top: (p - 1) * 8,
                      right: p * 3,
                      opacity: 0.7,
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Label below */}
            <div
              ref={(el) => { labelsRef.current[i] = el }}
              className="mt-3 text-center"
            >
              <div
                className="text-xs font-mono tracking-widest"
                style={{ color: stage.color }}
              >
                {stage.name}
              </div>
              <div
                className="text-xs mt-0.5"
                style={{ color: '#6B6B6B' }}
              >
                {stage.subtitle}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
