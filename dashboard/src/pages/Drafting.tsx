import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import {
    getDraftingIntakeSchema,
    generateContract,
    downloadDraft,
    listDraftingPlaybooks,
    type IntakeSchema,
    type IntakeSchemaStage,
    type IntakeSchemaField,
    type GenerateRequest,
    type GenerateResponse,
    type DraftingPlaybookSummary,
} from '@/api/client';

const STEPS = ['Contract Type', 'Details', 'Review', 'Generating', 'Results'];

const CONTRACT_TYPES = [
    { value: 'nda_mutual', label: 'NDA — Mutual', desc: 'Both parties share and protect confidential information equally.' },
    { value: 'nda_unilateral', label: 'NDA — Unilateral', desc: 'One party discloses confidential information to the other.' },
    { value: 'saas', label: 'SaaS Agreement', desc: 'Software-as-a-Service subscription with MSA, SLA, DPA, and Order Form.' },
];

const PERSPECTIVES = [
    { value: 'party_1', label: 'Party 1 (Drafting Party)' },
    { value: 'party_2', label: 'Party 2 (Counterparty)' },
    { value: 'balanced', label: 'Balanced (Neutral)' },
];

const RISK_APPETITES = [
    { value: 'protective', label: 'Protective', desc: 'Maximum protection for your client' },
    { value: 'balanced', label: 'Balanced', desc: 'Fair to both sides' },
    { value: 'commercial', label: 'Commercial', desc: 'Business-friendly and lean' },
];

