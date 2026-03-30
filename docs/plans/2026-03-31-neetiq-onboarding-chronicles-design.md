# Design: NeetiQ Onboarding Chronicles

**Date:** 2026-03-31
**Status:** Approved
**Author:** Avi + Claude

---

## Overview

An interactive, cinematic, multi-session onboarding experience for NeetiQ employees. The first "book" is **The ContraRed Chronicle** — a scroll-driven visual story of how ContraRed was built, with 3D hero scenes, animated diagrams, ambient audio, and quiz gates between sessions.

**URL:** `onboarding.neetiq.in`
**Architecture:** Standalone React app, multi-book library (ContraRed now, Smriti and others later)
**Target audience:** New NeetiQ hires
**Experience duration:** ~60-90 minutes across 4 sessions over the first week

---

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Where it lives | Standalone React app (`onboarding.neetiq.in`) | Maximum creative freedom, no Astro constraints |
| Visual format | Cinematic scroll story | Prestigious, on-brand, Awwwards-quality |
| Progress tracking | Progress bar + quiz gates | Clean, purposeful, ensures comprehension |
| Illustration style | Abstract & geometric | Sophisticated, no character art dependency |
| Session structure | Multi-session (4 days) | Prevents overload, builds anticipation |
| Audio | Ambient soundtrack + SFX | Full cinematic immersion, mutable |
| Quiz format | Mixed per session | Keeps each session fresh |
| 3D | One hero scene per session intro | "Wow factor" without performance tax |

---

## Multi-Book Architecture

```
onboarding.neetiq.in/
├── /                        ← Library home: pick your book
│   ├── ContraRed Chronicle  → /contrared
│   ├── Smriti Saga          → /smriti     (future)
│   ├── NeetiQ Foundations   → /neetiq     (future)
│   └── ...more books
│
├── /contrared/              ← Building now
│   ├── /session/1           ← The Origin Story
│   ├── /session/2           ← The Technology
│   ├── /session/3           ← The Real World
│   └── /session/4           ← The Full Picture
│
├── /smriti/                 ← Future
└── /neetiq/                 ← Future
```

Library Home shows book cards with progress. Future books show as locked with a shimmer.

---

## App Shell & Navigation

**Global Layout:**
- **Top bar (fixed):** NeetiQ logo (gold on dark), current session label, mute toggle, user avatar
- **Content area:** Scrollable GSAP ScrollTrigger pinned sections
- **Bottom bar (fixed):** Segmented progress bar (gold `#C5A880` fill), chapter indicator, percentage
- **Background:** `#0A0A0A` with grain texture overlay (SVG noise, 0.022 opacity)
- **Chapter transitions:** Gold scan-divider sweep

**Session Lock Screen:** Locked sessions show a locked-door UI with a message and link back to the previous session.

---

## The Four Sessions — ContraRed Chronicle

### Session 1: "The Origin Story" (Day 1, ~20 min)

| Chapter | Content | Visual Moment |
|---------|---------|---------------|
| Ch 1: The Meeting | Avi meets Mr. Satish | **3D Hero:** Rotating 3D contract unfolds, red highlight particles emerge from hidden clauses, camera pulls back to reveal scale |
| Ch 2: The Problem | Why contract review is broken | Animated counter: ₹72,000 ticks up. Particle stream shows hours flowing away. Geometric pipeline: junior → senior → partner |
| Ch 3: The First Spark | Avi's "aha moment" | Napkin sketch in Rough.js (hand-drawn contrast against sleek UI), transforms into clean geometric diagram |
| Ch 4: Baby Steps — Regex | First prototype | Code blocks type themselves. Regex patterns light up on match. RED/YELLOW/GREEN particles sort |
| Ch 5: The Big Decision | Why Word Add-in | Split-screen: standalone app fades left (rejected), Word Add-in glows gold right (chosen). Mock Word window assembles |
| **Quiz Gate** | Flashcard format | 3 quick true/false flip cards |

### Session 2: "The Technology" (Day 2, ~20 min)

