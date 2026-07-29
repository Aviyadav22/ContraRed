/**
 * DPDP Act Consent Banner
 *
 * Non-blocking bottom banner shown when:
 *   - User has not yet made a choice for optional AI purposes
 *   - Privacy policy version has changed since last acceptance
 *
 * Not a cookie banner (ContraRed uses HttpOnly auth cookies, no tracking).
 * This is a data processing consent notice per DPDP Act Section 5/6.
 */

import { useState, type CSSProperties } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConsentStatus, grantConsent, type ConsentStatus } from '@/api/client';
import { Button } from '@/components/ui';
import { Shield, X } from 'lucide-react';

const bannerStyle: CSSProperties = {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'var(--bg-primary)',
    borderTop: '2px solid var(--accent)',
    padding: '16px 24px',
    zIndex: 1000,
    boxShadow: '0 -4px 20px rgba(0,0,0,0.15)',
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    flexWrap: 'wrap',
};

export function ConsentBanner() {
    const queryClient = useQueryClient();
    const [dismissed, setDismissed] = useState(false);

    const { data: consentStatus } = useQuery<ConsentStatus>({
        queryKey: ['consent-status'],
        queryFn: getConsentStatus,
        staleTime: 60000,
        retry: false,
    });

    const ungrantedAI = consentStatus?.purposes.filter(p =>
            !p.is_required &&
            !p.granted &&
            !p.withdrawn_at &&
            ['contract_analysis', 'ai_drafting', 'risk_assessment'].includes(p.code)
        ) || [];
    const visible = Boolean(
        consentStatus &&
        (!consentStatus.has_consent_record || ungrantedAI.length > 0)
    );

    const grantMutation = useMutation({
        mutationFn: (codes: string[]) => grantConsent(codes),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['consent-status'] });
            setDismissed(true);
        },
    });

    if (!visible || dismissed) return null;

    return (
        <div style={bannerStyle}>
            <Shield size={20} style={{ color: 'var(--accent)', flexShrink: 0 }} />

            <div style={{ flex: 1, minWidth: 300 }}>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                    Enable AI-powered contract analysis
                </p>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
                    ContraRed uses AI services to analyze your contracts. Your consent is required under India's DPDP Act.
                    {' '}<a href="/settings/privacy" style={{ color: 'var(--accent)', textDecoration: 'none' }}>
                        Manage all preferences
                    </a>
                </p>
            </div>

            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDismissed(true)}
                >
                    Not Now
                </Button>
                <Button
                    variant="primary"
                    size="sm"
                    onClick={() => grantMutation.mutate(ungrantedAI.map(p => p.code))}
                    disabled={grantMutation.isPending}
                >
                    {grantMutation.isPending ? 'Enabling...' : 'Enable AI Features'}
                </Button>
            </div>

            <button
                onClick={() => setDismissed(true)}
                style={{
                    position: 'absolute', top: 8, right: 8,
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', padding: 4,
                }}
                aria-label="Dismiss"
            >
                <X size={16} />
            </button>
        </div>
    );
}
