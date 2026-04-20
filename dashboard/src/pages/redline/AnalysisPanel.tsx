import { useState, type CSSProperties } from 'react';
import type { AnalysisResult, RedlineItem, GenerateFixResponse } from '@/api/client';
import { Badge, TextInput, SelectInput } from '@/components/ui';
import { RiskCard } from './RiskCard';
import { BulkActions } from './BulkActions';
import type { RiskFilter, FixState, RiskLevelFilter, SortMode } from './types';
import { AlertTriangle, ChevronDown, ChevronUp, Shield } from 'lucide-react';

const bannerStyle: CSSProperties = {
    backgroundColor: 'var(--risk-high-bg)',
    border: '1px solid var(--risk-high-border)',
    color: 'var(--risk-high)',
    padding: 12,
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    lineHeight: 1.5,
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
};

interface Props {
    analysis: AnalysisResult;
    filteredRisks: RedlineItem[];
    filter: RiskFilter;
    onFilterChange: (partial: Partial<RiskFilter>) => void;
    fixStates: Map<string, FixState>;
    generatedFixes: Map<string, GenerateFixResponse>;
    onGenerateFix: (risk: RedlineItem) => void;
    onApplyFix: (riskId: string) => void;
    onRevertFix: (riskId: string) => void;
    onHighlightRisk: (riskId: string) => void;
    activeRiskId?: string;
    onApplyAll: () => void;
    onExportReport: () => void;
    onCopyRedlined: () => void;
    onReset: () => void;
    bulkProgress: { current: number; total: number } | null;
}

const panelStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
};

const summaryStyle: CSSProperties = {
    padding: '14px 16px',
    backgroundColor: 'var(--bg-surface)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
};

const riskCountStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    borderRadius: 'var(--radius-sm)',
    fontSize: 12,
    fontWeight: 600,
    lineHeight: 1,
};

