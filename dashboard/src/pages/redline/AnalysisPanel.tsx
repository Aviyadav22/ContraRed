import { useState, type CSSProperties } from 'react';
import type { AnalysisResult, RedlineItem, GenerateFixResponse } from '@/api/client';
import { Badge, TextInput, SelectInput } from '@/components/ui';
import { RiskCard } from './RiskCard';
import { BulkActions } from './BulkActions';
import type { RiskFilter, FixState, RiskLevelFilter, SortMode } from './types';
import { ChevronDown, ChevronUp, Shield } from 'lucide-react';

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

    return (
        <div style={panelStyle}>
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
                    />
                ))}
            </div>
        </div>
    );
}
