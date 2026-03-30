import { useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { gsap } from 'gsap'
import { useProgress } from '../../../stores/useProgress'

const SESSION_META = [
  { id: 1, title: 'The Origin Story', subtitle: 'How it all began', chapters: 5 },
  { id: 2, title: 'The Technology', subtitle: 'Under the hood', chapters: 4 },
  { id: 3, title: 'The Real World', subtitle: 'Deployment and validation', chapters: 4 },
  { id: 4, title: 'The Full Picture', subtitle: 'Architecture and beyond', chapters: 2 },
]

export default function ContraRedLanding() {
  const { books } = useProgress()
  const contrared = books.contrared
  const navigate = useNavigate()

  const containerRef = useRef<HTMLDivElement>(null)

  const sessions = contrared?.sessions ?? {}
  const completedSessions = Object.values(sessions).filter(
    (s) => s.status === 'completed'
  ).length
  const totalSessions = Object.keys(sessions).length
  const progressPct = totalSessions > 0 ? (completedSessions / totalSessions) * 100 : 0

  useEffect(() => {
    if (!containerRef.current) return
    gsap.fromTo(
      containerRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' },
    )
  }, [])

  return (
    <div ref={containerRef} className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay" style={{ opacity: 0 }}>
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link to="/" className="text-text-muted hover:text-gold text-sm font-mono transition-colors">
          {'\u2190'} Back to Library
        </Link>

        <div className="mt-8 mb-6">
          <div className="text-gold font-mono text-xs uppercase tracking-widest mb-2">Book 1</div>
          <h1 className="text-text-primary font-serif text-4xl">The ContraRed Chronicle</h1>
          <p className="text-text-muted mt-3 leading-relaxed">
            How a chance meeting turned into an AI-powered contract review platform.
            4 sessions across your first week.
          </p>
        </div>

        {/* Overall progress bar */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-muted font-mono text-xs">
              {completedSessions}/{totalSessions} sessions complete
            </span>
            <span className="text-gold font-mono text-xs">{Math.round(progressPct)}%</span>
          </div>
          <div className="h-2 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-gold rounded-full transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="space-y-4">
          {SESSION_META.map((meta) => {
            const session = contrared.sessions[meta.id]
            const isLocked = session.status === 'locked'
            const isCompleted = session.status === 'completed'
            const isAvailable = session.status === 'available' || session.status === 'in_progress'

            return (
              <button
                key={meta.id}
                onClick={() => {
                  if (isLocked) navigate('/locked')
                  else navigate(`/contrared/session/${meta.id}`)
                }}
                disabled={isLocked}
                className={`w-full text-left bg-surface border rounded-xl p-6 transition-all duration-300 ${
                  isLocked
                    ? 'border-border opacity-40 cursor-not-allowed'
                    : isCompleted
                    ? 'border-risk-green/30 hover:border-risk-green/50'
                    : 'border-border hover:border-gold/40 hover:shadow-[0_0_20px_rgba(197,168,128,0.08)]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="text-gold font-mono text-xs">Session {meta.id}</span>
                      {isCompleted && (
                        <span className="text-risk-green text-xs font-mono">
                          {'\u2713'} Complete
                        </span>
                      )}
                      {isLocked && (
                        <span className="text-text-muted text-xs">{'\u{1F512}'}</span>
                      )}
                    </div>
                    <h3 className="text-text-primary font-serif text-xl mt-1">{meta.title}</h3>
                    <p className="text-text-muted text-sm mt-1">
                      {meta.subtitle} {'\u00B7'} {meta.chapters} chapters
                    </p>
                  </div>
                  {isAvailable && (
                    <span className="text-gold font-mono text-sm">
                      {session.status === 'in_progress' ? 'Continue \u2192' : 'Start \u2192'}
                    </span>
                  )}
                </div>
              </button>
            )
          })}
        </div>

        {/* Badges section */}
        {contrared.badges.length > 0 && (
          <div className="mt-12">
            <h3 className="text-text-muted font-mono text-xs uppercase tracking-widest mb-4">
              Badges Earned
            </h3>
            <div className="flex gap-3 flex-wrap">
              {contrared.badges.map((badge) => (
                <div
                  key={badge}
                  className="bg-surface-elevated border border-gold/20 rounded-lg px-3 py-1.5 text-gold text-xs font-mono"
                >
                  {badge.replace(/-/g, ' ')}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
