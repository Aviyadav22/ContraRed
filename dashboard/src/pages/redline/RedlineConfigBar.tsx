import type { CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listPlaybooks } from '@/api/client';
import { Button, SelectInput } from '@/components/ui';

const JURISDICTIONS = [
    { value: '', label: 'Auto-detect' },
    { value: 'IN', label: 'India' },
    { value: 'US', label: 'United States' },
    { value: 'UK', label: 'United Kingdom' },
    { value: 'CA-US', label: 'California (US)' },
    { value: 'DE', label: 'Germany' },
    { value: 'SG', label: 'Singapore' },
    { value: 'AE', label: 'UAE' },
    { value: 'AU', label: 'Australia' },
];

const PARTY_SIDES = [
    { value: 'buyer', label: 'Buyer / Client' },
    { value: 'seller', label: 'Seller / Vendor' },
    { value: 'neutral', label: 'Neutral' },
];

interface Props {
    playbookId: string;
    onPlaybookChange: (id: string) => void;
    partySide: 'buyer' | 'seller' | 'neutral';
    onPartySideChange: (side: 'buyer' | 'seller' | 'neutral') => void;
    jurisdiction: string;
    onJurisdictionChange: (j: string) => void;
    charCount: number;
    isAnalyzing: boolean;
    canAnalyze: boolean;
    onAnalyze: () => void;
}

const barStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'flex-end',
    flexWrap: 'wrap',
    gap: 14,
    padding: '12px 16px',
    backgroundColor: 'var(--bg-surface)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)',
};

const fieldStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    flex: '1 1 180px',
    minWidth: 140,
};

const labelStyle: CSSProperties = {
    fontSize: 10,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
};

export function RedlineConfigBar({
    playbookId, onPlaybookChange,
    partySide, onPartySideChange,
    jurisdiction, onJurisdictionChange,
    charCount, isAnalyzing, canAnalyze, onAnalyze,
}: Props) {
    const { data: playbooks } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    return (
        <div style={barStyle}>
            <div style={fieldStyle}>
                <span style={labelStyle}>Playbook</span>
                <SelectInput
                    value={playbookId}
                    onChange={e => onPlaybookChange(e.target.value)}
                >
                    <option value="">Default</option>
                    {playbooks?.map(pb => (
                        <option key={pb.id} value={pb.id}>{pb.name}</option>
                    ))}
                </SelectInput>
            </div>

            <div style={{ ...fieldStyle, flex: '1 1 140px', minWidth: 130 }}>
                <span style={labelStyle}>Party Side</span>
                <SelectInput
                    value={partySide}
                    onChange={e => onPartySideChange(e.target.value as 'buyer' | 'seller' | 'neutral')}
                >
                    {PARTY_SIDES.map(ps => (
                        <option key={ps.value} value={ps.value}>{ps.label}</option>
                    ))}
                </SelectInput>
            </div>

            <div style={{ ...fieldStyle, flex: '1 1 130px', minWidth: 120 }}>
                <span style={labelStyle}>Jurisdiction</span>
                <SelectInput
                    value={jurisdiction}
                    onChange={e => onJurisdictionChange(e.target.value)}
                >
                    {JURISDICTIONS.map(j => (
                        <option key={j.value} value={j.value}>{j.label}</option>
                    ))}
                </SelectInput>
            </div>

            {charCount > 0 && (
                <span style={{
                    fontSize: 11,
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    paddingBottom: 6,
                }}>
                    {charCount.toLocaleString()} chars
                </span>
            )}

            <Button
                variant="primary"
                onClick={onAnalyze}
                disabled={!canAnalyze || isAnalyzing}
                style={{ whiteSpace: 'nowrap', flexShrink: 0 }}
            >
                {isAnalyzing ? 'Analyzing...' : 'Analyze Contract'}
            </Button>
        </div>
    );
}