interface FormData {
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

const DEFAULT_FORM: FormData = {
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

export default function Drafting() {
    const [step, setStep] = useState(0);
    const [form, setForm] = useState<FormData>({ ...DEFAULT_FORM });
    const [result, setResult] = useState<GenerateResponse | null>(null);
    const [error, setError] = useState('');

    const set = (key: keyof FormData, value: unknown) => setForm(prev => ({ ...prev, [key]: value }));

    const generateMutation = useMutation({
        mutationFn: generateContract,
        onSuccess: (data) => {
            setResult(data);
            setStep(4);
        },
        onError: (err: Error) => {
            setError(err.message || 'Generation failed');
            setStep(2); // go back to review
        },
    });

    const buildRequest = (): GenerateRequest => {
        const req: GenerateRequest = {
            contract_type: form.contract_type,
            drafting_perspective: form.drafting_perspective,
            risk_appetite: form.risk_appetite,
            jurisdiction: form.jurisdiction,
            party_1: { name: form.party_1_name, entity_type: form.party_1_entity_type, jurisdiction: form.party_1_jurisdiction, address: form.party_1_address },
            party_2: { name: form.party_2_name, entity_type: form.party_2_entity_type, jurisdiction: form.party_2_jurisdiction, address: form.party_2_address },
            term_months: form.term_months,
            governing_law: form.governing_law,
            dispute_resolution: form.dispute_resolution,
            venue: form.venue || undefined,
            effective_date: form.effective_date || undefined,
        };
        if (form.contract_type.startsWith('nda')) {
            req.nda_details = {
                purpose: form.nda_purpose,
                confidentiality_survival_years: form.nda_survival_years,
                ci_categories: form.nda_ci_categories ? form.nda_ci_categories.split(',').map(s => s.trim()).filter(Boolean) : undefined,
                non_solicitation: form.nda_non_solicitation,
                non_solicitation_months: form.nda_non_solicitation ? form.nda_non_solicitation_months : undefined,
                marking_requirement: form.nda_marking_requirement,
            };
        }
        if (form.contract_type === 'saas') {
            req.saas_details = {
                service_description: form.saas_service_description,
                pricing_model: form.saas_pricing_model,
                price_amount: form.saas_price_amount,
                billing_frequency: form.saas_billing_frequency,
                auto_renewal: form.saas_auto_renewal,
                uptime_commitment: form.saas_uptime,
                liability_cap_months: form.saas_liability_cap_months,
                authorized_users: form.saas_authorized_users,
                compliance_frameworks: form.saas_compliance_frameworks.length > 0 ? form.saas_compliance_frameworks : undefined,
            };
        }
        return req;
    };

    const handleGenerate = () => {
        setError('');
        setStep(3);
        generateMutation.mutate(buildRequest());
    };

    const handleDownload = async () => {
        if (!result) return;
        try {
            const blob = await downloadDraft(result.draft_id);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${result.title.replace(/\s+/g, '_')}.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            setError('Download failed');
        }
    };

    const canProceed = (): boolean => {
        if (step === 0) return !!form.contract_type;
        if (step === 1) {
            if (!form.party_1_name || !form.party_2_name || !form.governing_law) return false;
            if (form.contract_type.startsWith('nda') && !form.nda_purpose) return false;
            if (form.contract_type === 'saas' && (!form.saas_service_description || form.saas_price_amount <= 0)) return false;
            return true;
        }
        return true;
    };

    // ── Step Renderers ──

    const renderStepBar = () => (
        <div className="flex items-center justify-center gap-2 mb-8">
            {STEPS.map((label, i) => (
                <div key={label} className="flex items-center gap-2">
                    <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                            i < step ? 'text-white' : i === step ? 'text-white' : 'text-slate-400'
                        }`}
                        style={{
                            backgroundColor: i < step ? 'var(--risk-low)' : i === step ? 'var(--accent)' : 'var(--border)',
                        }}
                    >
                        {i < step ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                        ) : (
                            i + 1
                        )}
                    </div>
                    <span className={`text-sm hidden sm:inline ${i === step ? 'font-semibold' : ''}`} style={{ color: i === step ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {label}
                    </span>
                    {i < STEPS.length - 1 && <div className="w-6 h-px" style={{ backgroundColor: 'var(--border)' }} />}
                </div>
            ))}
        </div>
    );

    const renderStep0 = () => (
        <div className="animate-fade-in space-y-8">
            <div>
                <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>CONTRACT TYPE</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {CONTRACT_TYPES.map(ct => (
                        <button
                            key={ct.value}
                            onClick={() => set('contract_type', ct.value)}
                            className="text-left p-5 rounded-xl border-2 transition-all hover:shadow-md"
                            style={{
                                borderColor: form.contract_type === ct.value ? 'var(--accent)' : 'var(--border)',
                                backgroundColor: form.contract_type === ct.value ? 'var(--accent-glow)' : 'var(--bg-surface)',
                            }}
                        >
                            <div className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{ct.label}</div>
                            <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{ct.desc}</div>
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>PERSPECTIVE</h3>
                    <div className="space-y-2">
                        {PERSPECTIVES.map(p => (
                            <button
                                key={p.value}
                                onClick={() => set('drafting_perspective', p.value)}
                                className="w-full text-left px-4 py-3 rounded-lg border transition-all"
                                style={{
                                    borderColor: form.drafting_perspective === p.value ? 'var(--accent)' : 'var(--border)',
                                    backgroundColor: form.drafting_perspective === p.value ? 'var(--accent-glow)' : 'var(--bg-surface)',
                                }}
                            >
                                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{p.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
                <div>
                    <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-secondary)' }}>RISK APPETITE</h3>
                    <div className="space-y-2">
                        {RISK_APPETITES.map(r => (
                            <button
                                key={r.value}
                                onClick={() => set('risk_appetite', r.value)}
                                className="w-full text-left px-4 py-3 rounded-lg border transition-all"
                                style={{
                                    borderColor: form.risk_appetite === r.value ? 'var(--accent)' : 'var(--border)',
                                    backgroundColor: form.risk_appetite === r.value ? 'var(--accent-glow)' : 'var(--bg-surface)',
                                }}
                            >
                                <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{r.label}</div>
                                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.desc}</div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );

    const inputClass = "w-full px-3 py-2 rounded-lg border text-sm outline-none transition-colors focus:ring-2";
    const labelClass = "block text-xs font-medium mb-1";

    const renderStep1 = () => (
        <div className="animate-fade-in space-y-6">
            {/* Parties */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-5 rounded-xl border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>
                        {form.contract_type === 'saas' ? 'PROVIDER' : 'PARTY 1'}
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Legal Name *</label>
                            <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_1_name} onChange={e => set('party_1_name', e.target.value)} placeholder="e.g., Acme Inc." />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Entity Type</label>
                                <select className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_1_entity_type} onChange={e => set('party_1_entity_type', e.target.value)}>
                                    {['Inc.', 'LLC', 'Corp.', 'Ltd.', 'LP', 'LLP', 'Pvt. Ltd.', 'Individual'].map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Jurisdiction</label>
                                <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_1_jurisdiction} onChange={e => set('party_1_jurisdiction', e.target.value)} placeholder="US-DE" />
                            </div>
                        </div>
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Address</label>
                            <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_1_address} onChange={e => set('party_1_address', e.target.value)} placeholder="Optional" />
                        </div>
                    </div>
                </div>

                <div className="p-5 rounded-xl border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>
                        {form.contract_type === 'saas' ? 'CUSTOMER' : 'PARTY 2'}
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Legal Name *</label>
                            <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_2_name} onChange={e => set('party_2_name', e.target.value)} placeholder="e.g., Beta LLC" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Entity Type</label>
                                <select className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_2_entity_type} onChange={e => set('party_2_entity_type', e.target.value)}>
                                    {['Inc.', 'LLC', 'Corp.', 'Ltd.', 'LP', 'LLP', 'Pvt. Ltd.', 'Individual'].map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Jurisdiction</label>
                                <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_2_jurisdiction} onChange={e => set('party_2_jurisdiction', e.target.value)} placeholder="US-CA" />
                            </div>
                        </div>
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Address</label>
                            <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.party_2_address} onChange={e => set('party_2_address', e.target.value)} placeholder="Optional" />
                        </div>
                    </div>
                </div>
            </div>

            {/* NDA-specific fields */}
            {form.contract_type.startsWith('nda') && (
                <div className="p-5 rounded-xl border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>NDA DETAILS</h3>
                    <div className="space-y-3">
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Purpose of Disclosure *</label>
                            <textarea className={inputClass} style={{ borderColor: 'var(--border)' }} rows={2} value={form.nda_purpose} onChange={e => set('nda_purpose', e.target.value)} placeholder="e.g., Evaluate a potential technology partnership" />
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Term (months)</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.term_months} onChange={e => set('term_months', +e.target.value)} />
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Survival (years)</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.nda_survival_years} onChange={e => set('nda_survival_years', +e.target.value)} />
                            </div>
                            <div className="col-span-2">
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>CI Categories (comma-separated)</label>
                                <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.nda_ci_categories} onChange={e => set('nda_ci_categories', e.target.value)} placeholder="source code, financial data, customer lists" />
                            </div>
                        </div>
                        <div className="flex items-center gap-6 pt-1">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={form.nda_non_solicitation} onChange={e => set('nda_non_solicitation', e.target.checked)} className="rounded" />
                                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Non-Solicitation</span>
                            </label>
                            {form.nda_non_solicitation && (
                                <div className="flex items-center gap-2">
                                    <input type="number" className="w-16 px-2 py-1 rounded border text-sm" style={{ borderColor: 'var(--border)' }} value={form.nda_non_solicitation_months} onChange={e => set('nda_non_solicitation_months', +e.target.value)} />
                                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>months</span>
                                </div>
                            )}
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={form.nda_marking_requirement} onChange={e => set('nda_marking_requirement', e.target.checked)} className="rounded" />
                                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Marking Requirement</span>
                            </label>
                        </div>
                    </div>
                </div>
            )}

            {/* SaaS-specific fields */}
            {form.contract_type === 'saas' && (
                <div className="p-5 rounded-xl border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>SAAS DETAILS</h3>
                    <div className="space-y-3">
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Service Description *</label>
                            <textarea className={inputClass} style={{ borderColor: 'var(--border)' }} rows={2} value={form.saas_service_description} onChange={e => set('saas_service_description', e.target.value)} placeholder="e.g., Cloud-based CRM platform with AI analytics" />
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Pricing Model</label>
                                <select className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_pricing_model} onChange={e => set('saas_pricing_model', e.target.value)}>
                                    {['per_user_monthly', 'per_user_annual', 'flat_monthly', 'flat_annual', 'usage_based', 'tiered'].map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Price ($) *</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_price_amount || ''} onChange={e => set('saas_price_amount', +e.target.value)} placeholder="99.00" />
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Billing</label>
                                <select className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_billing_frequency} onChange={e => set('saas_billing_frequency', e.target.value)}>
                                    {['monthly', 'quarterly', 'annually'].map(f => <option key={f} value={f}>{f}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Term (months)</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.term_months} onChange={e => set('term_months', +e.target.value)} />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Uptime (%)</label>
                                <input type="number" step="0.1" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_uptime} onChange={e => set('saas_uptime', +e.target.value)} />
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Liability Cap (months)</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_liability_cap_months} onChange={e => set('saas_liability_cap_months', +e.target.value)} />
                            </div>
                            <div>
                                <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Authorized Users</label>
                                <input type="number" className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.saas_authorized_users} onChange={e => set('saas_authorized_users', +e.target.value)} />
                            </div>
                            <div className="flex items-end pb-1">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={form.saas_auto_renewal} onChange={e => set('saas_auto_renewal', e.target.checked)} className="rounded" />
                                    <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Auto-Renewal</span>
                                </label>
                            </div>
                        </div>
                        <div>
                            <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Compliance Frameworks</label>
                            <div className="flex flex-wrap gap-2 mt-1">
                                {['SOC2', 'ISO27001', 'GDPR', 'HIPAA', 'CCPA', 'DPDP'].map(fw => (
                                    <button
                                        key={fw}
                                        onClick={() => set('saas_compliance_frameworks',
                                            form.saas_compliance_frameworks.includes(fw)
                                                ? form.saas_compliance_frameworks.filter(f => f !== fw)
                                                : [...form.saas_compliance_frameworks, fw]
                                        )}
                                        className="px-3 py-1 rounded-full text-xs font-medium border transition-colors"
                                        style={{
                                            borderColor: form.saas_compliance_frameworks.includes(fw) ? 'var(--accent)' : 'var(--border)',
                                            backgroundColor: form.saas_compliance_frameworks.includes(fw) ? 'var(--accent-glow)' : 'var(--bg-surface)',
                                            color: form.saas_compliance_frameworks.includes(fw) ? 'var(--accent)' : 'var(--text-secondary)',
                                        }}
                                    >
                                        {fw}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Legal preferences */}
            <div className="p-5 rounded-xl border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>LEGAL PREFERENCES</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Governing Law *</label>
                        <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.governing_law} onChange={e => set('governing_law', e.target.value)} placeholder="e.g., Delaware" />
                    </div>
                    <div>
                        <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Dispute Resolution</label>
                        <select className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.dispute_resolution} onChange={e => set('dispute_resolution', e.target.value)}>
                            {['arbitration', 'litigation', 'mediation'].map(d => <option key={d} value={d}>{d}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className={labelClass} style={{ color: 'var(--text-secondary)' }}>Venue</label>
                        <input className={inputClass} style={{ borderColor: 'var(--border)' }} value={form.venue} onChange={e => set('venue', e.target.value)} placeholder="e.g., Wilmington, DE" />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderStep2 = () => {
        const ct = CONTRACT_TYPES.find(c => c.value === form.contract_type);
        const persp = PERSPECTIVES.find(p => p.value === form.drafting_perspective);
        const risk = RISK_APPETITES.find(r => r.value === form.risk_appetite);

        const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
            <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border)' }}>
                <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>{title}</h4>
                <div className="space-y-1">{children}</div>
            </div>
        );
        const Row = ({ label, value }: { label: string; value: string }) => (
            <div className="flex justify-between text-sm">
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{value || '—'}</span>
            </div>
        );

        return (
            <div className="animate-fade-in space-y-4">
                {error && (
                    <div className="p-3 rounded-lg text-sm" style={{ backgroundColor: 'var(--accent-glow)', color: 'var(--accent)' }}>
                        {error}
                    </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Section title="CONTRACT">
                        <Row label="Type" value={ct?.label || ''} />
                        <Row label="Perspective" value={persp?.label || ''} />
                        <Row label="Risk Appetite" value={risk?.label || ''} />
                    </Section>
                    <Section title="LEGAL">
                        <Row label="Governing Law" value={form.governing_law} />
                        <Row label="Dispute Resolution" value={form.dispute_resolution} />
                        <Row label="Venue" value={form.venue} />
                        <Row label="Term" value={`${form.term_months} months`} />
                    </Section>
                    <Section title="PARTY 1">
                        <Row label="Name" value={form.party_1_name} />
                        <Row label="Entity" value={form.party_1_entity_type} />
                        <Row label="Jurisdiction" value={form.party_1_jurisdiction} />
                    </Section>
                    <Section title="PARTY 2">
                        <Row label="Name" value={form.party_2_name} />
                        <Row label="Entity" value={form.party_2_entity_type} />
                        <Row label="Jurisdiction" value={form.party_2_jurisdiction} />
                    </Section>
                    {form.contract_type.startsWith('nda') && (
                        <Section title="NDA DETAILS">
                            <Row label="Purpose" value={form.nda_purpose} />
                            <Row label="CI Survival" value={`${form.nda_survival_years} years`} />
                            <Row label="Non-Solicitation" value={form.nda_non_solicitation ? `Yes (${form.nda_non_solicitation_months}mo)` : 'No'} />
                        </Section>
                    )}
                    {form.contract_type === 'saas' && (
                        <Section title="SAAS DETAILS">
                            <Row label="Service" value={form.saas_service_description.slice(0, 60)} />
                            <Row label="Price" value={`$${form.saas_price_amount} / ${form.saas_billing_frequency}`} />
                            <Row label="Uptime" value={`${form.saas_uptime}%`} />
                            <Row label="Users" value={String(form.saas_authorized_users)} />
                        </Section>
                    )}
                </div>
            </div>
        );
    };

    const renderStep3 = () => (
        <div className="animate-fade-in flex flex-col items-center justify-center py-16">
            <div className="relative mb-8">
                <div className="w-20 h-20 rounded-full border-4 animate-spin" style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Generating Your Contract</h3>
            <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)' }}>Our AI agents are drafting, reviewing, and polishing your document...</p>
            <div className="space-y-3 w-full max-w-sm">
                {['Validating inputs', 'Drafting clauses', 'Risk review', 'Compliance check', 'Quality assurance', 'Final assembly'].map((label, i) => (
                    <div key={label} className="flex items-center gap-3 text-sm">
                        <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--risk-low-bg)' }}>
                            <svg className="w-3 h-3 animate-pulse" style={{ color: 'var(--risk-low)' }} fill="currentColor" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="4" />
                            </svg>
                        </div>
                        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                    </div>
                ))}
            </div>
        </div>
    );

    const renderStep4 = () => {
        if (!result) return null;
        const scoreColor = (s: number) => s >= 80 ? 'var(--risk-low)' : s >= 60 ? 'var(--risk-high)' : 'var(--accent)';
        const scoreBg = (s: number) => s >= 80 ? 'var(--risk-low-bg)' : s >= 60 ? 'var(--risk-high-bg)' : 'var(--accent-glow)';
        return (
            <div className="animate-fade-in space-y-6">
                <div className="text-center mb-6">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-3" style={{ backgroundColor: 'var(--risk-low-bg)' }}>
                        <svg className="w-8 h-8" style={{ color: 'var(--risk-low)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <h3 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{result.title}</h3>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{result.total_sections} sections generated</p>
                </div>

                {/* Quality Scores */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: 'Overall', score: result.overall_score },
                        { label: 'Risk Alignment', score: result.risk_alignment },
                        { label: 'Compliance', score: result.compliance_score },
                        { label: 'Quality', score: result.qa_score },
                    ].map(({ label, score }) => (
                        <div key={label} className="p-4 rounded-xl text-center" style={{ backgroundColor: scoreBg(score) }}>
                            <div className="text-2xl font-bold" style={{ color: scoreColor(score) }}>{Math.round(score)}</div>
                            <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                        </div>
                    ))}
                </div>

                {/* Stats */}
                <div className="flex justify-center gap-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    <span>{result.annotations_applied} fixes applied</span>
                    <span>{result.conflicts_flagged} conflicts</span>
                    <span>{result.open_items} items for review</span>
                </div>

                {/* Actions */}
                <div className="flex justify-center gap-4 pt-4">
                    <button
                        onClick={handleDownload}
                        className="px-6 py-3 rounded-xl text-sm font-semibold text-white transition-transform active:scale-[0.98]"
                        style={{ backgroundColor: 'var(--accent)' }}
                    >
                        Download .docx
                    </button>
                    <button
                        onClick={() => { setStep(0); setForm({ ...DEFAULT_FORM }); setResult(null); }}
                        className="px-6 py-3 rounded-xl text-sm font-medium border transition-colors"
                        style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                    >
                        Draft Another
                    </button>
                </div>
            </div>
        );
    };

    return (
        <AppLayout>
            <div>
                <div className="mb-6">
                    <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Draft Contract</h1>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Generate a professional contract using AI-powered drafting agents</p>
                </div>

                {renderStepBar()}

                <div className="rounded-xl border p-6 md:p-8" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    {step === 0 && renderStep0()}
                    {step === 1 && renderStep1()}
                    {step === 2 && renderStep2()}
                    {step === 3 && renderStep3()}
                    {step === 4 && renderStep4()}
                </div>

                {/* Navigation buttons */}
                {step < 3 && (
                    <div className="flex justify-between mt-6">
                        <button
                            onClick={() => setStep(s => s - 1)}
                            disabled={step === 0}
                            className="px-5 py-2.5 rounded-lg text-sm font-medium border transition-colors disabled:opacity-30"
                            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                        >
                            Back
                        </button>
                        {step < 2 ? (
                            <button
                                onClick={() => setStep(s => s + 1)}
                                disabled={!canProceed()}
                                className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-40"
                                style={{ backgroundColor: 'var(--accent)' }}
                            >
                                Next
                            </button>
                        ) : (
                            <button
                                onClick={handleGenerate}
                                disabled={!canProceed() || generateMutation.isPending}
                                className="px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-transform active:scale-[0.98] disabled:opacity-40"
                                style={{ backgroundColor: 'var(--accent)' }}
                            >
                                Generate Contract
                            </button>
                        )}
                    </div>
                )}
            </div>
        </AppLayout>
    );
}
