import session1 from '../content/contrared/session-1.json'
import session2 from '../content/contrared/session-2.json'
import session3 from '../content/contrared/session-3.json'
import session4 from '../content/contrared/session-4.json'

/* ------------------------------------------------------------------ */
/*  TypeScript interfaces for session content                         */
/* ------------------------------------------------------------------ */

export interface VisualConfig {
  type: string
  config: Record<string, unknown>
}

export interface Section {
  type: 'text' | 'quote' | 'code' | 'counter' | 'split-screen' | 'diagram'
  content: string
  animation: string
  visual?: VisualConfig
}

export interface Chapter {
  id: number
  title: string
  sections: Section[]
}

export interface Question {
  id: string
  format: 'true-false' | 'drag-order' | 'multiple-choice' | 'interactive'
  question: string
  options?: string[]
  correctAnswer: string | string[]
  explanation: string
}

export interface Quiz {
  type: 'flashcard' | 'dragdrop' | 'scenario' | 'mixed'
  passingScore: number
  questions: Question[]
}

export interface Session {
  id: number
  title: string
  subtitle: string
  ambientTrack: string
  heroScene: string
  chapters: Chapter[]
  quiz: Quiz
}

/* ------------------------------------------------------------------ */
/*  Session map & helpers                                             */
/* ------------------------------------------------------------------ */

const sessions: Record<number, Session> = {
  1: session1 as unknown as Session,
  2: session2 as unknown as Session,
  3: session3 as unknown as Session,
  4: session4 as unknown as Session,
}

export function getSession(id: number): Session | null {
  return sessions[id] ?? null
}

export function getChapter(sessionId: number, chapterId: number): Chapter | null {
  const session = getSession(sessionId)
  if (!session) return null
  return session.chapters.find((c) => c.id === chapterId) ?? null
}

export function getAllSessions(): Session[] {
  return Object.values(sessions)
}

export const TOTAL_SESSIONS = Object.keys(sessions).length
