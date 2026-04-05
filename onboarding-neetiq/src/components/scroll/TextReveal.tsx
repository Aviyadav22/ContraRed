import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface TextRevealProps {
  children: string
  as?: 'h1' | 'h2' | 'h3'
  className?: string
}

export default function TextReveal({ children, as: Tag = 'h2', className = '' }: TextRevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const words = el.querySelectorAll('.word')
    const underline = el.querySelector('.underline-wipe')
    let trigger: ScrollTrigger | null = null

    const raf = requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect()
      if (rect.top > window.innerHeight) {
        // Below the fold — hide and animate on scroll
        gsap.set(words, { y: '115%', opacity: 0 })
        if (underline) gsap.set(underline, { scaleX: 0, transformOrigin: 'left' })

        trigger = ScrollTrigger.create({
          trigger: el,
          start: 'top 90%',
          once: true,
          onEnter: () => {
            gsap.to(words, { y: '0%', opacity: 1, duration: 0.8, ease: 'power3.out', stagger: 0.08 })
            if (underline) {
              gsap.to(underline, { scaleX: 1, duration: 0.6, delay: 0.08 * words.length + 0.4, ease: 'power2.out' })
            }
          },
        })
      }
      // Already visible — leave it alone
    })

    return () => {
      cancelAnimationFrame(raf)
      trigger?.kill()
      words.forEach((w) => gsap.killTweensOf(w))
      if (underline) gsap.killTweensOf(underline)
    }
  }, [children])

  const wordList = children.split(' ')

  return (
    <div ref={ref} className={`overflow-hidden ${className}`}>
      <Tag className="text-gold font-serif leading-tight">
        {wordList.map((word, i) => (
          <span key={i} className="inline-block overflow-hidden mr-[0.3em]">
            <span className="word inline-block">{word}</span>
          </span>
        ))}
      </Tag>
      <div className="underline-wipe h-[2px] bg-gold mt-3 w-24" />
    </div>
  )
}
