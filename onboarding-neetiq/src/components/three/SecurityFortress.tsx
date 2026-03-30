import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import GoldParticles from './GoldParticles'

const LAYER_RADII = [0.4, 0.65, 0.9, 1.15, 1.4, 1.65, 1.95]
const GOLD_TONES = [
  '#C5A880',
  '#BFA375',
  '#B89E6A',
  '#D4B88E',
  '#C1A47C',
  '#AE9468',
  '#D9C09A',
]

export default function SecurityFortress() {
  const groupRef = useRef<THREE.Group>(null)
  const layerRefs = useRef<(THREE.Mesh | null)[]>([])
  const coreRef = useRef<THREE.Mesh>(null)
  const startTime = useRef<number | null>(null)

  useFrame((state) => {
    if (startTime.current === null) {
      startTime.current = state.clock.elapsedTime
    }
    const elapsed = state.clock.elapsedTime - startTime.current

    // Gentle overall rotation
    if (groupRef.current) {
      groupRef.current.rotation.y = elapsed * 0.12
      groupRef.current.rotation.x = Math.sin(elapsed * 0.15) * 0.1
    }

    // Staggered layer appearance: each layer scales in 0.4s apart
    layerRefs.current.forEach((mesh, i) => {
      if (!mesh) return
      const delay = i * 0.4
      const progress = Math.min(1, Math.max(0, (elapsed - delay) / 0.6))
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      mesh.scale.setScalar(eased)

      // Subtle breathing per layer
      if (progress >= 1) {
        const breath = 1 + Math.sin(elapsed * 0.8 + i * 0.9) * 0.02
        mesh.scale.setScalar(breath)
      }
    })

    // Core pulsing glow
    if (coreRef.current) {
      const mat = coreRef.current.material as THREE.MeshStandardMaterial
      mat.emissiveIntensity = 1.5 + Math.sin(elapsed * 2) * 0.5
    }
  })

  return (
    <group ref={groupRef}>
      <GoldParticles count={150} />

      {/* Glowing core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshStandardMaterial
          color="#C5A880"
          emissive="#C5A880"
          emissiveIntensity={2}
        />
      </mesh>

      {/* Concentric translucent security layers */}
      {LAYER_RADII.map((radius, i) => (
        <mesh
          key={i}
          ref={(el) => {
            layerRefs.current[i] = el
          }}
          scale={0}
        >
          <icosahedronGeometry args={[radius, 1]} />
          <meshPhysicalMaterial
            color={GOLD_TONES[i]}
            emissive={GOLD_TONES[i]}
            emissiveIntensity={0.15}
            transmission={0.6}
            roughness={0.1}
            metalness={0.1}
            transparent
            opacity={0.18}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  )
}
