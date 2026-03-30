import { Link } from 'react-router-dom'
import { useProgress } from '../stores/useProgress'

export default function Home() {
  const { books, overallProgress } = useProgress()
  const contrared = books.contrared

  const completedSessions = Object.values(contrared.sessions).filter(s => s.status === 'completed').length
  const totalSessions = Object.keys(contrared.sessions).length

  return (
    <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay">
      <div className="max-w-4xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <span className="text-gold font-serif text-lg tracking-wide">NeetiQ</span>
          <h1 className="text-text-primary font-serif text-5xl mt-4 leading-tight">The NeetiQ Chronicles</h1>
          <p className="text-text-muted mt-3 text-lg">Your onboarding library. Pick a book.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-2xl mx-auto">
          {/* ContraRed Chronicle — available */}
          <Link
            to="/contrared"
            className="group bg-surface border border-border rounded-xl p-6 hover:border-gold/40 hover:shadow-[0_0_30px_rgba(197,168,128,0.1)] transition-all duration-300"
          >
            <div className="text-gold font-mono text-xs uppercase tracking-widest mb-2">Book 1</div>
            <h2 className="text-text-primary font-serif text-2xl group-hover:text-gold transition-colors">
              ContraRed Chronicle
            </h2>
            <p className="text-text-muted mt-2 text-sm leading-relaxed">
              Contract AI — How a chance meeting became an AI-powered legal review platform.
            </p>
            <div className="mt-4 text-sm text-text-muted">{totalSessions} sessions</div>
            <div className="mt-3 h-1.5 bg-border rounded-full overflow-hidden">
              <div
                className="h-full bg-gold rounded-full transition-all duration-700"
                style={{ width: `${(completedSessions / totalSessions) * 100}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-text-muted font-mono">
              {completedSessions === 0 ? 'Not started' : `${completedSessions}/${totalSessions} complete`}
            </div>
          </Link>

          {/* Smriti Saga — locked/coming soon */}
          <div className="bg-surface border border-border rounded-xl p-6 opacity-50 cursor-not-allowed">
            <div className="text-text-muted font-mono text-xs uppercase tracking-widest mb-2">Book 2</div>
            <h2 className="text-text-muted font-serif text-2xl">Smriti Saga</h2>
            <p className="text-text-muted mt-2 text-sm leading-relaxed">
              Litigation Intelligence — Coming soon.
            </p>
            <div className="mt-4 flex items-center gap-2 text-sm text-text-muted">
              <span>{'\u{1F512}'}</span> Locked
            </div>
            <div className="mt-3 h-1.5 shimmer rounded-full" />
          </div>
        </div>

        {overallProgress > 0 && (
          <div className="text-center mt-12 text-text-muted text-sm font-mono">
            Overall: {overallProgress}% complete
          </div>
        )}
      </div>
    </div>
  )
}
