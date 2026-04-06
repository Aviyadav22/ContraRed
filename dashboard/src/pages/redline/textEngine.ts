/**
 * Pure text manipulation functions for web-based contract redlining.
 * No React dependencies — all functions are stateless and testable.
 */

// ============================================================================
// Find clause position in document text
// ============================================================================

export function findClausePosition(
    documentText: string,
    clauseText: string,
): { start: number; end: number } | null {
    if (!clauseText || !documentText) return null;

    // Tier 1: Exact match
    const idx = documentText.indexOf(clauseText);
    if (idx !== -1) {
        return { start: idx, end: idx + clauseText.length };
    }

    // Tier 2: Normalized whitespace match
    const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();
    const normalizedDoc = normalize(documentText);
    const normalizedClause = normalize(clauseText);
    const normIdx = normalizedDoc.indexOf(normalizedClause);
    if (normIdx !== -1) {
        // Map back to original positions by walking both strings
        let origPos = 0;
        let normPos = 0;
        // Skip to normIdx in normalized space
        while (normPos < normIdx && origPos < documentText.length) {
            if (/\s/.test(documentText[origPos])) {
                // In original, skip whitespace runs that map to single space
                while (origPos < documentText.length && /\s/.test(documentText[origPos])) origPos++;
                normPos++; // single space in normalized
            } else {
                origPos++;
                normPos++;
            }
        }
        const start = origPos;
        // Now walk normalizedClause.length in normalized space
        let clauseNormPos = 0;
        while (clauseNormPos < normalizedClause.length && origPos < documentText.length) {
            if (/\s/.test(documentText[origPos])) {
                while (origPos < documentText.length && /\s/.test(documentText[origPos])) origPos++;
                clauseNormPos++;
            } else {
                origPos++;
                clauseNormPos++;
            }
        }
        return { start, end: origPos };
    }

    // Tier 3: Substring match on first 150 chars
    const prefix = normalizedClause.slice(0, 150);
    if (prefix.length >= 20) {
        const prefixIdx = normalizedDoc.indexOf(prefix);
        if (prefixIdx !== -1) {
            // Rough mapping — use same walk approach but less precise
            let origPos = 0;
            let nPos = 0;
            while (nPos < prefixIdx && origPos < documentText.length) {
                if (/\s/.test(documentText[origPos])) {
                    while (origPos < documentText.length && /\s/.test(documentText[origPos])) origPos++;
                    nPos++;
                } else {
                    origPos++;
                    nPos++;
                }
            }
            // Estimate end based on original clause length
            const estimatedEnd = Math.min(origPos + clauseText.length, documentText.length);
            return { start: origPos, end: estimatedEnd };
        }
    }

    return null;
}

// ============================================================================
// Apply fix edits to text
// ============================================================================

export interface ApplyResult {
    newText: string;
    edits: Array<{
        start: number;
        end: number;
        original: string;
        replacement: string;
    }>;
}

export function applyFixEdits(
    text: string,
    edits: Array<{ find: string; replace: string }>,
): ApplyResult {
    // Find positions of all edits first
    const positioned: Array<{
        start: number;
        end: number;
        original: string;
        replacement: string;
    }> = [];

    for (const edit of edits) {
        const idx = text.indexOf(edit.find);
        if (idx !== -1) {
            positioned.push({
                start: idx,
                end: idx + edit.find.length,
                original: edit.find,
                replacement: edit.replace,
            });
        } else {
            // Try normalized whitespace match
            const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();
            const normText = normalize(text);
            const normFind = normalize(edit.find);
            const normIdx = normText.indexOf(normFind);
            if (normIdx !== -1) {
                // Approximate: use the normalized index as rough start
                // Walk original text to find actual position
                let origPos = 0;
                let nPos = 0;
                while (nPos < normIdx && origPos < text.length) {
                    if (/\s/.test(text[origPos])) {
                        while (origPos < text.length && /\s/.test(text[origPos])) origPos++;
                        nPos++;
                    } else {
                        origPos++;
                        nPos++;
                    }
                }
                const start = origPos;
                let cPos = 0;
                while (cPos < normFind.length && origPos < text.length) {
                    if (/\s/.test(text[origPos])) {
                        while (origPos < text.length && /\s/.test(text[origPos])) origPos++;
                        cPos++;
                    } else {
                        origPos++;
                        cPos++;
                    }
                }
                positioned.push({
                    start,
                    end: origPos,
                    original: text.slice(start, origPos),
                    replacement: edit.replace,
                });
            }
        }
    }

    // Sort by position descending so replacements don't shift earlier positions
    positioned.sort((a, b) => b.start - a.start);

    let result = text;
    for (const p of positioned) {
        result = result.slice(0, p.start) + p.replacement + result.slice(p.end);
    }

    // Re-sort ascending for return
    positioned.sort((a, b) => a.start - b.start);

    return { newText: result, edits: positioned };
}

// ============================================================================
// Word-level diff
// ============================================================================

export interface DiffToken {
    type: 'equal' | 'delete' | 'insert';
    text: string;
}

