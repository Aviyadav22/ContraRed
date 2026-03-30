import { motion } from 'motion/react'

interface BadgeUnlockProps {
  badge: { name: string; icon: string; description: string }
  onDismiss?: () => void
}

export default function BadgeUnlock({ badge, onDismiss }: BadgeUnlockProps) {
  return (
    <motion.div
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className="relative overflow-hidden rounded-xl border p-8 text-center"
      style={{
        backgroundColor: '#1A1A1A',
        borderColor: '#C5A880',
      }}
    >
      {/* Gold shimmer overlay */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        initial={{ x: '-100%' }}
        animate={{ x: '200%' }}
        transition={{ duration: 1.5, delay: 0.3, ease: 'easeInOut' }}
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(197,168,128,0.15) 50%, transparent 100%)',
          width: '50%',
        }}
      />

      {/* Badge icon */}
      <motion.div
        className="text-5xl mb-4"
        initial={{ rotateZ: -30, scale: 0 }}
        animate={{ rotateZ: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 12, delay: 0.2 }}
      >
        {badge.icon}
      </motion.div>

      {/* Badge name */}
      <motion.h3
        className="text-xl font-serif mb-2"
        style={{ color: '#C5A880', fontFamily: 'Georgia, serif' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        {badge.name}
      </motion.h3>

      {/* Earned label */}
      <motion.div
        className="text-xs font-mono tracking-widest uppercase mb-3"
        style={{ color: '#8B7355' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        Earned!
      </motion.div>

      {/* Description */}
      <motion.p
        className="text-sm"
        style={{ color: '#6B6B6B' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        {badge.description}
      </motion.p>

      {/* Dismiss button */}
      {onDismiss && (
        <motion.button
          onClick={onDismiss}
          className="mt-6 px-4 py-2 rounded-md border text-xs font-mono transition-colors"
          style={{
            borderColor: '#1E1E1E',
            color: '#6B6B6B',
            backgroundColor: 'transparent',
          }}
          whileHover={{ borderColor: '#C5A880', color: '#C5A880' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          Continue
        </motion.button>
      )}
    </motion.div>
  )
}
