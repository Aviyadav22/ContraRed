import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface PlaybookCardsProps {
  className?: string
}

const playbooks = [
  'NDA Mutual',
  'NDA Unilateral',
  'MSA',
  'SaaS',
  'Vendor',
  'Employment',
  'Lease',
  'Consulting',
  'DPA',
  'Joint Venture',
]

export default function PlaybookCards({ className = '' }: PlaybookCardsProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cardsRef = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const cards = cardsRef.current.filter(Boolean) as HTMLDivElement[]

    // Start stacked
    cards.forEach((card) => {
      gsap.set(card, {
        rotateZ: 0,
        x: 0,
        y: 0,
        opacity: 1,
      })
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 70%',
        end: 'bottom 40%',
        scrub: 0.5,
      },
    })

    // Fan out with rotation stagger
    const mid = (cards.length - 1) / 2
    cards.forEach((card, i) => {
      const offset = i - mid
      tl.to(
        card,
        {
          rotateZ: offset * 6,
          x: offset * 48,
          y: Math.abs(offset) * -8,
          duration: 1,
          ease: 'power2.out',
        },
        0
      )
    })

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`relative flex justify-center items-center py-16 ${className}`}>
      <div className="relative" style={{ width: 200, height: 140 }}>
        {playbooks.map((name, i) => (
          <div
            key={name}
            ref={(el) => { cardsRef.current[i] = el }}
            className="absolute inset-0 rounded-lg border px-4 py-5 flex flex-col justify-between"
            style={{
              backgroundColor: '#111111',
              borderColor: '#1E1E1E',
              borderTopColor: '#C5A880',
              borderTopWidth: 3,
              zIndex: playbooks.length - i,
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            }}
          >
            <div
              className="text-xs font-mono tracking-wide"
              style={{ color: '#C5A880' }}
            >
              {name}
            </div>
            <div
              className="text-xs"
              style={{ color: '#6B6B6B' }}
            >
              Playbook
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
