import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface DeploymentMapProps {
  className?: string
}

const nodes = [
  { id: 'render', label: 'Render', subtitle: 'Backend', x: 50, y: 10 },
  { id: 'dashboard', label: 'Netlify', subtitle: 'Dashboard', x: 90, y: 50 },
  { id: 'addin', label: 'Netlify', subtitle: 'Add-in', x: 10, y: 50 },
  { id: 'supabase', label: 'Supabase', subtitle: 'Database', x: 50, y: 90 },
]

const connections = [
  { from: 0, to: 1 },
  { from: 0, to: 2 },
  { from: 0, to: 3 },
  { from: 1, to: 3 },
  { from: 2, to: 3 },
]

export default function DeploymentMap({ className = '' }: DeploymentMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const nodeRefs = useRef<(HTMLDivElement | null)[]>([])
  const lineRefs = useRef<(SVGLineElement | null)[]>([])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Hide connections initially
    lineRefs.current.forEach((line) => {
      if (!line) return
      const length = line.getTotalLength()
      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length })
    })

    // Set initial node state
    nodeRefs.current.forEach((node) => {
      if (node) gsap.set(node, { scale: 0, opacity: 0 })
    })

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: container,
        start: 'top 70%',
      },
    })

    // Pop in nodes
    nodeRefs.current.forEach((node, i) => {
      if (!node) return
      tl.to(
        node,
        { scale: 1, opacity: 1, duration: 0.4, ease: 'back.out(1.7)' },
        i * 0.15
      )
    })

    // Draw connections
    lineRefs.current.forEach((line, i) => {
      if (!line) return
      tl.to(
        line,
        { strokeDashoffset: 0, duration: 0.5, ease: 'power2.inOut' },
        0.6 + i * 0.12
      )
    })

    // Disaster flash on Render node then resolve
    const renderNode = nodeRefs.current[0]
    if (renderNode) {
      tl.to(
        renderNode,
        { boxShadow: '0 0 20px rgba(220,38,38,0.8)', duration: 0.2 },
        '+=0.5'
      )
      tl.to(
        renderNode,
        { boxShadow: '0 0 20px rgba(220,38,38,0.8)', duration: 0.4 },
      )
      tl.to(
        renderNode,
        { boxShadow: '0 0 15px rgba(34,197,94,0.5)', duration: 0.3 },
      )
      tl.to(
        renderNode,
        { boxShadow: '0 0 8px rgba(197,168,128,0.3)', duration: 0.5 },
      )
    }

    return () => {
      tl.kill()
    }
  }, [])

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative" style={{ paddingBottom: '80%' }}>
        {/* SVG connections */}
        <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
          {connections.map((conn, i) => {
            const fromNode = nodes[conn.from]
            const toNode = nodes[conn.to]
            return (
              <line
                key={i}
                ref={(el) => { lineRefs.current[i] = el }}
                x1={`${fromNode.x}%`}
                y1={`${fromNode.y}%`}
                x2={`${toNode.x}%`}
                y2={`${toNode.y}%`}
                stroke="#C5A880"
                strokeWidth="1"
                opacity="0.5"
              />
            )
          })}
        </svg>

        {/* Nodes */}
        {nodes.map((node, i) => (
          <div
            key={node.id}
            ref={(el) => { nodeRefs.current[i] = el }}
            className="absolute flex flex-col items-center -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${node.x}%`, top: `${node.y}%`, zIndex: 1 }}
          >
            <div
              className="rounded-lg border px-4 py-3 text-center"
              style={{
                backgroundColor: '#111111',
                borderColor: '#1E1E1E',
                boxShadow: '0 0 8px rgba(197,168,128,0.3)',
              }}
            >
              <div
                className="text-xs font-mono font-bold"
                style={{ color: '#C5A880' }}
              >
                {node.label}
              </div>
              <div
                className="text-xs mt-0.5"
                style={{ color: '#6B6B6B' }}
              >
                {node.subtitle}
              </div>
            </div>

            {/* Pulse ring */}
            <div
              className="absolute inset-0 rounded-lg border animate-ping"
              style={{
                borderColor: 'rgba(197,168,128,0.2)',
                animationDuration: '3s',
              }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
