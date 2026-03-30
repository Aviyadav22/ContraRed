import { Howl, Howler } from 'howler'

const sfxCache: Record<string, Howl> = {}
let ambientHowl: Howl | null = null

const SFX_MAP: Record<string, string> = {
  whoosh: '/audio/sfx/whoosh.ogg',
  chime: '/audio/sfx/chime.ogg',
  correct: '/audio/sfx/correct.ogg',
  wrong: '/audio/sfx/wrong.ogg',
  snap: '/audio/sfx/snap.ogg',
  unlock: '/audio/sfx/unlock.ogg',
  badge: '/audio/sfx/badge-earned.ogg',
  completion: '/audio/sfx/completion-swell.ogg',
}

export const audioManager = {
  playAmbient(src: string) {
    if (ambientHowl) {
      ambientHowl.fade(ambientHowl.volume(), 0, 500)
      setTimeout(() => ambientHowl?.unload(), 600)
    }
    ambientHowl = new Howl({ src: [src], loop: true, volume: 0 })
    ambientHowl.play()
    ambientHowl.fade(0, 0.6, 1000)
  },

  stopAmbient() {
    if (ambientHowl) {
      ambientHowl.fade(ambientHowl.volume(), 0, 500)
      setTimeout(() => { ambientHowl?.unload(); ambientHowl = null }, 600)
    }
  },

  playSfx(name: keyof typeof SFX_MAP) {
    const src = SFX_MAP[name]
    if (!src) return
    if (!sfxCache[name]) {
      sfxCache[name] = new Howl({ src: [src], volume: 0.5 })
    }
    sfxCache[name].play()
  },

  setMuted(muted: boolean) {
    Howler.mute(muted)
  },

  setVolume(vol: number) {
    Howler.volume(vol)
  },
}
