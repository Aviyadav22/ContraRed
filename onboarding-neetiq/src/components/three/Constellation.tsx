import { useRef, useState, useCallback } from 'react'
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { Line, Html } from '@react-three/drei'
import * as THREE from 'three'
import GoldParticles from './GoldParticles'

interface ArchNode {
  name: string
  position: THREE.Vector3
}

const NODES: ArchNode[] = [
  { name: 'Word Add-in', position: new THREE.Vector3(-2.5, 1.5, 0) },
  { name: 'React Dashboard', position: new THREE.Vector3(-1.5, 2.2, 0.5) },
  { name: 'API Gateway', position: new THREE.Vector3(0, 1.8, -0.3) },
  { name: 'Auth Service', position: new THREE.Vector3(1.5, 2, 0.4) },
  { name: 'FastAPI Backend', position: new THREE.Vector3(0, 0, 0) },
  { name: 'Vertex AI', position: new THREE.Vector3(2, 0.5, -0.5) },
  { name: 'Gemini Analyzer', position: new THREE.Vector3(2.5, -0.5, 0.3) },
  { name: 'Playbook Engine', position: new THREE.Vector3(1, -1, -0.8) },
  { name: 'PostgreSQL', position: new THREE.Vector3(-1, -1.5, 0) },
  { name: 'Redis Cache', position: new THREE.Vector3(-2, -0.5, 0.5) },
  { name: 'Supabase', position: new THREE.Vector3(-1.5, -2.2, -0.3) },
  { name: 'PDF Parser', position: new THREE.Vector3(0.5, -2, 0.6) },
  { name: 'Clause Detector', position: new THREE.Vector3(2, -1.8, -0.2) },
  { name: 'Risk Scorer', position: new THREE.Vector3(1.5, -2.5, 0.4) },
  { name: 'Export Engine', position: new THREE.Vector3(-2.5, 0.2, -0.4) },
]

/** Edges: index pairs into NODES. */
const EDGES: [number, number][] = [
  [0, 4],
  [1, 4],
  [2, 4],
  [3, 4],
  [4, 5],
  [4, 7],
  [4, 8],
  [4, 14],
  [5, 6],
  [6, 12],
  [7, 12],
  [8, 10],
  [9, 4],
  [11, 4],
  [12, 13],
  [13, 7],
]

export default function Constellation() {
  const groupRef = useRef<THREE.Group>(null)
  const pulseRefs = useRef<(THREE.Mesh | null)[]>([])
  const nodeRefs = useRef<(THREE.Mesh | null)[]>([])
  const [hoveredNode, setHoveredNode] = useState<number | null>(null)

  const handlePointerOver = useCallback((i: number) => (_e: ThreeEvent<PointerEvent>) => {
    setHoveredNode(i)
  }, [])

  const handlePointerOut = useCallback(() => {
    setHoveredNode(null)
  }, [])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.06
    }

    // Animate data-flow pulses along edges
    EDGES.forEach((edge, i) => {
      const mesh = pulseRefs.current[i]
      if (!mesh) return
      const t = ((state.clock.elapsedTime * 0.25 + i * 0.15) % 1)
      const from = NODES[edge[0]].position
      const to = NODES[edge[1]].position
      mesh.position.lerpVectors(from, to, t)
    })

    // Node glow on hover
    nodeRefs.current.forEach((mesh, i) => {
      if (!mesh) return
      const mat = mesh.material as THREE.MeshStandardMaterial
      if (i === hoveredNode) {
        mat.emissiveIntensity = 2.0
        mesh.scale.setScalar(1.4)
      } else {
        mat.emissiveIntensity = 0.6
        mesh.scale.setScalar(1)
      }
    })
  })

  return (
    <group ref={groupRef}>
      <GoldParticles count={100} />

      {/* Nodes */}
      {NODES.map((node, i) => (
        <group key={`node-${i}`} position={node.position}>
          <mesh
            ref={(el) => {
              nodeRefs.current[i] = el
            }}
            onPointerOver={handlePointerOver(i)}
            onPointerOut={handlePointerOut}
          >
            <sphereGeometry args={[0.1, 12, 12]} />
            <meshStandardMaterial
              color="#C5A880"
              emissive="#C5A880"
              emissiveIntensity={0.6}
            />
          </mesh>

          {/* Label on hover */}
          {hoveredNode === i && (
            <Html
              center
              distanceFactor={6}
              style={{
                pointerEvents: 'none',
                whiteSpace: 'nowrap',
              }}
            >
              <div
                style={{
                  background: 'rgba(10, 10, 10, 0.85)',
                  color: '#C5A880',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  border: '1px solid rgba(197, 168, 128, 0.3)',
                  transform: 'translateY(-24px)',
                }}
              >
                {node.name}
              </div>
            </Html>
          )}
        </group>
      ))}

      {/* Connections */}
      {EDGES.map((edge, i) => (
        <Line
          key={`edge-${i}`}
          points={[NODES[edge[0]].position, NODES[edge[1]].position]}
          color="#C5A880"
          lineWidth={0.5}
          transparent
          opacity={0.2}
        />
      ))}

      {/* Data-flow pulses */}
      {EDGES.map((_, i) => (
        <mesh
          key={`pulse-${i}`}
          ref={(el) => {
            pulseRefs.current[i] = el
          }}
        >
          <sphereGeometry args={[0.03, 6, 6]} />
          <meshStandardMaterial
            color="#ffffff"
            emissive="#C5A880"
            emissiveIntensity={1.5}
          />
        </mesh>
      ))}
    </group>
  )
}