| Chapter | Content | Visual Moment |
|---------|---------|---------------|
| Ch 6: The Brain Upgrade | AI enters | **3D Hero:** Neural network mesh materializes, gold energy pulses through nodes, camera flies through |
| Ch 7: The Playbook System | Teaching AI | 10 playbook cards fan out as a deck. Rules appear as floating tag clouds |
| Ch 8: The Engine Room | 5-stage pipeline | Horizontal pipeline visualization. Scroll scrubs a glowing orb through 5 geometric chambers. Particles transform at each stage |
| Ch 9: The Control Center | Dashboard | Animated dashboard assembles: charts draw, numbers count up, cards slide in |
| **Quiz Gate** | Drag-and-drop | "Drag the 5 pipeline stages into the correct order" |

### Session 3: "The Real World" (Day 3, ~20 min)

| Chapter | Content | Visual Moment |
|---------|---------|---------------|
| Ch 10: The Security Fort | 7 security layers | **3D Hero:** Fortress assembles layer by layer. Each security layer is a translucent geometric shell around a glowing core. Camera orbits |
| Ch 11: Going Live | Deployment journey | Three infra nodes (Render, Netlify x2, Supabase) connect with pulsing gold lines. "Disaster" moments flash red, resolve green |
| Ch 12: The Lawyer Test | GC Pilot results | Scorecard bars fill to 7.5/10, 7/10, 6/10. "CONDITIONAL GO" typewriter-reveals |
| Ch 13: The Great Migration | Vertex AI | Consumer API node crumbles, enterprise Vertex AI node assembles with shield particles |
| **Quiz Gate** | Scenario-based | "A contract has no liability cap. What risk level does ContraRed assign?" |

### Session 4: "The Full Picture" (Day 4, ~15 min)

| Chapter | Content | Visual Moment |
|---------|---------|---------------|
| Ch 14: How It All Works | Full architecture | **3D Hero:** Complete architecture as explorable 3D constellation. Orbit controls. Nodes glow on hover. Connections pulse with data flow |
| Ch 15: What's Next | Roadmap | Timeline extends into distance. Road markers for each phase. "Welcome to NeetiQ. Your chapter starts now." |
| **Final Challenge** | Mixed mini-exam | 5 questions: 1 flashcard, 1 drag-and-drop, 2 scenario, 1 "spot the risk" interactive |
| **Completion** | Celebration | Gold confetti. Badge: "ContraRed Chronicle — Complete". Certificate with name and date |

---

## Tech Stack

```
Framework:        React 19 + Vite 7 + TypeScript
Routing:          React Router v7
Styling:          TailwindCSS 4 (NeetiQ design tokens)

Animation:
  ├── GSAP + ScrollTrigger     → Scroll-pinned sections, timeline scrubbing
  ├── Motion (Framer Motion)   → Component transitions, layout animations
  ├── Lottie                   → Micro-animations (checkmarks, unlocks, celebrations)
  └── Rough.js                 → Napkin sketch moment (Ch 3 only)

3D:
  ├── React Three Fiber        → 3D hero scenes (4 total)
  ├── @react-three/drei        → OrbitControls, Float, Stars
  └── @react-three/postprocessing → Bloom, god rays (gold glow)

Audio:            Howler.js (ambient + SFX, global mute)

Quiz:
  ├── Flashcard component      → Flip cards, true/false
  ├── @dnd-kit                 → Drag-and-drop ordering
  ├── Scenario component       → Multiple choice + explanation
  └── Interactive component    → "Spot the risk" clause highlighter

State:            Zustand (progress, audio, quiz)
Persistence:      localStorage + optional Supabase sync
Content:          JSON files per session (editable without code)
Deployment:       Netlify (onboarding.neetiq.in)
```

**Performance Budget:**

| Metric | Target |
|--------|--------|
| Initial load | < 3 seconds |
| Lighthouse Performance | > 85 |
| 3D scene load | < 2 seconds (lazy loaded) |
| Total bundle (excl. 3D) | < 500KB gzipped |
| 3D assets per scene | < 500KB each |
| Scroll animations | 60fps (only transform + opacity) |

---

## Visual Design System

