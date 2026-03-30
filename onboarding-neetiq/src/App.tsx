function App() {
  return (
    <div className="min-h-screen bg-bg text-text-primary grain-overlay grid-overlay">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-gold font-serif text-4xl">NeetiQ Chronicles</h1>
        <p className="text-text-muted mt-2 font-sans">Your onboarding library.</p>
        <div className="scan-divider my-8" />
        <p className="text-text-primary font-sans">If you see gold text on dark background with a grain texture, a subtle grid, and a gold divider sweep — everything works.</p>
        <div className="mt-6 p-4 bg-surface border border-border rounded-lg">
          <code className="font-mono text-sm text-risk-green">✓ TailwindCSS configured</code>
        </div>
      </div>
    </div>
  )
}

export default App
