import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface GoldParticlesProps {
  count?: number
}

export default function GoldParticles({ count = 200 }: GoldParticlesProps) {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 10
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10
      pos[i * 3 + 2] = (Math.random() - 0.5) * 10
    }
    return pos
  }, [count])

  useFrame((_, delta) => {
    if (!ref.current) return
    const posArr = ref.current.geometry.attributes.position
      .array as Float32Array
    for (let i = 0; i < count; i++) {
      posArr[i * 3 + 1] += delta * 0.1 // drift upward
      if (posArr[i * 3 + 1] > 5) posArr[i * 3 + 1] = -5 // wrap
    }
    ref.current.geometry.attributes.position.needsUpdate = true
  })

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [positions])

  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        size={0.02}
        color="#C5A880"
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  )
}