**Colors:**
```
Background:       #0A0A0A   (deep black)
Surface:          #111111   (cards, modals)
Surface-elevated: #1A1A1A   (quiz panels, hover)
Border:           #1E1E1E   (subtle dividers)
Text-primary:     #E8E8E8   (off-white)
Text-muted:       #6B6B6B   (secondary)
Accent-gold:      #C5A880   (primary brand)
Accent-gold-dim:  #8B7355   (inactive/visited)
Risk-red:         #DC2626
Risk-yellow:      #EAB308
Risk-green:       #22C55E
3D-glow:          #C5A880 @ 40% opacity
```

**Typography:**
```
Headlines:    Georgia (serif)
Body:         Inter (sans)
Code/Labels:  JetBrains Mono
Napkin sketch: Caveat (handwriting, Ch 3 only)
```

**Textures & Effects:**
- Grain overlay: SVG noise at 0.022 opacity
- Grid overlay: Palantir-style at 0.025 opacity
- Gold scan-divider: horizontal gradient sweep between chapters
- Ambient glow: radial #C5A880 behind key elements

**Scroll Animation Patterns:**
- Chapter titles: words clip-reveal from bottom, staggered 80ms, gold underline wipes after
- Body text: fade-in + translateY(30px), 0.6s, paragraphs stagger 120ms
- Diagrams: SVG stroke-dashoffset draw, nodes scale(0.8→1) with bounce, connections pulse
- Code blocks: terminal-type at 40ms/char, syntax highlighting fades in after
- Counters: count-up with easeOutExpo, gold pulse on completion
- Chapter transitions: current fades to 0.3, gold sweep, next clip-reveals from below

