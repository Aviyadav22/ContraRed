import { useState, useCallback, useMemo, useRef } from 'react';
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
            // Pre-populate generated fixes from inline suggestions
            const fixes = new Map<string, GenerateFixResponse>();
            for (const risk of result.risks) {
                if (risk.suggested_fix) {
                    fixes.set(risk.id, {
                        fix_text: risk.suggested_fix,
                        fix_edits: risk.fix_edits,
                        reasoning: risk.fix_reasoning || '',
                        fix_verified: true,
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
    const applyAllFixes = useCallback(async () => {
        if (!analysis) return;
        const risksToFix = analysis.risks.filter(r => {
            const state = fixStates.get(r.id);
            return state !== 'applied';
        });
        setBulkProgress({ current: 0, total: risksToFix.length });

        for (let i = 0; i < risksToFix.length; i++) {
            const risk = risksToFix[i];
            setBulkProgress({ current: i + 1, total: risksToFix.length });

            // Generate fix if needed
            if (!generatedFixes.has(risk.id)) {
                await generateFixForRisk(risk);
            }

            // Apply if generated
            const state = fixStates.get(risk.id);
            if (state === 'generated' || generatedFixes.has(risk.id)) {
                applyFix(risk.id);
            }
        }
        setBulkProgress(null);
    }, [analysis, fixStates, generatedFixes, generateFixForRisk, applyFix]);

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
