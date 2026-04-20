import { STEPS } from './types';

interface DraftingStepperProps {
    currentStep: number;
}

/**
 * Only the first 3 steps (Contract Type / Details / Review) represent explicit
 * user actions. Steps 4+ (Generating / Results) are post-submit states — they
 * render as checkmark circles once the user has moved past Review so it's clear
 * those aren't actionable.
 */
const ACTION_STEPS = 3;

export default function DraftingStepper({ currentStep }: DraftingStepperProps) {
    return (
        <div className="flex items-center justify-center mb-8 px-2">
            {STEPS.map((label, i) => {
                const isCompleted = i < currentStep;
                const isActive = i === currentStep;
                const isPostSubmit = i >= ACTION_STEPS;
                const isLast = i === STEPS.length - 1;

                const circleBg = isCompleted
                    ? 'var(--risk-low)'
                    : isActive
                        ? 'var(--accent)'
                        : 'var(--border)';

                const showCheck = isCompleted || (isPostSubmit && !isActive);

                return (
                    <div key={label} className="flex items-center flex-1 last:flex-none min-w-0">
                        <div className="flex items-center gap-2 min-w-0">
                            <div
                                className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors shrink-0"
                                style={{
                                    backgroundColor: circleBg,
                                    color: isCompleted || isActive ? '#FFFFFF' : 'var(--text-muted)',
                                }}
                                aria-current={isActive ? 'step' : undefined}
                            >
                                {showCheck ? (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                ) : isPostSubmit && isActive ? (
                                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="40 20" strokeLinecap="round" />
                                    </svg>
                                ) : (
                                    i + 1
                                )}
                            </div>
                            <span
                                className={`text-sm hidden sm:inline truncate ${isActive ? 'font-semibold' : ''}`}
                                style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                            >
                                {label}
                            </span>
                        </div>
                        {!isLast && (
                            <div
                                className="flex-1 h-px mx-2 sm:mx-3 min-w-[16px]"
                                style={{
                                    backgroundColor: isCompleted ? 'var(--risk-low)' : 'var(--border)',
                                }}
                            />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
