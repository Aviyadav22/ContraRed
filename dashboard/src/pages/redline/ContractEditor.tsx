import { useRef, useEffect, useCallback, type CSSProperties } from 'react';
import type { RedlineItem } from '@/api/client';
import { findClausePosition, type RiskHighlight } from './textEngine';
import type { AppliedFix, PagePhase } from './types';

interface Props {
    contractText: string;
    onTextChange: (text: string) => void;
    editedText: string;
    phase: PagePhase;
    risks: RedlineItem[];
    appliedEdits: AppliedFix[];
    activeRiskId?: string;
    onActiveRiskChange?: (id: string | undefined) => void;
}

const wrapperStyle: CSSProperties = {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    minHeight: 0,
};

const editorStyle: CSSProperties = {
    flex: 1,
    padding: '24px 28px',
    fontSize: 14,
    lineHeight: 1.8,
    fontFamily: "'Georgia', 'Times New Roman', serif",
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    overflowY: 'auto',
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
    outline: 'none',
    minHeight: 200,
};

const placeholderOverlayStyle: CSSProperties = {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    pointerEvents: 'none',
    zIndex: 1,
};

export function ContractEditor({
    contractText, onTextChange, editedText, phase,
    risks, appliedEdits, activeRiskId, onActiveRiskChange,
}: Props) {
    const editorRef = useRef<HTMLDivElement>(null);
    const isResultsMode = phase === 'results';
    const isEmpty = !contractText.trim();

    // Handle paste — strip formatting
    const handlePaste = useCallback((e: React.ClipboardEvent) => {
        if (isResultsMode) return;
        e.preventDefault();
        const plainText = e.clipboardData.getData('text/plain');

        if (editorRef.current) {
            if (isEmpty) {
                editorRef.current.textContent = plainText;
            } else {
                const selection = window.getSelection();
                if (selection && selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    range.deleteContents();
                    range.insertNode(document.createTextNode(plainText));
                    range.collapse(false);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            }
            onTextChange(editorRef.current.innerText || '');
        }
    }, [isResultsMode, onTextChange, isEmpty]);

    const handleInput = useCallback(() => {
        if (isResultsMode) return;
        if (editorRef.current) {
            onTextChange(editorRef.current.innerText || '');
        }
    }, [isResultsMode, onTextChange]);

    // In results mode, render highlighted HTML
    useEffect(() => {
        if (!isResultsMode || !editorRef.current) return;

        const textToRender = editedText || contractText;
        const appliedRiskIds = new Set(appliedEdits.map(e => e.riskId));

        // Build highlights for unfixed risks
        const highlights: RiskHighlight[] = [];
        for (const risk of risks) {
            if (appliedRiskIds.has(risk.id)) continue;
            const pos = findClausePosition(textToRender, risk.clause_text);
            if (pos) {
                highlights.push({
                    riskId: risk.id,
                    riskLevel: risk.risk_level,
                    start: pos.start,
                    end: pos.end,
                });
            }
        }

        // Build highlights for applied fixes (show replacement text in green)
        for (const edit of appliedEdits) {
            if (!edit.fixText) continue;
            const pos = findClausePosition(textToRender, edit.fixText);
            if (pos) {
                highlights.push({
                    riskId: edit.riskId,
                    riskLevel: 'APPLIED' as any,
                    start: pos.start,
                    end: pos.end,
                });
            }
        }

        // Sort by start position, remove overlaps
        highlights.sort((a, b) => a.start - b.start);
        const filtered: RiskHighlight[] = [];
        let lastEnd = 0;
        for (const h of highlights) {
            if (h.start >= lastEnd) {
                filtered.push(h);
                lastEnd = h.end;
            }
        }

        // Render HTML
        const html = buildHighlightedHtml(textToRender, filtered);
        editorRef.current.innerHTML = html;
    }, [isResultsMode, editedText, contractText, risks, appliedEdits]);

    // Scroll to active risk
    useEffect(() => {
        if (!activeRiskId || !editorRef.current) return;
        const mark = editorRef.current.querySelector(`[data-risk-id="${activeRiskId}"]`);
        if (mark) {
            mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
            (mark as HTMLElement).style.outline = '2px solid var(--accent)';
            (mark as HTMLElement).style.outlineOffset = '2px';
            setTimeout(() => {
                (mark as HTMLElement).style.outline = 'none';
            }, 2000);
        }
    }, [activeRiskId]);

    // Handle click on highlighted risk
    const handleClick = useCallback((e: React.MouseEvent) => {
        const target = (e.target as HTMLElement).closest('[data-risk-id]');
        if (target && onActiveRiskChange) {
            onActiveRiskChange(target.getAttribute('data-risk-id') || undefined);
        }
    }, [onActiveRiskChange]);

    return (
        <div style={wrapperStyle}>
            {isEmpty && !isResultsMode && (
                <div style={placeholderOverlayStyle}>
                    <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-muted)' }}>
                        Paste your contract here
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)', opacity: 0.7 }}>
                        NDA, SaaS, MSA, Employment, DPA...
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', opacity: 0.5, marginTop: 4 }}>
                        Ctrl+V to paste &middot; Min 50 characters
                    </div>
                </div>
            )}

            <div
                ref={editorRef}
                contentEditable={!isResultsMode}
                suppressContentEditableWarning
                style={{
                    ...editorStyle,
                    cursor: isResultsMode ? 'default' : 'text',
                    backgroundColor: isResultsMode ? 'var(--bg-app)' : 'var(--bg-surface)',
                    borderColor: isResultsMode ? 'var(--border)' : isEmpty ? 'var(--border)' : 'var(--border-strong)',
                }}
                onPaste={handlePaste}
                onInput={handleInput}
                onClick={isResultsMode ? handleClick : undefined}
                dangerouslySetInnerHTML={
                    isResultsMode ? undefined : (isEmpty ? undefined : { __html: escapeHtml(contractText) })
                }
            />
        </div>
    );
}

// ---- HTML rendering ----

function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

const HIGHLIGHT_STYLES: Record<string, { bg: string; border: string }> = {
    RED: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.35)' },
    YELLOW: { bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.30)' },
    GREEN: { bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.25)' },
    APPLIED: { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.40)' },
};

function buildHighlightedHtml(text: string, highlights: RiskHighlight[]): string {
    let html = '';
    let cursor = 0;

    for (const h of highlights) {
        if (h.start > cursor) {
            html += escapeHtml(text.slice(cursor, h.start));
        }

        const style = HIGHLIGHT_STYLES[h.riskLevel] || HIGHLIGHT_STYLES.YELLOW;
        const isApplied = h.riskLevel === ('APPLIED' as any);

        html += `<mark data-risk-id="${h.riskId}" style="background:${style.bg};border-bottom:2px solid ${style.border};border-radius:2px;padding:2px 1px;cursor:pointer${isApplied ? ';font-style:italic' : ''}">${escapeHtml(text.slice(h.start, h.end))}</mark>`;
        cursor = h.end;
    }

    if (cursor < text.length) {
        html += escapeHtml(text.slice(cursor));
    }

    return html;
}
