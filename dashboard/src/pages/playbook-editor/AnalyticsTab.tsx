export function AnalyticsTab() {
    return (
        <div className="text-center py-24 px-8 bg-white rounded-xl border border-slate-200">
            <svg width="64" height="64" fill="none" stroke="var(--text-muted)" viewBox="0 0 24 24" className="mx-auto mb-6">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Analytics dashboard coming in Phase 9</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
                Track rule hit rates, most flagged clauses, condition trigger frequency, and negotiation tier usage across all scans using this playbook.
            </p>
        </div>
    );
}
