# NeetiQ Onboarding Chronicles — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a cinematic, interactive onboarding experience at `onboarding.neetiq.in` — a multi-book library starting with "The ContraRed Chronicle" (4 sessions, 15 chapters, 3D heroes, scroll animations, audio, quiz gates).

**Architecture:** Standalone React 19 SPA with GSAP ScrollTrigger for scroll-driven animations, React Three Fiber for 4 session-intro 3D scenes, Howler.js for ambient audio + SFX, Zustand for state, localStorage for persistence, JSON files for content. Deployed on Netlify.

**Tech Stack:** React 19, Vite 7, TypeScript, TailwindCSS 4, GSAP + ScrollTrigger, Motion (Framer Motion), React Three Fiber + drei + postprocessing, Howler.js, Rough.js, @dnd-kit, Zustand, Lottie, Netlify.

**Design Doc:** `docs/plans/2026-03-31-neetiq-onboarding-chronicles-design.md`

**Source Content:** `story/` folder (15 markdown chapter files to transform into JSON)

---

## Phase 1: Project Scaffold (Foundation)

### Task 1: Initialize Vite + React + TypeScript project

**Files:**
- Create: `onboarding-neetiq/package.json`
- Create: `onboarding-neetiq/vite.config.ts`
- Create: `onboarding-neetiq/tsconfig.json`
- Create: `onboarding-neetiq/tsconfig.app.json`
- Create: `onboarding-neetiq/tsconfig.node.json`
- Create: `onboarding-neetiq/index.html`
- Create: `onboarding-neetiq/src/main.tsx`
- Create: `onboarding-neetiq/src/App.tsx`
- Create: `onboarding-neetiq/src/vite-env.d.ts`

**Step 1: Scaffold the project**

```bash
cd "d:/Startup/Redliniing/V1 addon word"
npm create vite@latest onboarding-neetiq -- --template react-ts
```

**Step 2: Install core dependencies**

```bash
cd onboarding-neetiq
npm install react-router-dom@7 zustand
npm install -D tailwindcss@4 @tailwindcss/vite
```

**Step 3: Install animation dependencies**

```bash
npm install gsap @gsap/react motion lottie-react roughjs
```

**Step 4: Install 3D dependencies**

```bash
npm install three @react-three/fiber @react-three/drei @react-three/postprocessing
npm install -D @types/three
```

**Step 5: Install audio + quiz dependencies**

```bash
npm install howler @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
npm install -D @types/howler
```

**Step 6: Install testing dependencies**

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

**Step 7: Verify it runs**

```bash
npm run dev
```
Expected: Vite dev server starts at localhost:5173, default React page loads.

**Step 8: Commit**

```bash
git add onboarding-neetiq/
git commit -m "feat(onboarding): scaffold Vite + React + TypeScript project with all dependencies"
```

---

### Task 2: Configure TailwindCSS with NeetiQ design tokens

**Files:**
- Create: `onboarding-neetiq/src/styles/tailwind.css`
- Modify: `onboarding-neetiq/vite.config.ts`
- Create: `onboarding-neetiq/tailwind.config.ts`
- Modify: `onboarding-neetiq/index.html` (add font links)

**Step 1: Create tailwind.css with NeetiQ tokens**

Create `onboarding-neetiq/src/styles/tailwind.css`:
```css
@import "tailwindcss";

@theme {
  /* NeetiQ Color Palette */
  --color-bg: #0A0A0A;
  --color-surface: #111111;
  --color-surface-elevated: #1A1A1A;
  --color-border: #1E1E1E;
  --color-text-primary: #E8E8E8;
  --color-text-muted: #6B6B6B;
  --color-gold: #C5A880;
  --color-gold-dim: #8B7355;
  --color-risk-red: #DC2626;
  --color-risk-yellow: #EAB308;
  --color-risk-green: #22C55E;

  /* Typography */
  --font-family-serif: Georgia, 'Times New Roman', serif;
  --font-family-sans: 'Inter', system-ui, sans-serif;
  --font-family-mono: 'JetBrains Mono', monospace;
  --font-family-handwriting: 'Caveat', cursive;
}
```

**Step 2: Add Vite TailwindCSS plugin**

Update `onboarding-neetiq/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

**Step 3: Add Google Fonts to index.html**

Add to `<head>` in `onboarding-neetiq/index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Caveat:wght@400;600&display=swap" rel="stylesheet">
```

**Step 4: Update main.tsx to import tailwind.css**

```typescript
import './styles/tailwind.css'
```

**Step 5: Verify Tailwind works**

Update `App.tsx` to use a NeetiQ-styled div:
```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text-primary">
      <h1 className="text-gold font-serif text-4xl p-8">NeetiQ Chronicles</h1>
    </div>
  )
}
```

Run: `npm run dev`
Expected: Dark background (#0A0A0A), gold heading in Georgia serif.

**Step 6: Commit**

```bash
git add onboarding-neetiq/
git commit -m "feat(onboarding): configure TailwindCSS 4 with NeetiQ design tokens"
```

---

### Task 3: Add grain texture, grid overlay, and base CSS animations

**Files:**
- Create: `onboarding-neetiq/src/styles/grain.css`
- Create: `onboarding-neetiq/src/styles/animations.css`
- Modify: `onboarding-neetiq/src/styles/tailwind.css` (import new files)

**Step 1: Create grain.css**

Create `onboarding-neetiq/src/styles/grain.css`:
```css
/* SVG noise grain overlay — NeetiQ manuscript texture */
.grain-overlay::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.022;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}

/* Palantir-style subtle grid */
.grid-overlay::after {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9998;
  pointer-events: none;
  opacity: 0.025;
  background-image:
    linear-gradient(rgba(197, 168, 128, 0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(197, 168, 128, 0.3) 1px, transparent 1px);
  background-size: 60px 60px;
}
```

**Step 2: Create animations.css**

Create `onboarding-neetiq/src/styles/animations.css`:
```css
/* Gold scan-divider sweep between chapters */
@keyframes scan-sweep {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.scan-divider {
  position: relative;
  height: 1px;
  background: var(--color-border);
  overflow: hidden;
  margin: 3rem 0;
}

.scan-divider::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, var(--color-gold), transparent);
  animation: scan-sweep 2s ease-in-out;
}

/* Clip reveal from bottom */
@keyframes clip-reveal {
  from {
    clip-path: inset(100% 0 0 0);
    transform: translateY(20px);
  }
  to {
    clip-path: inset(0 0 0 0);
    transform: translateY(0);
  }
}

/* Gold underline wipe */
@keyframes underline-wipe {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}

/* Typewriter cursor blink */
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.cursor-blink::after {
  content: '▊';
  color: var(--color-gold);
  animation: cursor-blink 0.8s infinite;
}

/* Fade in up */
@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Shimmer for locked books */
@keyframes shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

.shimmer {
  background: linear-gradient(
    90deg,
    var(--color-border) 25%,
    var(--color-gold-dim) 50%,
    var(--color-border) 75%
  );
  background-size: 200% auto;
  animation: shimmer 3s ease-in-out infinite;
}
```

**Step 3: Import in tailwind.css**

Add to top of `tailwind.css`:
```css
@import "./grain.css";
@import "./animations.css";
```

**Step 4: Add grain + grid to App.tsx**

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay">
      <h1 className="text-gold font-serif text-4xl p-8">NeetiQ Chronicles</h1>
      <div className="scan-divider mx-8" />
    </div>
  )
}
```

**Step 5: Verify visually**

