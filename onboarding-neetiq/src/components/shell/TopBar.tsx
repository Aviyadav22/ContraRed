import { useAudio } from '../../stores/useAudio'

interface TopBarProps {
  sessionLabel?: string
}

export default function TopBar({ sessionLabel }: TopBarProps) {
  const { muted, toggleMute } = useAudio()

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-bg/80 backdrop-blur-md border-b border-border flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <span className="text-gold font-serif text-lg font-semibold tracking-wide">NeetiQ</span>
        {sessionLabel && (
          <span className="text-text-muted font-mono text-xs uppercase tracking-widest">
            {sessionLabel}
          </span>
        )}
      </div>
      <div className="flex items-center gap-4">
        <button
          onClick={toggleMute}
          className="text-text-muted hover:text-gold transition-colors text-sm font-mono"
          aria-label={muted ? 'Unmute audio' : 'Mute audio'}
        >
          {muted ? '\u{1F507}' : '\u{1F50A}'}
        </button>
      </div>
    </header>
  )
}
