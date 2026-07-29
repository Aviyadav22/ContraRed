import { useQuery } from '@tanstack/react-query';
import { getDraftAddinPayload, type GenerateResponse } from '@/api/client';

interface StepResultsProps {
    result: GenerateResponse | null;
    onDownload: () => void;
    onReset: () => void;
}

interface PreviewSection {
    heading: string;
    content: string;
}

const PREVIEW_SECTION_COUNT = 2;
const PREVIEW_CHAR_LIMIT = 700;

function truncate(text: string, max: number): string {
    if (!text) return '';
    if (text.length <= max) return text;
    return text.slice(0, max).trimEnd() + '…';
}

export default function StepResults({ result, onDownload, onReset }: StepResultsProps) {
    const draftId = result?.draft_id;
    const {
        data: preview,
        isFetching: previewLoading,
        isError: previewError,
    } = useQuery({
        queryKey: ['draft-preview', draftId],
        queryFn: async () => {
            const payload = await getDraftAddinPayload(draftId!);
            const sections = (payload?.sections as PreviewSection[] | undefined) ?? [];
            return sections
                .filter(s => s?.content && s.content.trim().length > 40)
                .slice(0, PREVIEW_SECTION_COUNT)
                .map(s => ({
                    heading: s.heading || '',
                    content: truncate(s.content, PREVIEW_CHAR_LIMIT),
                }));
        },
        enabled: Boolean(draftId),
        retry: false,
    });

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

            {/* Preview */}
            {!previewError && (
                <div
                    className="rounded-xl border p-5 mt-2"
                    style={{
                        borderColor: 'var(--border)',
                        backgroundColor: 'var(--bg-app)',
                    }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="text-sm font-semibold tracking-wide uppercase" style={{ color: 'var(--text-secondary)' }}>
                            Preview
                        </h4>
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            First {PREVIEW_SECTION_COUNT} sections · truncated
                        </span>
                    </div>

                    {previewLoading && (
                        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                            <div
                                className="w-4 h-4 rounded-full border-2 animate-spin"
                                style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }}
                            />
                            Loading preview…
                        </div>
                    )}

                    {!previewLoading && preview && preview.length > 0 && (
                        <div className="space-y-5">
                            {preview.map((section, idx) => (
                                <div key={idx}>
                                    <h5
                                        className="text-sm font-semibold mb-2"
                                        style={{ color: 'var(--text-primary)' }}
                                    >
                                        {section.heading}
                                    </h5>
                                    <p
                                        className="text-sm whitespace-pre-wrap leading-relaxed"
                                        style={{ color: 'var(--text-secondary)' }}
                                    >
                                        {section.content}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}

                    {!previewLoading && preview && preview.length === 0 && (
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                            No preview available. Download the full contract to review.
                        </p>
                    )}
                </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap justify-center gap-4 pt-4">
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
