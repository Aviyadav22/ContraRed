import { useEffect } from 'react'
import { useAudio } from '../stores/useAudio'
import { audioManager } from '../lib/audioManager'

export function useAudioPlayer(ambientTrack?: string) {
  const muted = useAudio((s) => s.muted)
  const volume = useAudio((s) => s.volume)
  const setTrack = useAudio((s) => s.setTrack)

  // Sync mute state
  useEffect(() => {
    audioManager.setMuted(muted)
  }, [muted])

  // Sync volume
  useEffect(() => {
    audioManager.setVolume(volume)
  }, [volume])

  // Play ambient track when provided
  useEffect(() => {
    if (ambientTrack) {
      audioManager.playAmbient(ambientTrack)
      setTrack(ambientTrack)
    }
    return () => {
      audioManager.stopAmbient()
    }
  }, [ambientTrack, setTrack])

  return {
    playSfx: audioManager.playSfx.bind(audioManager),
  }
}
