import type { CSSProperties } from 'react';
import { Button } from '@/components/ui';
import { Download, Copy, RotateCcw, Zap } from 'lucide-react';

interface Props {
    onApplyAll: () => void;
    onExportReport: () => void;
    onCopyRedlined: () => void;
    onReset: () => void;
    bulkProgress: { current: number; total: number } | null;
    hasAnalysis: boolean;
    appliedCount: number;
    totalRisks: number;
}

const barStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 10px',
    backgroundColor: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
};

export function BulkActions({
    onApplyAll, onExportReport, onCopyRedlined, onReset,
    bulkProgress, hasAnalysis, appliedCount, totalRisks,
}: Props) {
    if (!hasAnalysis) return null;

    return (
        <div style={barStyle}>
            <Button
                variant="primary"
                onClick={onApplyAll}
                disabled={!!bulkProgress || appliedCount === totalRisks}
                style={{ fontSize: 12, padding: '5px 10px' }}
            >
                <Zap size={13} style={{ marginRight: 3 }} />
                {bulkProgress
                    ? `${bulkProgress.current}/${bulkProgress.total}...`
                    : 'Apply All'
                }
            </Button>

            {appliedCount > 0 && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)', padding: '0 2px' }}>
                    {appliedCount}/{totalRisks}
                </span>
            )}

            <div style={{ flex: 1 }} />

            <Button variant="ghost" onClick={onExportReport} style={{ fontSize: 12, padding: '5px 8px' }}>
                <Download size={13} style={{ marginRight: 3 }} />
                Export
            </Button>

            <Button variant="ghost" onClick={onCopyRedlined} style={{ fontSize: 12, padding: '5px 8px' }}>
                <Copy size={13} style={{ marginRight: 3 }} />
                Copy
            </Button>

            <Button variant="ghost" onClick={onReset} style={{ fontSize: 12, padding: '5px 8px' }}>
                <RotateCcw size={13} style={{ marginRight: 3 }} />
                Reset
            </Button>
        </div>
    );
}
