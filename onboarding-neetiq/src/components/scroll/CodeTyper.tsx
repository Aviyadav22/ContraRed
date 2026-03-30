import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface CodeTyperProps {
  code: string
  language?: string
  className?: string
}

export default function CodeTyper({ code, language = '', className = '' }: CodeTyperProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [displayText, setDisplayText] = useState('')
  const [typing, setTyping] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!ref.current) return

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 80%',
      onEnter: () => {
        if (!typing && !done) {
          setTyping(true)
        }
      },
      once: true,
    })

    return () => trigger.kill()
  }, [typing, done])

  useEffect(() => {
    if (!typing) return

    let i = 0
    const interval = setInterval(() => {
      if (i < code.length) {
        setDisplayText(code.slice(0, i + 1))
        i++
      } else {
        clearInterval(interval)
        setTyping(false)
        setDone(true)
      }
    }, 25)

    return () => clearInterval(interval)
  }, [typing, code])

  return (
    <div ref={ref} className={`bg-surface rounded-lg border border-border overflow-hidden ${className}`}>
      {language && (
        <div className="px-4 py-2 border-b border-border flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-risk-red/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-risk-yellow/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-risk-green/60" />
          <span className="ml-2 text-text-muted font-mono text-xs">{language}</span>
        </div>
      )}
      <pre className="p-4 overflow-x-auto">
        <code className="font-mono text-sm text-text-primary">
          {displayText}
          {typing && <span className="cursor-blink" />}
        </code>
      </pre>
    </div>
  )
}
