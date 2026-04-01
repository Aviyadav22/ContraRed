import { type GenerateResponse } from '@/api/client';

interface StepResultsProps {
    result: GenerateResponse | null;
    onDownload: () => void;
    onReset: () => void;
}

export default function StepResults({ result, onDownload, onReset }: StepResultsProps) {
    if (!result) return null;

    const scoreColor = (s: number) => s >= 80 ? 'var(--risk-low)' : s >= 60 ? 'var(--risk-high)' : 'var(--accent)';
    const scoreBg = (s: number) => s >= 80 ? 'var(--risk-low-bg)' : s >= 60 ? 'var(--risk-high-bg)' : 'var(--accent-glow)';

    return (
        <div className="animate-fade-in space-y-6">
            <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-3" style={{ backgroundColor: 'var(--risk-low-bg)' }}>
                    <svg className="w-8 h-8" style={{ color: 'var(--risk-low)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{result.title}</h3>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{result.total_sections} sections generated</p>
            </div>

            {/* Quality Scores */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: 'Overall', score: result.overall_score },
                    { label: 'Risk Alignment', score: result.risk_alignment },
                    { label: 'Compliance', score: result.compliance_score },
                    { label: 'Quality', score: result.qa_score },
                ].map(({ label, score }) => (
                    <div key={label} className="p-4 rounded-xl text-center" style={{ backgroundColor: scoreBg(score) }}>
                        <div className="text-2xl font-bold" style={{ color: scoreColor(score) }}>{Math.round(score)}</div>
                        <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                    </div>
                ))}
            </div>

            {/* Stats */}
            <div className="flex justify-center gap-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <span>{result.annotations_applied} fixes applied</span>
                <span>{result.conflicts_flagged} conflicts</span>
                <span>{result.open_items} items for review</span>
            </div>

            {/* Actions */}
            <div className="flex justify-center gap-4 pt-4">
                <button
                    onClick={onDownload}
                    className="px-6 py-3 rounded-xl text-sm font-semibold text-white transition-transform active:scale-[0.98]"
                    style={{ backgroundColor: 'var(--accent)' }}
                >
                    Download .docx
                </button>
                <button
                    onClick={onReset}
                    className="px-6 py-3 rounded-xl text-sm font-medium border transition-colors"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                >
                    Draft Another
                </button>
            </div>
        </div>
    );
}
