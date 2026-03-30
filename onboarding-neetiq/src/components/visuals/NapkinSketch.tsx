import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import rough from 'roughjs'

gsap.registerPlugin(ScrollTrigger)

interface NapkinSketchProps {
  className?: string
}

export default function NapkinSketch({ className = '' }: NapkinSketchProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const svgCleanRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const svgClean = svgCleanRef.current
    const container = containerRef.current
    if (!canvas || !svgClean || !container) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const w = canvas.width
    const h = canvas.height
    const rc = rough.canvas(canvas)

    // Clear canvas
    ctx.clearRect(0, 0, w, h)

    // Define box positions
    const boxes = [
      { x: 40, y: 80, w: 160, h: 60, label: 'Contract Input' },
      { x: 280, y: 80, w: 160, h: 60, label: 'Regex Engine' },
      { x: 520, y: 80, w: 160, h: 60, label: 'Risk Output' },
    ]

    // Define arrows
    const arrows = [
      { x1: 200, y1: 110, x2: 280, y2: 110 },
      { x1: 440, y1: 110, x2: 520, y2: 110 },
    ]

    // Hide clean SVG initially
    gsap.set(svgClean, { opacity: 0 })

    // Draw stroke-by-stroke on scroll
    const drawElements: (() => void)[] = []

    // Each box draw function
    boxes.forEach((box) => {
      drawElements.push(() => {
        rc.rectangle(box.x, box.y, box.w, box.h, {
          stroke: '#C5A880',
          strokeWidth: 1.5,
          roughness: 2.5,
          fill: 'rgba(197,168,128,0.05)',
          fillStyle: 'hachure',
        })
        ctx.font = '16px Caveat, cursive'
        ctx.fillStyle = '#C5A880'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(box.label, box.x + box.w / 2, box.y + box.h / 2)
      })
    })

    // Each arrow draw function
    arrows.forEach((arrow) => {
      drawElements.push(() => {
        rc.line(arrow.x1, arrow.y1, arrow.x2, arrow.y2, {
          stroke: '#C5A880',
          strokeWidth: 1.5,
          roughness: 2,
        })
        // Arrowhead
        rc.line(arrow.x2 - 12, arrow.y1 - 8, arrow.x2, arrow.y2, {
          stroke: '#C5A880',
          strokeWidth: 1.5,
          roughness: 1.5,
        })
        rc.line(arrow.x2 - 12, arrow.y1 + 8, arrow.x2, arrow.y2, {
          stroke: '#C5A880',
          strokeWidth: 1.5,
          roughness: 1.5,
        })
      })
    })

    // Animate drawing step by step
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 80%',
      },
    })

    // Clear canvas first, then draw each element with delay
    ctx.clearRect(0, 0, w, h)
    drawElements.forEach((drawFn, i) => {
      tl.call(drawFn, undefined, i * 0.4)
    })

    // After hand-drawn, morph into clean SVG
    tl.to(canvas, { opacity: 0, duration: 0.6 }, '+=0.8')
    tl.to(svgClean, { opacity: 1, duration: 0.6 }, '<')

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        className="rounded-lg overflow-hidden"
        style={{ backgroundColor: '#161616' }}
      >
        {/* Hand-drawn canvas */}
        <canvas
          ref={canvasRef}
          width={720}
          height={220}
          className="w-full h-auto"
        />

        {/* Clean geometric SVG version */}
        <div
          ref={svgCleanRef}
          className="absolute inset-0 flex items-center justify-center"
        >
          <svg
            viewBox="0 0 720 220"
            className="w-full h-auto"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Contract Input box */}
            <rect
              x="40"
              y="80"
              width="160"
              height="60"
              rx="8"
              stroke="#C5A880"
              strokeWidth="1.5"
              fill="rgba(197,168,128,0.08)"
            />
            <text
              x="120"
              y="114"
              textAnchor="middle"
              fill="#C5A880"
              fontFamily="Inter, sans-serif"
              fontSize="14"
            >
              Contract Input
            </text>

            {/* Arrow 1 */}
            <line
              x1="200"
              y1="110"
              x2="270"
              y2="110"
              stroke="#C5A880"
              strokeWidth="1.5"
            />
            <polygon points="280,110 268,104 268,116" fill="#C5A880" />

            {/* Regex Engine box */}
            <rect
              x="280"
              y="80"
              width="160"
              height="60"
              rx="8"
              stroke="#C5A880"
              strokeWidth="1.5"
              fill="rgba(197,168,128,0.08)"
            />
            <text
              x="360"
              y="114"
              textAnchor="middle"
              fill="#C5A880"
              fontFamily="Inter, sans-serif"
              fontSize="14"
            >
              Regex Engine
            </text>

            {/* Arrow 2 */}
            <line
              x1="440"
              y1="110"
              x2="510"
              y2="110"
              stroke="#C5A880"
              strokeWidth="1.5"
            />
            <polygon points="520,110 508,104 508,116" fill="#C5A880" />

            {/* Risk Output box */}
            <rect
              x="520"
              y="80"
              width="160"
              height="60"
              rx="8"
              stroke="#C5A880"
              strokeWidth="1.5"
              fill="rgba(197,168,128,0.08)"
            />
            <text
              x="600"
              y="114"
              textAnchor="middle"
              fill="#C5A880"
              fontFamily="Inter, sans-serif"
              fontSize="14"
            >
              Risk Output
            </text>
          </svg>
        </div>
      </div>
    </div>
  )
}
