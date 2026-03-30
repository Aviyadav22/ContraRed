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
    if (!ref.current) return

    const words = ref.current.querySelectorAll('.word')

    gsap.set(words, { y: '115%', opacity: 0 })

    gsap.to(words, {
      y: '0%',
      opacity: 1,
      duration: 0.8,
      ease: 'power3.out',
      stagger: 0.08,
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 85%',
      },
    })

    // Gold underline wipe after text lands
    const underline = ref.current.querySelector('.underline-wipe')
    if (underline) {
      gsap.fromTo(
        underline,
        { scaleX: 0, transformOrigin: 'left' },
        {
          scaleX: 1,
          duration: 0.6,
          delay: 0.08 * words.length + 0.4,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: ref.current,
            start: 'top 85%',
          },
        }
      )
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
