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
    useQuiz.getState().answerQuestion('q1', 'true')
    useQuiz.getState().answerQuestion('q2', 'true')
    useQuiz.getState().answerQuestion('q3', 'true')
    const result = useQuiz.getState().submit()
    expect(result.score).toBe(2)
    expect(result.total).toBe(3)
    expect(result.passed).toBe(false)
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
