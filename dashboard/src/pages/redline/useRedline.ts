import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
    analyzeContract,
    generateFix as apiGenerateFix,
    exportRedlineReport,
    type RedlineItem,
    type AnalysisResult,
    type GenerateFixResponse,
} from '@/api/client';
import { applyFixEdits, findClausePosition } from './textEngine';
import { useToast } from '@/contexts/ToastContext';
import type { PagePhase, FixState, RiskFilter, AppliedFix, UseRedlineReturn } from './types';

export function useRedline(): UseRedlineReturn {
    // ---- Input state ----
    const [contractText, setContractText] = useState('');
    const [playbookId, setPlaybookId] = useState('');
    const [partySide, setPartySide] = useState<'buyer' | 'seller' | 'neutral'>('buyer');
    const [jurisdiction, setJurisdiction] = useState('');

    // ---- Analysis state ----
    const [phase, setPhase] = useState<PagePhase>('input');
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
    const [analyzeError, setAnalyzeError] = useState<string | null>(null);

    // ---- Fix state ----
    const [fixStates, setFixStates] = useState<Map<string, FixState>>(new Map());
    const [generatedFixes, setGeneratedFixes] = useState<Map<string, GenerateFixResponse>>(new Map());
    const [editedText, setEditedText] = useState('');
    const [appliedEdits, setAppliedEdits] = useState<AppliedFix[]>([]);
    const [bulkProgress, setBulkProgress] = useState<{ current: number; total: number } | null>(null);

    // ---- Filter state ----
    const [filter, setFilterState] = useState<RiskFilter>({ level: 'ALL', search: '', sort: 'risk' });

    // Ref to track the latest edited text for sequential fix applications
    const editedTextRef = useRef('');
    editedTextRef.current = editedText;

    // Ref-synced fix states so async loops (e.g. applyAllFixes) can read
    // the latest values without being trapped in a stale closure.
    const fixStatesRef = useRef<Map<string, FixState>>(new Map());
    fixStatesRef.current = fixStates;

    // Ref-synced generated fixes for the same reason.
    const generatedFixesRef = useRef<Map<string, GenerateFixResponse>>(new Map());
    generatedFixesRef.current = generatedFixes;

    const { addToast } = useToast();
    // Keep a ref so memoised callbacks don't have to re-create when addToast identity changes.
    const addToastRef = useRef(addToast);
    useEffect(() => { addToastRef.current = addToast; }, [addToast]);

    // ---- Analysis mutation ----
    const analyzeMutation = useMutation({
        mutationFn: (text: string) =>
            analyzeContract(text, {
                playbook_id: playbookId || undefined,
                party_side: partySide,
                jurisdiction: jurisdiction || undefined,
            }),
        onMutate: () => {
            setPhase('analyzing');
            setAnalyzeError(null);
        },
        onSuccess: (result) => {
            setAnalysis(result);
            setEditedText(contractText);
            editedTextRef.current = contractText;
            setPhase('results');
            // Initialize fix states
            const states = new Map<string, FixState>();
            for (const risk of result.risks) {
                states.set(risk.id, risk.suggested_fix ? 'generated' : 'idle');
            }
            setFixStates(states);
            // Pre-populate generated fixes from inline suggestions.
            // Preserve whatever `fix_verified` / `fix_warnings` the backend stamped —
            // if the backend did not stamp them, leave them undefined so the UI can
            // honestly display "unverified" rather than silently claiming verified.
            const fixes = new Map<string, GenerateFixResponse>();
            for (const risk of result.risks) {
                if (risk.suggested_fix) {
                    fixes.set(risk.id, {
                        fix_text: risk.suggested_fix,
                        fix_edits: risk.fix_edits,
                        reasoning: risk.fix_reasoning || '',
                        // Only set when backend provided it; cast because GenerateFixResponse
                        // historically required this field but the pipeline-cached path
                        // legitimately may not have verified inline suggestions.
                        fix_verified: risk.fix_verified as boolean,
                        fix_warnings: risk.fix_warnings,
                    });
                }
            }
            setGeneratedFixes(fixes);
        },
        onError: (err: Error) => {
            setAnalyzeError(err.message || 'Analysis failed');
            setPhase('input');
        },
    });

    const startAnalysis = useCallback(() => {
        if (!contractText.trim() || contractText.length < 50) return;
        analyzeMutation.mutate(contractText);
    }, [contractText, analyzeMutation]);

    // ---- Generate fix for a single risk ----
    const generateFixForRisk = useCallback(async (risk: RedlineItem) => {
        setFixStates(prev => new Map(prev).set(risk.id, 'generating'));
        try {
            const result = await apiGenerateFix({
                original_text: risk.clause_text,
                recommendation: risk.recommendation,
                rule_name: risk.rule_name,
                redline_type: risk.redline_type,
                surrounding_context: getSurroundingContext(editedTextRef.current, risk.clause_text),
                playbook_id: playbookId || undefined,
                contract_text: editedTextRef.current,
            });
            setGeneratedFixes(prev => new Map(prev).set(risk.id, result));
            setFixStates(prev => new Map(prev).set(risk.id, 'generated'));
        } catch {
            setFixStates(prev => new Map(prev).set(risk.id, 'error'));
        }
    }, [playbookId]);

    // ---- Apply a fix ----
    const applyFix = useCallback((riskId: string) => {
        const fix = generatedFixes.get(riskId);
        const risk = analysis?.risks.find(r => r.id === riskId);
        if (!fix || !risk) return;

        const currentText = editedTextRef.current;
        let newText: string | null = null;
        let usedEdits: Array<{ find: string; replace: string }> = [];

        // Strategy 1: Try surgical edits if available
        if (fix.fix_edits && fix.fix_edits.length > 0) {
            const result = applyFixEdits(currentText, fix.fix_edits);
            if (result.newText !== currentText) {
                newText = result.newText;
                usedEdits = fix.fix_edits;
            }
        }

        // Strategy 2: Fallback to full clause replacement
        if (!newText && fix.fix_text && risk.redline_type === 'violation') {
            const pos = findClausePosition(currentText, risk.clause_text);
            if (pos) {
                newText = currentText.slice(0, pos.start) + fix.fix_text + currentText.slice(pos.end);
                usedEdits = [{ find: risk.clause_text, replace: fix.fix_text }];
            }
        }

        // Strategy 3: Missing clause — append
        if (!newText && fix.fix_text && risk.redline_type === 'missing') {
            newText = currentText + '\n\n' + fix.fix_text;
            usedEdits = [];
        }

        if (newText) {
            setEditedText(newText);
            editedTextRef.current = newText;
            setAppliedEdits(prev => [...prev, {
                riskId,
                originalText: risk.clause_text,
                fixText: fix.fix_text,
                fixEdits: usedEdits,
            }]);
            setFixStates(prev => new Map(prev).set(riskId, 'applied'));
        }
    }, [generatedFixes, analysis]);

    // ---- Revert a fix ----
    const revertFix = useCallback((riskId: string) => {
        const editIdx = appliedEdits.findIndex(e => e.riskId === riskId);
        if (editIdx === -1) return;

        // Re-apply all edits except this one from the original contract text
        const remaining = appliedEdits.filter(e => e.riskId !== riskId);
        let text = contractText;
        for (const edit of remaining) {
            if (edit.fixEdits.length > 0) {
                const { newText } = applyFixEdits(text, edit.fixEdits);
                text = newText;
            }
        }
        setEditedText(text);
        editedTextRef.current = text;
        setAppliedEdits(remaining);
        setFixStates(prev => new Map(prev).set(riskId, 'generated'));
    }, [appliedEdits, contractText]);

    // ---- Bulk apply ----
    // Strategy: generate any missing fixes first, then plan ALL edits against the
    // ORIGINAL contract text in one pass. Detect overlaps against the source (not
    // the progressively-edited text), apply non-overlapping edits in reverse order,
    // skip overlapping ones. This avoids fix A's replacement cascading into fix B's
    // find window and corrupting the document.
    const applyAllFixes = useCallback(async () => {
        if (!analysis) return;

        // Risks still needing action — read from refs so the loop sees fresh state.
        const risksToFix = analysis.risks.filter(r => fixStatesRef.current.get(r.id) !== 'applied');
        setBulkProgress({ current: 0, total: risksToFix.length });

        // Phase 1: Generate any missing fixes. (Sequential to avoid flooding the AI.)
        for (let i = 0; i < risksToFix.length; i++) {
            const risk = risksToFix[i];
            setBulkProgress({ current: i + 1, total: risksToFix.length });
            if (!generatedFixesRef.current.has(risk.id)) {
                await generateFixForRisk(risk);
            }
        }

        // Phase 2: Plan all edits against the ORIGINAL source (contractText), not the
        // progressively-edited text. This is the single source of truth for position
        // overlap detection.
        type Planned = {
            riskId: string;
            start: number;
            end: number;
            find: string;
            replace: string;
            risk: RedlineItem;
        };
        const planned: Planned[] = [];
        const missingClauseAppends: { risk: RedlineItem; fix: GenerateFixResponse }[] = [];
        const skippedNoMatch: string[] = [];

        const totalAttempted = risksToFix.length;

        for (const risk of risksToFix) {
            const fix = generatedFixesRef.current.get(risk.id);
            if (!fix) {
                skippedNoMatch.push(risk.id);
                continue;
            }

            // Missing-clause fixes are appends — don't need position planning.
            if (risk.redline_type === 'missing') {
                missingClauseAppends.push({ risk, fix });
                continue;
            }

            // Prefer surgical edits. Find each `find` in the ORIGINAL contractText.
            if (fix.fix_edits && fix.fix_edits.length > 0) {
                let allLocated = true;
                const edits: Planned[] = [];
                for (const e of fix.fix_edits) {
                    const idx = contractText.indexOf(e.find);
                    if (idx === -1) {
                        // Try normalized-whitespace fallback via findClausePosition.
                        const pos = findClausePosition(contractText, e.find);
                        if (!pos) { allLocated = false; break; }
                        edits.push({
                            riskId: risk.id, start: pos.start, end: pos.end,
                            find: contractText.slice(pos.start, pos.end), replace: e.replace, risk,
                        });
                    } else {
                        edits.push({
                            riskId: risk.id, start: idx, end: idx + e.find.length,
                            find: e.find, replace: e.replace, risk,
                        });
                    }
                }
                if (allLocated) {
                    planned.push(...edits);
                    continue;
                }
            }

            // Fallback: whole-clause replacement using the original clause_text.
            if (fix.fix_text) {
                const pos = findClausePosition(contractText, risk.clause_text);
                if (pos) {
                    planned.push({
                        riskId: risk.id, start: pos.start, end: pos.end,
                        find: contractText.slice(pos.start, pos.end),
                        replace: fix.fix_text, risk,
                    });
                    continue;
                }
            }

            skippedNoMatch.push(risk.id);
        }

        // Phase 3: Sort by start, detect overlaps, mark skipped risks.
        planned.sort((a, b) => a.start - b.start);
        const kept: Planned[] = [];
        const skippedOverlap = new Set<string>();

        for (let i = 0; i < planned.length; i++) {
            const cur = planned[i];
            // Does this edit overlap with any already-kept edit?
            const overlap = kept.some(k => cur.start < k.end && cur.end > k.start);
            if (overlap) {
                skippedOverlap.add(cur.riskId);
                continue;
            }
            kept.push(cur);
        }

        // Also skip sibling edits from the same risk if one edit of that risk overlapped.
        // (We treat a risk atomically: apply ALL its edits or NONE of them.)
        const keptByRisk = new Map<string, Planned[]>();
        for (const k of kept) {
            if (skippedOverlap.has(k.riskId)) continue;
            const arr = keptByRisk.get(k.riskId) || [];
            arr.push(k);
            keptByRisk.set(k.riskId, arr);
        }
        // Drop any kept edits whose risk had at least one sibling drop.
        const atomicallyKept: Planned[] = [];
        for (const [riskId, edits] of keptByRisk.entries()) {
            if (skippedOverlap.has(riskId)) continue;
            atomicallyKept.push(...edits);
        }

        // Phase 4: Apply kept edits in reverse order on a single string (the ORIGINAL).
        atomicallyKept.sort((a, b) => b.start - a.start);
        let batchedText = contractText;
        const newAppliedEdits: AppliedFix[] = [];
        const appliedRiskIds = new Set<string>();

        for (const p of atomicallyKept) {
            batchedText = batchedText.slice(0, p.start) + p.replace + batchedText.slice(p.end);
            appliedRiskIds.add(p.riskId);
        }

        // Convert kept edits into AppliedFix records (grouped by risk).
        for (const [riskId, edits] of keptByRisk.entries()) {
            if (!appliedRiskIds.has(riskId)) continue;
            const risk = edits[0].risk;
            const fix = generatedFixesRef.current.get(riskId);
            newAppliedEdits.push({
                riskId,
                originalText: risk.clause_text,
                fixText: fix?.fix_text || '',
                fixEdits: edits.map(e => ({ find: e.find, replace: e.replace })),
            });
        }

        // Phase 5: Append missing-clause fixes at the end (order-preserving, no overlap risk).
        for (const { risk, fix } of missingClauseAppends) {
            if (!fix.fix_text) continue;
            batchedText = batchedText + '\n\n' + fix.fix_text;
            appliedRiskIds.add(risk.id);
            newAppliedEdits.push({
                riskId: risk.id,
                originalText: risk.clause_text,
                fixText: fix.fix_text,
                fixEdits: [],
            });
        }

        // Phase 6: Commit the batched result in one setState.
        setEditedText(batchedText);
        editedTextRef.current = batchedText;
        setAppliedEdits(prev => {
            // Drop previous entries for any risk we just re-applied, then append new ones.
            const replaced = prev.filter(e => !appliedRiskIds.has(e.riskId));
            return [...replaced, ...newAppliedEdits];
        });
        setFixStates(prev => {
            const next = new Map(prev);
            for (const id of appliedRiskIds) next.set(id, 'applied');
            return next;
        });

        setBulkProgress(null);

        // Phase 7: Report outcome.
        const appliedCount = appliedRiskIds.size;
        const skippedCount = skippedOverlap.size + skippedNoMatch.length;
        if (skippedCount > 0) {
            addToastRef.current(
                `Applied ${appliedCount} of ${totalAttempted} fixes. ${skippedCount} skipped due to conflicts on the same text — apply those individually.`,
                'warning',
            );
        } else if (appliedCount > 0) {
            addToastRef.current(`Applied ${appliedCount} fixes.`, 'success');
        }
    }, [analysis, contractText, generateFixForRisk]);

    // ---- Filtering ----
    const setFilter = useCallback((partial: Partial<RiskFilter>) => {
        setFilterState(prev => ({ ...prev, ...partial }));
    }, []);

    const filteredRisks = useMemo(() => {
        if (!analysis) return [];
        let risks = [...analysis.risks];

        // Level filter
        if (filter.level !== 'ALL') {
            risks = risks.filter(r => r.risk_level === filter.level);
        }

        // Search
        if (filter.search) {
            const q = filter.search.toLowerCase();
            risks = risks.filter(r =>
                r.rule_name.toLowerCase().includes(q) ||
                r.clause_text.toLowerCase().includes(q) ||
                r.explanation.toLowerCase().includes(q)
            );
        }

        // Sort
        if (filter.sort === 'risk') {
            const order = { RED: 0, YELLOW: 1, GREEN: 2 };
            risks.sort((a, b) => order[a.risk_level] - order[b.risk_level]);
        } else if (filter.sort === 'position') {
            risks.sort((a, b) => (a.paragraph_index ?? 999) - (b.paragraph_index ?? 999));
        } else if (filter.sort === 'type') {
            risks.sort((a, b) => a.clause_type.localeCompare(b.clause_type));
        }

        return risks;
    }, [analysis, filter]);

    // ---- Export ----
    const handleExportReport = useCallback(async () => {
        if (!analysis) return;
        const blob = await exportRedlineReport({
            filename: analysis.filename || 'contract',
            executive_summary: analysis.executive_summary,
            redlines: analysis.risks.map(r => ({
                id: r.id,
                risk_level: r.risk_level,
                rule_name: r.rule_name,
                clause_text: r.clause_text,
                explanation: r.explanation,
                recommendation: r.recommendation,
                suggested_fix: generatedFixes.get(r.id)?.fix_text || r.suggested_fix,
                redline_type: r.redline_type,
                is_deal_breaker: r.is_deal_breaker,
            })),
            risk_summary: analysis.risk_summary,
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${analysis.filename || 'contract'}-risk-report.docx`;
        a.click();
        URL.revokeObjectURL(url);
    }, [analysis, generatedFixes]);

    const handleCopyRedlined = useCallback(() => {
        navigator.clipboard.writeText(editedText);
    }, [editedText]);

    // ---- Reset ----
    const reset = useCallback(() => {
        setContractText('');
        setPhase('input');
        setAnalysis(null);
        setAnalyzeError(null);
        setFixStates(new Map());
        setGeneratedFixes(new Map());
        setEditedText('');
        setAppliedEdits([]);
        setBulkProgress(null);
        setFilterState({ level: 'ALL', search: '', sort: 'risk' });
    }, []);

    return {
        contractText, setContractText,
        playbookId, setPlaybookId,
        partySide, setPartySide,
        jurisdiction, setJurisdiction,
        phase, analysis, analyzeError, startAnalysis,
        fixStates, generatedFixes, generateFixForRisk, applyFix, revertFix, applyAllFixes, bulkProgress,
        editedText, appliedEdits,
        filter, setFilter, filteredRisks,
        handleExportReport, handleCopyRedlined,
        reset,
    };
}

// ---- Helpers ----

function getSurroundingContext(text: string, clauseText: string, windowChars = 500): string {
    const pos = findClausePosition(text, clauseText);
    if (!pos) return '';
    const start = Math.max(0, pos.start - windowChars);
    const end = Math.min(text.length, pos.end + windowChars);
    return text.slice(start, end);
}