**3D Scene Shared Language:**
- Dark void background (#0A0A0A)
- Gold emissive materials (#C5A880)
- Translucent glass geometry (MeshPhysicalMaterial, transmission: 0.6)
- Bloom postprocessing (strength: 0.4, gold tint)
- Floating gold dust particles
- Auto-rotation when idle, orbit-controls on interaction
- Fade-in from black (no pop-in)

**Quiz Visual Language:**
- Container: surface-elevated card, gold top-border, "Knowledge Check" in mono uppercase
- Flashcards: 3D flip (rotateY 180deg), green check or red X
- Drag-and-drop: gold-bordered pills, pulsing drop zones, snap + glow on correct
- Scenarios: card options, hover lifts, gold border on select, explanation reveals
- Completion: gold confetti, badge spring-in, "Session Complete" in Georgia

---

## Audio Design

**Ambient Soundtrack (one per session):**
- Dark, warm ambient pad (~3 min seamless loop)
- Session 1: Warm, hopeful
- Session 2: Electronic, pulsing
- Session 3: Slightly tense, resolving
- Session 4: Expansive, triumphant
- Subtle digital texture layer at 30% volume, intermittent

**Sound Effects:**

| Trigger | Sound |
|---------|-------|
| Chapter transition | Soft whoosh + chime |
| Headline reveal | Subtle tonal sweep |
| Diagram drawing | Soft pen scratch |
| Code typing | Ambient key taps |
| Counter counting | Ticking, stops with "lock" |
| 3D scene load | Low hum building |
| Quiz appear | Gentle two-note chime |
| Quiz correct | Bright celebration tone |
| Quiz wrong | Soft low tone |
| Drag-drop snap | Tactile click |
| Session unlock | 3-note ascending chime |
| Final completion | Brief orchestral swell (4s) |
| Badge earned | Metallic shimmer |

**Controls:** Single mute toggle in top bar. State persisted. Default ON. Respects prefers-reduced-motion. 0.5s fade on mute.

**Asset budget:** < 2MB total compressed (OGG/MP3). Source: freesound.org, jsfxr.

---

## Data Model

**User Progress:**
```typescript
interface OnboardingState {
  user: { id: string; name: string; email: string; startedAt: string };
  books: {
    [bookId: string]: {
      status: 'locked' | 'available' | 'in_progress' | 'completed';
      sessions: {
        [sessionId: number]: {
          status: 'locked' | 'in_progress' | 'completed';
          unlockedAt: string | null;
          completedAt: string | null;
          chaptersCompleted: number[];
          currentChapter: number;
          scrollProgress: number;
          timeSpentSeconds: number;
          quiz: {
            attempts: number;
            score: number;
            passed: boolean;
            answers: Record<string, string>;
          };
        };
      };
      badges: string[];
    };
  };
  overallProgress: number;
}
```

**Content Schema:**
```typescript
interface Session {
  id: number;
  title: string;
  subtitle: string;
  ambientTrack: string;
  heroScene: string;
  chapters: Chapter[];
  quiz: Quiz;
}
interface Chapter {
  id: number;
  title: string;
  sections: {
    type: 'text' | 'diagram' | 'code' | 'counter' | 'split-screen' | 'quote';
    content: string;
    animation: string;
    visual?: { type: string; config: Record<string, any> };
  }[];
}
interface Quiz {
  type: 'flashcard' | 'dragdrop' | 'scenario' | 'mixed';
  passingScore: number;
  questions: {
    id: string;
    format: 'true-false' | 'drag-order' | 'multiple-choice' | 'interactive';
    question: string;
    options?: string[];
    correctAnswer: string | string[];
    explanation: string;
  }[];
}
```

**Admin Visibility (optional Supabase sync):**
- Table showing each employee's progress per book
- Average completion time, pass rate, drop-off points
- Works fully offline with localStorage; Supabase adds admin dashboard

---

## Badge System

| Badge | Earned When | Icon |
|-------|-------------|------|
| "The Origin" | Complete Session 1 | Gold scroll |
| "Tech Architect" | Complete Session 2 | Gold circuit board |
| "Battle Tested" | Complete Session 3 | Gold shield |
| "Full Spectrum" | Complete Session 4 | Gold constellation |
| "Perfect Score" | 100% on any quiz | Gold star |
| "Speed Reader" | Any session under 15min | Gold lightning |
| "Chronicle Complete" | All 4 sessions done | Gold NeetiQ logo |

---

## File Structure

```
onboarding-neetiq/
├── public/
│   ├── audio/ambient/          (4 session tracks, OGG)
│   ├── audio/sfx/              (12 sound effects, OGG)
│   ├── lottie/                 (checkmark, confetti, loading, unlock)
│   └── fonts/                  (Caveat handwriting font)
├── src/
│   ├── main.tsx
│   ├── App.tsx                 (Router + providers)
│   ├── routes/
│   │   ├── Home.tsx            (Library book selection)
│   │   ├── books/contrared/
│   │   │   ├── Landing.tsx     (Session select)
│   │   │   ├── Session.tsx     (Session loader + 3D hero)
│   │   │   ├── Chapter.tsx     (Scroll chapter renderer)
│   │   │   └── Quiz.tsx        (Quiz gate)
│   │   ├── Completion.tsx      (Shared celebration)
│   │   └── Lock.tsx            (Shared lock screen)
│   ├── components/
│   │   ├── shell/              (TopBar, ProgressBar, ScanDivider)
│   │   ├── scroll/             (ScrollSection, TextReveal, BodyReveal,
│   │   │                        CodeTyper, CounterReveal, SplitScreen,
│   │   │                        DiagramDraw)
│   │   ├── visuals/            (PipelineVisualizer, ArchitectureDiagram,
│   │   │                        ParticleFlow, NapkinSketch, ScoreCard,
│   │   │                        PlaybookCards, DeploymentMap)
│   │   ├── three/              (ContractUnfold, NeuralNetwork,
│   │   │                        SecurityFortress, Constellation,
│   │   │                        GoldParticles, SceneWrapper)
│   │   ├── quiz/               (QuizContainer, Flashcard, DragDrop,
│   │   │                        Scenario, InteractiveClause, QuizResults)
│   │   └── celebrations/       (BadgeUnlock, SessionComplete, Certificate)
│   ├── content/
│   │   └── contrared/          (session-1.json through session-4.json)
│   ├── stores/                 (useProgress, useAudio, useQuiz)
│   ├── hooks/                  (useScrollAnimation, useAudioPlayer,
│   │                            useChapterProgress, usePersistence)
│   ├── lib/                    (audioManager, supabaseClient, contentLoader)
│   └── styles/                 (tailwind.css, grain.css, animations.css)
├── tailwind.config.ts
├── vite.config.ts
├── tsconfig.json
├── package.json
└── netlify.toml
```

---

## Next Steps

This design doc covers the complete ContraRed Chronicle onboarding experience. Implementation should follow a phased approach, building the foundation first (shell, routing, scroll engine) then layering visual richness (3D, audio, quizzes) on top.