Run: `npm run dev`
Expected: Dark background with subtle grain texture, faint grid lines, gold divider line with sweep animation.

**Step 6: Commit**

```bash
git add onboarding-neetiq/
git commit -m "feat(onboarding): add grain texture, grid overlay, and CSS animation system"
```

---

### Task 4: Set up Vitest and test configuration

**Files:**
- Create: `onboarding-neetiq/vitest.config.ts`
- Create: `onboarding-neetiq/src/test/setup.ts`
- Modify: `onboarding-neetiq/package.json` (add test script)

**Step 1: Create vitest config**

Create `onboarding-neetiq/vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})
```

**Step 2: Create test setup file**

Create `onboarding-neetiq/src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

**Step 3: Add test script to package.json**

Add to `scripts` in `package.json`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

**Step 4: Write a smoke test**

Create `onboarding-neetiq/src/test/smoke.test.ts`:
```typescript
import { describe, it, expect } from 'vitest'

describe('smoke test', () => {
  it('project is configured correctly', () => {
    expect(1 + 1).toBe(2)
  })
})
```

**Step 5: Run test to verify**

```bash
cd onboarding-neetiq && npm test
```
Expected: 1 test passes.

**Step 6: Commit**

```bash
git add onboarding-neetiq/
git commit -m "feat(onboarding): configure Vitest with jsdom environment"
```

---

## Phase 2: State Management & Persistence

### Task 5: Create Zustand progress store with localStorage persistence

**Files:**
- Create: `onboarding-neetiq/src/stores/useProgress.ts`
- Create: `onboarding-neetiq/src/test/stores/useProgress.test.ts`

**Step 1: Write failing tests for progress store**

Create `onboarding-neetiq/src/test/stores/useProgress.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useProgress } from '../../stores/useProgress'

describe('useProgress store', () => {
  beforeEach(() => {
    useProgress.getState().reset()
    localStorage.clear()
  })

  it('initializes with contrared book available, session 1 available', () => {
    const state = useProgress.getState()
    expect(state.books.contrared.status).toBe('available')
    expect(state.books.contrared.sessions[1].status).toBe('available')
    expect(state.books.contrared.sessions[2].status).toBe('locked')
  })

  it('starts a session', () => {
    useProgress.getState().startSession('contrared', 1)
    const session = useProgress.getState().books.contrared.sessions[1]
    expect(session.status).toBe('in_progress')
    expect(session.unlockedAt).toBeTruthy()
  })

  it('completes a chapter', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().completeChapter('contrared', 1, 1)
    const session = useProgress.getState().books.contrared.sessions[1]
    expect(session.chaptersCompleted).toContain(1)
    expect(session.currentChapter).toBe(2)
  })

  it('updates scroll progress', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().updateScrollProgress('contrared', 1, 45)
    const session = useProgress.getState().books.contrared.sessions[1]
    expect(session.scrollProgress).toBe(45)
  })

  it('records quiz score and unlocks next session on pass', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().submitQuiz('contrared', 1, 3, 3, { q1: 'a', q2: 'b', q3: 'c' })
    const s1 = useProgress.getState().books.contrared.sessions[1]
    const s2 = useProgress.getState().books.contrared.sessions[2]
    expect(s1.quiz.passed).toBe(true)
    expect(s1.quiz.score).toBe(3)
    expect(s1.status).toBe('completed')
    expect(s2.status).toBe('available')
  })

  it('does not unlock next session on quiz fail', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().submitQuiz('contrared', 1, 1, 3, { q1: 'a' })
    const s1 = useProgress.getState().books.contrared.sessions[1]
    const s2 = useProgress.getState().books.contrared.sessions[2]
    expect(s1.quiz.passed).toBe(false)
    expect(s1.status).toBe('in_progress')
    expect(s2.status).toBe('locked')
  })

  it('awards badges on session completion', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().submitQuiz('contrared', 1, 3, 3, {})
    const badges = useProgress.getState().books.contrared.badges
    expect(badges).toContain('the-origin')
  })

  it('calculates overall progress', () => {
    useProgress.getState().startSession('contrared', 1)
    useProgress.getState().submitQuiz('contrared', 1, 3, 3, {})
    expect(useProgress.getState().overallProgress).toBe(25) // 1 of 4 sessions
  })

  it('persists to localStorage', () => {
    useProgress.getState().startSession('contrared', 1)
    // Simulate rehydration
    const saved = localStorage.getItem('neetiq-onboarding-progress')
    expect(saved).toBeTruthy()
    const parsed = JSON.parse(saved!)
    expect(parsed.state.books.contrared.sessions[1].status).toBe('in_progress')
  })
})
```

**Step 2: Run tests — verify they fail**

```bash
cd onboarding-neetiq && npm test
```
Expected: FAIL — module `../../stores/useProgress` not found.

**Step 3: Implement the progress store**

Create `onboarding-neetiq/src/stores/useProgress.ts`:
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface QuizState {
  attempts: number
  score: number
  passed: boolean
  answers: Record<string, string>
}

interface SessionState {
  status: 'locked' | 'available' | 'in_progress' | 'completed'
  unlockedAt: string | null
  completedAt: string | null
  chaptersCompleted: number[]
  currentChapter: number
  scrollProgress: number
  timeSpentSeconds: number
  quiz: QuizState
}

interface BookState {
  status: 'locked' | 'available' | 'in_progress' | 'completed'
  sessions: Record<number, SessionState>
  badges: string[]
}

interface ProgressState {
  user: { id: string; name: string; email: string; startedAt: string } | null
  books: Record<string, BookState>
  overallProgress: number

  // Actions
  setUser: (user: { id: string; name: string; email: string }) => void
  startSession: (bookId: string, sessionId: number) => void
  completeChapter: (bookId: string, sessionId: number, chapterId: number) => void
  updateScrollProgress: (bookId: string, sessionId: number, progress: number) => void
  submitQuiz: (bookId: string, sessionId: number, score: number, total: number, answers: Record<string, string>) => void
  addTime: (bookId: string, sessionId: number, seconds: number) => void
  reset: () => void
}

const SESSION_BADGES: Record<number, string> = {
  1: 'the-origin',
  2: 'tech-architect',
  3: 'battle-tested',
  4: 'full-spectrum',
}

const PASSING_SCORE = 0.7

function createDefaultSession(status: 'locked' | 'available'): SessionState {
  return {
    status,
    unlockedAt: null,
    completedAt: null,
    chaptersCompleted: [],
    currentChapter: 1,
    scrollProgress: 0,
    timeSpentSeconds: 0,
    quiz: { attempts: 0, score: 0, passed: false, answers: {} },
  }
}

function createDefaultBooks(): Record<string, BookState> {
  return {
    contrared: {
      status: 'available',
      sessions: {
        1: createDefaultSession('available'),
        2: createDefaultSession('locked'),
        3: createDefaultSession('locked'),
        4: createDefaultSession('locked'),
      },
      badges: [],
    },
  }
}

function calculateOverallProgress(books: Record<string, BookState>): number {
  let completedSessions = 0
  let totalSessions = 0
  for (const book of Object.values(books)) {
    for (const session of Object.values(book.sessions)) {
      totalSessions++
      if (session.status === 'completed') completedSessions++
    }
  }
  return totalSessions === 0 ? 0 : Math.round((completedSessions / totalSessions) * 100)
}

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      user: null,
      books: createDefaultBooks(),
      overallProgress: 0,

      setUser: (user) => set({ user: { ...user, startedAt: new Date().toISOString() } }),

      startSession: (bookId, sessionId) =>
        set((state) => {
          const books = structuredClone(state.books)
          const session = books[bookId].sessions[sessionId]
          if (session.status === 'locked') return state
          session.status = 'in_progress'
          session.unlockedAt = session.unlockedAt ?? new Date().toISOString()
          books[bookId].status = 'in_progress'
          return { books }
        }),

      completeChapter: (bookId, sessionId, chapterId) =>
        set((state) => {
          const books = structuredClone(state.books)
          const session = books[bookId].sessions[sessionId]
          if (!session.chaptersCompleted.includes(chapterId)) {
            session.chaptersCompleted.push(chapterId)
          }
          session.currentChapter = chapterId + 1
          return { books }
        }),

      updateScrollProgress: (bookId, sessionId, progress) =>
        set((state) => {
          const books = structuredClone(state.books)
          books[bookId].sessions[sessionId].scrollProgress = progress
          return { books }
        }),

      submitQuiz: (bookId, sessionId, score, total, answers) =>
        set((state) => {
          const books = structuredClone(state.books)
          const session = books[bookId].sessions[sessionId]
          const passed = score / total >= PASSING_SCORE

          session.quiz = {
            attempts: session.quiz.attempts + 1,
            score,
            passed,
            answers,
          }

          if (passed) {
            session.status = 'completed'
            session.completedAt = new Date().toISOString()

            // Award session badge
            const badge = SESSION_BADGES[sessionId]
            if (badge && !books[bookId].badges.includes(badge)) {
              books[bookId].badges.push(badge)
            }

            // Perfect score badge
            if (score === total && !books[bookId].badges.includes('perfect-score')) {
              books[bookId].badges.push('perfect-score')
            }

            // Unlock next session
            const nextSession = books[bookId].sessions[sessionId + 1]
            if (nextSession && nextSession.status === 'locked') {
              nextSession.status = 'available'
            }

            // Check if all sessions complete
            const allComplete = Object.values(books[bookId].sessions).every(
              (s) => s.status === 'completed'
            )
            if (allComplete) {
              books[bookId].status = 'completed'
              if (!books[bookId].badges.includes('chronicle-complete')) {
                books[bookId].badges.push('chronicle-complete')
              }
            }
          }

          return { books, overallProgress: calculateOverallProgress(books) }
        }),

      addTime: (bookId, sessionId, seconds) =>
        set((state) => {
          const books = structuredClone(state.books)
          books[bookId].sessions[sessionId].timeSpentSeconds += seconds
          return { books }
        }),

      reset: () => set({ user: null, books: createDefaultBooks(), overallProgress: 0 }),
    }),
    {
      name: 'neetiq-onboarding-progress',
    }
  )
)
```

