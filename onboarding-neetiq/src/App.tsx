import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'

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

export default function App() {
  return (
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
  )
}
