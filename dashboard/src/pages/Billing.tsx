import { Link } from 'react-router-dom';
import { getStoredUser } from '@/api/client';

export default function Billing() {
    const user = getStoredUser();

    const plans = [
        {
            name: 'Free',
            price: '₹0',
            period: '/month',
            scans: '5 documents/month',
            features: ['Basic clause detection', '5 documents/month', 'Community support'],
            current: user?.subscription_tier === 'free',
        },
        {
            name: 'Pro',
            price: '₹4,100',
            period: '/month',
            scans: 'Unlimited',
            features: ['All clause detection', 'Unlimited documents', 'Custom playbooks', 'Priority support'],
            current: user?.subscription_tier === 'pro',
            popular: true,
        },
        {
            name: 'Enterprise',
            price: '₹16,500',
            period: '/month',
            scans: 'Unlimited',
            features: ['Everything in Pro', 'Custom integrations', 'SLA guarantee', 'Dedicated account manager'],
            current: user?.subscription_tier === 'enterprise',
        },
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
            {/* Header */}
            <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <Link to="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <span className="text-xl font-bold text-slate-900 dark:text-white">Contra<span className="text-red-500">Red</span></span>
                        </Link>

                        <nav className="flex items-center gap-6">
                            <Link to="/" className="text-slate-600 dark:text-slate-300 hover:text-blue-600 font-medium">Dashboard</Link>
                            <Link to="/playbooks" className="text-slate-600 dark:text-slate-300 hover:text-blue-600 font-medium">Playbooks</Link>
                            <Link to="/billing" className="text-blue-600 dark:text-blue-400 font-semibold">Billing</Link>
                        </nav>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Billing & Subscription</h1>
                <p className="text-slate-500 dark:text-slate-400 mb-8">
                    Current plan: <span className="font-semibold text-blue-600">{user?.subscription_tier?.toUpperCase() || 'FREE'}</span>
                </p>

                {/* Plans Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    {plans.map((plan) => (
                        <div
                            key={plan.name}
                            className={`bg-white dark:bg-slate-800 rounded-xl border-2 p-6 relative ${plan.popular
                                    ? 'border-blue-500 shadow-lg'
                                    : plan.current
                                        ? 'border-green-500'
                                        : 'border-slate-200 dark:border-slate-700'
                                }`}
                        >
                            {plan.popular && (
                                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                                    POPULAR
                                </span>
                            )}
                            {plan.current && (
                                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                                    CURRENT
                                </span>
                            )}

                            <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">{plan.name}</h3>
                            <div className="mb-4">
                                <span className="text-3xl font-bold text-slate-900 dark:text-white">{plan.price}</span>
                                <span className="text-slate-500 dark:text-slate-400">{plan.period}</span>
                            </div>

                            <ul className="space-y-3 mb-6">
                                {plan.features.map((feature, idx) => (
                                    <li key={idx} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        {feature}
                                    </li>
                                ))}
                            </ul>

                            <button
                                disabled={plan.current}
                                className={`w-full py-3 rounded-lg font-medium transition ${plan.current
                                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                        : plan.popular
                                            ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                            : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
                                    }`}
                            >
                                {plan.current ? 'Current Plan' : `Upgrade to ${plan.name}`}
                            </button>
                        </div>
                    ))}
                </div>

                {/* Razorpay Notice */}
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6">
                    <div className="flex items-start gap-4">
                        <svg className="w-6 h-6 text-amber-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <div>
                            <h4 className="font-semibold text-amber-800 dark:text-amber-200 mb-1">Razorpay Integration Pending</h4>
                            <p className="text-sm text-amber-700 dark:text-amber-300">
                                Payment processing via Razorpay Subscriptions API will be enabled after backend billing endpoints are implemented.
                                For now, contact us to upgrade: <a href="mailto:support@contrared.ai" className="underline">support@contrared.ai</a>
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
