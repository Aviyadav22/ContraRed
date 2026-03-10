import { getStoredUser } from '@/api/client';
import AppHeader from '@/components/AppHeader';

export default function Billing() {
    const user = getStoredUser();

    const plans = [
        {
            name: 'Starter',
            price: '\u20b90',
            period: '/month',
            features: ['Basic clause detection', '5 documents/month', 'Default playbook', 'Community support'],
            current: user?.subscription_tier === 'free',
            popular: false,
            accent: 'slate',
        },
        {
            name: 'Pro',
            price: '\u20b94,100',
            period: '/month',
            features: ['All clause detection', 'Unlimited documents', 'Custom playbooks', 'Priority support'],
            current: user?.subscription_tier === 'pro',
            popular: true,
            accent: 'slate',
        },
        {
            name: 'Enterprise',
            price: '\u20b916,500',
            period: '/month',
            features: ['Everything in Pro', 'Custom integrations', 'SLA guarantee', 'Dedicated account manager'],
            current: user?.subscription_tier === 'enterprise',
            popular: false,
            accent: 'slate',
        },
    ];

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            <main className="max-w-7xl mx-auto px-8 py-10">
                <div className="mb-10">
                    <h1 className="text-2xl font-bold text-slate-900">Billing & Subscription</h1>
                    <p className="text-sm text-slate-500 mt-1.5">
                        Current plan: <strong className="text-slate-900">{user?.subscription_tier?.toUpperCase() || 'STARTER'}</strong>
                    </p>
                </div>

                {/* Plans Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                    {plans.map((plan) => (
                        <div
                            key={plan.name}
                            className={`bg-white rounded-xl p-7 relative border-2 ${
                                plan.popular
                                    ? 'border-slate-900'
                                    : plan.current
                                        ? 'border-green-600'
                                        : 'border-slate-200'
                            }`}
                        >
                            {plan.popular && (
                                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[11px] font-bold px-3.5 py-1 rounded-full tracking-wide">
                                    MOST POPULAR
                                </span>
                            )}
                            {plan.current && (
                                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green-600 text-white text-[11px] font-bold px-3.5 py-1 rounded-full">
                                    CURRENT PLAN
                                </span>
                            )}
                            <h3 className="text-lg font-bold text-slate-900 mb-2">{plan.name}</h3>
                            <div className="mb-5">
                                <span className="text-3xl font-extrabold text-slate-900">{plan.price}</span>
                                <span className="text-sm text-slate-500">{plan.period}</span>
                            </div>
                            <ul className="list-none p-0 mb-6 flex flex-col gap-2.5">
                                {plan.features.map((feature, idx) => (
                                    <li key={idx} className="flex items-center gap-2.5 text-sm text-slate-600">
                                        <svg width="16" height="16" fill="none" stroke="#16a34a" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                        </svg>
                                        {feature}
                                    </li>
                                ))}
                            </ul>
                            <button
                                disabled={plan.current}
                                className={`w-full py-3 text-sm font-semibold rounded-lg transition-colors ${
                                    plan.current
                                        ? 'bg-slate-100 text-slate-400 cursor-default'
                                        : plan.popular
                                            ? 'bg-slate-900 text-white hover:bg-slate-800 cursor-pointer'
                                            : 'bg-slate-100 text-slate-900 hover:bg-slate-200 cursor-pointer'
                                }`}
                            >
                                {plan.current ? 'Current Plan' : `Upgrade to ${plan.name}`}
                            </button>
                        </div>
                    ))}
                </div>

                {/* Notice */}
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 flex gap-4">
                    <svg width="22" height="22" fill="none" stroke="#d97706" viewBox="0 0 24 24" className="shrink-0 mt-0.5">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                        <h4 className="text-sm font-bold text-amber-800 mb-1">Payment Integration Pending</h4>
                        <p className="text-sm text-amber-700">
                            Billing via Razorpay will be enabled soon. To upgrade now, contact us at{' '}
                            <a href="mailto:support@contrared.ai" className="text-amber-800 font-semibold hover:underline">support@contrared.ai</a>
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}
