import { useState, type CSSProperties } from 'react';
import type { RedlineItem, GenerateFixResponse } from '@/api/client';
import { Badge, Button, Card } from '@/components/ui';
import { wordDiff } from './textEngine';
import type { FixState } from './types';
import {
    ChevronDown,
    ChevronUp,
    Wand2,
    Check,
    AlertTriangle,
    Undo2,
    Eye,
} from 'lucide-react';

const LEVEL_BADGE: Record<string, 'critical' | 'high' | 'low'> = {
    RED: 'critical',
    YELLOW: 'high',
    GREEN: 'low',
};

const LEVEL_LABEL: Record<string, string> = {
    RED: 'High Risk',
    YELLOW: 'Medium Risk',
    GREEN: 'Low Risk',
};

interface Props {
    risk: RedlineItem;
    fixState: FixState;
    generatedFix?: GenerateFixResponse;
    onGenerateFix: () => void;
    onApplyFix: () => void;
    onRevertFix: () => void;
    onHighlight: () => void;
    isActive: boolean;
    // When true, the AI backend is unavailable — disable fix generation.
    aiDown?: boolean;
}

export function RiskCard({
    risk, fixState, generatedFix,
    onGenerateFix, onApplyFix, onRevertFix, onHighlight,
    isActive, aiDown,
}: Props) {
    const [expanded, setExpanded] = useState(false);

    const cardStyle: CSSProperties = {
        marginBottom: 10,
        border: isActive ? '2px solid var(--accent)' : '1px solid var(--border)',
        transition: 'border var(--transition-fast)',
    };

    const headerStyle: CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        cursor: 'pointer',
        padding: '10px 14px',
        flexWrap: 'wrap',
    };

    const clauseStyle: CSSProperties = {
        fontSize: 13,
        color: 'var(--text-secondary)',
        backgroundColor: 'var(--bg-app)',
        padding: '8px 10px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        maxHeight: 120,
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        lineHeight: 1.5,
        margin: '8px 0',
    };

    const sectionStyle: CSSProperties = {
        fontSize: 13,
        color: 'var(--text-secondary)',
        lineHeight: 1.5,
        marginTop: 8,
    };

    return (
        <Card style={cardStyle}>
            {/* Header */}
            <div style={headerStyle} onClick={() => setExpanded(!expanded)}>
                <Badge variant={LEVEL_BADGE[risk.risk_level] || 'high'}>
                    {LEVEL_LABEL[risk.risk_level] || risk.risk_level}
                </Badge>
                {risk.is_deal_breaker && (
                    <Badge variant="critical" size="sm">Deal Breaker</Badge>
                )}
                {fixState === 'applied' && (
                    <Badge variant="low" size="sm">Applied</Badge>
                )}
                <span style={{
                    flex: 1,
                    fontSize: 13,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    minWidth: 0,
                }}>
                    {formatRuleName(risk.rule_name)}
                </span>
                {risk.clause_type && (
                    <span style={{
                        fontSize: 10,
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        flexShrink: 0,
                    }}>
                        {risk.clause_type}
                    </span>
                )}
                {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>

            {/* Expanded content */}
            {expanded && (
                <div style={{ padding: '0 14px 14px' }}>
                    {/* Clause text */}
                    {risk.redline_type === 'violation' && (
                        <div style={clauseStyle}>
                            {risk.clause_text}
                        </div>
                    )}
                    {risk.redline_type === 'missing' && (
                        <div style={{
                            ...clauseStyle,
                            borderStyle: 'dashed',
                            color: 'var(--text-muted)',
                            fontStyle: 'italic',
                        }}>
                            Missing clause — {risk.clause_type}
                        </div>
                    )}

                    {/* Explanation */}
                    <div style={sectionStyle}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Why it matters: </span>
                        {risk.explanation}
                    </div>

                    {/* Recommendation */}
                    {risk.recommendation && (
                        <div style={sectionStyle}>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Recommendation: </span>
                            {risk.recommendation}
                        </div>
                    )}

                    {/* Confidence */}
                    {risk.confidence_level && (
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                            Confidence: {risk.confidence_level}
                            {risk.confidence != null && ` (${Math.round(risk.confidence * 100)}%)`}
                        </div>
                    )}

                    {/* Fix section */}
                    <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {fixState === 'idle' && (
                            <Button
                                variant="secondary"
                                onClick={onGenerateFix}
                                disabled={aiDown}
                                title={aiDown ? 'AI analysis is unavailable — fix generation is disabled.' : undefined}
                            >
                                <Wand2 size={14} style={{ marginRight: 4 }} />
                                Generate Fix
                            </Button>
                        )}

                        {fixState === 'generating' && (
                            <Button variant="secondary" disabled>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{
                                        width: 12, height: 12,
                                        border: '2px solid var(--border)',
                                        borderTopColor: 'var(--accent)',
                                        borderRadius: '50%',
                                        animation: 'spin 0.7s linear infinite',
                                    }} />
                                    Generating...
                                </span>
                            </Button>
                        )}

                        {fixState === 'error' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <AlertTriangle size={14} style={{ color: 'var(--risk-critical)' }} />
                                <span style={{ fontSize: 13, color: 'var(--risk-critical)' }}>Fix generation failed</span>
                                <Button
                                    variant="ghost"
                                    onClick={onGenerateFix}
                                    disabled={aiDown}
                                    title={aiDown ? 'AI analysis is unavailable — retry is disabled.' : undefined}
                                >
                                    Retry
                                </Button>
                            </div>
                        )}

                        {(fixState === 'generated' || fixState === 'applied') && generatedFix && (
                            <>
                                {/* Word-level diff preview */}
                                <DiffPreview
                                    original={risk.clause_text}
                                    fixText={generatedFix.fix_text}
                                    redlineType={risk.redline_type}
                                />

                                {/* Reasoning */}
                                {generatedFix.reasoning && (
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                        {generatedFix.reasoning}
                                    </div>
                                )}

                                {/* Unverified fix warning — AI "find" text may not exist in source */}
                                {generatedFix.fix_verified === false && (
                                    <div style={{
                                        fontSize: 12,
                                        color: 'var(--risk-high)',
                                        backgroundColor: 'var(--risk-high-bg)',
                                        border: '1px solid var(--risk-high-border)',
                                        borderRadius: 'var(--radius-sm)',
                                        padding: '8px 10px',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: 4,
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontWeight: 600 }}>
                                            <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 2 }} />
                                            <span>Unverified — AI's "find" text may not exist in the source. Review before applying.</span>
                                        </div>
                                        {generatedFix.fix_warnings && generatedFix.fix_warnings.length > 0 && (
                                            <ul style={{ margin: '4px 0 0 18px', padding: 0, lineHeight: 1.5 }}>
                                                {generatedFix.fix_warnings.map((w, i) => (
                                                    <li key={i}>{w}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}

                                {/* Non-blocking warnings when fix is verified but has soft warnings */}
                                {generatedFix.fix_verified !== false && generatedFix.fix_warnings && generatedFix.fix_warnings.length > 0 && (
                                    <div style={{ fontSize: 12, color: 'var(--risk-high)', display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                                        <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 2 }} />
                                        <span>{generatedFix.fix_warnings.join('. ')}</span>
                                    </div>
                                )}

                                {/* Action buttons */}
                                <div style={{ display: 'flex', gap: 8 }}>
                                    {fixState === 'generated' && (
                                        <Button variant="primary" onClick={onApplyFix}>
                                            <Check size={14} style={{ marginRight: 4 }} />
                                            Apply Fix
                                        </Button>
                                    )}
                                    {fixState === 'applied' && (
                                        <Button variant="ghost" onClick={onRevertFix}>
                                            <Undo2 size={14} style={{ marginRight: 4 }} />
                                            Revert
                                        </Button>
                                    )}
                                    <Button variant="ghost" onClick={onHighlight}>
                                        <Eye size={14} style={{ marginRight: 4 }} />
                                        Show in Text
                                    </Button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </Card>
    );
}

// ---- Diff Preview Sub-component ----

function DiffPreview({ original, fixText, redlineType }: {
    original: string;
    fixText: string;
    redlineType: 'violation' | 'missing';
}) {
    const containerStyle: CSSProperties = {
        fontSize: 13,
        lineHeight: 1.6,
        padding: '10px 12px',
        backgroundColor: 'var(--bg-app)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        maxHeight: 200,
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
    };

    if (redlineType === 'missing') {
        return (
            <div style={containerStyle}>
                <ins style={{
                    color: 'var(--risk-low)',
                    backgroundColor: 'rgba(34,197,94,0.1)',
                    textDecoration: 'none',
                }}>
                    {fixText}
                </ins>
            </div>
        );
    }

    const tokens = wordDiff(original, fixText);

    return (
        <div style={containerStyle}>
            {tokens.map((token, i) => {
                if (token.type === 'equal') {
                    return <span key={i}>{token.text}</span>;
                }
                if (token.type === 'delete') {
                    return (
                        <del key={i} style={{
                            color: 'var(--risk-critical)',
                            textDecoration: 'line-through',
                            backgroundColor: 'rgba(239,68,68,0.08)',
                        }}>
                            {token.text}
                        </del>
                    );
                }
                return (
                    <ins key={i} style={{
                        color: 'var(--risk-low)',
                        backgroundColor: 'rgba(34,197,94,0.1)',
                        textDecoration: 'none',
                    }}>
                        {token.text}
                    </ins>
                );
            })}
        </div>
    );
}

// ---- Helpers ----

function formatRuleName(name: string): string {
    return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}