**Step 4: Run tests — verify they pass**

```bash
cd onboarding-neetiq && npm test
```
Expected: All 9 tests pass.

**Step 5: Commit**

```bash
git add onboarding-neetiq/src/stores/ onboarding-neetiq/src/test/stores/
git commit -m "feat(onboarding): add Zustand progress store with localStorage persistence"
```

---

### Task 6: Create Zustand audio store

**Files:**
- Create: `onboarding-neetiq/src/stores/useAudio.ts`
- Create: `onboarding-neetiq/src/test/stores/useAudio.test.ts`

**Step 1: Write failing tests**

Create `onboarding-neetiq/src/test/stores/useAudio.test.ts`:
```typescript
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
```

**Step 2: Run tests — verify they fail**

```bash
cd onboarding-neetiq && npm test
```
Expected: FAIL — module not found.

**Step 3: Implement the audio store**

Create `onboarding-neetiq/src/stores/useAudio.ts`:
```typescript
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
```

**Step 4: Run tests — verify they pass**

```bash
cd onboarding-neetiq && npm test
```
Expected: All tests pass.

**Step 5: Commit**

```bash
git add onboarding-neetiq/src/stores/useAudio.ts onboarding-neetiq/src/test/stores/useAudio.test.ts
git commit -m "feat(onboarding): add Zustand audio store with mute persistence"
```

---

### Task 7: Create Zustand quiz store

**Files:**
- Create: `onboarding-neetiq/src/stores/useQuiz.ts`
- Create: `onboarding-neetiq/src/test/stores/useQuiz.test.ts`

**Step 1: Write failing tests**

Create `onboarding-neetiq/src/test/stores/useQuiz.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useQuiz } from '../../stores/useQuiz'

describe('useQuiz store', () => {
  beforeEach(() => {
    useQuiz.getState().reset()
  })

  it('initializes with empty state', () => {
    const state = useQuiz.getState()
    expect(state.currentQuestion).toBe(0)
    expect(state.answers).toEqual({})
    expect(state.submitted).toBe(false)
  })

  it('loads questions', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'true-false', question: 'Test?', correctAnswer: 'true', explanation: 'Because.' },
    ])
    expect(useQuiz.getState().questions).toHaveLength(1)
  })

  it('records an answer', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'true-false', question: 'Test?', correctAnswer: 'true', explanation: 'Because.' },
    ])
    useQuiz.getState().answerQuestion('q1', 'true')
    expect(useQuiz.getState().answers.q1).toBe('true')
  })

  it('advances to next question', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'true-false', question: 'Q1?', correctAnswer: 'true', explanation: '' },
      { id: 'q2', format: 'true-false', question: 'Q2?', correctAnswer: 'false', explanation: '' },
    ])
    useQuiz.getState().nextQuestion()
    expect(useQuiz.getState().currentQuestion).toBe(1)
  })

  it('calculates score on submit', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'true-false', question: 'Q1?', correctAnswer: 'true', explanation: '' },
      { id: 'q2', format: 'true-false', question: 'Q2?', correctAnswer: 'false', explanation: '' },
      { id: 'q3', format: 'true-false', question: 'Q3?', correctAnswer: 'true', explanation: '' },
    ])
    useQuiz.getState().answerQuestion('q1', 'true')  // correct
    useQuiz.getState().answerQuestion('q2', 'true')  // wrong
    useQuiz.getState().answerQuestion('q3', 'true')  // correct
    const result = useQuiz.getState().submit()
    expect(result.score).toBe(2)
    expect(result.total).toBe(3)
    expect(result.passed).toBe(false) // 2/3 = 66% < 70%
  })

  it('passes quiz at 70% threshold', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'true-false', question: 'Q1?', correctAnswer: 'true', explanation: '' },
      { id: 'q2', format: 'true-false', question: 'Q2?', correctAnswer: 'false', explanation: '' },
      { id: 'q3', format: 'true-false', question: 'Q3?', correctAnswer: 'true', explanation: '' },
    ])
    useQuiz.getState().answerQuestion('q1', 'true')
    useQuiz.getState().answerQuestion('q2', 'false')
    useQuiz.getState().answerQuestion('q3', 'true')
    const result = useQuiz.getState().submit()
    expect(result.score).toBe(3)
    expect(result.passed).toBe(true)
  })

  it('handles drag-order answers (array comparison)', () => {
    useQuiz.getState().loadQuestions([
      { id: 'q1', format: 'drag-order', question: 'Order?', correctAnswer: ['a', 'b', 'c'], explanation: '' },
    ])
    useQuiz.getState().answerQuestion('q1', JSON.stringify(['a', 'b', 'c']))
    const result = useQuiz.getState().submit()
    expect(result.score).toBe(1)
  })
})
```

**Step 2: Run tests — verify they fail**

