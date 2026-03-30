import { Link } from 'react-router-dom'

export default function Lock() {
  return (
    <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <div className="text-6xl mb-6">{'\u{1F512}'}</div>
        <h2 className="text-gold font-serif text-3xl">Session Locked</h2>
        <p className="text-text-muted mt-3 leading-relaxed">
          Complete the previous session's quiz to unlock this one.
        </p>
        <Link
          to="/contrared"
          className="inline-block mt-6 px-6 py-2.5 border border-gold/40 text-gold rounded-lg font-mono text-sm hover:bg-gold/10 transition-colors"
        >
          {'\u2190'} Back to Sessions
        </Link>
      </div>
    </div>
  )
}
