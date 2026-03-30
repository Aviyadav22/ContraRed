import { useEffect, useRef, useCallback } from 'react'
import { motion } from 'motion/react'

interface SessionCompleteProps {
  sessionNumber: number
  sessionTitle: string
  onContinue: () => void
}

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

const GOLD_COLORS = ['#C5A880', '#8B7355', '#E8D5B7', '#A08B6A', '#D4C4A0']

function createConfettiSystem(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return { stop: () => {} }

  canvas.width = canvas.offsetWidth * 2
  canvas.height = canvas.offsetHeight * 2
  ctx.scale(2, 2)

  const particles: Particle[] = []
  let animFrame = 0
  let running = true

  // Burst confetti
  for (let i = 0; i < 80; i++) {
    const angle = (Math.random() * Math.PI * 2)
    const speed = 3 + Math.random() * 6
    particles.push({
      x: canvas.offsetWidth / 2,
      y: canvas.offsetHeight / 2,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 4,
      size: 3 + Math.random() * 5,
      color: GOLD_COLORS[Math.floor(Math.random() * GOLD_COLORS.length)],
      alpha: 1,
      decay: 0.008 + Math.random() * 0.008,
      gravity: 0.08 + Math.random() * 0.04,
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

export default function SessionComplete({
  sessionNumber,
  sessionTitle,
  onContinue,
}: SessionCompleteProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const systemRef = useRef<{ stop: () => void } | null>(null)

  const initConfetti = useCallback(() => {
    if (canvasRef.current) {
      systemRef.current?.stop()
      systemRef.current = createConfettiSystem(canvasRef.current)
    }
  }, [])

  useEffect(() => {
    // Small delay for component to mount
    const timer = setTimeout(initConfetti, 200)
    return () => {
      clearTimeout(timer)
      systemRef.current?.stop()
    }
  }, [initConfetti])

  return (
    <div className="relative flex flex-col items-center justify-center py-16 px-8">
      {/* Confetti canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 10 }}
      />

      {/* Content */}
      <motion.div
        className="relative z-20 text-center"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
      >
        {/* Session Complete heading */}
        <motion.h2
          className="text-3xl font-serif mb-2"
          style={{ color: '#C5A880', fontFamily: 'Georgia, serif' }}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.5 }}
        >
          Session Complete
        </motion.h2>

        {/* Session info */}
        <motion.div
          className="text-sm font-mono mb-1"
          style={{ color: '#8B7355' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          Session {sessionNumber}
        </motion.div>

        <motion.div
          className="text-lg mb-8"
          style={{ color: '#E8E8E8' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          {sessionTitle}
        </motion.div>

        {/* Badge earned display */}
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border mb-8"
          style={{ borderColor: '#C5A880', backgroundColor: 'rgba(197,168,128,0.08)' }}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 1 }}
        >
          <span className="text-sm" style={{ color: '#C5A880' }}>
            Badge Earned
          </span>
        </motion.div>

        <br />

        {/* Continue button */}
        <motion.button
          onClick={onContinue}
          className="px-8 py-3 rounded-lg font-mono text-sm tracking-wide transition-all"
          style={{
            backgroundColor: '#C5A880',
            color: '#0A0A0A',
          }}
          whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(197,168,128,0.4)' }}
          whileTap={{ scale: 0.98 }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.2 }}
        >
          Continue
        </motion.button>
      </motion.div>
    </div>
  )
}
