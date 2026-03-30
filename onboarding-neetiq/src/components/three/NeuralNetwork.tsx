import { useRef, useMemo, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import * as THREE from 'three'
import GoldParticles from './GoldParticles'

const NODE_COUNT = 20
const CONNECTION_DISTANCE = 2.2

interface NodeData {
  position: THREE.Vector3
}

interface Connection {
  from: number
  to: number
}

export default function NeuralNetwork() {
  const groupRef = useRef<THREE.Group>(null)
  const [pulseOffsets] = useState(() =>
    Array.from({ length: 60 }, () => Math.random()),
  )

  // Generate node positions and connections
  const { nodes, connections } = useMemo(() => {
    const ns: NodeData[] = []
    for (let i = 0; i < NODE_COUNT; i++) {
      ns.push({
        position: new THREE.Vector3(
          (Math.random() - 0.5) * 4,
          (Math.random() - 0.5) * 3,
          (Math.random() - 0.5) * 3,
        ),
      })
    }

    const conns: Connection[] = []
    for (let i = 0; i < NODE_COUNT; i++) {
      for (let j = i + 1; j < NODE_COUNT; j++) {
        if (ns[i].position.distanceTo(ns[j].position) < CONNECTION_DISTANCE) {
          conns.push({ from: i, to: j })
        }
      }
    }
    return { nodes: ns, connections: conns }
  }, [])

  // Pulse spheres that travel along connections
  const pulseRefs = useRef<(THREE.Mesh | null)[]>([])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.08
    }

    // Animate pulses along connections
    connections.forEach((conn, i) => {
      const mesh = pulseRefs.current[i]
      if (!mesh) return
      const t =
        ((state.clock.elapsedTime * 0.3 + pulseOffsets[i % pulseOffsets.length]) % 1)
      const from = nodes[conn.from].position
      const to = nodes[conn.to].position
      mesh.position.lerpVectors(from, to, t)
    })
  })

  return (
    <group ref={groupRef}>
      <GoldParticles count={100} />

      {/* Nodes */}
      {nodes.map((node, i) => (
        <mesh key={`node-${i}`} position={node.position}>
          <sphereGeometry args={[0.08, 12, 12]} />
          <meshStandardMaterial
            color="#C5A880"
            emissive="#C5A880"
            emissiveIntensity={0.8}
          />
        </mesh>
      ))}

      {/* Connections */}
      {connections.map((conn, i) => {
        const from = nodes[conn.from].position
        const to = nodes[conn.to].position
        return (
          <Line
            key={`line-${i}`}
            points={[from, to]}
            color="#C5A880"
            lineWidth={0.5}
            transparent
            opacity={0.25}
          />
        )
      })}

      {/* Energy pulses traveling along connections */}
      {connections.map((_, i) => (
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
            emissiveIntensity={2}
          />
        </mesh>
      ))}
    </group>
  )
}
