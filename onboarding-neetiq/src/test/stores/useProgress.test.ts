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
    expect(useProgress.getState().overallProgress).toBe(25)
  })

  it('persists to localStorage', () => {
    useProgress.getState().startSession('contrared', 1)
    const saved = localStorage.getItem('neetiq-onboarding-progress')
    expect(saved).toBeTruthy()
    const parsed = JSON.parse(saved!)
    expect(parsed.state.books.contrared.sessions[1].status).toBe('in_progress')
  })
})
