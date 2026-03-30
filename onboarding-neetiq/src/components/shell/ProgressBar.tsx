interface ProgressBarProps {
  current: number
  total: number
  label?: string
}

export default function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percentage = total === 0 ? 0 : Math.round((current / total) * 100)

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 h-10 bg-bg/80 backdrop-blur-md border-t border-border flex items-center px-6 gap-4">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-gold rounded-full transition-all duration-700 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-text-muted font-mono text-xs whitespace-nowrap">
        {label ?? `${percentage}%`}
      </span>
    </footer>
  )
}
