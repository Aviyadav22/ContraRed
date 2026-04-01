import { useState, useEffect, type CSSProperties } from 'react';
import { getStoredUser, getSubscription, getUsageStats, listInvoices, createSubscription, type SubscriptionInfo, type UsageStats, type InvoiceItem } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge } from '@/components/ui';
import { Check, AlertTriangle } from 'lucide-react';

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

const thStyle: CSSProperties = {
    textAlign: 'left', padding: '8px 12px', fontWeight: 500, fontSize: 12,
    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em',
};
const tdStyle: CSSProperties = { padding: '8px 12px' };

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
        { name: 'Free', features: ['Basic clause detection', '5 scans/month', 'Default playbook', 'Community support'], current: (subscription?.plan || user?.subscription_tier) === 'free', popular: false },
        { name: 'Starter', features: ['All clause detection', '50 scans/month', 'Custom playbooks', 'Email support'], current: (subscription?.plan || user?.subscription_tier) === 'starter', popular: false },
        { name: 'Pro', features: ['Everything in Starter', '200 scans/month', 'Batch processing', 'Priority support'], current: (subscription?.plan || user?.subscription_tier) === 'pro', popular: true },
        { name: 'Business', features: ['Everything in Pro', '1,000 scans/month', 'Team analytics', 'SSO integration', 'Dedicated support'], current: (subscription?.plan || user?.subscription_tier) === 'business', popular: false },
        { name: 'Enterprise', features: ['Everything in Business', 'Unlimited scans', 'Custom integrations', 'SLA guarantee', 'Dedicated account manager'], current: (subscription?.plan || user?.subscription_tier) === 'enterprise', popular: false },
    ];

    const usagePercent = usage ? Math.min(100, Math.round((usage.scans_used / Math.max(usage.scans_limit, 1)) * 100)) : 0;

    const currencyBtnStyle = (active: boolean): CSSProperties => ({
        padding: '6px 12px', fontSize: 12, fontWeight: 600, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
        backgroundColor: active ? 'var(--accent)' : 'transparent',
        color: active ? '#fff' : 'var(--text-muted)',
        transition: 'all var(--transition-fast)',
    });

    return (
        <AppLayout>
            {/* Toast notification */}
            {toast && (
                <div style={{
                    position: 'fixed', top: 80, right: 24, zIndex: 50,
                    background: 'var(--risk-high-bg)', border: '1px solid var(--risk-high-border)',
                    color: 'var(--risk-high)', padding: '12px 20px', borderRadius: 'var(--radius-md)',
                    boxShadow: 'var(--shadow-lg)', fontSize: 14, fontWeight: 500,
                }}>
                    {toast}
                </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 40 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Billing & Subscription</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 6 }}>
                        Current plan: <strong style={{ color: 'var(--text-primary)' }}>{(subscription?.plan || user?.subscription_tier || 'free').toUpperCase()}</strong>
                        {subscription?.current_period_end && (
                            <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>
                                (renews {new Date(subscription.current_period_end).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })})
                            </span>
                        )}
                    </p>
                </div>
                {/* Currency Toggle */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 4 }}>
                    <button onClick={() => setCurrency('INR')} style={currencyBtnStyle(currency === 'INR')}>INR</button>
                    <button onClick={() => setCurrency('USD')} style={currencyBtnStyle(currency === 'USD')}>USD</button>
                </div>
            </div>

            {/* Usage Meter */}
            {usage && (
                <Card style={{ marginBottom: 32 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                        <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Usage This Period</h2>
                        <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                            {usage.scans_used} / {usage.scans_limit} scans
                        </span>
                    </div>
                    <div style={{ width: '100%', height: 12, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                        <div
                            style={{
                                height: '100%', borderRadius: 'var(--radius-sm)', transition: 'width 0.4s ease',
                                width: `${usagePercent}%`,
                                background: usagePercent >= 90 ? 'var(--risk-critical)' : usagePercent >= 70 ? 'var(--risk-high)' : 'var(--risk-low)',
                            }}
                        />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                        <span>{usage.scans_remaining} scans remaining</span>
                        {usage.overage_count > 0 && (
                            <span style={{ color: 'var(--risk-high)', fontWeight: 500 }}>{usage.overage_count} overage scans</span>
                        )}
                    </div>
                </Card>
            )}

            {/* Plans Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24, marginBottom: 40 }}>
                {plans.map((plan) => {
                    const price = PLAN_PRICES[plan.name]?.[currency === 'INR' ? 'inr' : 'usd'] || 'Custom';
                    const borderColor = plan.popular ? 'var(--accent)' : plan.current ? 'var(--risk-low)' : 'var(--border)';
                    return (
                        <div
                            key={plan.name}
                            style={{
                                backgroundColor: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)',
                                padding: 28, position: 'relative',
                                border: `2px solid ${borderColor}`,
                                boxShadow: plan.popular ? '0 0 16px var(--accent-glow)' : plan.current ? '0 0 12px rgba(34,197,94,0.15)' : 'none',
                            }}
                        >
                            {plan.popular && (
                                <span style={{
                                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                                    background: 'var(--accent)', color: '#fff', fontSize: 11, fontWeight: 700,
                                    padding: '4px 14px', borderRadius: 'var(--radius-sm)', letterSpacing: '0.04em',
                                }}>
                                    MOST POPULAR
                                </span>
                            )}
                            {plan.current && (
                                <span style={{
                                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                                    background: 'var(--risk-low)', color: '#fff', fontSize: 11, fontWeight: 700,
                                    padding: '4px 14px', borderRadius: 'var(--radius-sm)',
                                }}>
                                    CURRENT PLAN
                                </span>
                            )}
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>{plan.name}</h3>
                            <div style={{ marginBottom: 20 }}>
                                <span style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)' }}>{price}</span>
                                {plan.name !== 'Enterprise' && <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>/month</span>}
                            </div>
                            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
                                {plan.features.map((feature, idx) => (
                                    <li key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: 'var(--text-secondary)' }}>
                                        <Check size={16} style={{ color: 'var(--risk-low)', flexShrink: 0 }} />
                                        {feature}
                                    </li>
                                ))}
                            </ul>
                            <Button
                                variant={plan.current ? 'ghost' : plan.popular ? 'primary' : 'secondary'}
                                disabled={plan.current || upgrading !== null}
                                onClick={() => handleUpgrade(plan.name)}
                                style={{ width: '100%' }}
                            >
                                {plan.current ? 'Current Plan'
                                    : upgrading === plan.name ? 'Processing...'
                                    : plan.name === 'Enterprise' ? 'Contact Sales'
                                    : `Upgrade to ${plan.name}`}
                            </Button>
                        </div>
                    );
                })}
            </div>

            {/* Invoice History */}
            {invoices.length > 0 && (
                <Card style={{ marginBottom: 32 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Invoice History</h2>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                    <th scope="col" style={thStyle}>Date</th>
                                    <th scope="col" style={thStyle}>Plan</th>
                                    <th scope="col" style={thStyle}>Description</th>
                                    <th scope="col" style={{ ...thStyle, textAlign: 'right' }}>Amount</th>
                                    <th scope="col" style={thStyle}>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {invoices.map((inv) => (
                                    <tr key={inv.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                        <td style={{ ...tdStyle, color: 'var(--text-secondary)' }}>
                                            {new Date(inv.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                        </td>
                                        <td style={{ ...tdStyle, color: 'var(--text-primary)', fontWeight: 500 }}>{inv.plan}</td>
                                        <td style={{ ...tdStyle, color: 'var(--text-muted)' }}>{inv.description}</td>
                                        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-primary)', fontWeight: 500 }}>
                                            {inv.currency === 'INR' ? '\u20b9' : '$'}{inv.amount}
                                        </td>
                                        <td style={tdStyle}>
                                            <Badge variant={inv.status === 'paid' ? 'low' : 'high'}>{inv.status}</Badge>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {/* Notice */}
            <div style={{
                background: 'var(--risk-high-bg)', border: '1px solid var(--risk-high-border)',
                borderRadius: 'var(--radius-lg)', padding: 24, display: 'flex', gap: 16,
            }}>
                <AlertTriangle size={22} style={{ color: 'var(--risk-high)', flexShrink: 0, marginTop: 2 }} />
                <div>
                    <h4 style={{ fontSize: 14, fontWeight: 700, color: 'var(--risk-high)', marginBottom: 4 }}>Payment Integration Pending</h4>
                    <p style={{ fontSize: 14, color: 'var(--risk-high)' }}>
                        Billing via Razorpay will be enabled soon. To upgrade now, contact us at{' '}
                        <a href="mailto:support@contrared.ai" style={{ color: 'var(--risk-high)', fontWeight: 600, textDecoration: 'underline' }}>support@contrared.ai</a>
                    </p>
                </div>
            </div>
        </AppLayout>
    );
}
