# Audio Assets

This directory contains placeholder audio files for the NeetiQ onboarding experience. The files are currently empty stubs — Howler.js will fail silently when attempting to load them, which is acceptable during development.

## Sourcing Real Assets

### Ambient tracks (`ambient/`)

Session background music loops. Source from:
- [Freesound.org](https://freesound.org) — search for "ambient loop", CC0 license
- [Pixabay Music](https://pixabay.com/music/) — royalty-free

| File | Description | Mood |
|------|-------------|------|
| `session-1-warm.ogg` | Warm acoustic/pad loop | Welcoming, safe |
| `session-2-electronic.ogg` | Light electronic loop | Focused, modern |
| `session-3-tense.ogg` | Subtle tension loop | Suspenseful, alert |
| `session-4-triumphant.ogg` | Uplifting orchestral loop | Celebratory, grand |

### Sound effects (`sfx/`)

Short one-shot sounds. Generate with:
- [jsfxr](https://sfxr.me/) — retro/UI sound generator
- [Freesound.org](https://freesound.org) — CC0 samples

| File | Description | Duration |
|------|-------------|----------|
| `whoosh.ogg` | Transition swoosh | ~0.3s |
| `chime.ogg` | Notification chime | ~0.5s |
| `correct.ogg` | Correct answer ding | ~0.4s |
| `wrong.ogg` | Wrong answer buzz | ~0.3s |
| `snap.ogg` | Snap/click for drag interactions | ~0.2s |
| `unlock.ogg` | Unlock sound for achievements | ~0.6s |
| `badge-earned.ogg` | Badge award fanfare | ~1.0s |
| `completion-swell.ogg` | Session completion swell | ~1.5s |

## Format Requirements

- Format: OGG Vorbis (`.ogg`) — best browser support with small file size
- Sample rate: 44100 Hz
- Ambient tracks: mono, 96-128 kbps, loopable
- SFX: mono, 128 kbps
