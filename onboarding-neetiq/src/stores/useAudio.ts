import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AudioState {
  muted: boolean
  volume: number
  currentTrack: string | null
  toggleMute: () => void
  setVolume: (volume: number) => void
  setTrack: (track: string | null) => void
  reset: () => void
}

export const useAudio = create<AudioState>()(
  persist(
    (set) => ({
      muted: false,
      volume: 0.6,
      currentTrack: null,
      toggleMute: () => set((state) => ({ muted: !state.muted })),
      setVolume: (volume) => set({ volume: Math.max(0, Math.min(1, volume)) }),
      setTrack: (track) => set({ currentTrack: track }),
      reset: () => set({ muted: false, volume: 0.6, currentTrack: null }),
    }),
    {
      name: 'neetiq-onboarding-audio',
      partialize: (state) => ({ muted: state.muted, volume: state.volume }),
    }
  )
)