export function AnalysisPanel({
    analysis, filteredRisks, filter, onFilterChange,
    fixStates, generatedFixes, onGenerateFix, onApplyFix, onRevertFix, onHighlightRisk,
    activeRiskId,
    onApplyAll, onExportReport, onCopyRedlined, onReset,
    bulkProgress,
}: Props) {
    const [summaryExpanded, setSummaryExpanded] = useState(false);
    const appliedCount = Array.from(fixStates.values()).filter(s => s === 'applied').length;

    // AI-first philosophy: when the backend could not use AI, the user must
    // see this clearly — not be left to guess why the findings look thin.
    const aiDown = analysis.ai_used === false;
    // Partial pipeline: AI ran but some stages failed/timed out.
    const partialIncompleteNoFindings = analysis.pipeline_partial && analysis.total_risks === 0 && !aiDown;
    const partialWithFindings = analysis.pipeline_partial && analysis.total_risks > 0 && !aiDown;

    return (
        <div style={panelStyle}>
            {/* AI-down banner — highest priority, takes over if AI is offline */}
            {aiDown && (
                <div style={bannerStyle} role="alert">
                    <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                    <div>
                        <div style={{ fontWeight: 700, marginBottom: 2 }}>
                            AI analysis unavailable — showing rule-engine findings only.
                        </div>
                        <div>
                            Risk explanations and automatic fixes may be limited. Please retry.
                        </div>
                    </div>
                </div>
            )}

            {/* Partial pipeline with zero findings — equally loud, same style */}
            {partialIncompleteNoFindings && (
                <div style={bannerStyle} role="alert">
                    <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                    <div style={{ fontWeight: 700 }}>
                        Analysis incomplete — no findings to report. Please retry.
                    </div>
                </div>
            )}

            {/* Partial pipeline with findings — quieter warning so the user knows results may be thin */}
            {partialWithFindings && (
                <div style={{
                    ...bannerStyle,
                    fontWeight: 500,
                    fontSize: 12,
                }}>
                    <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>Some analysis stages did not complete. Results may be incomplete.</span>
                </div>
            )}

            {/* Risk Summary Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                flexWrap: 'wrap',
            }}>
                <Shield size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {analysis.total_risks} Risk{analysis.total_risks !== 1 ? 's' : ''} Found
                </span>
                <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', flexShrink: 0 }}>
                    <span style={{
                        ...riskCountStyle,
                        backgroundColor: 'rgba(239,68,68,0.12)',
                        color: '#F87171',
                    }}>
                        {analysis.risk_summary.red} Red
                    </span>
                    <span style={{
                        ...riskCountStyle,
                        backgroundColor: 'rgba(245,158,11,0.12)',
                        color: '#FBBF24',
                    }}>
                        {analysis.risk_summary.yellow} Yellow
                    </span>
                    <span style={{
                        ...riskCountStyle,
                        backgroundColor: 'rgba(34,197,94,0.12)',
                        color: '#4ADE80',
                    }}>
                        {analysis.risk_summary.green} Green
                    </span>
                </div>
            </div>

            {/* Executive Summary — collapsed by default */}
            {analysis.executive_summary.length > 0 && (
                <div style={summaryStyle}>
                    <div
                        style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: 8 }}
                        onClick={() => setSummaryExpanded(!summaryExpanded)}
                    >
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                            Executive Summary
                        </span>
                        {analysis.jurisdiction_name && (
                            <Badge variant="neutral" size="sm">{analysis.jurisdiction_name}</Badge>
                        )}
                        {analysis.pipeline_partial && (
                            <Badge variant="high" size="sm">Partial</Badge>
                        )}
                        <div style={{ flex: 1 }} />
                        {summaryExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>
                    {summaryExpanded && (
                        <ul style={{
                            margin: '10px 0 0',
                            paddingLeft: 18,
                            fontSize: 13,
                            color: 'var(--text-secondary)',
                            lineHeight: 1.7,
                        }}>
                            {analysis.executive_summary.map((point, i) => (
                                <li key={i} style={{ marginBottom: 6 }}>{point}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

            {/* Bulk Actions */}
            <BulkActions
                onApplyAll={onApplyAll}
                onExportReport={onExportReport}
                onCopyRedlined={onCopyRedlined}
                onReset={onReset}
                bulkProgress={bulkProgress}
                hasAnalysis
                appliedCount={appliedCount}
                totalRisks={analysis.total_risks}
            />

            {/* Filter Bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <SelectInput
                    value={filter.level}
                    onChange={e => onFilterChange({ level: e.target.value as RiskLevelFilter })}
                    style={{ width: 115, flexShrink: 0 }}
                >
                    <option value="ALL">All Levels</option>
                    <option value="RED">Red</option>
                    <option value="YELLOW">Yellow</option>
                    <option value="GREEN">Green</option>
                </SelectInput>

                <TextInput
                    placeholder="Search..."
                    value={filter.search}
                    onChange={e => onFilterChange({ search: e.target.value })}
                    style={{ flex: 1, minWidth: 80 }}
                />

                <SelectInput
                    value={filter.sort}
                    onChange={e => onFilterChange({ sort: e.target.value as SortMode })}
                    style={{ width: 120, flexShrink: 0 }}
                >
                    <option value="risk">By Risk</option>
                    <option value="position">By Position</option>
                    <option value="type">By Type</option>
                </SelectInput>
            </div>

            {/* Risk Cards — flow naturally, no scroll container */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {filteredRisks.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        padding: 32,
                        color: 'var(--text-muted)',
                        fontSize: 13,
                    }}>
                        {filter.level !== 'ALL' || filter.search
                            ? 'No risks match your filters.'
                            : 'No risks detected.'}
                    </div>
                )}
                {filteredRisks.map(risk => (
                    <RiskCard
                        key={risk.id}
                        risk={risk}
                        fixState={fixStates.get(risk.id) || 'idle'}
                        generatedFix={generatedFixes.get(risk.id)}
                        onGenerateFix={() => onGenerateFix(risk)}
                        onApplyFix={() => onApplyFix(risk.id)}
                        onRevertFix={() => onRevertFix(risk.id)}
                        onHighlight={() => onHighlightRisk(risk.id)}
                        isActive={activeRiskId === risk.id}
                        aiDown={aiDown}
                    />
                ))}
            </div>
        </div>
    );
}
