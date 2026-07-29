import type { RedlineItem, GenerateFixResponse } from '@/api/client';

export type PagePhase = 'input' | 'analyzing' | 'results';

export type FixState = 'idle' | 'generating' | 'generated' | 'applied' | 'error';

export type RiskLevelFilter = 'ALL' | 'RED' | 'YELLOW' | 'GREEN';

export type SortMode = 'risk' | 'position' | 'type';

export interface RiskFilter {
    level: RiskLevelFilter;
    search: string;
    sort: SortMode;
}

export interface AppliedFix {
    riskId: string;
    originalText: string;
    fixText: string;
    fixEdits: Array<{ find: string; replace: string }>;
}

export interface TextEdit {
    start: number;
    end: number;
    originalText: string;
    replacementText: string;
    riskId: string;
}

export type TierPreference = 'ideal' | 'acceptable' | 'walk_away' | 'escalate';
export type ContractSide = '' | 'vendor' | 'customer';
export type PartySide = '' | 'buyer' | 'seller' | 'neutral';

export interface UseRedlineReturn {
    // Input state
    contractText: string;
    setContractText: (text: string) => void;
    playbookId: string;
    setPlaybookId: (id: string) => void;
    partySide: PartySide;
    setPartySide: (side: PartySide) => void;
    jurisdiction: string;
    setJurisdiction: (j: string) => void;
    // Phase 6 (negotiation tiers + conditional logic)
    tierPreference: TierPreference;
    setTierPreference: (t: TierPreference) => void;
    counterpartyType: string;
    setCounterpartyType: (s: string) => void;
    dealSize: string;  // raw input; coerced to number when sent
    setDealSize: (s: string) => void;
    contractSide: ContractSide;
    setContractSide: (s: ContractSide) => void;
    // Compliance layer overlays (e.g. DPDP)
    complianceLayers: string[];
    setComplianceLayers: (codes: string[]) => void;

    // Analysis
    phase: PagePhase;
    analysis: import('@/api/client').AnalysisResult | null;
    analyzeError: string | null;
    startAnalysis: () => void;

    // Fixes
    fixStates: Map<string, FixState>;
    generatedFixes: Map<string, GenerateFixResponse>;
    generateFixForRisk: (risk: RedlineItem) => Promise<void>;
    applyFix: (riskId: string) => void;
    revertFix: (riskId: string) => void;
    applyAllFixes: () => Promise<void>;
    bulkProgress: { current: number; total: number } | null;

    // Edited text
    editedText: string;
    appliedEdits: AppliedFix[];

    // Filtering
    filter: RiskFilter;
    setFilter: (f: Partial<RiskFilter>) => void;
    filteredRisks: RedlineItem[];

    // Export
    handleExportReport: () => Promise<void>;
    handleCopyRedlined: () => void;

    // Reset
    reset: () => void;
}
