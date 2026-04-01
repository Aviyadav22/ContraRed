import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout';
import {
    generateContract,
    downloadDraft,
    type GenerateRequest,
    type GenerateResponse,
} from '@/api/client';
import { type DraftingFormData, DEFAULT_FORM } from './types';
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

    const set = (key: keyof DraftingFormData, value: unknown) => setForm(prev => ({ ...prev, [key]: value }));

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

    const handleReset = () => {
        setStep(0);
        setForm({ ...DEFAULT_FORM });
        setResult(null);
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
                    {step === 1 && <StepDetails form={form} set={set} />}
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
            </div>
        </AppLayout>
    );
}