```bash
cd onboarding-neetiq && npm test
```
Expected: FAIL.

**Step 3: Implement the quiz store**

Create `onboarding-neetiq/src/stores/useQuiz.ts`:
```typescript
import { create } from 'zustand'

interface Question {
  id: string
  format: 'true-false' | 'drag-order' | 'multiple-choice' | 'interactive'
  question: string
  options?: string[]
  correctAnswer: string | string[]
  explanation: string
}

interface QuizResult {
  score: number
  total: number
  passed: boolean
  answers: Record<string, string>
}

interface QuizState {
  questions: Question[]
  currentQuestion: number
  answers: Record<string, string>
  submitted: boolean
  result: QuizResult | null

  loadQuestions: (questions: Question[]) => void
  answerQuestion: (questionId: string, answer: string) => void
  nextQuestion: () => void
  prevQuestion: () => void
  submit: () => QuizResult
  reset: () => void
}

const PASSING_SCORE = 0.7

function isCorrect(question: Question, answer: string): boolean {
  if (Array.isArray(question.correctAnswer)) {
    try {
      const parsed = JSON.parse(answer)
      if (Array.isArray(parsed)) {
        return JSON.stringify(parsed) === JSON.stringify(question.correctAnswer)
      }
    } catch {
      // Not JSON, compare as string
    }
    return false
  }
  return answer === question.correctAnswer
}

export const useQuiz = create<QuizState>()((set, get) => ({
  questions: [],
  currentQuestion: 0,
  answers: {},
  submitted: false,
  result: null,

  loadQuestions: (questions) => set({ questions, currentQuestion: 0, answers: {}, submitted: false, result: null }),

  answerQuestion: (questionId, answer) =>
    set((state) => ({ answers: { ...state.answers, [questionId]: answer } })),

  nextQuestion: () =>
    set((state) => ({
      currentQuestion: Math.min(state.currentQuestion + 1, state.questions.length - 1),
    })),

  prevQuestion: () =>
    set((state) => ({
      currentQuestion: Math.max(state.currentQuestion - 1, 0),
    })),

  submit: () => {
    const { questions, answers } = get()
    let score = 0
    for (const q of questions) {
      const answer = answers[q.id]
      if (answer && isCorrect(q, answer)) score++
    }
    const result: QuizResult = {
      score,
      total: questions.length,
      passed: score / questions.length >= PASSING_SCORE,
      answers,
    }
    set({ submitted: true, result })
    return result
  },

  reset: () => set({ questions: [], currentQuestion: 0, answers: {}, submitted: false, result: null }),
}))
```

**Step 4: Run tests — verify they pass**

```bash
cd onboarding-neetiq && npm test
```
Expected: All tests pass.

**Step 5: Commit**

```bash
git add onboarding-neetiq/src/stores/useQuiz.ts onboarding-neetiq/src/test/stores/useQuiz.test.ts
git commit -m "feat(onboarding): add Zustand quiz store with scoring and pass/fail logic"
```

---

## Phase 3: App Shell & Routing

### Task 8: Set up React Router with multi-book routes

**Files:**
- Modify: `onboarding-neetiq/src/App.tsx`
- Create: `onboarding-neetiq/src/routes/Home.tsx`
- Create: `onboarding-neetiq/src/routes/books/contrared/Landing.tsx`
- Create: `onboarding-neetiq/src/routes/books/contrared/Session.tsx`
- Create: `onboarding-neetiq/src/routes/Lock.tsx`
- Create: `onboarding-neetiq/src/routes/Completion.tsx`

**Step 1: Create placeholder route components**

Create each file with a minimal placeholder:

`onboarding-neetiq/src/routes/Home.tsx`:
```tsx
export default function Home() {
  return <div className="min-h-screen bg-bg text-text-primary p-8">
    <h1 className="text-gold font-serif text-4xl">The NeetiQ Chronicles</h1>
    <p className="text-text-muted mt-2">Your onboarding library. Pick a book.</p>
  </div>
}
```

`onboarding-neetiq/src/routes/books/contrared/Landing.tsx`:
```tsx
export default function ContraRedLanding() {
  return <div className="min-h-screen bg-bg text-text-primary p-8">
    <h1 className="text-gold font-serif text-3xl">The ContraRed Chronicle</h1>
    <p className="text-text-muted mt-2">4 sessions across your first week.</p>
  </div>
}
```

`onboarding-neetiq/src/routes/books/contrared/Session.tsx`:
```tsx
import { useParams } from 'react-router-dom'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  return <div className="min-h-screen bg-bg text-text-primary p-8">
    <h1 className="text-gold font-serif text-3xl">Session {sessionId}</h1>
  </div>
}
```

`onboarding-neetiq/src/routes/Lock.tsx`:
```tsx
export default function Lock() {
  return <div className="min-h-screen bg-bg text-text-primary flex items-center justify-center">
    <div className="text-center">
      <div className="text-6xl mb-4">🔒</div>
      <h2 className="text-gold font-serif text-2xl">Session Locked</h2>
      <p className="text-text-muted mt-2">Complete the previous session to unlock.</p>
    </div>
  </div>
}
```

`onboarding-neetiq/src/routes/Completion.tsx`:
```tsx
export default function Completion() {
  return <div className="min-h-screen bg-bg text-text-primary flex items-center justify-center">
    <div className="text-center">
      <h1 className="text-gold font-serif text-4xl">Chronicle Complete</h1>
    </div>
  </div>
}
```

**Step 2: Wire up App.tsx with router**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'

const Home = lazy(() => import('./routes/Home'))
const ContraRedLanding = lazy(() => import('./routes/books/contrared/Landing'))
const ContraRedSession = lazy(() => import('./routes/books/contrared/Session'))
const Lock = lazy(() => import('./routes/Lock'))
const Completion = lazy(() => import('./routes/Completion'))

function Loading() {
  return <div className="min-h-screen bg-bg flex items-center justify-center">
    <div className="text-gold animate-pulse font-mono text-sm">Loading...</div>
  </div>
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay">
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/contrared" element={<ContraRedLanding />} />
            <Route path="/contrared/session/:sessionId" element={<ContraRedSession />} />
            <Route path="/locked" element={<Lock />} />
            <Route path="/completion" element={<Completion />} />
          </Routes>
        </Suspense>
      </div>
    </BrowserRouter>
  )
}
```

**Step 3: Verify routing works**

```bash
cd onboarding-neetiq && npm run dev
```
Navigate to: `/`, `/contrared`, `/contrared/session/1`, `/locked`, `/completion`
Expected: Each route shows its placeholder content.

**Step 4: Commit**

```bash
git add onboarding-neetiq/src/
git commit -m "feat(onboarding): set up React Router with multi-book route structure"
```

---

### Task 9: Build TopBar and ProgressBar shell components

**Files:**
- Create: `onboarding-neetiq/src/components/shell/TopBar.tsx`
- Create: `onboarding-neetiq/src/components/shell/ProgressBar.tsx`
- Create: `onboarding-neetiq/src/components/shell/ScanDivider.tsx`
- Create: `onboarding-neetiq/src/components/shell/Layout.tsx`

**Step 1: Build TopBar**

Create `onboarding-neetiq/src/components/shell/TopBar.tsx`:
```tsx
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
          {muted ? '🔇' : '🔊'}
        </button>
      </div>
    </header>
  )
}
```

**Step 2: Build ProgressBar**

Create `onboarding-neetiq/src/components/shell/ProgressBar.tsx`:
```tsx
interface ProgressBarProps {
  current: number
  total: number
  label?: string
}

