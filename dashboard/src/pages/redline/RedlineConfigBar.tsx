import { useState, type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listPlaybooks, listComplianceLayers } from '@/api/client';
import { Button, SelectInput, TextInput } from '@/components/ui';
import type { TierPreference, ContractSide } from './types';

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

const TIER_PREFERENCES: { value: TierPreference; label: string; hint: string }[] = [
    { value: 'ideal', label: 'Ideal', hint: 'Use the rule\'s primary position' },
    { value: 'acceptable', label: 'Acceptable', hint: 'Use the next-best fallback position' },
    { value: 'walk_away', label: 'Walk-away', hint: 'Use the minimum acceptable position' },
    { value: 'escalate', label: 'Escalate', hint: 'Tier 4 — flag for senior review' },
];

const CONTRACT_SIDES: { value: ContractSide; label: string }[] = [
    { value: '', label: '—' },
    { value: 'vendor', label: 'Vendor (we provide)' },
    { value: 'customer', label: 'Customer (we receive)' },
];

interface Props {
    playbookId: string;
    onPlaybookChange: (id: string) => void;
    partySide: 'buyer' | 'seller' | 'neutral';
    onPartySideChange: (side: 'buyer' | 'seller' | 'neutral') => void;
    jurisdiction: string;
    onJurisdictionChange: (j: string) => void;
    tierPreference: TierPreference;
    onTierPreferenceChange: (t: TierPreference) => void;
    counterpartyType: string;
    onCounterpartyTypeChange: (s: string) => void;
    dealSize: string;
    onDealSizeChange: (s: string) => void;
    contractSide: ContractSide;
    onContractSideChange: (s: ContractSide) => void;
    complianceLayers: string[];
    onComplianceLayersChange: (codes: string[]) => void;
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
    tierPreference, onTierPreferenceChange,
    counterpartyType, onCounterpartyTypeChange,
    dealSize, onDealSizeChange,
    contractSide, onContractSideChange,
    complianceLayers, onComplianceLayersChange,
    charCount, isAnalyzing, canAnalyze, onAnalyze,
}: Props) {
    const { data: playbooks } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });
    const { data: complianceLayerOptions } = useQuery({
        queryKey: ['compliance-layers'],
        queryFn: listComplianceLayers,
        staleTime: 5 * 60 * 1000,
    });
    const [showAdvanced, setShowAdvanced] = useState(false);
    const advancedActive =
        tierPreference !== 'ideal' ||
        !!counterpartyType.trim() ||
        !!dealSize.trim() ||
        !!contractSide ||
        complianceLayers.length > 0;

    const toggleLayer = (code: string) => {
        if (complianceLayers.includes(code)) {
            onComplianceLayersChange(complianceLayers.filter(c => c !== code));
        } else {
            onComplianceLayersChange([...complianceLayers, code]);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
                    variant="ghost"
                    onClick={() => setShowAdvanced(v => !v)}
                    style={{ whiteSpace: 'nowrap', flexShrink: 0, fontSize: 12 }}
                    aria-label="Toggle negotiation tier and deal context controls"
                >
                    {showAdvanced ? 'Hide' : 'Show'} negotiation context{advancedActive ? ' •' : ''}
                </Button>

                <Button
                    variant="primary"
                    onClick={onAnalyze}
                    disabled={!canAnalyze || isAnalyzing}
                    style={{ whiteSpace: 'nowrap', flexShrink: 0 }}
                >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Contract'}
                </Button>
            </div>

            {showAdvanced && (
                <div style={barStyle}>
                    <div style={{ ...fieldStyle, flex: '1 1 160px', minWidth: 150 }}>
                        <span style={labelStyle} title="Which negotiation position the AI should adopt — when a rule has tier-level positions, the chosen tier replaces the default primary position.">
                            Negotiation Tier
                        </span>
                        <SelectInput
                            value={tierPreference}
                            onChange={e => onTierPreferenceChange(e.target.value as TierPreference)}
                        >
                            {TIER_PREFERENCES.map(t => (
                                <option key={t.value} value={t.value} title={t.hint}>{t.label}</option>
                            ))}
                        </SelectInput>
                    </div>

                    <div style={{ ...fieldStyle, flex: '1 1 170px', minWidth: 150 }}>
                        <span style={labelStyle} title="Counterparty classification — fortune_500, startup, government, etc. Used by playbook conditions to apply rule overrides.">
                            Counterparty Type
                        </span>
                        <TextInput
                            value={counterpartyType}
                            onChange={e => onCounterpartyTypeChange(e.target.value)}
                            placeholder="e.g. fortune_500"
                        />
                    </div>

                    <div style={{ ...fieldStyle, flex: '1 1 140px', minWidth: 120 }}>
                        <span style={labelStyle} title="Total deal value in USD. Used by numeric conditions (e.g. 'deal_size > 1M ⇒ downgrade liability cap risk').">
                            Deal Size (USD)
                        </span>
                        <TextInput
                            type="number"
                            value={dealSize}
                            onChange={e => onDealSizeChange(e.target.value)}
                            placeholder="e.g. 250000"
                            min="0"
                        />
                    </div>

                    <div style={{ ...fieldStyle, flex: '1 1 160px', minWidth: 150 }}>
                        <span style={labelStyle} title="Which side of the contract you're on. Drives contract_side conditions.">
                            Contract Side
                        </span>
                        <SelectInput
                            value={contractSide}
                            onChange={e => onContractSideChange(e.target.value as ContractSide)}
                        >
                            {CONTRACT_SIDES.map(c => (
                                <option key={c.value || 'none'} value={c.value}>{c.label}</option>
                            ))}
                        </SelectInput>
                    </div>

                    {complianceLayerOptions && complianceLayerOptions.length > 0 && (
                        <div style={{ flex: '2 1 280px', minWidth: 240, display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <span style={labelStyle} title="Apply jurisdiction-specific compliance overlays (e.g. DPDP) on top of the base playbook.">
                                Compliance Overlays
                            </span>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                {complianceLayerOptions.map(layer => (
                                    <label
                                        key={layer.code}
                                        style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: 6,
                                            fontSize: 12,
                                            padding: '4px 10px',
                                            borderRadius: 9999,
                                            border: complianceLayers.includes(layer.code)
                                                ? '1px solid var(--accent)'
                                                : '1px solid var(--border)',
                                            backgroundColor: complianceLayers.includes(layer.code)
                                                ? 'var(--accent-subtle, #DBEAFE)'
                                                : 'var(--bg-elevated)',
                                            cursor: 'pointer',
                                            userSelect: 'none',
                                        }}
                                        title={`${layer.name} (${layer.rule_count} rule${layer.rule_count === 1 ? '' : 's'})`}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={complianceLayers.includes(layer.code)}
                                            onChange={() => toggleLayer(layer.code)}
                                            style={{ margin: 0 }}
                                        />
                                        {layer.name}
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
