import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface ArchitectureDiagramProps {
  className?: string
}

export default function ArchitectureDiagram({ className = '' }: ArchitectureDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const svg = svgRef.current
    if (!container || !svg) return

    // Self-drawing paths
    const paths = svg.querySelectorAll<SVGPathElement | SVGLineElement | SVGRectElement>(
      'path, line, rect.draw'
    )
    paths.forEach((el) => {
      if (el instanceof SVGGeometryElement) {
        const length = el.getTotalLength()
        gsap.set(el, { strokeDasharray: length, strokeDashoffset: length })
      }
    })

    // Labels hidden
    const labels = svg.querySelectorAll<SVGTextElement>('text')
    gsap.set(labels, { opacity: 0 })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 70%',
      },
    })

    // Draw paths
    tl.to(paths, {
      strokeDashoffset: 0,
      duration: 1.2,
      ease: 'power2.inOut',
      stagger: 0.15,
    })

    // Fade in labels
    tl.to(labels, {
      opacity: 1,
      duration: 0.4,
      stagger: 0.08,
    }, '-=0.3')

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`${className}`}>
      <svg
        ref={svgRef}
        viewBox="0 0 600 400"
        className="w-full h-auto"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Layer 1: User World */}
        <rect
          className="draw"
          x="30"
          y="20"
          width="540"
          height="90"
          rx="8"
          stroke="#C5A880"
          strokeWidth="1"
          fill="none"
        />
        <text x="50" y="45" fill="#6B6B6B" fontSize="10" fontFamily="Inter, sans-serif">
          USER WORLD
        </text>

        {/* Word Add-in */}
        <rect
          className="draw"
          x="60"
          y="55"
          width="120"
          height="40"
          rx="6"
          stroke="#C5A880"
          strokeWidth="1"
          fill="none"
        />
        <text x="120" y="80" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Word Add-in
        </text>

        {/* Dashboard */}
        <rect
          className="draw"
          x="220"
          y="55"
          width="120"
          height="40"
          rx="6"
          stroke="#C5A880"
          strokeWidth="1"
          fill="none"
        />
        <text x="280" y="80" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Dashboard
        </text>

        {/* Layer 2: Backend */}
        <rect
          className="draw"
          x="30"
          y="140"
          width="540"
          height="120"
          rx="8"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="50" y="165" fill="#6B6B6B" fontSize="10" fontFamily="Inter, sans-serif">
          BACKEND
        </text>

        {/* FastAPI */}
        <rect
          className="draw"
          x="60"
          y="175"
          width="120"
          height="40"
          rx="6"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="120" y="200" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          FastAPI
        </text>

        {/* Pipeline */}
        <rect
          className="draw"
          x="220"
          y="175"
          width="160"
          height="40"
          rx="6"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="300" y="200" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Analysis Pipeline
        </text>

        {/* Playbook Engine */}
        <rect
          className="draw"
          x="420"
          y="175"
          width="130"
          height="40"
          rx="6"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="485" y="200" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Playbooks
        </text>

        {/* Layer 3: Data */}
        <rect
          className="draw"
          x="30"
          y="290"
          width="540"
          height="90"
          rx="8"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="50" y="315" fill="#6B6B6B" fontSize="10" fontFamily="Inter, sans-serif">
          DATA LAYER
        </text>

        {/* Supabase */}
        <rect
          className="draw"
          x="60"
          y="325"
          width="120"
          height="40"
          rx="6"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="120" y="350" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Supabase
        </text>

        {/* Vertex AI */}
        <rect
          className="draw"
          x="220"
          y="325"
          width="120"
          height="40"
          rx="6"
          stroke="#8B7355"
          strokeWidth="1"
          fill="none"
        />
        <text x="280" y="350" textAnchor="middle" fill="#C5A880" fontSize="11" fontFamily="'JetBrains Mono', monospace">
          Vertex AI
        </text>

        {/* Connection arrows: User World → Backend */}
        <line className="draw" x1="120" y1="95" x2="120" y2="175" stroke="#C5A880" strokeWidth="1" />
        <line className="draw" x1="280" y1="95" x2="280" y2="175" stroke="#C5A880" strokeWidth="1" />

        {/* Arrowheads for down arrows */}
        <path className="draw" d="M115,170 L120,178 L125,170" stroke="#C5A880" strokeWidth="1" fill="none" />
        <path className="draw" d="M275,170 L280,178 L285,170" stroke="#C5A880" strokeWidth="1" fill="none" />

        {/* Connection arrows: Backend → Data */}
        <line className="draw" x1="120" y1="215" x2="120" y2="325" stroke="#8B7355" strokeWidth="1" />
        <line className="draw" x1="300" y1="215" x2="280" y2="325" stroke="#8B7355" strokeWidth="1" />

        {/* Arrowheads for down arrows */}
        <path className="draw" d="M115,320 L120,328 L125,320" stroke="#8B7355" strokeWidth="1" fill="none" />
        <path className="draw" d="M275,320 L280,328 L285,320" stroke="#8B7355" strokeWidth="1" fill="none" />

        {/* Horizontal connections in backend */}
        <line className="draw" x1="180" y1="195" x2="220" y2="195" stroke="#8B7355" strokeWidth="1" />
        <line className="draw" x1="380" y1="195" x2="420" y2="195" stroke="#8B7355" strokeWidth="1" />

        <path className="draw" d="M216,190 L222,195 L216,200" stroke="#8B7355" strokeWidth="1" fill="none" />
        <path className="draw" d="M416,190 L422,195 L416,200" stroke="#8B7355" strokeWidth="1" fill="none" />
      </svg>
    </div>
  )
}