export default function ProgressBar({ current, total, label }: ProgressBarProps) {
  const percentage = total === 0 ? 0 : Math.round((current / total) * 100)

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 h-10 bg-bg/80 backdrop-blur-md border-t border-border flex items-center px-6 gap-4">
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-gold rounded-full transition-all duration-700 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-text-muted font-mono text-xs whitespace-nowrap">
        {label ?? `${percentage}%`}
      </span>
    </footer>
  )
}
```

**Step 3: Build ScanDivider**

Create `onboarding-neetiq/src/components/shell/ScanDivider.tsx`:
```tsx
interface ScanDividerProps {
  className?: string
}

export default function ScanDivider({ className = '' }: ScanDividerProps) {
  return <div className={`scan-divider ${className}`} />
}
```

**Step 4: Build Layout wrapper**

Create `onboarding-neetiq/src/components/shell/Layout.tsx`:
```tsx
import { ReactNode } from 'react'
import TopBar from './TopBar'
import ProgressBar from './ProgressBar'

interface LayoutProps {
  children: ReactNode
  sessionLabel?: string
  progress?: { current: number; total: number; label?: string }
}

export default function Layout({ children, sessionLabel, progress }: LayoutProps) {
  return (
    <>
      <TopBar sessionLabel={sessionLabel} />
      <main className="pt-14 pb-10">
        {children}
      </main>
      {progress && <ProgressBar {...progress} />}
    </>
  )
}
```

**Step 5: Wire Layout into a session route for visual verification**

Update `ContraRedSession.tsx` to use Layout:
```tsx
import { useParams } from 'react-router-dom'
import Layout from '../../../components/shell/Layout'
import ScanDivider from '../../../components/shell/ScanDivider'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  return (
    <Layout
      sessionLabel={`Session ${sessionId} of 4`}
      progress={{ current: 2, total: 5, label: 'Ch 2 of 5' }}
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-gold font-serif text-4xl">Session {sessionId}</h1>
        <ScanDivider className="my-8" />
        <p className="text-text-muted">Content will go here...</p>
      </div>
    </Layout>
  )
}
```

**Step 6: Verify visually**

```bash
cd onboarding-neetiq && npm run dev
```
Navigate to `/contrared/session/1`.
Expected: Top bar with "NeetiQ" logo + session label + mute button. Bottom progress bar at 40%. Gold scan divider between title and content.

**Step 7: Commit**

```bash
git add onboarding-neetiq/src/components/shell/ onboarding-neetiq/src/routes/
git commit -m "feat(onboarding): build shell components — TopBar, ProgressBar, ScanDivider, Layout"
```

---

## Phase 4: Scroll Animation Primitives

### Task 10: Build GSAP ScrollTrigger scroll section component

**Files:**
- Create: `onboarding-neetiq/src/components/scroll/ScrollSection.tsx`
- Create: `onboarding-neetiq/src/hooks/useScrollAnimation.ts`

**Step 1: Create the GSAP scroll hook**

Create `onboarding-neetiq/src/hooks/useScrollAnimation.ts`:
```typescript
import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useScrollAnimation() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  }, [])

  return { containerRef, gsap, ScrollTrigger }
}
```

**Step 2: Create ScrollSection component**

Create `onboarding-neetiq/src/components/scroll/ScrollSection.tsx`:
```tsx
import { useEffect, useRef, ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface ScrollSectionProps {
  children: ReactNode
  pin?: boolean
  scrub?: boolean | number
  className?: string
  onEnter?: () => void
  onLeave?: () => void
}

export default function ScrollSection({
  children,
  pin = false,
  scrub = false,
  className = '',
  onEnter,
  onLeave,
}: ScrollSectionProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 80%',
      end: pin ? '+=100%' : 'bottom 20%',
      pin: pin ? ref.current : false,
      scrub: scrub,
      onEnter,
      onLeave,
    })

    // Animate children in
    const children = ref.current.querySelectorAll('.reveal-child')
    if (children.length > 0) {
      gsap.fromTo(
        children,
        { opacity: 0, y: 30 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.12,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: ref.current,
            start: 'top 80%',
          },
        }
      )
    }

    return () => {
      trigger.kill()
    }
  }, [pin, scrub, onEnter, onLeave])

  return (
    <div ref={ref} className={`min-h-[50vh] ${className}`}>
      {children}
    </div>
  )
}
```

**Step 3: Verify with a test page**

Update `ContraRedSession.tsx` to use ScrollSection:
```tsx
import { useParams } from 'react-router-dom'
import Layout from '../../../components/shell/Layout'
import ScanDivider from '../../../components/shell/ScanDivider'
import ScrollSection from '../../../components/scroll/ScrollSection'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  return (
    <Layout
      sessionLabel={`Session ${sessionId} of 4`}
      progress={{ current: 2, total: 5, label: 'Ch 2 of 5' }}
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        {[1, 2, 3, 4, 5].map((i) => (
          <ScrollSection key={i}>
            <h2 className="reveal-child text-gold font-serif text-3xl mb-4">Section {i}</h2>
            <p className="reveal-child text-text-muted">Content reveals as you scroll down...</p>
            <ScanDivider className="mt-12 reveal-child" />
          </ScrollSection>
        ))}
      </div>
    </Layout>
  )
}
```

**Step 4: Verify visually**

```bash
cd onboarding-neetiq && npm run dev
```
Navigate to `/contrared/session/1`, scroll down.
Expected: Sections fade-in + slide-up as they enter the viewport, staggered 120ms between children.

**Step 5: Commit**

```bash
git add onboarding-neetiq/src/components/scroll/ onboarding-neetiq/src/hooks/
git commit -m "feat(onboarding): build GSAP ScrollTrigger scroll section with reveal animations"
```

---

### Task 11: Build text animation components (TextReveal, BodyReveal, CodeTyper, CounterReveal)

**Files:**
- Create: `onboarding-neetiq/src/components/scroll/TextReveal.tsx`
- Create: `onboarding-neetiq/src/components/scroll/BodyReveal.tsx`
- Create: `onboarding-neetiq/src/components/scroll/CodeTyper.tsx`
- Create: `onboarding-neetiq/src/components/scroll/CounterReveal.tsx`

**Step 1: Build TextReveal (clip-reveal headline)**

Create `onboarding-neetiq/src/components/scroll/TextReveal.tsx`:
```tsx
import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface TextRevealProps {
  children: string
  as?: 'h1' | 'h2' | 'h3'
  className?: string
}

