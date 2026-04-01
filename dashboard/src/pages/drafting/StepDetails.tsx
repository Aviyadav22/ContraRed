import { type DraftingFormData } from './types';

interface StepDetailsProps {
    form: DraftingFormData;
    set: (key: keyof DraftingFormData, value: unknown) => void;
}

const inputClass = "w-full px-3 py-2 rounded-lg border text-sm outline-none transition-colors focus:ring-2";
const labelClass = "block text-xs font-medium mb-1";

export default function StepDetails({ form, set }: StepDetailsProps) {
    return (
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
}
