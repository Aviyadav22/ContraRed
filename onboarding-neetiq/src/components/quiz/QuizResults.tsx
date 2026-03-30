interface QuizResultsProps {
  score: number
  total: number
  passed: boolean
  onContinue: () => void
  onRetry: () => void
}

export default function QuizResults({
  score,
  total,
  passed,
  onContinue,
  onRetry,
}: QuizResultsProps) {
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <p className="font-serif text-5xl text-gold font-bold">
        {score} / {total}
      </p>
      <p className="font-mono text-sm text-text-muted">{percentage}%</p>

      {passed ? (
        <>
          <p className="font-serif text-xl text-risk-green">
            Session Complete
          </p>
          <button
            onClick={onContinue}
            className="bg-gold text-bg font-sans font-medium px-6 py-3 rounded-lg hover:opacity-90 transition-opacity"
          >
            Continue
          </button>
        </>
      ) : (
        <>
          <p className="font-serif text-xl text-risk-red">Not quite...</p>
          <button
            onClick={onRetry}
            className="border border-gold text-gold font-sans font-medium px-6 py-3 rounded-lg hover:bg-gold/10 transition-colors"
          >
            Retry
          </button>
        </>
      )}
    </div>
  )
}
