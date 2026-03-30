import { Link } from 'react-router-dom'

export default function Completion() {
  return (
    <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay flex items-center justify-center">
      <div className="text-center max-w-lg px-6">
        <h1 className="text-gold font-serif text-5xl">Chronicle Complete</h1>
        <p className="text-text-muted mt-4 text-lg leading-relaxed">
          You've completed The ContraRed Chronicle. Welcome to NeetiQ.
        </p>
        <Link
          to="/"
          className="inline-block mt-8 px-6 py-2.5 bg-gold text-bg rounded-lg font-mono text-sm hover:bg-gold/90 transition-colors font-semibold"
        >
          Back to Library
        </Link>
      </div>
    </div>
  )
}