export default function TextReveal({ children, as: Tag = 'h2', className = '' }: TextRevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const words = ref.current.querySelectorAll('.word')

    gsap.set(words, { y: '115%', opacity: 0 })

    gsap.to(words, {
      y: '0%',
      opacity: 1,
      duration: 0.8,
      ease: 'power3.out',
      stagger: 0.08,
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 85%',
      },
    })

    // Gold underline wipe after text lands
    const underline = ref.current.querySelector('.underline-wipe')
    if (underline) {
      gsap.fromTo(
        underline,
        { scaleX: 0, transformOrigin: 'left' },
        {
          scaleX: 1,
          duration: 0.6,
          delay: 0.08 * words.length + 0.4,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: ref.current,
            start: 'top 85%',
          },
        }
      )
    }
  }, [children])

  const words = children.split(' ')

  return (
    <div ref={ref} className={`overflow-hidden ${className}`}>
      <Tag className="text-gold font-serif leading-tight">
        {words.map((word, i) => (
          <span key={i} className="inline-block overflow-hidden mr-[0.3em]">
            <span className="word inline-block">{word}</span>
          </span>
        ))}
      </Tag>
      <div className="underline-wipe h-[2px] bg-gold mt-3 w-24" />
    </div>
  )
}
```

**Step 2: Build BodyReveal (fade-in paragraphs)**

Create `onboarding-neetiq/src/components/scroll/BodyReveal.tsx`:
```tsx
import { useEffect, useRef, ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface BodyRevealProps {
  children: ReactNode
  className?: string
}

export default function BodyReveal({ children, className = '' }: BodyRevealProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    gsap.fromTo(
      ref.current,
      { opacity: 0, y: 30 },
      {
        opacity: 1,
        y: 0,
        duration: 0.6,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: ref.current,
          start: 'top 85%',
        },
      }
    )
  }, [])

  return (
    <div ref={ref} className={`text-text-primary leading-relaxed ${className}`}>
      {children}
    </div>
  )
}
```

**Step 3: Build CodeTyper (terminal-style typing)**

Create `onboarding-neetiq/src/components/scroll/CodeTyper.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface CodeTyperProps {
  code: string
  language?: string
  className?: string
}

export default function CodeTyper({ code, language = '', className = '' }: CodeTyperProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [displayText, setDisplayText] = useState('')
  const [typing, setTyping] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!ref.current) return

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 80%',
      onEnter: () => {
        if (!typing && !done) {
          setTyping(true)
        }
      },
      once: true,
    })

    return () => trigger.kill()
  }, [typing, done])

  useEffect(() => {
    if (!typing) return

    let i = 0
    const interval = setInterval(() => {
      if (i < code.length) {
        setDisplayText(code.slice(0, i + 1))
        i++
      } else {
        clearInterval(interval)
        setTyping(false)
        setDone(true)
      }
    }, 25)

    return () => clearInterval(interval)
  }, [typing, code])

  return (
    <div ref={ref} className={`bg-surface rounded-lg border border-border overflow-hidden ${className}`}>
      {language && (
        <div className="px-4 py-2 border-b border-border flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-risk-red/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-risk-yellow/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-risk-green/60" />
          <span className="ml-2 text-text-muted font-mono text-xs">{language}</span>
        </div>
      )}
      <pre className="p-4 overflow-x-auto">
        <code className="font-mono text-sm text-text-primary">
          {displayText}
          {typing && <span className="cursor-blink" />}
        </code>
      </pre>
    </div>
  )
}
```

**Step 4: Build CounterReveal (animated number)**

Create `onboarding-neetiq/src/components/scroll/CounterReveal.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface CounterRevealProps {
  target: number
  prefix?: string
  suffix?: string
  duration?: number
  className?: string
}

export default function CounterReveal({
  target,
  prefix = '',
  suffix = '',
  duration = 2,
  className = '',
}: CounterRevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!ref.current) return

    const obj = { val: 0 }

    const trigger = ScrollTrigger.create({
      trigger: ref.current,
      start: 'top 85%',
      onEnter: () => {
        gsap.to(obj, {
          val: target,
          duration,
          ease: 'expo.out',
          onUpdate: () => setValue(Math.round(obj.val)),
        })
      },
      once: true,
    })

    return () => trigger.kill()
  }, [target, duration])

  return (
    <div ref={ref} className={`font-mono text-gold ${className}`}>
      <span className="text-text-muted text-sm">{prefix}</span>
      <span className="text-5xl font-bold tabular-nums">{value.toLocaleString()}</span>
      <span className="text-text-muted text-sm">{suffix}</span>
    </div>
  )
}
```

**Step 5: Verify all components visually**

Create a test page in `ContraRedSession.tsx` that uses all four components, scroll through to verify animations.

**Step 6: Commit**

```bash
git add onboarding-neetiq/src/components/scroll/
git commit -m "feat(onboarding): build scroll animation primitives — TextReveal, BodyReveal, CodeTyper, CounterReveal"
```

---

### Task 12: Build DiagramDraw (SVG self-drawing) and SplitScreen components

**Files:**
- Create: `onboarding-neetiq/src/components/scroll/DiagramDraw.tsx`
- Create: `onboarding-neetiq/src/components/scroll/SplitScreen.tsx`

**Step 1: Build DiagramDraw**

Create `onboarding-neetiq/src/components/scroll/DiagramDraw.tsx`:
```tsx
import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface DiagramDrawProps {
  children: React.ReactNode // SVG content
  className?: string
}

