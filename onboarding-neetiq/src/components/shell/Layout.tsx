import { type ReactNode } from 'react'
import TopBar from './TopBar'
import ProgressBar from './ProgressBar'

interface LayoutProps {
  children: ReactNode
  sessionLabel?: string
  progress?: { current: number; total: number; label?: string }
}

export default function Layout({ children, sessionLabel, progress }: LayoutProps) {
  return (
    <>
      <TopBar sessionLabel={sessionLabel} />
      <main className="pt-14 pb-10">
        {children}
      </main>
      {progress && <ProgressBar {...progress} />}
    </>
  )
}
