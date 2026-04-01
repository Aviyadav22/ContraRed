export interface DraftingFormData {
    contract_type: string;
    drafting_perspective: string;
    risk_appetite: string;
    jurisdiction: string;
    party_1_name: string;
    party_1_entity_type: string;
    party_1_jurisdiction: string;
    party_1_address: string;
    party_2_name: string;
    party_2_entity_type: string;
    party_2_jurisdiction: string;
    party_2_address: string;
    term_months: number;
    governing_law: string;
    dispute_resolution: string;
    venue: string;
    effective_date: string;
    // NDA
    nda_purpose: string;
    nda_survival_years: number;
    nda_ci_categories: string;
    nda_non_solicitation: boolean;
    nda_non_solicitation_months: number;
    nda_marking_requirement: boolean;
    // SaaS
    saas_service_description: string;
    saas_pricing_model: string;
    saas_price_amount: number;
    saas_billing_frequency: string;
    saas_auto_renewal: boolean;
    saas_uptime: number;
    saas_liability_cap_months: number;
    saas_authorized_users: number;
    saas_compliance_frameworks: string[];
}

export const DEFAULT_FORM: DraftingFormData = {
    contract_type: '',
    drafting_perspective: 'balanced',
    risk_appetite: 'balanced',
    jurisdiction: 'US-DE',
    party_1_name: '',
    party_1_entity_type: 'Inc.',
    party_1_jurisdiction: 'US-DE',
    party_1_address: '',
    party_2_name: '',
    party_2_entity_type: 'LLC',
    party_2_jurisdiction: 'US-DE',
    party_2_address: '',
    term_months: 24,
    governing_law: '',
    dispute_resolution: 'arbitration',
    venue: '',
    effective_date: '',
    nda_purpose: '',
    nda_survival_years: 3,
    nda_ci_categories: '',
    nda_non_solicitation: false,
    nda_non_solicitation_months: 12,
    nda_marking_requirement: false,
    saas_service_description: '',
    saas_pricing_model: 'per_user_monthly',
    saas_price_amount: 0,
    saas_billing_frequency: 'monthly',
    saas_auto_renewal: true,
    saas_uptime: 99.9,
    saas_liability_cap_months: 12,
    saas_authorized_users: 10,
    saas_compliance_frameworks: [],
};

export const STEPS = ['Contract Type', 'Details', 'Review', 'Generating', 'Results'];

export const CONTRACT_TYPES = [
    { value: 'nda_mutual', label: 'NDA — Mutual', desc: 'Both parties share and protect confidential information equally.' },
    { value: 'nda_unilateral', label: 'NDA — Unilateral', desc: 'One party discloses confidential information to the other.' },
    { value: 'saas', label: 'SaaS Agreement', desc: 'Software-as-a-Service subscription with MSA, SLA, DPA, and Order Form.' },
];

export const PERSPECTIVES = [
    { value: 'party_1', label: 'Party 1 (Drafting Party)' },
    { value: 'party_2', label: 'Party 2 (Counterparty)' },
    { value: 'balanced', label: 'Balanced (Neutral)' },
];

export const RISK_APPETITES = [
    { value: 'protective', label: 'Protective', desc: 'Maximum protection for your client' },
    { value: 'balanced', label: 'Balanced', desc: 'Fair to both sides' },
    { value: 'commercial', label: 'Commercial', desc: 'Business-friendly and lean' },
];
