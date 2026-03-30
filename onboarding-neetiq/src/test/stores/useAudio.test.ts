import { describe, it, expect, beforeEach } from 'vitest'
import { useAudio } from '../../stores/useAudio'

describe('useAudio store', () => {
  beforeEach(() => {
    useAudio.getState().reset()
    localStorage.clear()
  })

  it('initializes with audio enabled', () => {
    expect(useAudio.getState().muted).toBe(false)
  })

  it('toggles mute', () => {
    useAudio.getState().toggleMute()
    expect(useAudio.getState().muted).toBe(true)
    useAudio.getState().toggleMute()
    expect(useAudio.getState().muted).toBe(false)
  })

  it('sets current track', () => {
    useAudio.getState().setTrack('/audio/ambient/session-1-origin.ogg')
    expect(useAudio.getState().currentTrack).toBe('/audio/ambient/session-1-origin.ogg')
  })

  it('sets volume', () => {
    useAudio.getState().setVolume(0.5)
    expect(useAudio.getState().volume).toBe(0.5)
  })

  it('persists mute state', () => {
    useAudio.getState().toggleMute()
    const saved = localStorage.getItem('neetiq-onboarding-audio')
    expect(saved).toBeTruthy()
    const parsed = JSON.parse(saved!)
    expect(parsed.state.muted).toBe(true)
  })
})
