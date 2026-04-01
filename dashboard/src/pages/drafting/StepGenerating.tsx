export default function StepGenerating() {
    return (
        <div className="animate-fade-in flex flex-col items-center justify-center py-16">
            <div className="relative mb-8">
                <div className="w-20 h-20 rounded-full border-4 animate-spin" style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Generating Your Contract</h3>
            <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)' }}>Our AI agents are drafting, reviewing, and polishing your document...</p>
            <div className="space-y-3 w-full max-w-sm">
                {['Validating inputs', 'Drafting clauses', 'Risk review', 'Compliance check', 'Quality assurance', 'Final assembly'].map((label, i) => (
                    <div key={label} className="flex items-center gap-3 text-sm">
                        <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--risk-low-bg)' }}>
                            <svg className="w-3 h-3 animate-pulse" style={{ color: 'var(--risk-low)' }} fill="currentColor" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="4" />
                            </svg>
                        </div>
                        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
