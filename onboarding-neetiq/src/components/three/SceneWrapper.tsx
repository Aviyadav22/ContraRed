import { Suspense, useState, useEffect, type ReactNode } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'

interface SceneWrapperProps {
  children: ReactNode
  className?: string
  enableOrbit?: boolean
}

export default function SceneWrapper({
  children,
  className = '',
  enableOrbit = true,
}: SceneWrapperProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div
      className={`w-full h-[60vh] bg-bg transition-opacity duration-1000 ${visible ? 'opacity-100' : 'opacity-0'} ${className}`}
    >
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 2]}>
        <color attach="background" args={['#0A0A0A']} />
        <ambientLight intensity={0.3} />
        <pointLight position={[10, 10, 10]} intensity={0.8} color="#C5A880" />
        <Suspense fallback={null}>
          {children}
          {enableOrbit && (
            <OrbitControls
              enableZoom={false}
              autoRotate
              autoRotateSpeed={0.5}
            />
          )}
        </Suspense>
        <EffectComposer>
          <Bloom
            intensity={0.4}
            luminanceThreshold={0.6}
            luminanceSmoothing={0.9}
          />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
