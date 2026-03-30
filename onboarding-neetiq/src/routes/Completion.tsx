import { Link, Navigate } from 'react-router-dom'
import { useEffect, useRef, useCallback } from 'react'
import { useProgress } from '../stores/useProgress'
import Certificate from '../components/celebrations/Certificate'

const GOLD_COLORS = ['#C5A880', '#8B7355', '#E8D5B7', '#A08B6A', '#D4C4A0']

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  alpha: number
  decay: number
  gravity: number
}

function createConfetti(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return { stop: () => {} }

  canvas.width = canvas.offsetWidth * 2
  canvas.height = canvas.offsetHeight * 2
  ctx.scale(2, 2)

  const particles: Particle[] = []
  let animFrame = 0
  let running = true

  for (let i = 0; i < 120; i++) {
    const angle = Math.random() * Math.PI * 2
    const speed = 4 + Math.random() * 8
    particles.push({
      x: canvas.offsetWidth / 2 + (Math.random() - 0.5) * 200,
      y: canvas.offsetHeight * 0.3,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 5,
      size: 3 + Math.random() * 6,
      color: GOLD_COLORS[Math.floor(Math.random() * GOLD_COLORS.length)],
      alpha: 1,
      decay: 0.005 + Math.random() * 0.005,
      gravity: 0.06 + Math.random() * 0.03,
    })
  }

  function tick() {
    if (!running || !ctx) return
    ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight)

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i]
      p.x += p.vx
      p.vy += p.gravity
      p.y += p.vy
      p.alpha -= p.decay

      if (p.alpha <= 0) {
        particles.splice(i, 1)
        continue
      }

      ctx.globalAlpha = p.alpha
      ctx.fillStyle = p.color
      ctx.fillRect(p.x, p.y, p.size, p.size * 0.6)
    }

    ctx.globalAlpha = 1
    if (particles.length > 0) {
      animFrame = requestAnimationFrame(tick)
    }
  }

  animFrame = requestAnimationFrame(tick)

  return {
    stop: () => {
      running = false
      cancelAnimationFrame(animFrame)
    },
  }
}

function formatTime(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function Completion() {
  const { books, user } = useProgress()
  const contrared = books.contrared
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const systemRef = useRef<{ stop: () => void } | null>(null)

  const allComplete = Object.values(contrared.sessions).every(
    (s) => s.status === 'completed'
  )

  const initConfetti = useCallback(() => {
    if (canvasRef.current) {
      systemRef.current?.stop()
      systemRef.current = createConfetti(canvasRef.current)
    }
  }, [])

  useEffect(() => {
    if (allComplete) {
      const timer = setTimeout(initConfetti, 300)
      return () => {
        clearTimeout(timer)
        systemRef.current?.stop()
      }
    }
  }, [allComplete, initConfetti])

  if (!allComplete) {
    return <Navigate to="/contrared" replace />
  }

  const totalTime = Object.values(contrared.sessions).reduce(
    (acc, s) => acc + s.timeSpentSeconds,
    0
  )

  const completionDate = contrared.sessions[4]?.completedAt
    ? new Date(contrared.sessions[4].completedAt).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : new Date().toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })

  const userName = user?.name || 'Team Member'

  return (
    <div className="relative min-h-screen bg-bg text-text-primary grain-overlay grid-overlay">
      {/* Confetti canvas */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full pointer-events-none z-50"
      />

      <div className="relative z-10 max-w-3xl mx-auto px-6 py-20">
        {/* Certificate */}
        <Certificate
          userName={userName}
          completionDate={completionDate}
          bookTitle="The ContraRed Chronicle"
        />

        {/* Welcome message */}
        <div className="text-center mt-16">
          <h2 className="text-gold font-serif text-3xl leading-relaxed">
            Welcome to NeetiQ.
          </h2>
          <p className="text-gold/70 font-serif text-xl mt-2 italic">
            Your chapter starts now.
          </p>
        </div>

        {/* Badges earned */}
        {contrared.badges.length > 0 && (
          <div className="mt-12 text-center">
            <h3 className="text-text-muted font-mono text-xs uppercase tracking-widest mb-4">
              All Badges Earned
            </h3>
            <div className="flex gap-3 flex-wrap justify-center">
              {contrared.badges.map((badge) => (
                <div
                  key={badge}
                  className="bg-surface-elevated border border-gold/20 rounded-lg px-4 py-2 text-gold text-sm font-mono"
                >
                  {badge.replace(/-/g, ' ')}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats */}
        {totalTime > 0 && (
          <div className="mt-8 text-center text-text-muted text-sm font-mono">
            Total time: {formatTime(totalTime)}
          </div>
        )}

        {/* Back to home */}
        <div className="text-center mt-12">
          <Link
            to="/"
            className="inline-block px-8 py-3 bg-gold text-bg rounded-lg font-mono text-sm hover:bg-gold/90 transition-colors font-semibold"
          >
            Back to Library
          </Link>
        </div>
      </div>
    </div>
  )
}
