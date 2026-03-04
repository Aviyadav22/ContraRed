import { getStoredUser } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function Billing() {
    const user = getStoredUser();

    const plans = [
        {
            name: 'Starter',
            price: '₹0',
            period: '/month',
            features: ['Basic clause detection', '5 documents/month', 'Default playbook', 'Community support'],
            current: user?.subscription_tier === 'free',
            accent: '#475569',
        },
        {
            name: 'Pro',
            price: '₹4,100',
            period: '/month',
            features: ['All clause detection', 'Unlimited documents', 'Custom playbooks', 'Priority support'],
            current: user?.subscription_tier === 'pro',
            popular: true,
            accent: '#0f172a',
        },
        {
            name: 'Enterprise',
            price: '₹16,500',
            period: '/month',
            features: ['Everything in Pro', 'Custom integrations', 'SLA guarantee', 'Dedicated account manager'],
            current: user?.subscription_tier === 'enterprise',
            accent: '#475569',
        },
    ];

    return (
        <div style={{ fontFamily: "'Inter', system-ui, sans-serif", minHeight: '100vh', backgroundColor: '#f8fafc' }}>
            <AppHeader />

            <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 32px' }}>
                <div style={{ marginBottom: 40 }}>
                    <h1 style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', margin: 0 }}>Billing & Subscription</h1>
                    <p style={{ fontSize: 14, color: '#64748b', margin: '6px 0 0' }}>
                        Current plan: <strong style={{ color: '#0f172a' }}>{user?.subscription_tier?.toUpperCase() || 'STARTER'}</strong>
                    </p>
                </div>

                {/* Plans Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, marginBottom: 40 }}>
                    {plans.map((plan) => (
                        <div
                            key={plan.name}
                            style={{
                                backgroundColor: '#ffffff',
                                borderRadius: 12,
                                border: `2px solid ${plan.popular ? '#0f172a' : plan.current ? '#16a34a' : '#e2e8f0'}`,
                                padding: 28,
                                position: 'relative',
                            }}
                        >
                            {plan.popular && (
                                <span style={{
                                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                                    backgroundColor: '#0f172a', color: '#ffffff',
                                    fontSize: 11, fontWeight: 700, padding: '4px 14px', borderRadius: 100,
                                    letterSpacing: 0.5,
                                }}>
                                    MOST POPULAR
                                </span>
                            )}
                            {plan.current && (
                                <span style={{
                                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                                    backgroundColor: '#16a34a', color: '#ffffff',
                                    fontSize: 11, fontWeight: 700, padding: '4px 14px', borderRadius: 100,
                                }}>
                                    CURRENT PLAN
                                </span>
                            )}
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', margin: '0 0 8px' }}>{plan.name}</h3>
                            <div style={{ marginBottom: 20 }}>
                                <span style={{ fontSize: 32, fontWeight: 800, color: '#0f172a' }}>{plan.price}</span>
                                <span style={{ fontSize: 14, color: '#64748b' }}>{plan.period}</span>
                            </div>
                            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                                {plan.features.map((feature, idx) => (
                                    <li key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: '#475569' }}>
                                        <svg width="16" height="16" fill="none" stroke="#16a34a" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                        </svg>
                                        {feature}
                                    </li>
                                ))}
                            </ul>
                            <button
                                disabled={plan.current}
                                style={{
                                    width: '100%',
                                    padding: '12px 0',
                                    fontSize: 14,
                                    fontWeight: 600,
                                    borderRadius: 8,
                                    border: 'none',
                                    cursor: plan.current ? 'default' : 'pointer',
                                    backgroundColor: plan.current ? '#f1f5f9' : plan.popular ? '#0f172a' : '#f1f5f9',
                                    color: plan.current ? '#94a3b8' : plan.popular ? '#ffffff' : '#0f172a',
                                }}
                            >
                                {plan.current ? 'Current Plan' : `Upgrade to ${plan.name}`}
                            </button>
                        </div>
                    ))}
                </div>

                {/* Notice */}
                <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12, padding: 24, display: 'flex', gap: 16 }}>
                    <svg width="22" height="22" fill="none" stroke="#d97706" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 2 }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                        <h4 style={{ fontSize: 14, fontWeight: 700, color: '#92400e', margin: '0 0 4px' }}>Payment Integration Pending</h4>
                        <p style={{ fontSize: 14, color: '#b45309', margin: 0 }}>
                            Billing via Razorpay will be enabled soon. To upgrade now, contact us at{' '}
                            <a href="mailto:support@contrared.ai" style={{ color: '#92400e', fontWeight: 600 }}>support@contrared.ai</a>
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
