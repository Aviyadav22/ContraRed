import { useParams, Navigate, useNavigate } from 'react-router-dom'
import { lazy, Suspense, useEffect, useState, useCallback, useMemo, type ReactElement } from 'react'
import Layout from '../../../components/shell/Layout'
import ScrollSection from '../../../components/scroll/ScrollSection'
import TextReveal from '../../../components/scroll/TextReveal'
import BodyReveal from '../../../components/scroll/BodyReveal'
import QuizContainer from '../../../components/quiz/QuizContainer'
import QuizResults from '../../../components/quiz/QuizResults'
import SessionComplete from '../../../components/celebrations/SessionComplete'
import Chapter from './Chapter'
import { getSession, type Quiz, type Question } from '../../../lib/contentLoader'
import { useProgress } from '../../../stores/useProgress'
import { useQuiz } from '../../../stores/useQuiz'
import { useAudioPlayer } from '../../../hooks/useAudioPlayer'

// Lazy-load 3D scenes for code splitting
const SceneWrapper = lazy(() => import('../../../components/three/SceneWrapper'))
const GoldParticles = lazy(() => import('../../../components/three/GoldParticles'))
const ContractUnfold = lazy(() => import('../../../components/three/ContractUnfold'))
const NeuralNetwork = lazy(() => import('../../../components/three/NeuralNetwork'))
const SecurityFortress = lazy(() => import('../../../components/three/SecurityFortress'))
const Constellation = lazy(() => import('../../../components/three/Constellation'))

// Lazy-load quiz components
const Flashcard = lazy(() => import('../../../components/quiz/Flashcard'))
const DragDrop = lazy(() => import('../../../components/quiz/DragDrop'))
const Scenario = lazy(() => import('../../../components/quiz/Scenario'))

const HERO_SCENES: Record<number, () => ReactElement> = {
  1: () => <ContractUnfold />,
  2: () => <NeuralNetwork />,
  3: () => <SecurityFortress />,
  4: () => <Constellation />,
}

const SESSION_TITLES: Record<number, { title: string; subtitle: string }> = {
  1: { title: 'The Origin Story', subtitle: 'From a chance meeting to the birth of ContraRed' },
  2: { title: 'The Technology', subtitle: 'AI, Playbooks, the Pipeline, and the Control Center' },
  3: { title: 'The Real World', subtitle: 'Security, deployment, the lawyer test, and the great migration' },
  4: { title: 'The Full Picture', subtitle: 'Architecture, numbers, and the road ahead' },
}

