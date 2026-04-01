import { STEPS } from './types';

interface DraftingStepperProps {
    currentStep: number;
}

export default function DraftingStepper({ currentStep }: DraftingStepperProps) {
    return (
        <div className="flex items-center justify-center gap-2 mb-8">
            {STEPS.map((label, i) => (
                <div key={label} className="flex items-center gap-2">
                    <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                            i < currentStep ? 'text-white' : i === currentStep ? 'text-white' : 'text-slate-400'
                        }`}
                        style={{
                            backgroundColor: i < currentStep ? 'var(--risk-low)' : i === currentStep ? 'var(--accent)' : 'var(--border)',
                        }}
                    >
                        {i < currentStep ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                        ) : (
                            i + 1
                        )}
                    </div>
                    <span className={`text-sm hidden sm:inline ${i === currentStep ? 'font-semibold' : ''}`} style={{ color: i === currentStep ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {label}
                    </span>
                    {i < STEPS.length - 1 && <div className="w-6 h-px" style={{ backgroundColor: 'var(--border)' }} />}
                </div>
            ))}
        </div>
    );
}
