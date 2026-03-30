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
      return false
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
