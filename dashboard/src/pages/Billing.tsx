import { useState, useEffect } from 'react';
import { getStoredUser, getSubscription, getUsageStats, listInvoices, createSubscription, type SubscriptionInfo, type UsageStats, type InvoiceItem } from '@/api/client';
import AppHeader from '@/components/AppHeader';

type Currency = 'INR' | 'USD';

const PLAN_PRICES: Record<string, { inr: string; usd: string }> = {
    Free: { inr: '\u20b90', usd: '$0' },
    Starter: { inr: '\u20b9999', usd: '$12' },
    Pro: { inr: '\u20b92,999', usd: '$36' },
    Business: { inr: '\u20b96,999', usd: '$84' },
    Enterprise: { inr: 'Custom', usd: 'Custom' },
};

const ALLOWED_PAYMENT_DOMAINS = ['razorpay.com', 'stripe.com', 'checkout.stripe.com', 'api.razorpay.com'];

function isAllowedPaymentUrl(url: string): boolean {
    try {
        const parsed = new URL(url);
        return ALLOWED_PAYMENT_DOMAINS.some(domain =>
            parsed.hostname === domain || parsed.hostname.endsWith('.' + domain)
        );
    } catch {
        return false;
    }
}

export default function Billing() {
    const user = getStoredUser();
    const [currency, setCurrency] = useState<Currency>('INR');
    const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
    const [usage, setUsage] = useState<UsageStats | null>(null);
    const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
    const [upgrading, setUpgrading] = useState<string | null>(null);
    const [toast, setToast] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                const [sub, usg, inv] = await Promise.allSettled([
                    getSubscription(),
                    getUsageStats(),
                    listInvoices(),
                ]);
                if (sub.status === 'fulfilled') setSubscription(sub.value);
                if (usg.status === 'fulfilled') setUsage(usg.value);
                if (inv.status === 'fulfilled') setInvoices(inv.value);
            } catch {
                // silently degrade
            } finally {
                // data loaded
            }
        }
        fetchData();
    }, []);

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 4000);
    };

    const handleUpgrade = async (planName: string) => {
        if (planName === 'Enterprise') {
            window.location.href = 'mailto:support@contrared.ai?subject=Enterprise Plan Inquiry';
            return;
        }
        setUpgrading(planName);
        try {
            const gateway = currency === 'INR' ? 'razorpay' : 'stripe';
            const result = await createSubscription(planName.toLowerCase(), gateway, currency);
            const paymentUrl = result.short_url || result.checkout_url;
            if (paymentUrl && isAllowedPaymentUrl(paymentUrl)) {
                window.location.href = paymentUrl;
            } else if (paymentUrl) {
                showToast('Invalid payment URL received. Please try again.');
            } else {
                showToast('Payment integration coming soon. Contact support@contrared.ai to upgrade.');
            }
        } catch {
            showToast('Payment integration coming soon. Contact support@contrared.ai to upgrade.');
        } finally {
            setUpgrading(null);
        }
    };

    const plans = [
        {
            name: 'Free',
            features: ['Basic clause detection', '5 scans/month', 'Default playbook', 'Community support'],
            current: (subscription?.plan || user?.subscription_tier) === 'free',
            popular: false,
        },
        {
            name: 'Starter',
            features: ['All clause detection', '50 scans/month', 'Custom playbooks', 'Email support'],
            current: (subscription?.plan || user?.subscription_tier) === 'starter',
            popular: false,
        },
        {
            name: 'Pro',
            features: ['Everything in Starter', '200 scans/month', 'Batch processing', 'Priority support'],
            current: (subscription?.plan || user?.subscription_tier) === 'pro',
            popular: true,
        },
        {
            name: 'Business',
            features: ['Everything in Pro', '1,000 scans/month', 'Team analytics', 'SSO integration', 'Dedicated support'],
            current: (subscription?.plan || user?.subscription_tier) === 'business',
            popular: false,
        },
        {
            name: 'Enterprise',
            features: ['Everything in Business', 'Unlimited scans', 'Custom integrations', 'SLA guarantee', 'Dedicated account manager'],
            current: (subscription?.plan || user?.subscription_tier) === 'enterprise',
            popular: false,
        },
    ];

    const usagePercent = usage ? Math.min(100, Math.round((usage.scans_used / Math.max(usage.scans_limit, 1)) * 100)) : 0;

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            {/* Toast notification */}
            {toast && (
                <div className="fixed top-20 right-6 z-50 bg-amber-50 border border-amber-200 text-amber-800 px-5 py-3 rounded-lg shadow-lg text-sm font-medium animate-[fadeIn_0.2s_ease-out]">
                    {toast}
                </div>
            )}

            <main className="max-w-7xl mx-auto px-8 py-10">
                <div className="flex justify-between items-start mb-10">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Billing & Subscription</h1>
                        <p className="text-sm text-slate-500 mt-1.5">
                            Current plan: <strong className="text-slate-900">{(subscription?.plan || user?.subscription_tier || 'free').toUpperCase()}</strong>
                            {subscription?.current_period_end && (
                                <span className="ml-2 text-slate-400">
                                    (renews {new Date(subscription.current_period_end).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })})
                                </span>
                            )}
                        </p>
                    </div>

                    {/* Currency Toggle */}
                    <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg p-1">
                        <button
                            onClick={() => setCurrency('INR')}
                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                currency === 'INR' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            INR
                        </button>
                        <button
                            onClick={() => setCurrency('USD')}
                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                currency === 'USD' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            USD
                        </button>
                    </div>
                </div>

                {/* Usage Meter */}
                {usage && (
                    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
                        <div className="flex items-center justify-between mb-3">
                            <h2 className="text-base font-semibold text-slate-900">Usage This Period</h2>
                            <span className="text-sm text-slate-500">
                                {usage.scans_used} / {usage.scans_limit} scans
                            </span>
                        </div>
                        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all ${usagePercent >= 90 ? 'bg-red-500' : usagePercent >= 70 ? 'bg-amber-400' : 'bg-green-500'}`}
                                style={{ width: `${usagePercent}%` }}
                            />
                        </div>
                        <div className="flex justify-between mt-2 text-xs text-slate-400">
                            <span>{usage.scans_remaining} scans remaining</span>
                            {usage.overage_count > 0 && (
                                <span className="text-amber-600 font-medium">{usage.overage_count} overage scans</span>
                            )}
                        </div>
                    </div>
                )}

                {/* Plans Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 mb-10">
                    {plans.map((plan) => {
                        const price = PLAN_PRICES[plan.name]?.[currency === 'INR' ? 'inr' : 'usd'] || 'Custom';
                        return (
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
                                    <span className="text-3xl font-extrabold text-slate-900">{price}</span>
                                    {plan.name !== 'Enterprise' && <span className="text-sm text-slate-500">/month</span>}
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
                                    disabled={plan.current || upgrading !== null}
                                    onClick={() => handleUpgrade(plan.name)}
                                    className={`w-full py-3 text-sm font-semibold rounded-lg transition-colors ${
                                        plan.current
                                            ? 'bg-slate-100 text-slate-400 cursor-default'
                                            : plan.popular
                                                ? 'bg-slate-900 text-white hover:bg-slate-800 cursor-pointer'
                                                : 'bg-slate-100 text-slate-900 hover:bg-slate-200 cursor-pointer'
                                    } disabled:opacity-50`}
                                >
                                    {plan.current
                                        ? 'Current Plan'
                                        : upgrading === plan.name
                                            ? 'Processing...'
                                            : plan.name === 'Enterprise'
                                                ? 'Contact Sales'
                                                : `Upgrade to ${plan.name}`}
                                </button>
                            </div>
                        );
                    })}
                </div>

                {/* Invoice History */}
                {invoices.length > 0 && (
                    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
                        <h2 className="text-lg font-semibold text-slate-900 mb-4">Invoice History</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-slate-200">
                                        <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Date</th>
                                        <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Plan</th>
                                        <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Description</th>
                                        <th scope="col" className="text-right py-2 px-3 font-medium text-slate-500">Amount</th>
                                        <th scope="col" className="text-left py-2 px-3 font-medium text-slate-500">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {invoices.map((inv) => (
                                        <tr key={inv.id} className="border-b border-slate-100">
                                            <td className="py-2 px-3 text-slate-600">
                                                {new Date(inv.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                            </td>
                                            <td className="py-2 px-3 text-slate-700 font-medium">{inv.plan}</td>
                                            <td className="py-2 px-3 text-slate-500">{inv.description}</td>
                                            <td className="py-2 px-3 text-right text-slate-900 font-medium">
                                                {inv.currency === 'INR' ? '\u20b9' : '$'}{inv.amount}
                                            </td>
                                            <td className="py-2 px-3">
                                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                                    inv.status === 'paid' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                                                }`}>
                                                    {inv.status}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

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
