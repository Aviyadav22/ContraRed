import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface DiagramDrawProps {
  children: React.ReactNode
  className?: string
}

export default function DiagramDraw({ children, className = '' }: DiagramDrawProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const paths = ref.current.querySelectorAll('path, line, polyline, circle, rect, ellipse')

    paths.forEach((path) => {
      if (path instanceof SVGGeometryElement) {
        const length = path.getTotalLength()
        gsap.set(path, { strokeDasharray: length, strokeDashoffset: length, opacity: 1 })
      }
    })

    gsap.to(paths, {
      strokeDashoffset: 0,
      duration: 1.5,
      ease: 'power2.inOut',
      stagger: 0.2,
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 80%',
      },
    })

    // Fade in fills after drawing
    const fills = ref.current.querySelectorAll('[data-fill]')
    gsap.fromTo(
      fills,
      { opacity: 0 },
      {
        opacity: 1,
        duration: 0.5,
        delay: 1.5,
        stagger: 0.1,
        scrollTrigger: {
          trigger: ref.current,
          start: 'top 80%',
        },
      }
    )
  }, [])

  return (
    <div ref={ref} className={`${className}`}>
      {children}
    </div>
  )
}
