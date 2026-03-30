import type { ReactNode } from 'react'

interface QuizContainerProps {
  title?: string
  children: ReactNode
  className?: string
}

export default function QuizContainer({
  title,
  children,
  className = '',
}: QuizContainerProps) {
  return (
    <div
      className={`bg-surface-elevated rounded-lg border border-border overflow-hidden ${className}`}
      style={{ borderTop: '4px solid var(--color-gold)' }}
    >
      <div className="p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-gold mb-1">
          Knowledge Check
        </p>
        {title && (
          <h3 className="font-serif text-xl text-text-primary">{title}</h3>
        )}
      </div>
      <div className="px-6 pb-6">{children}</div>
    </div>
  )
}
