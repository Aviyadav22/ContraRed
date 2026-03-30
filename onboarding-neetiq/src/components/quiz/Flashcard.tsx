import { useState } from 'react'

interface FlashcardProps {
  question: string
  answer: string
  isCorrect: boolean
  onAnswer: (correct: boolean) => void
}

export default function Flashcard({
  question,
  answer,
  isCorrect,
  onAnswer,
}: FlashcardProps) {
  const [flipped, setFlipped] = useState(false)

  function handleFlip() {
    if (flipped) return
    setFlipped(true)
    onAnswer(isCorrect)
  }

  return (
    <div
      className="cursor-pointer"
      style={{ perspective: '1000px' }}
      onClick={handleFlip}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleFlip()
      }}
    >
      <div
        className="relative w-full transition-transform duration-[600ms]"
        style={{
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
        }}
      >
        {/* Front */}
        <div
          className="bg-surface border border-border rounded-lg p-6 min-h-[200px] flex items-center justify-center"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <p className="font-serif text-lg text-text-primary text-center">
            {question}
          </p>
        </div>

        {/* Back */}
        <div
          className="absolute inset-0 bg-surface border border-border rounded-lg p-6 min-h-[200px] flex flex-col items-center justify-center gap-3"
          style={{
            backfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
          }}
        >
          <span
            className={`text-4xl ${isCorrect ? 'text-risk-green' : 'text-risk-red'}`}
          >
            {isCorrect ? '\u2713' : '\u2717'}
          </span>
          <p className="font-sans text-text-primary text-center">{answer}</p>
        </div>
      </div>
    </div>
  )
}