export default function DiagramDraw({ children, className = '' }: DiagramDrawProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const paths = ref.current.querySelectorAll('path, line, polyline, circle, rect, ellipse')

    paths.forEach((path) => {
      if (path instanceof SVGGeometryElement) {
        const length = path.getTotalLength()
        gsap.set(path, { strokeDasharray: length, strokeDashoffset: length, opacity: 1 })
      }
    })

    gsap.to(paths, {
      strokeDashoffset: 0,
      duration: 1.5,
      ease: 'power2.inOut',
      stagger: 0.2,
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 80%',
      },
    })

    // Fade in fills after drawing
    const fills = ref.current.querySelectorAll('[data-fill]')
    gsap.fromTo(
      fills,
      { opacity: 0 },
      {
        opacity: 1,
        duration: 0.5,
        delay: 1.5,
        stagger: 0.1,
        scrollTrigger: {
          trigger: ref.current,
          start: 'top 80%',
        },
      }
    )
  }, [])

  return (
    <div ref={ref} className={`${className}`}>
      {children}
    </div>
  )
}
```

**Step 2: Build SplitScreen**

Create `onboarding-neetiq/src/components/scroll/SplitScreen.tsx`:
```tsx
import { useEffect, useRef, ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface SplitScreenProps {
  left: ReactNode
  right: ReactNode
  leftLabel?: string
  rightLabel?: string
  leftFade?: boolean // true = left fades out (rejected)
  rightGlow?: boolean // true = right glows gold (chosen)
  className?: string
}

export default function SplitScreen({
  left,
  right,
  leftLabel,
  rightLabel,
  leftFade = false,
  rightGlow = false,
  className = '',
}: SplitScreenProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const leftEl = ref.current.querySelector('.split-left')
    const rightEl = ref.current.querySelector('.split-right')

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: ref.current,
        start: 'top 75%',
      },
    })

    tl.fromTo(leftEl, { x: -50, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6 })
    tl.fromTo(rightEl, { x: 50, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6 }, '<0.2')

    if (leftFade) {
      tl.to(leftEl, { opacity: 0.3, scale: 0.95, duration: 0.8, delay: 0.5 })
    }
    if (rightGlow) {
      tl.to(rightEl, {
        boxShadow: '0 0 30px rgba(197, 168, 128, 0.3)',
        borderColor: '#C5A880',
        duration: 0.8,
      }, '<')
    }
  }, [leftFade, rightGlow])

  return (
    <div ref={ref} className={`grid grid-cols-2 gap-6 ${className}`}>
      <div className="split-left bg-surface border border-border rounded-lg p-6">
        {leftLabel && <div className="text-text-muted font-mono text-xs uppercase tracking-widest mb-3">{leftLabel}</div>}
        {left}
      </div>
      <div className="split-right bg-surface border border-border rounded-lg p-6">
        {rightLabel && <div className="text-gold font-mono text-xs uppercase tracking-widest mb-3">{rightLabel}</div>}
        {right}
      </div>
    </div>
  )
}
```

**Step 3: Verify visually**

**Step 4: Commit**

```bash
git add onboarding-neetiq/src/components/scroll/
git commit -m "feat(onboarding): build DiagramDraw and SplitScreen scroll components"
```

---

## Phase 5: Quiz Engine

### Task 13: Build Flashcard quiz component

**Files:**
- Create: `onboarding-neetiq/src/components/quiz/QuizContainer.tsx`
- Create: `onboarding-neetiq/src/components/quiz/Flashcard.tsx`
- Create: `onboarding-neetiq/src/components/quiz/QuizResults.tsx`

_Implementation: QuizContainer wraps all quiz types with "Knowledge Check" header in mono uppercase, gold top-border. Flashcard does 3D flip on click (rotateY 180deg via CSS transform, perspective: 1000px). QuizResults shows score, pass/fail, and "Continue" or "Retry" button._

**Step 1-4: Build components, verify visually, commit**

```bash
git commit -m "feat(onboarding): build Flashcard quiz component with flip animation and results"
```

---

### Task 14: Build DragDrop quiz component

**Files:**
- Create: `onboarding-neetiq/src/components/quiz/DragDrop.tsx`

_Implementation: Uses @dnd-kit/sortable. Items are gold-bordered pills. Drop zones pulse. Correct order snaps with green glow. Wrong order shakes._

**Step 1-4: Build, verify, commit**

```bash
git commit -m "feat(onboarding): build DragDrop quiz component with @dnd-kit sortable"
```

---

### Task 15: Build Scenario and InteractiveClause quiz components

**Files:**
- Create: `onboarding-neetiq/src/components/quiz/Scenario.tsx`
- Create: `onboarding-neetiq/src/components/quiz/InteractiveClause.tsx`

_Implementation: Scenario is multiple choice cards with hover-lift, gold border on select, explanation reveal after submit. InteractiveClause displays a contract clause where the user clicks/highlights the risky words._

**Step 1-4: Build, verify, commit**

```bash
git commit -m "feat(onboarding): build Scenario and InteractiveClause quiz components"
```

---

## Phase 6: Audio System

### Task 16: Build Howler.js audio manager and hook

**Files:**
- Create: `onboarding-neetiq/src/lib/audioManager.ts`
- Create: `onboarding-neetiq/src/hooks/useAudioPlayer.ts`

_Implementation: audioManager is a singleton that manages Howl instances for ambient tracks and SFX. Exposes `playAmbient(track)`, `stopAmbient()`, `playSfx(name)`, `setMuted(bool)`. useAudioPlayer hook subscribes to useAudio store and syncs mute state with the manager._

**Step 1: Build audioManager.ts**

```typescript
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
```

**Step 2: Build useAudioPlayer hook, verify, commit**

```bash
git commit -m "feat(onboarding): build Howler.js audio manager with ambient + SFX support"
```

---

## Phase 7: 3D Hero Scenes

### Task 17: Build shared SceneWrapper and GoldParticles

**Files:**
- Create: `onboarding-neetiq/src/components/three/SceneWrapper.tsx`
- Create: `onboarding-neetiq/src/components/three/GoldParticles.tsx`

_Implementation: SceneWrapper provides Canvas with bloom postprocessing, fade-in from black, dark background. GoldParticles uses drei's Points with random positions and gold emissive material, slowly drifting upward._

**Commit:** `feat(onboarding): build shared 3D SceneWrapper with bloom and GoldParticles`

---

### Task 18: Build Session 1 3D hero — ContractUnfold

**Files:**
- Create: `onboarding-neetiq/src/components/three/ContractUnfold.tsx`

_Implementation: A 3D plane (contract page) that unfolds/rotates. Red particle emitters spring from specific points (hidden clauses). Camera slowly pulls back. Uses drei's Float for gentle hover. Auto-rotates._

**Commit:** `feat(onboarding): build ContractUnfold 3D hero scene for Session 1`

---

### Task 19: Build Session 2 3D hero — NeuralNetwork

**Files:**
- Create: `onboarding-neetiq/src/components/three/NeuralNetwork.tsx`

_Implementation: Nodes as gold-emissive spheres connected by lines (BufferGeometry). Energy pulses travel along connections (animated vertex colors). Camera flies through the network on scroll._

**Commit:** `feat(onboarding): build NeuralNetwork 3D hero scene for Session 2`

---

### Task 20: Build Session 3 3D hero — SecurityFortress

**Files:**
- Create: `onboarding-neetiq/src/components/three/SecurityFortress.tsx`

_Implementation: Concentric translucent shells (MeshPhysicalMaterial with transmission) that build layer by layer. Glowing core at center. Each layer represents a security level. Orbit controls._

**Commit:** `feat(onboarding): build SecurityFortress 3D hero scene for Session 3`

---

### Task 21: Build Session 4 3D hero — Constellation

**Files:**
- Create: `onboarding-neetiq/src/components/three/Constellation.tsx`

_Implementation: Architecture components as star-like nodes in 3D space. Connections pulse with traveling gold dots. Nodes glow on hover (raycast). Labels appear on hover via drei Html. Orbit controls. The "God view" of ContraRed._

**Commit:** `feat(onboarding): build Constellation 3D hero scene for Session 4`

---

## Phase 8: Visual Components (Chapter-Specific)

### Task 22: Build NapkinSketch (Rough.js) for Chapter 3

**Files:**
- Create: `onboarding-neetiq/src/components/visuals/NapkinSketch.tsx`

_Implementation: Uses Rough.js to draw the original ContraRed architecture sketch with a hand-drawn look. Animates stroke by stroke on scroll. Then morphs into a clean geometric SVG diagram._

**Commit:** `feat(onboarding): build NapkinSketch with Rough.js for Chapter 3`

---

### Task 23: Build PipelineVisualizer for Chapter 8

**Files:**
- Create: `onboarding-neetiq/src/components/visuals/PipelineVisualizer.tsx`

_Implementation: Horizontal 5-stage pipeline. Each stage is a geometric chamber (SVG). Scroll scrubs a glowing orb through stages. Particles change color/shape at each stage boundary. Labels appear as orb enters each chamber. The crown jewel visual._

**Commit:** `feat(onboarding): build 5-stage PipelineVisualizer for Chapter 8`

---

### Task 24: Build remaining visual components

**Files:**
- Create: `onboarding-neetiq/src/components/visuals/ParticleFlow.tsx`
- Create: `onboarding-neetiq/src/components/visuals/PlaybookCards.tsx`
- Create: `onboarding-neetiq/src/components/visuals/ScoreCard.tsx`
- Create: `onboarding-neetiq/src/components/visuals/DeploymentMap.tsx`
- Create: `onboarding-neetiq/src/components/visuals/ArchitectureDiagram.tsx`

_ParticleFlow: Gold particles streaming in a direction (Canvas 2D or Three.js). PlaybookCards: 10 cards that fan out like a deck. ScoreCard: Animated bar chart for GC Pilot scores. DeploymentMap: 4 infrastructure nodes with pulsing connections. ArchitectureDiagram: Full system SVG that draws itself._

**Commit:** `feat(onboarding): build ParticleFlow, PlaybookCards, ScoreCard, DeploymentMap, ArchitectureDiagram`

---

## Phase 9: Celebration Components

### Task 25: Build BadgeUnlock, SessionComplete, and Certificate

**Files:**
- Create: `onboarding-neetiq/src/components/celebrations/BadgeUnlock.tsx`
- Create: `onboarding-neetiq/src/components/celebrations/SessionComplete.tsx`
- Create: `onboarding-neetiq/src/components/celebrations/Certificate.tsx`

_BadgeUnlock: Spring-physics animated badge card (Motion useSpring). Gold shimmer effect. SessionComplete: Gold confetti (Lottie or canvas particles) + "Session Complete" in Georgia. Certificate: Downloadable HTML/SVG certificate with user name, date, "ContraRed Chronicle — Complete"._

**Commit:** `feat(onboarding): build celebration components — BadgeUnlock, SessionComplete, Certificate`

---

## Phase 10: Content Authoring

### Task 26: Transform story/ markdown into session-1.json

**Files:**
- Create: `onboarding-neetiq/src/content/contrared/session-1.json`

_Read story/01-the-meeting.md through story/05-the-big-decision.md. Transform into structured JSON per the Content Schema (sections with type, content, animation, visual config). Add quiz questions (3 flashcard true/false for Session 1)._

**Commit:** `content(onboarding): add Session 1 — The Origin Story (chapters 1-5 + quiz)`

---

### Task 27: Transform into session-2.json

**Files:**
- Create: `onboarding-neetiq/src/content/contrared/session-2.json`

_Read story/06 through story/09. Structure as JSON. Add quiz (drag-and-drop pipeline ordering)._

**Commit:** `content(onboarding): add Session 2 — The Technology (chapters 6-9 + quiz)`

---

### Task 28: Transform into session-3.json

**Files:**
- Create: `onboarding-neetiq/src/content/contrared/session-3.json`

_Read story/10 through story/13. Structure as JSON. Add quiz (3 scenario questions)._

**Commit:** `content(onboarding): add Session 3 — The Real World (chapters 10-13 + quiz)`

---

### Task 29: Transform into session-4.json

**Files:**
- Create: `onboarding-neetiq/src/content/contrared/session-4.json`

_Read story/14 and story/15. Structure as JSON. Add mixed final challenge (5 questions across all formats)._

**Commit:** `content(onboarding): add Session 4 — The Full Picture (chapters 14-15 + final challenge)`

---

## Phase 11: Page Assembly

### Task 30: Build content loader and chapter renderer

**Files:**
- Create: `onboarding-neetiq/src/lib/contentLoader.ts`
- Modify: `onboarding-neetiq/src/routes/books/contrared/Chapter.tsx`

_contentLoader imports JSON, provides typed access. Chapter.tsx maps section types to scroll components (text → TextReveal+BodyReveal, code → CodeTyper, counter → CounterReveal, diagram → DiagramDraw, etc.)._

**Commit:** `feat(onboarding): build content loader and dynamic chapter renderer`

---

### Task 31: Build Home page (book library)

**Files:**
- Modify: `onboarding-neetiq/src/routes/Home.tsx`

_Gold-bordered book cards, progress indicators, locked/shimmer states for future books. Uses useProgress store._

**Commit:** `feat(onboarding): build Home page with book library grid`

---

### Task 32: Build ContraRed Landing page (session selector)

**Files:**
- Modify: `onboarding-neetiq/src/routes/books/contrared/Landing.tsx`

_4 session cards (locked/available/completed states). Session metadata (title, subtitle, chapter count). Badge display. Overall ContraRed progress._

**Commit:** `feat(onboarding): build ContraRed Landing with session selector`

---

### Task 33: Build Session page (3D hero + chapter scroll + quiz gate)

**Files:**
- Modify: `onboarding-neetiq/src/routes/books/contrared/Session.tsx`

_Loads session JSON. Renders 3D hero scene at top (lazy loaded). Scrolls through chapters. Ends with quiz gate. Tracks progress in Zustand. Plays ambient track. Session lock check (redirect to /locked if not available)._

**Commit:** `feat(onboarding): build Session page with 3D hero, chapter scroll, and quiz gate`

---

### Task 34: Build Completion page

**Files:**
- Modify: `onboarding-neetiq/src/routes/Completion.tsx`

_All badges earned, total time, certificate generation, confetti animation, "Welcome to NeetiQ" message._

**Commit:** `feat(onboarding): build Completion page with certificate and confetti`

---

## Phase 12: Audio Assets & Polish

### Task 35: Source and add placeholder audio files

**Files:**
- Create: `onboarding-neetiq/public/audio/ambient/` (4 tracks)
- Create: `onboarding-neetiq/public/audio/sfx/` (12 SFX)

_Use jsfxr (https://sfxr.me/) to generate placeholder SFX. Use a royalty-free ambient pad for placeholder soundtrack. Total < 2MB._

**Commit:** `assets(onboarding): add placeholder audio — ambient tracks and SFX`

---

### Task 36: Add Lottie animation files

**Files:**
- Create: `onboarding-neetiq/public/lottie/checkmark.json`
- Create: `onboarding-neetiq/public/lottie/confetti-gold.json`
- Create: `onboarding-neetiq/public/lottie/loading-orb.json`
- Create: `onboarding-neetiq/public/lottie/unlock-shimmer.json`

_Source from LottieFiles free library or create minimal custom ones. Recolor to gold (#C5A880)._

**Commit:** `assets(onboarding): add Lottie animation files`

---

## Phase 13: Deployment

### Task 37: Configure Netlify deployment

**Files:**
- Create: `onboarding-neetiq/netlify.toml`

```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
```

**Commit:** `chore(onboarding): add Netlify deployment config`

---

### Task 38: Performance audit and optimization

**Steps:**
1. Run `npm run build` — check bundle size
2. Verify 3D scenes are lazy-loaded (React.lazy + Suspense)
3. Verify audio files load on demand (not upfront)
4. Run Lighthouse — target > 85 performance score
5. Add `loading="lazy"` to any images
6. Verify `prefers-reduced-motion` disables animations gracefully

**Commit:** `perf(onboarding): optimize bundle splitting, lazy loading, and reduced-motion support`

---

## Dependency Graph

```
Phase 1 (Tasks 1-4): Scaffold
    ↓