type SessionPhase = 'reading' | 'quiz' | 'results' | 'celebration'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  const id = Number(sessionId)
  const navigate = useNavigate()

  const sessionProgress = useProgress((s) => s.books.contrared?.sessions[id])
  const startSession = useProgress((s) => s.startSession)
  const completeChapter = useProgress((s) => s.completeChapter)
  const updateScrollProgress = useProgress((s) => s.updateScrollProgress)
  const submitQuizProgress = useProgress((s) => s.submitQuiz)

  const quizStore = useQuiz()

  const [phase, setPhase] = useState<SessionPhase>('reading')
  const [completedChapters, setCompletedChapters] = useState<Set<number>>(new Set())

  // Load session content
  const sessionData = useMemo(() => getSession(id), [id])

  // Audio
  useAudioPlayer(sessionData?.ambientTrack)

  // Redirect if locked
  if (sessionProgress?.status === 'locked') {
    return <Navigate to="/locked" replace />
  }

  // Start session on mount if available
  useEffect(() => {
    if (sessionProgress?.status === 'available') {
      startSession('contrared', id)
    }
  }, [id, sessionProgress?.status, startSession])

  // Load quiz questions when entering quiz phase
  useEffect(() => {
    if (phase === 'quiz' && sessionData?.quiz?.questions) {
      quizStore.loadQuestions(sessionData.quiz.questions)
    }
  }, [phase, sessionData])

  // Track scroll progress
  useEffect(() => {
    function handleScroll() {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight
      if (scrollHeight > 0) {
        const progress = Math.round((window.scrollY / scrollHeight) * 100)
        updateScrollProgress('contrared', id, progress)
      }
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [id, updateScrollProgress])

  const handleChapterComplete = useCallback(
    (chapterId: number) => {
      setCompletedChapters((prev) => {
        const next = new Set(prev)
        next.add(chapterId)
        return next
      })
      completeChapter('contrared', id, chapterId)
    },
    [id, completeChapter]
  )

  const allChaptersComplete = sessionData
    ? sessionData.chapters.every((c: any) => completedChapters.has(c.id))
    : false

  // Auto-transition to quiz when all chapters are read
  useEffect(() => {
    if (allChaptersComplete && phase === 'reading') {
      setPhase('quiz')
    }
  }, [allChaptersComplete, phase])

  const handleQuizSubmit = useCallback(() => {
    const result = quizStore.submit()
    submitQuizProgress('contrared', id, result.score, result.total, result.answers)
    setPhase('results')
  }, [id, quizStore, submitQuizProgress])

  const handleQuizRetry = useCallback(() => {
    quizStore.reset()
    if (sessionData?.quiz?.questions) {
      quizStore.loadQuestions(sessionData.quiz.questions)
    }
    setPhase('quiz')
  }, [quizStore, sessionData])

  const handleQuizContinue = useCallback(() => {
    setPhase('celebration')
  }, [])

  const handleSessionContinue = useCallback(() => {
    if (id >= 4) {
      navigate('/completion')
    } else {
      navigate(`/contrared/session/${id + 1}`)
    }
  }, [id, navigate])

  if (!sessionData) {
    return <Navigate to="/contrared" replace />
  }

  const meta = SESSION_TITLES[id] || { title: `Session ${id}`, subtitle: '' }
  const chapters = sessionData.chapters || []
  const totalChapters = chapters.length
  const currentChapterCount = completedChapters.size

  const HeroScene = HERO_SCENES[id]

  return (
    <Layout
      sessionLabel={`Session ${id} of 4`}
      progress={{ current: currentChapterCount, total: totalChapters, label: `Ch ${currentChapterCount} of ${totalChapters}` }}
    >
      {/* 3D Hero Scene */}
      <Suspense
        fallback={
          <div className="w-full h-[60vh] bg-bg flex items-center justify-center">
            <div className="text-gold animate-pulse font-mono text-sm tracking-widest">
              LOADING SCENE
            </div>
          </div>
        }
      >
        <SceneWrapper>
          <GoldParticles />
          {HeroScene && <HeroScene />}
        </SceneWrapper>
      </Suspense>

      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Session title */}
        <ScrollSection>
          <TextReveal as="h1">{meta.title}</TextReveal>
          <BodyReveal className="mt-4">
            <p className="text-text-muted text-lg">{meta.subtitle}</p>
          </BodyReveal>
        </ScrollSection>

        {/* Chapters */}
        <div className="mt-12">
          {chapters.map((chapter: any) => (
            <Chapter
              key={chapter.id}
              chapter={chapter}
              onComplete={() => handleChapterComplete(chapter.id)}
            />
          ))}
        </div>

        {/* Quiz Gate */}
        {phase !== 'reading' && (
          <div className="mt-16">
            {phase === 'quiz' && (
              <Suspense
                fallback={
                  <div className="text-gold animate-pulse font-mono text-sm text-center py-8">
                    LOADING QUIZ
                  </div>
                }
              >
                <QuizContainer title={`Session ${id} Knowledge Check`}>
                  <QuizSection
                    quiz={sessionData.quiz}
                    quizStore={quizStore}
                    onSubmit={handleQuizSubmit}
                  />
                </QuizContainer>
              </Suspense>
            )}

            {phase === 'results' && quizStore.result && (
              <QuizResults
                score={quizStore.result.score}
                total={quizStore.result.total}
                passed={quizStore.result.passed}
                onContinue={handleQuizContinue}
                onRetry={handleQuizRetry}
              />
            )}

            {phase === 'celebration' && (
              <SessionComplete
                sessionNumber={id}
                sessionTitle={meta.title}
                onContinue={handleSessionContinue}
              />
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}

/**
 * Inner component that renders the appropriate quiz type based on session data.
 */
function QuizSection({
  quiz,
  quizStore,
  onSubmit,
}: {
  quiz: Quiz
  quizStore: {
    questions: Question[]
    answers: Record<string, string>
    answerQuestion: (questionId: string, answer: string) => void
  }
  onSubmit: () => void
}) {
  const { questions, answers, answerQuestion } = quizStore
  const allAnswered = questions.length > 0 && Object.keys(answers).length >= questions.length

  if (quiz.type === 'flashcard') {
    return (
      <div className="space-y-6">
        {questions.map((q) => (
          <Flashcard
            key={q.id}
            question={q.question}
            answer={q.explanation}
            isCorrect={q.correctAnswer === 'true'}
            onAnswer={(correct) => answerQuestion(q.id, correct ? 'true' : 'false')}
          />
        ))}
        {allAnswered && (
          <button
            onClick={onSubmit}
            className="w-full bg-gold text-bg font-mono text-sm py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
          >
            Submit Answers
          </button>
        )}
      </div>
    )
  }

  if (quiz.type === 'dragdrop') {
    const q = questions[0]
    if (!q) return null
    return (
      <div className="space-y-6">
        <p className="font-serif text-lg text-text-primary">{q.question}</p>
        <DragDrop
          items={q.options || []}
          correctOrder={Array.isArray(q.correctAnswer) ? q.correctAnswer : []}
          onComplete={(userOrder) => {
            answerQuestion(q.id, JSON.stringify(userOrder))
          }}
        />
        {allAnswered && (
          <button
            onClick={onSubmit}
            className="w-full bg-gold text-bg font-mono text-sm py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
          >
            Submit Answer
          </button>
        )}
      </div>
    )
  }

  if (quiz.type === 'scenario') {
    return (
      <div className="space-y-8">
        {questions.map((q) => (
          <Scenario
            key={q.id}
            question={q.question}
            options={q.options || []}
            correctIndex={(q.options || []).indexOf(
              Array.isArray(q.correctAnswer) ? q.correctAnswer[0] : q.correctAnswer
            )}
            explanation={q.explanation}
            onAnswer={(correct) => answerQuestion(q.id, correct ? q.correctAnswer as string : '__wrong__')}
          />
        ))}
        {allAnswered && (
          <button
            onClick={onSubmit}
            className="w-full bg-gold text-bg font-mono text-sm py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
          >
            Submit Answers
          </button>
        )}
      </div>
    )
  }

  // Mixed quiz type: render each question based on its format
  if (quiz.type === 'mixed') {
    return (
      <div className="space-y-8">
        {questions.map((q) => {
          if (q.format === 'true-false') {
            return (
              <Flashcard
                key={q.id}
                question={q.question}
                answer={q.explanation}
                isCorrect={q.correctAnswer === 'true'}
                onAnswer={(correct) => answerQuestion(q.id, correct ? 'true' : 'false')}
              />
            )
          }

          if (q.format === 'drag-order') {
            return (
              <div key={q.id} className="space-y-4">
                <p className="font-serif text-lg text-text-primary">{q.question}</p>
                <DragDrop
                  items={q.options || []}
                  correctOrder={Array.isArray(q.correctAnswer) ? q.correctAnswer : []}
                  onComplete={(userOrder) => {
                    answerQuestion(q.id, JSON.stringify(userOrder))
                  }}
                />
              </div>
            )
          }

          if (q.format === 'multiple-choice') {
            return (
              <Scenario
                key={q.id}
                question={q.question}
                options={q.options || []}
                correctIndex={(q.options || []).indexOf(
                  Array.isArray(q.correctAnswer) ? q.correctAnswer[0] : q.correctAnswer
                )}
                explanation={q.explanation}
                onAnswer={(correct) =>
                  answerQuestion(q.id, correct ? (q.correctAnswer as string) : '__wrong__')
                }
              />
            )
          }

          // Default fallback
          return (
            <div key={q.id} className="text-text-muted text-sm">
              Unsupported question format: {q.format}
            </div>
          )
        })}
        {allAnswered && (
          <button
            onClick={onSubmit}
            className="w-full bg-gold text-bg font-mono text-sm py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
          >
            Submit All Answers
          </button>
        )}
      </div>
    )
  }

  return <div className="text-text-muted">Unknown quiz type</div>
}
