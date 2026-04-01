import React from 'react';
import { type DraftingFormData, CONTRACT_TYPES, PERSPECTIVES, RISK_APPETITES } from './types';

interface StepReviewProps {
    form: DraftingFormData;
    error: string;
}

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border)' }}>
        <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>{title}</h4>
        <div className="space-y-1">{children}</div>
    </div>
);

const Row = ({ label, value }: { label: string; value: string }) => (
    <div className="flex justify-between text-sm">
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{value || '\u2014'}</span>
    </div>
);

export default function StepReview({ form, error }: StepReviewProps) {
    const ct = CONTRACT_TYPES.find(c => c.value === form.contract_type);
    const persp = PERSPECTIVES.find(p => p.value === form.drafting_perspective);
    const risk = RISK_APPETITES.find(r => r.value === form.risk_appetite);

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
}
