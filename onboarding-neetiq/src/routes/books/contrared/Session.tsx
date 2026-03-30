import { useParams, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useProgress } from '../../../stores/useProgress'
import Layout from '../../../components/shell/Layout'
import ScanDivider from '../../../components/shell/ScanDivider'

export default function ContraRedSession() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const { books, startSession } = useProgress()
  const id = Number(sessionId)
  const session = books.contrared?.sessions[id]

  useEffect(() => {
    if (!session || session.status === 'locked') {
      navigate('/locked')
      return
    }
    if (session.status === 'available') {
      startSession('contrared', id)
    }
  }, [session, id, navigate, startSession])

  if (!session) return null

  const titles: Record<number, string> = {
    1: 'The Origin Story',
    2: 'The Technology',
    3: 'The Real World',
    4: 'The Full Picture',
  }

  return (
    <Layout
      sessionLabel={`Session ${id} of 4`}
      progress={{
        current: session.chaptersCompleted.length,
        total: id <= 2 ? 5 : id === 3 ? 4 : 2,
        label: `Ch ${session.currentChapter}`,
      }}
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-gold font-serif text-4xl">{titles[id]}</h1>
        <ScanDivider className="my-8" />
        <p className="text-text-muted">
          Session {id} content will be rendered here by the scroll chapter system.
        </p>
        <p className="text-text-muted mt-4 font-mono text-sm">
          Status: {session.status} {'\u00B7'} Chapters completed: {session.chaptersCompleted.length}
        </p>
      </div>
    </Layout>
  )
}
