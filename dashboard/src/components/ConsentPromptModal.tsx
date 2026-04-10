import { useState, useEffect, useCallback, type CSSProperties } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { grantConsent } from '@/api/client';
import { onConsentNeeded, type ConsentRequest } from '@/api/consentPrompt';
import { Shield, CheckCircle, AlertTriangle } from 'lucide-react';

const PURPOSE_INFO: Record<string, { name: string; description: string }> = {
    contract_analysis: {
        name: 'AI Contract Analysis',
        description: 'Analyse contract clauses, identify risks, and generate redline suggestions using AI.',
    },
    ai_drafting: {
        name: 'AI Contract Drafting',
        description: 'Generate contract drafts and clause suggestions using AI models.',
    },
    billing: {
        name: 'Billing & Payments',
        description: 'Process subscription payments and manage billing information.',
    },
    sso_integration: {
        name: 'SSO Integration',
        description: 'Enable single sign-on with your organisation identity provider.',
    },
    risk_assessment: {
        name: 'Risk Assessment',
        description: 'Assess and score contract risks using AI-powered analysis.',
    },
};

export function ConsentPromptModal() {
    const [pending, setPending] = useState<ConsentRequest | null>(null);
    const [granting, setGranting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        return onConsentNeeded((req) => {
            setError(null);
            setGranting(false);
            setPending(req);
        });
    }, []);

    const handleGrant = useCallback(async () => {
        if (!pending) return;
        setGranting(true);
        setError(null);
        try {
            await grantConsent(pending.purposes);
            pending.resolve();
            setPending(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to grant consent.');
            setGranting(false);
        }
    }, [pending]);

    const handleDecline = useCallback(() => {
        if (!pending) return;
        pending.reject('Consent declined');
        setPending(null);
    }, [pending]);

    if (!pending) return null;

    const cardStyle: CSSProperties = {
        padding: 14,
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border)',
        backgroundColor: 'var(--bg-secondary)',
        marginBottom: 10,
    };

    return (
        <Modal
            open={true}
            onClose={handleDecline}
            title="Consent Required"
            size="md"
            footer={
                <>
                    <Button variant="ghost" onClick={handleDecline} disabled={granting}>
                        Decline
                    </Button>
                    <Button variant="primary" onClick={handleGrant} disabled={granting}>
                        {granting ? 'Granting...' : 'Grant Consent'}
                    </Button>
                </>
            }
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Shield size={22} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <p style={{ margin: 0, fontSize: 14, color: 'var(--text-primary)' }}>
                    This feature requires your consent before it can process your data.
                    You can withdraw consent at any time from Settings.
                </p>
            </div>

            {pending.purposes.map((code) => {
                const info = PURPOSE_INFO[code] || { name: code, description: '' };
                return (
                    <div key={code} style={cardStyle}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            <CheckCircle size={16} style={{ color: 'var(--green)' }} />
                            <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
                                {info.name}
                            </span>
                        </div>
                        {info.description && (
                            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', paddingLeft: 24 }}>
                                {info.description}
                            </p>
                        )}
                    </div>
                );
            })}

            {error && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    marginTop: 12, padding: 10, borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(239,68,68,0.1)', color: 'var(--red)', fontSize: 13,
                }}>
                    <AlertTriangle size={16} />
                    {error}
                </div>
            )}
        </Modal>
    );
}
