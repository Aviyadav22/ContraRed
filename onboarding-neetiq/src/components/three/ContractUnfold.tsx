import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import * as THREE from 'three'
import GoldParticles from './GoldParticles'

/** Positions where "hidden risk" red particles spawn on the contract page. */
const RISK_POSITIONS = [
  [0.4, 0.3, 0.06],
  [-0.3, -0.2, 0.06],
  [0.1, -0.5, 0.06],
  [-0.5, 0.5, 0.06],
  [0.35, -0.4, 0.06],
] as const

export default function ContractUnfold() {
  const pageRef = useRef<THREE.Mesh>(null)
  const riskRefs = useRef<(THREE.Mesh | null)[]>([])

  // Grid texture for the contract page
  const gridTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 256
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#111111'
    ctx.fillRect(0, 0, 256, 256)
    ctx.strokeStyle = '#1a1a1a'
    ctx.lineWidth = 1
    for (let i = 0; i < 256; i += 16) {
      ctx.beginPath()
      ctx.moveTo(i, 0)
      ctx.lineTo(i, 256)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(0, i)
      ctx.lineTo(256, i)
      ctx.stroke()
    }
    // Fake text lines
    ctx.fillStyle = '#222222'
    for (let y = 20; y < 240; y += 14) {
      const width = 100 + Math.random() * 120
      ctx.fillRect(20, y, width, 4)
    }
    const tex = new THREE.CanvasTexture(canvas)
    tex.needsUpdate = true
    return tex
  }, [])

  useFrame((state) => {
    if (!pageRef.current) return
    // Gentle rotation
    pageRef.current.rotation.y =
      Math.sin(state.clock.elapsedTime * 0.3) * 0.15

    // Pulse and drift red risk spheres
    riskRefs.current.forEach((mesh, i) => {
      if (!mesh) return
      const t = state.clock.elapsedTime + i * 1.2
      const pulse = 0.8 + Math.sin(t * 2) * 0.3
      mesh.scale.setScalar(pulse)
      // Drift outward slowly
      mesh.position.z = 0.06 + Math.sin(t * 0.5) * 0.15
    })
  })

  return (
    <group>
      <GoldParticles count={120} />

      <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.4}>
        {/* Contract page */}
        <mesh ref={pageRef}>
          <boxGeometry args={[1.6, 2.2, 0.02]} />
          <meshPhysicalMaterial
            map={gridTexture}
            color="#1a1a1a"
            emissive="#C5A880"
            emissiveIntensity={0.05}
            roughness={0.4}
            metalness={0.2}
            transmission={0.15}
            transparent
            opacity={0.9}
          />
        </mesh>

        {/* Gold edge highlights */}
        <mesh position={[0, 0, 0.011]}>
          <boxGeometry args={[1.62, 2.22, 0.001]} />
          <meshStandardMaterial
            color="#C5A880"
            emissive="#C5A880"
            emissiveIntensity={0.3}
            transparent
            opacity={0.15}
            wireframe
          />
        </mesh>

        {/* Hidden-risk red particles */}
        {RISK_POSITIONS.map((pos, i) => (
          <mesh
            key={i}
            ref={(el) => {
              riskRefs.current[i] = el
            }}
            position={[pos[0], pos[1], pos[2]]}
          >
            <sphereGeometry args={[0.04, 8, 8]} />
            <meshStandardMaterial
              color="#ff3333"
              emissive="#ff3333"
              emissiveIntensity={1.5}
              transparent
              opacity={0.8}
            />
          </mesh>
        ))}
      </Float>
    </group>
  )
}
