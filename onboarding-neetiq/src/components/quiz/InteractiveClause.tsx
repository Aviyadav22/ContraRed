import { useState, useCallback } from 'react'

interface InteractiveClauseProps {
  clause: string
  riskyWords: string[]
  onComplete: (found: string[]) => void
}

export default function InteractiveClause({
  clause,
  riskyWords,
  onComplete,
}: InteractiveClauseProps) {
  const [found, setFound] = useState<string[]>([])
  const [flashWord, setFlashWord] = useState<string | null>(null)

  const riskySet = new Set(riskyWords.map((w) => w.toLowerCase()))

  const words = clause.split(/(\s+)/)

  const handleWordClick = useCallback(
    (word: string) => {
      const clean = word.replace(/[.,;:!?"'()[\]{}]/g, '')
      const lower = clean.toLowerCase()

      if (riskySet.has(lower)) {
        if (!found.includes(lower)) {
          const next = [...found, lower]
          setFound(next)
          if (next.length === riskyWords.length) {
            onComplete(next)
          }
        }
      } else {
        setFlashWord(word)
        setTimeout(() => setFlashWord(null), 400)
      }
    },
    [found, riskySet, riskyWords.length, onComplete]
  )

  return (
    <div className="flex flex-col gap-4">
      <p className="font-mono text-xs text-text-muted uppercase tracking-wide">
        Found {found.length} of {riskyWords.length} risky terms
      </p>

      <div className="bg-surface border border-border rounded-lg p-6 font-serif text-text-primary leading-relaxed select-none">
        {words.map((segment, i) => {
          if (/^\s+$/.test(segment)) {
            return <span key={i}>{segment}</span>
          }

          const clean = segment.replace(/[.,;:!?"'()[\]{}]/g, '')
          const lower = clean.toLowerCase()
          const isRisky = riskySet.has(lower)
          const isFound = found.includes(lower)
          const isFlashing = flashWord === segment

          return (
            <span
              key={i}
              onClick={() => handleWordClick(segment)}
              className={`cursor-pointer rounded px-0.5 transition-colors duration-200 ${
                isFound
                  ? 'text-risk-red font-bold'
                  : isFlashing
                    ? 'bg-risk-red/20'
                    : isRisky
                      ? 'hover:bg-gold/10'
                      : 'hover:bg-white/5'
              }`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleWordClick(segment)
              }}
            >
              {segment}
            </span>
          )
        })}
      </div>
    </div>
  )
}
