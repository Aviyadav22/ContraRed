import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import {
    generateContract,
    downloadDraft,
    type GenerateRequest,
    type GenerateResponse,
} from '@/api/client';
import { useToast } from '@/contexts/toast';
import { type DraftingFormData, DEFAULT_FORM } from './types';

// Framework hint → contract jurisdiction code. User-selected compliance
// frameworks are a strong signal for the contract jurisdiction.
const FRAMEWORK_JURISDICTION_HINT: Record<string, string> = {
    DPDP: 'IN',
    GDPR: 'EU',
    CCPA: 'US-CA',
    CPRA: 'US-CA',
    HIPAA: 'US',
    LGPD: 'BR',
    PDPA: 'SG',
};

// Keywords in governing-law text → canonical jurisdiction code.
const GOVERNING_LAW_HINT: Record<string, string> = {
    india: 'IN',
    indian: 'IN',
    delaware: 'US-DE',
    california: 'US-CA',
    'new york': 'US-NY',
    texas: 'US-TX',
    england: 'GB',
    uk: 'GB',
    'united kingdom': 'GB',
    singapore: 'SG',
    germany: 'DE',
    france: 'FR',
    australia: 'AU',
    uae: 'AE',
    'united arab emirates': 'AE',
};

/**
 * Derive the contract's jurisdiction from the user's inputs.
 * Priority: explicit non-default value > matching party jurisdictions >
 * governing-law text lookup > compliance-framework signal > default.
 *
 * Fixes the PatentOS bug where users who set both parties to IN, typed
 * "India" as governing law, and selected DPDP still ended up with the
 * contract's internal jurisdiction defaulting to US-DE, which suppressed
 * the DPDP-DPA repair path in the backend coherence pass.
 */
function deriveJurisdiction(form: DraftingFormData): string {
    // 1. Respect an explicit non-default jurisdiction choice.
    if (form.jurisdiction && form.jurisdiction !== 'US-DE') {
        return form.jurisdiction;
    }
    // 2. Both parties share a non-US country.
    const country = (code: string) => (code || '').split('-')[0];
    const p1 = country(form.party_1_jurisdiction);
    const p2 = country(form.party_2_jurisdiction);
    if (p1 && p1 === p2 && p1 !== 'US') {
        return form.party_1_jurisdiction;
    }
    // 3. Governing-law text lookup.
    const gl = (form.governing_law || '').toLowerCase();
    for (const [kw, code] of Object.entries(GOVERNING_LAW_HINT)) {
        if (gl.includes(kw)) return code;
    }
    // 4. Compliance-framework vote.
    if (form.contract_type === 'saas' && form.saas_compliance_frameworks.length > 0) {
        const votes: Record<string, number> = {};
        for (const fw of form.saas_compliance_frameworks) {
            const target = FRAMEWORK_JURISDICTION_HINT[fw];
            if (target) votes[target] = (votes[target] ?? 0) + 1;
        }
        const entries = Object.entries(votes);
        if (entries.length === 1) return entries[0][0];
        if (entries.length > 1) {
            entries.sort((a, b) => b[1] - a[1]);
            if (entries[0][1] > entries[1][1]) return entries[0][0];
        }
    }
    // 5. Fall back to whatever was set.
    return form.jurisdiction || 'US-DE';
}
import DraftingStepper from './DraftingStepper';
import StepContractType from './StepContractType';
import StepDetails from './StepDetails';
import StepReview from './StepReview';
import StepGenerating from './StepGenerating';
import StepResults from './StepResults';

