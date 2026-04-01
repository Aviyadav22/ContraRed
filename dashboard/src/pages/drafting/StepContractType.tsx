import { type DraftingFormData, CONTRACT_TYPES, PERSPECTIVES, RISK_APPETITES } from './types';

interface StepContractTypeProps {
    form: DraftingFormData;
    set: (key: keyof DraftingFormData, value: unknown) => void;
}

export default function StepContractType({ form, set }: StepContractTypeProps) {
    return (
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
}
