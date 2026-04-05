import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense, Component, type ReactNode, type ErrorInfo } from 'react'

const Home = lazy(() => import('./routes/Home'))
const ContraRedLanding = lazy(() => import('./routes/books/contrared/Landing'))
const ContraRedSession = lazy(() => import('./routes/books/contrared/Session'))
const Lock = lazy(() => import('./routes/Lock'))
const Completion = lazy(() => import('./routes/Completion'))

function Loading() {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center grain-overlay">
      <div className="text-gold animate-pulse font-mono text-sm tracking-widest">LOADING</div>
    </div>
  )
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App Error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-bg flex items-center justify-center p-8">
          <div className="max-w-lg text-center">
            <h1 className="text-red-500 font-mono text-xl mb-4">Something went wrong</h1>
            <pre className="text-left text-red-400 font-mono text-xs bg-gray-900 p-4 rounded overflow-auto max-h-60">
              {this.state.error?.message}
              {'\n\n'}
              {this.state.error?.stack}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-gold text-black rounded font-mono text-sm"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/contrared" element={<ContraRedLanding />} />
            <Route path="/contrared/session/:sessionId" element={<ContraRedSession />} />
            <Route path="/locked" element={<Lock />} />
            <Route path="/completion" element={<Completion />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