export default function Drafting() {
    const [step, setStep] = useState(0);
    const [form, setForm] = useState<DraftingFormData>({ ...DEFAULT_FORM });
    const [result, setResult] = useState<GenerateResponse | null>(null);
    const [error, setError] = useState('');
    const abortRef = useRef<AbortController | null>(null);
    const { addToast } = useToast();

    const set = (key: keyof DraftingFormData, value: unknown) => setForm(prev => ({ ...prev, [key]: value }));

    const generateMutation = useMutation({
        mutationFn: (req: GenerateRequest) => {
            abortRef.current = new AbortController();
            return generateContract(req, abortRef.current.signal);
        },
        onSuccess: (data) => {
            setResult(data);
            setStep(4);
        },
        onError: (err: Error) => {
            // If the user cancelled, don't surface a scary error — just silently reset.
            if (err.name === 'AbortError') {
                setError('');
                setStep(2);
                return;
            }
            setError(err.message || 'Generation failed');
            setStep(2); // go back to review
        },
    });

    const buildRequest = (): GenerateRequest => {
        // Derive the contract's jurisdiction from all user signals so that
        // downstream repair passes (DPA = DPDP for IN, CCPA for US-CA, etc.)
        // fire correctly even when the hidden jurisdiction field hasn't been
        // touched.
        const effectiveJurisdiction = deriveJurisdiction(form);

        const req: GenerateRequest = {
            contract_type: form.contract_type,
            drafting_perspective: form.drafting_perspective,
            risk_appetite: form.risk_appetite,
            jurisdiction: effectiveJurisdiction,
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
                data_regions: form.saas_data_regions.length > 0 ? form.saas_data_regions : undefined,
            };
        }
        if (form.contract_type === 'msa') {
            // MSA flows into AI via negotiation_context so per-clause prompts
            // pick up scope, payment terms, and liability-cap multiplier.
            req.negotiation_context = [
                form.msa_scope_of_services ? `Scope of Services: ${form.msa_scope_of_services}` : '',
                form.msa_payment_terms ? `Payment Terms: ${form.msa_payment_terms}` : '',
                form.msa_liability_cap_multiplier > 0 ? `Liability Cap: ${form.msa_liability_cap_multiplier}x annual fees paid in the 12 months preceding the claim` : '',
            ].filter(Boolean).join(' | ');
        }
        if (form.contract_type === 'employment') {
            req.employee_title = form.employment_title;
            req.base_salary = form.employment_base_salary;
            req.reporting_manager = form.employment_reporting_manager;
            req.work_location = form.employment_work_location;
        }
        return req;
    };

    const handleGenerate = () => {
        // Guard against rapid double-clicks firing two mutations.
        if (generateMutation.isPending) return;
        setError('');
        setStep(3);
        generateMutation.mutate(buildRequest());
    };

    const handleCancelGeneration = () => {
        // Abort the in-flight request and reset UI to Review step.
        abortRef.current?.abort();
        generateMutation.reset();
        setError('');
        setStep(2);
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
            addToast('Downloaded contract as .docx', 'success');
        } catch {
            setError('Download failed');
            addToast('Download failed', 'error');
        }
    };

    const handleReset = () => {
        setStep(0);
        setForm({ ...DEFAULT_FORM });
        setResult(null);
    };

    // Compute which required fields are empty on the Details step.
    const getMissingFields = (): string[] => {
        if (step !== 1) return [];
        const missing: string[] = [];
        const party1Label = form.contract_type === 'saas'
            ? 'Provider name'
            : form.contract_type === 'msa'
                ? 'Service Provider name'
                : form.contract_type === 'employment'
                    ? 'Company name'
                    : 'Party 1 name';
        const party2Label = form.contract_type === 'saas'
            ? 'Customer name'
            : form.contract_type === 'msa'
                ? 'Client name'
                : form.contract_type === 'employment'
                    ? 'Employee name'
                    : 'Party 2 name';
        if (!form.party_1_name) missing.push(party1Label);
        if (!form.party_2_name) missing.push(party2Label);
        if (!form.governing_law) missing.push('Governing Law');
        if (form.contract_type.startsWith('nda') && !form.nda_purpose) missing.push('Purpose of Disclosure');
        if (form.contract_type === 'saas') {
            if (!form.saas_service_description) missing.push('Service Description');
            if (form.saas_price_amount <= 0) missing.push('Price');
        }
        if (form.contract_type === 'msa') {
            if (!form.msa_scope_of_services) missing.push('Scope of Services');
        }
        if (form.contract_type === 'employment') {
            if (!form.employment_title) missing.push('Job Title');
            if (!form.employment_base_salary) missing.push('Base Salary');
        }
        return missing;
    };

    const missingFields = getMissingFields();

    const canProceed = (): boolean => {
        if (step === 0) return !!form.contract_type;
        if (step === 1) return missingFields.length === 0;
        return true;
    };

    return (
        <AppLayout>
            <div>
                <div className="mb-6">
                    <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Draft Contract</h1>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Generate a professional contract using AI-powered drafting agents</p>
                </div>

                <DraftingStepper currentStep={step} />

                <div className="rounded-xl border p-6 md:p-8" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}>
                    {step === 0 && <StepContractType form={form} set={set} />}
                    {step === 1 && <StepDetails form={form} set={set} missingFields={missingFields} />}
                    {step === 2 && <StepReview form={form} error={error} />}
                    {step === 3 && <StepGenerating />}
                    {step === 4 && <StepResults result={result} onDownload={handleDownload} onReset={handleReset} />}
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

                {/* Cancel button during generation */}
                {step === 3 && (
                    <div className="flex justify-center mt-6">
                        <button
                            onClick={handleCancelGeneration}
                            className="px-5 py-2.5 rounded-lg text-sm font-medium border transition-colors"
                            style={{
                                borderColor: 'var(--border)',
                                color: 'var(--text-secondary)',
                                backgroundColor: 'var(--bg-surface)',
                            }}
                        >
                            Cancel Generation
                        </button>
                    </div>
                )}
            </div>
        </AppLayout>
    );
}
