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
    (set) => ({
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

            const badge = SESSION_BADGES[sessionId]
            if (badge && !books[bookId].badges.includes(badge)) {
              books[bookId].badges.push(badge)
            }

            if (score === total && !books[bookId].badges.includes('perfect-score')) {
              books[bookId].badges.push('perfect-score')
            }

            const nextSession = books[bookId].sessions[sessionId + 1]
            if (nextSession && nextSession.status === 'locked') {
              nextSession.status = 'available'
            }

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
    { name: 'neetiq-onboarding-progress' }
  )
)