Phase 2 (Tasks 5-7): State management ←── can parallel with Phase 3
    ↓
Phase 3 (Tasks 8-9): Shell + routing
    ↓
Phase 4 (Tasks 10-12): Scroll primitives ←── can parallel with Phase 5, 6
    ↓
Phase 5 (Tasks 13-15): Quiz engine
Phase 6 (Task 16): Audio system
Phase 7 (Tasks 17-21): 3D scenes ←── can parallel with Phase 8
Phase 8 (Tasks 22-24): Visual components
    ↓
Phase 9 (Task 25): Celebrations
Phase 10 (Tasks 26-29): Content JSON ←── can parallel with Phase 7-9
    ↓
Phase 11 (Tasks 30-34): Page assembly (needs all above)
    ↓
Phase 12 (Tasks 35-36): Audio + Lottie assets
    ↓
Phase 13 (Tasks 37-38): Deploy + optimize
```

**Total: 38 tasks across 13 phases. Estimated: 4-5 weeks for a polished v1.**

---

## Parallelization Opportunities

These task groups can be worked on simultaneously by separate agents:

| Agent | Tasks | Focus |
|-------|-------|-------|
| Agent A | 5-7 | Zustand stores |
| Agent B | 10-12 | Scroll primitives |
| Agent C | 13-15 | Quiz components |
| Agent D | 17-21 | 3D scenes |
| Agent E | 22-24 | Visual components |
| Agent F | 26-29 | Content JSON |

After all converge → Phase 11 (page assembly) integrates everything.