export function wordDiff(original: string, replacement: string): DiffToken[] {
    const wordsA = tokenize(original);
    const wordsB = tokenize(replacement);

    // LCS-based diff
    const lcs = computeLCS(wordsA, wordsB);
    const tokens: DiffToken[] = [];

    let i = 0;
    let j = 0;
    for (const match of lcs) {
        // Emit deletes for unmatched words in A
        while (i < match.aIdx) {
            tokens.push({ type: 'delete', text: wordsA[i] });
            i++;
        }
        // Emit inserts for unmatched words in B
        while (j < match.bIdx) {
            tokens.push({ type: 'insert', text: wordsB[j] });
            j++;
        }
        // Emit equal
        tokens.push({ type: 'equal', text: wordsA[i] });
        i++;
        j++;
    }
    // Remaining
    while (i < wordsA.length) {
        tokens.push({ type: 'delete', text: wordsA[i] });
        i++;
    }
    while (j < wordsB.length) {
        tokens.push({ type: 'insert', text: wordsB[j] });
        j++;
    }

    return tokens;
}

function tokenize(text: string): string[] {
    // Split on word boundaries, preserving whitespace and punctuation as tokens
    return text.match(/\S+|\s+/g) || [];
}

interface LCSMatch {
    aIdx: number;
    bIdx: number;
}

function computeLCS(a: string[], b: string[]): LCSMatch[] {
    const m = a.length;
    const n = b.length;
    // DP table
    const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
    for (let i = m - 1; i >= 0; i--) {
        for (let j = n - 1; j >= 0; j--) {
            if (a[i] === b[j]) {
                dp[i][j] = dp[i + 1][j + 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
            }
        }
    }

    // Backtrack
    const result: LCSMatch[] = [];
    let i = 0;
    let j = 0;
    while (i < m && j < n) {
        if (a[i] === b[j]) {
            result.push({ aIdx: i, bIdx: j });
            i++;
            j++;
        } else if (dp[i + 1][j] >= dp[i][j + 1]) {
            i++;
        } else {
            j++;
        }
    }
    return result;
}

// ============================================================================
// HTML generation for inline diff display
// ============================================================================

function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export interface RiskHighlight {
    riskId: string;
    riskLevel: 'RED' | 'YELLOW' | 'GREEN';
    start: number;
    end: number;
}

export interface InlineDiff {
    riskId: string;
    start: number;
    end: number;
    original: string;
    replacement: string;
}

const RISK_BG: Record<string, string> = {
    RED: 'rgba(239,68,68,0.12)',
    YELLOW: 'rgba(245,158,11,0.10)',
    GREEN: 'rgba(34,197,94,0.08)',
};

const RISK_BORDER: Record<string, string> = {
    RED: 'rgba(239,68,68,0.35)',
    YELLOW: 'rgba(245,158,11,0.30)',
    GREEN: 'rgba(34,197,94,0.25)',
};

export function generateDiffHtml(
    text: string,
    highlights: RiskHighlight[],
    diffs: InlineDiff[],
): string {
    // Build a sorted list of non-overlapping segments
    type Segment = {
        start: number;
        end: number;
        type: 'plain' | 'highlight' | 'diff';
        riskId?: string;
        riskLevel?: string;
        original?: string;
        replacement?: string;
    };

    const segments: Segment[] = [];

    // Add diff segments (these take priority over highlights)
    for (const d of diffs) {
        segments.push({
            start: d.start,
            end: d.end,
            type: 'diff',
            riskId: d.riskId,
            original: d.original,
            replacement: d.replacement,
        });
    }

    // Add highlight segments (skip if overlapping with a diff)
    for (const h of highlights) {
        const overlaps = segments.some(s => s.type === 'diff' && s.start < h.end && s.end > h.start);
        if (!overlaps) {
            segments.push({
                start: h.start,
                end: h.end,
                type: 'highlight',
                riskId: h.riskId,
                riskLevel: h.riskLevel,
            });
        }
    }

    // Sort by start position
    segments.sort((a, b) => a.start - b.start);

    // Build HTML
    let html = '';
    let cursor = 0;

    for (const seg of segments) {
        // Plain text before this segment
        if (seg.start > cursor) {
            html += escapeHtml(text.slice(cursor, seg.start));
        }

        if (seg.type === 'highlight') {
            const bg = RISK_BG[seg.riskLevel || 'YELLOW'];
            const border = RISK_BORDER[seg.riskLevel || 'YELLOW'];
            html += `<mark data-risk-id="${seg.riskId}" style="background:${bg};border-bottom:2px solid ${border};border-radius:2px;padding:2px 1px;cursor:pointer">${escapeHtml(text.slice(seg.start, seg.end))}</mark>`;
            cursor = seg.end;
        } else if (seg.type === 'diff') {
            html += `<del style="color:var(--risk-critical);text-decoration:line-through;background:rgba(239,68,68,0.08)">${escapeHtml(seg.original || '')}</del>`;
            html += `<ins style="color:var(--risk-low);background:rgba(34,197,94,0.12);text-decoration:none">${escapeHtml(seg.replacement || '')}</ins>`;
            cursor = seg.end;
        }
    }

    // Remaining text
    if (cursor < text.length) {
        html += escapeHtml(text.slice(cursor));
    }

    return html;
}
