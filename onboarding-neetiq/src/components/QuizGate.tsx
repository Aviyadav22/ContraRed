import { useState, useEffect, useCallback } from 'react'
import type { Quiz, Question } from '../lib/contentLoader.ts'
import { useQuiz } from '../stores/useQuiz.ts'
import { useProgress } from '../stores/useProgress.ts'
import QuizContainer from './quiz/QuizContainer.tsx'
import QuizResults from './quiz/QuizResults.tsx'
import Flashcard from './quiz/Flashcard.tsx'
import DragDrop from './quiz/DragDrop.tsx'
import Scenario from './quiz/Scenario.tsx'
import SessionComplete from './celebrations/SessionComplete.tsx'

/* ------------------------------------------------------------------ */
/*  Per-question renderer                                             */
/* ------------------------------------------------------------------ */

function QuestionRenderer({
  question,
  onAnswer,
}: {
  question: Question
  onAnswer: (questionId: string, answer: string) => void
}) {
  switch (question.format) {
    case 'true-false':
      return (
        <div className="space-y-3">
          <p className="font-serif text-lg text-text-primary">{question.question}</p>
          <div className="flex gap-3">
            {['true', 'false'].map((val) => (
              <button
                key={val}
                onClick={() => onAnswer(question.id, val)}
                className="flex-1 bg-surface border border-border rounded-lg p-4 text-text-primary font-mono text-sm hover:-translate-y-0.5 transition-all capitalize"
              >
                {val}
              </button>
            ))}
          </div>
        </div>
      )

    case 'drag-order':
      return (
        <div className="space-y-3">
          <p className="font-serif text-lg text-text-primary">{question.question}</p>
          <DragDrop
            items={question.options ?? []}
            correctOrder={question.correctAnswer as string[]}
            onComplete={(userOrder) => {
              onAnswer(question.id, JSON.stringify(userOrder))
            }}
          />
        </div>
      )

    case 'multiple-choice':
      return (
        <Scenario
          question={question.question}
          options={question.options ?? []}
          correctIndex={(question.options ?? []).indexOf(question.correctAnswer as string)}
          explanation={question.explanation}
          onAnswer={(correct) => {
            onAnswer(question.id, correct ? (question.correctAnswer as string) : '__wrong__')
          }}
        />
      )

    case 'interactive':
      // For interactive questions, render as multiple-choice variant
      return (
        <Scenario
          question={question.question}
          options={question.options ?? []}
          correctIndex={(question.options ?? []).indexOf(question.correctAnswer as string)}
          explanation={question.explanation}
          onAnswer={(correct) => {
            onAnswer(question.id, correct ? (question.correctAnswer as string) : '__wrong__')
          }}
        />
      )

    default:
      return (
        <p className="text-text-muted">Unknown question format.</p>
      )
  }
}

/* ------------------------------------------------------------------ */
/*  QuizGate                                                          */
/* ------------------------------------------------------------------ */

interface QuizGateProps {
  sessionId: number
  quiz: Quiz
  sessionTitle: string
  onComplete: () => void
}

type Phase = 'quiz' | 'results' | 'celebration'

export default function QuizGate({ sessionId, quiz, sessionTitle, onComplete }: QuizGateProps) {
  const { loadQuestions, answerQuestion, submit, reset, currentQuestion, questions, answers, submitted, result } = useQuiz()
  const submitQuiz = useProgress((s) => s.submitQuiz)
  const [phase, setPhase] = useState<Phase>('quiz')

  // Load quiz questions on mount
  useEffect(() => {
    reset()
    loadQuestions(quiz.questions as Parameters<typeof loadQuestions>[0])
  }, [quiz, loadQuestions, reset])

  const handleAnswer = useCallback(
    (questionId: string, answer: string) => {
      answerQuestion(questionId, answer)
    },
    [answerQuestion],
  )

  const handleSubmit = useCallback(() => {
    const quizResult = submit()
    submitQuiz('contrared', sessionId, quizResult.score, quizResult.total, quizResult.answers)
    setPhase('results')
  }, [submit, submitQuiz, sessionId])

  const handleRetry = useCallback(() => {
    reset()
    loadQuestions(quiz.questions as Parameters<typeof loadQuestions>[0])
    setPhase('quiz')
  }, [reset, loadQuestions, quiz])

  const handleContinueFromResults = useCallback(() => {
    if (result?.passed) {
      setPhase('celebration')
    }
  }, [result])

  // Determine if all questions have been answered
  const allAnswered = questions.length > 0 && Object.keys(answers).length >= questions.length

  // For flashcard/sequential types, show one question at a time
  const isSequential = quiz.type === 'flashcard' || quiz.type === 'scenario'

  if (phase === 'celebration') {
    return (
      <SessionComplete
        sessionNumber={sessionId}
        sessionTitle={sessionTitle}
        onContinue={onComplete}
      />
    )
  }

  if (phase === 'results' && submitted && result) {
    return (
      <QuizContainer title="Results">
        <QuizResults
          score={result.score}
          total={result.total}
          passed={result.passed}
          onContinue={handleContinueFromResults}
          onRetry={handleRetry}
        />
      </QuizContainer>
    )
  }

  // Quiz phase
  return (
    <QuizContainer title={`Session ${sessionId} Quiz`}>
      <div className="space-y-8">
        {isSequential ? (
          // Show one question at a time
          questions.length > 0 && (
            <div>
              <div className="text-text-muted font-mono text-xs mb-4">
                Question {currentQuestion + 1} of {questions.length}
              </div>
              {quiz.type === 'flashcard' ? (
                <Flashcard
                  key={questions[currentQuestion].id}
                  question={questions[currentQuestion].question}
                  answer={questions[currentQuestion].explanation}
                  isCorrect={true}
                  onAnswer={() => {
                    // For true-false flashcards, render as true/false buttons
                  }}
                />
              ) : null}
              {/* Also provide true/false or multi-choice for flashcard questions */}
              <div className="mt-4">
                <QuestionRenderer
                  key={questions[currentQuestion].id}
                  question={questions[currentQuestion]}
                  onAnswer={(qId, answer) => {
                    handleAnswer(qId, answer)
                    // Auto-advance after a small delay
                    if (currentQuestion < questions.length - 1) {
                      setTimeout(() => {
                        useQuiz.getState().nextQuestion()
                      }, 800)
                    }
                  }}
                />
              </div>
            </div>
          )
        ) : (
          // Show all questions (dragdrop, mixed)
          questions.map((q) => (
            <div key={q.id}>
              <QuestionRenderer question={q} onAnswer={handleAnswer} />
            </div>
          ))
        )}

        {allAnswered && !submitted && (
          <div className="flex justify-center pt-4">
            <button
              onClick={handleSubmit}
              className="bg-gold text-bg font-mono text-sm px-8 py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
            >
              Submit Answers
            </button>
          </div>
        )}
      </div>
    </QuizContainer>
  )
}
