import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { useProgress } from '../stores/useProgress'

const BOOKS = [
  {
    id: 'contrared',
    number: 1,
    title: 'ContraRed Chronicle',
    description: 'Contract AI -- How a chance meeting became an AI-powered legal review platform.',
    totalSessions: 4,
    available: true,
    link: '/contrared',
    icon: '\u{1F4DC}',
  },
  {
    id: 'smriti',
    number: 2,
    title: 'Smriti Saga',
    description: 'Litigation Intelligence -- Coming soon.',
    totalSessions: 0,
    available: false,
    link: '',
    icon: '\u{2696}',
  },
  {
    id: 'foundations',
    number: 3,
    title: 'NeetiQ Foundations',
    description: 'Platform architecture and principles -- Coming soon.',
    totalSessions: 0,
    available: false,
    link: '',
    icon: '\u{1F3DB}',
  },
]

export default function Home() {
  const { books, overallProgress } = useProgress()
  const containerRef = useRef<HTMLDivElement>(null)

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
      <div className="max-w-4xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <span className="text-gold font-serif text-lg tracking-wide">NeetiQ</span>
          <h1 className="text-text-primary font-serif text-5xl mt-4 leading-tight">
            The NeetiQ Chronicles
          </h1>
          <p className="text-text-muted mt-3 text-lg">
            Your onboarding library. Pick a book to begin.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {BOOKS.map((book) => {
            const bookData = books[book.id]
            const completedSessions = bookData
              ? Object.values(bookData.sessions).filter((s) => s.status === 'completed').length
              : 0
            const totalSessions = bookData
              ? Object.keys(bookData.sessions).length
              : book.totalSessions
            const progressPct =
              totalSessions > 0 ? (completedSessions / totalSessions) * 100 : 0
            const hasStarted = completedSessions > 0

            if (book.available) {
              return (
                <Link
                  key={book.id}
                  to={book.link}
                  className="group bg-surface border border-border rounded-xl p-6 hover:border-gold/40 hover:shadow-[0_0_30px_rgba(197,168,128,0.1)] transition-all duration-300"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{book.icon}</span>
                    <span className="text-gold font-mono text-xs uppercase tracking-widest">
                      Book {book.number}
                    </span>
                  </div>
                  <h2 className="text-text-primary font-serif text-2xl group-hover:text-gold transition-colors">
                    {book.title}
                  </h2>
                  <p className="text-text-muted mt-2 text-sm leading-relaxed">
                    {book.description}
                  </p>
                  <div className="mt-4 text-sm text-text-muted">
                    {totalSessions} sessions
                  </div>
                  <div className="mt-3 h-1.5 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gold rounded-full transition-all duration-700"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <div className="mt-2 text-xs text-text-muted font-mono">
                    {!hasStarted
                      ? 'Not started'
                      : `${completedSessions}/${totalSessions} complete`}
                  </div>
                </Link>
              )
            }

            return (
              <div
                key={book.id}
                className="relative bg-surface border border-border rounded-xl p-6 opacity-50 cursor-not-allowed overflow-hidden"
              >
                {/* Shimmer animation */}
                <div className="absolute inset-0 shimmer pointer-events-none" />
                <div className="relative">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{book.icon}</span>
                    <span className="text-text-muted font-mono text-xs uppercase tracking-widest">
                      Book {book.number}
                    </span>
                  </div>
                  <h2 className="text-text-muted font-serif text-2xl">{book.title}</h2>
                  <p className="text-text-muted mt-2 text-sm leading-relaxed">
                    {book.description}
                  </p>
                  <div className="mt-4 flex items-center gap-2 text-sm text-text-muted">
                    <span>{'\u{1F512}'}</span> Locked
                  </div>
                  <div className="mt-2 inline-block bg-gold/10 border border-gold/20 rounded-full px-3 py-0.5 text-gold text-xs font-mono">
                    Coming Soon
                  </div>
                </div>
              </div>
            )
          })}
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
