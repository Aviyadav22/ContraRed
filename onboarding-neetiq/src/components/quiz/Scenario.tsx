import { useState } from 'react'

interface ScenarioProps {
  question: string
  options: string[]
  correctIndex: number
  explanation: string
  onAnswer: (correct: boolean) => void
}

export default function Scenario({
  question,
  options,
  correctIndex,
  explanation,
  onAnswer,
}: ScenarioProps) {
  const [selected, setSelected] = useState<number | null>(null)
  const answered = selected !== null

  function handleSelect(index: number) {
    if (answered) return
    setSelected(index)
    onAnswer(index === correctIndex)
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="font-serif text-lg text-text-primary">{question}</p>

      <div className="flex flex-col gap-3">
        {options.map((option, i) => {
          let borderClass = 'border-border'
          if (answered && i === correctIndex) borderClass = 'border-risk-green'
          else if (answered && i === selected) borderClass = 'border-risk-red'
          else if (!answered) borderClass = 'border-border'

          const selectedGold =
            !answered && selected === null ? '' : ''

          return (
            <button
              key={i}
              onClick={() => handleSelect(i)}
              disabled={answered}
              className={`bg-surface border ${borderClass} rounded-lg p-4 text-left text-text-primary font-sans transition-all cursor-pointer disabled:cursor-default hover:enabled:-translate-y-0.5 ${selectedGold}`}
            >
              {option}
            </button>
          )
        })}
      </div>

      {answered && (
        <div className="bg-surface-elevated border-l-4 border-gold p-4 mt-4 text-text-muted font-sans text-sm animate-[fadeIn_0.3s_ease-in]">
          {explanation}
        </div>
      )}
    </div>
  )
}
