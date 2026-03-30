import { useParams, Navigate, useNavigate } from 'react-router-dom'
import { lazy, Suspense, useEffect, useState, useCallback, useMemo } from 'react'
import { gsap } from 'gsap'
import { useRef } from 'react'
import Layout from '../../../components/shell/Layout'
import ScanDivider from '../../../components/shell/ScanDivider'
import ScrollSection from '../../../components/scroll/ScrollSection'
import TextReveal from '../../../components/scroll/TextReveal'
import BodyReveal from '../../../components/scroll/BodyReveal'
import ChapterRenderer from '../../../components/ChapterRenderer'
import QuizGate from '../../../components/QuizGate'
import { getSession, TOTAL_SESSIONS } from '../../../lib/contentLoader'
import { useProgress } from '../../../stores/useProgress'
import { useAudioPlayer } from '../../../hooks/useAudioPlayer'

/* ------------------------------------------------------------------ */
/*  Lazy-loaded 3D scenes                                             */
/* ------------------------------------------------------------------ */

const SceneWrapper = lazy(() => import('../../../components/three/SceneWrapper'))
const GoldParticles = lazy(() => import('../../../components/three/GoldParticles'))
const ContractUnfold = lazy(() => import('../../../components/three/ContractUnfold'))
const NeuralNetwork = lazy(() => import('../../../components/three/NeuralNetwork'))
const SecurityFortress = lazy(() => import('../../../components/three/SecurityFortress'))
const Constellation = lazy(() => import('../../../components/three/Constellation'))

const HERO_SCENES: Record<number, React.LazyExoticComponent<React.ComponentType>> = {
  1: ContractUnfold,
  2: NeuralNetwork,
  3: SecurityFortress,
  4: Constellation,
}

/* ------------------------------------------------------------------ */
/*  Session page                                                      */
/* ------------------------------------------------------------------ */

export default function ContraRedSession() {
  const { sessionId } = useParams()
  const id = Number(sessionId)
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)

  // Progress store
  const sessionProgress = useProgress((s) => s.books.contrared?.sessions[id])
  const startSession = useProgress((s) => s.startSession)
  const completeChapter = useProgress((s) => s.completeChapter)
  const updateScrollProgress = useProgress((s) => s.updateScrollProgress)
  const addTime = useProgress((s) => s.addTime)

  // Session content
  const sessionData = useMemo(() => getSession(id), [id])

  // State
  const [showQuiz, setShowQuiz] = useState(false)
  const [completedChapterIds, setCompletedChapterIds] = useState<Set<number>>(new Set())

  // Graceful ambient audio (won't crash if audio files don't exist)
  useAudioPlayer(sessionData?.ambientTrack)

  // Start session on mount
  useEffect(() => {
    if (sessionProgress?.status === 'available') {
      startSession('contrared', id)
    }
  }, [id, sessionProgress?.status, startSession])

  // Time tracking: add 10s every 10 seconds
  useEffect(() => {
    if (!sessionData) return
    const timer = setInterval(() => {
      addTime('contrared', id, 10)
    }, 10_000)
    return () => clearInterval(timer)
  }, [id, addTime, sessionData])

  // Track scroll progress
  useEffect(() => {
    if (!sessionData) return
    function handleScroll() {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight
      if (scrollHeight > 0) {
        const progress = Math.round((window.scrollY / scrollHeight) * 100)
        updateScrollProgress('contrared', id, progress)
      }
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [id, updateScrollProgress, sessionData])

  // Entrance animation
  useEffect(() => {
    if (!containerRef.current) return
    gsap.fromTo(
      containerRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.8, ease: 'power2.out' },
    )
  }, [id])

  // Chapter completion handler
  const handleChapterComplete = useCallback(
    (chapterId: number) => {
      setCompletedChapterIds((prev) => {
        const next = new Set(prev)
        next.add(chapterId)
        return next
      })
      completeChapter('contrared', id, chapterId)
    },
    [id, completeChapter],
  )

  // Auto-show quiz when all chapters complete
  const allChaptersComplete = sessionData
    ? sessionData.chapters.every((c) => completedChapterIds.has(c.id))
    : false

  useEffect(() => {
    if (allChaptersComplete && !showQuiz) {
      setShowQuiz(true)
    }
  }, [allChaptersComplete, showQuiz])

  // Lock check (after all hooks)
  if (sessionProgress?.status === 'locked') {
    return <Navigate to="/locked" replace />
  }

  // Invalid session (after all hooks)
  if (!sessionData) {
    return <Navigate to="/contrared" replace />
  }

  // Quiz completion: navigate to next session or completion
  const handleQuizComplete = useCallback(() => {
    if (id >= TOTAL_SESSIONS) {
      navigate('/completion')
    } else {
      navigate(`/contrared/session/${id + 1}`)
    }
  }, [id, navigate])

  // Progress calculation
  const totalChapters = sessionData.chapters.length
  const currentChapterCount = completedChapterIds.size

  // Determine hero scene component
  const HeroComponent = HERO_SCENES[id]

  return (
    <Layout
      sessionLabel={`Session ${id} of ${TOTAL_SESSIONS}`}
      progress={{
        current: currentChapterCount,
        total: totalChapters,
        label: `Ch ${Math.min(currentChapterCount + 1, totalChapters)} of ${totalChapters}`,
      }}
    >
      <div ref={containerRef} style={{ opacity: 0 }}>
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
            {HeroComponent && <HeroComponent />}
          </SceneWrapper>
        </Suspense>

        <div className="max-w-3xl mx-auto px-6 py-12">
          {/* Session header */}
          <ScrollSection>
            <TextReveal as="h1">{sessionData.title}</TextReveal>
            <BodyReveal className="mt-4">
              <p className="text-text-muted text-lg">{sessionData.subtitle}</p>
            </BodyReveal>
          </ScrollSection>

          {/* Chapters */}
          <div className="mt-12">
            {sessionData.chapters.map((chapter, i) => (
              <div key={chapter.id}>
                {i > 0 && <ScanDivider className="my-12" />}
                <ChapterRenderer
                  chapter={chapter}
                  onChapterComplete={() => handleChapterComplete(chapter.id)}
                />
              </div>
            ))}
          </div>

          <ScanDivider className="my-12" />

          {/* Quiz Gate */}
          {!showQuiz ? (
            <ScrollSection>
              <div className="text-center py-12">
                <h2 className="text-gold font-serif text-3xl mb-4">Knowledge Check</h2>
                <p className="text-text-muted mb-8">
                  Test your understanding of {sessionData.title}.
                </p>
                <button
                  onClick={() => setShowQuiz(true)}
                  className="bg-gold text-bg font-mono text-sm px-8 py-3 rounded-lg hover:opacity-90 transition-opacity font-semibold"
                >
                  Start Quiz
                </button>
              </div>
            </ScrollSection>
          ) : (
            <QuizGate
              sessionId={id}
              quiz={sessionData.quiz}
              sessionTitle={sessionData.title}
              onComplete={handleQuizComplete}
            />
          )}
        </div>
      </div>
    </Layout>
  )
}
