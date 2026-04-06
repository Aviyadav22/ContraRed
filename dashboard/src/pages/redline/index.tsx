import { useState, type CSSProperties } from 'react';
import { AppLayout } from '@/components/layout';
import { useRedline } from './useRedline';
import { RedlineConfigBar } from './RedlineConfigBar';
import { ContractEditor } from './ContractEditor';
import { AnalysisPanel } from './AnalysisPanel';
import { Scissors } from 'lucide-react';

const pageStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
};

const twoColStyle: CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr 440px',
    gap: 20,
    alignItems: 'start',
};

/* The editor column sticks to the top of the viewport while the user
   scrolls through risk cards on the right.  The topbar is 48px and the
   AppLayout inner wrapper adds 32px top-padding, so we offset by 80px
   (48 topbar + 32 padding).  Height is viewport minus that offset minus
   a small bottom margin. */
const editorStickyStyle: CSSProperties = {
    position: 'sticky',
    top: -32,           // pulls up to cancel the 32px padding so it pins right under the topbar
    height: 'calc(100vh - 56px)', // 48px topbar + 8px breathing room
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
};

const analyzingStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 14,
    padding: '80px 20px',
    color: 'var(--text-secondary)',
};

export default function RedlinePage() {
    const rl = useRedline();
    const [activeRiskId, setActiveRiskId] = useState<string | undefined>();

    const canAnalyze = rl.contractText.trim().length >= 50;

    return (
        <AppLayout>
            <div style={pageStyle}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Scissors size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                    <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                        AI Redlining
                    </h1>
                    {rl.phase === 'results' && rl.analysis && rl.analysis.tokens_used > 0 && (
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                            {rl.analysis.tokens_used.toLocaleString()} tokens
                        </span>
                    )}
                </div>

                {/* Config bar */}
                <RedlineConfigBar
                    playbookId={rl.playbookId}
                    onPlaybookChange={rl.setPlaybookId}
                    partySide={rl.partySide}
                    onPartySideChange={rl.setPartySide}
                    jurisdiction={rl.jurisdiction}
                    onJurisdictionChange={rl.setJurisdiction}
                    charCount={rl.contractText.length}
                    isAnalyzing={rl.phase === 'analyzing'}
                    canAnalyze={canAnalyze}
                    onAnalyze={rl.startAnalysis}
                />

                {/* Error */}
                {rl.analyzeError && (
                    <div style={{
                        padding: '10px 14px',
                        backgroundColor: 'rgba(239,68,68,0.08)',
                        border: '1px solid rgba(239,68,68,0.25)',
                        borderRadius: 'var(--radius-md)',
                        color: '#F87171',
                        fontSize: 13,
                    }}>
                        {rl.analyzeError}
                    </div>
                )}

                {/* Analyzing spinner */}
                {rl.phase === 'analyzing' && (
                    <div style={analyzingStyle}>
                        <div style={{
                            width: 36, height: 36,
                            border: '3px solid var(--border)',
                            borderTopColor: 'var(--accent)',
                            borderRadius: '50%',
                            animation: 'spin 0.7s linear infinite',
                        }} />
                        <div style={{ fontSize: 15, fontWeight: 500 }}>Analyzing contract...</div>
                        <div style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 420, textAlign: 'center' }}>
                            6-stage pipeline: extraction, classification, risk assessment, verification, enrichment, fix generation
                        </div>
                    </div>
                )}

                {/* Input mode — full width editor */}
                {rl.phase === 'input' && (
                    <div style={{ minHeight: 400 }}>
                        <ContractEditor
                            contractText={rl.contractText}
                            onTextChange={rl.setContractText}
                            editedText={rl.editedText}
                            phase={rl.phase}
                            risks={[]}
                            appliedEdits={[]}
                        />
                    </div>
                )}

                {/* Results mode — editor sticks, risk cards scroll with page */}
                {rl.phase === 'results' && rl.analysis && (
                    <div style={twoColStyle}>
                        {/* Left: Sticky editor — always visible */}
                        <div style={editorStickyStyle}>
                            <ContractEditor
                                contractText={rl.contractText}
                                onTextChange={rl.setContractText}
                                editedText={rl.editedText}
                                phase={rl.phase}
                                risks={rl.analysis.risks}
                                appliedEdits={rl.appliedEdits}
                                activeRiskId={activeRiskId}
                                onActiveRiskChange={setActiveRiskId}
                            />
                        </div>

                        {/* Right: Analysis panel — scrolls with page */}
                        <div>
                            <AnalysisPanel
                                analysis={rl.analysis}
                                filteredRisks={rl.filteredRisks}
                                filter={rl.filter}
                                onFilterChange={rl.setFilter}
                                fixStates={rl.fixStates}
                                generatedFixes={rl.generatedFixes}
                                onGenerateFix={rl.generateFixForRisk}
                                onApplyFix={rl.applyFix}
                                onRevertFix={rl.revertFix}
                                onHighlightRisk={setActiveRiskId}
                                activeRiskId={activeRiskId}
                                onApplyAll={rl.applyAllFixes}
                                onExportReport={rl.handleExportReport}
                                onCopyRedlined={rl.handleCopyRedlined}
                                onReset={rl.reset}
                                bulkProgress={rl.bulkProgress}
                            />
                        </div>
                    </div>
                )}
            </div>
        </AppLayout>
    );
}
