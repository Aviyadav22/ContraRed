import { useState, type CSSProperties } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getConsentStatus, grantConsent, withdrawConsent,
    getConsentHistory, getConsentReceipts, getCurrentPrivacyPolicy,
    type ConsentStatus, type ConsentEvent, type ConsentReceipt,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Badge } from '@/components/ui';
import { Modal } from '@/components/ui/Modal';
import { Shield, Download, Clock, AlertTriangle, Check, ChevronDown, ChevronUp } from 'lucide-react';

const sectionStyle: CSSProperties = {
    marginBottom: 32,
};

const purposeCardStyle: CSSProperties = {
    padding: 20,
    borderRadius: 12,
    border: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)',
    marginBottom: 12,
    transition: 'border-color 0.2s',
};

const toggleStyle = (active: boolean): CSSProperties => ({
    width: 48,
    height: 26,
    borderRadius: 13,
    backgroundColor: active ? 'var(--accent)' : 'var(--border)',
    position: 'relative',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    flexShrink: 0,
});

const toggleDotStyle = (active: boolean): CSSProperties => ({
    width: 20,
    height: 20,
    borderRadius: '50%',
    backgroundColor: '#fff',
    position: 'absolute',
    top: 3,
    left: active ? 25 : 3,
    transition: 'left 0.2s',
    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
});

const chipStyle: CSSProperties = {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 6,
    fontSize: 11,
    fontWeight: 500,
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-muted)',
    marginRight: 6,
    marginBottom: 4,
};

export default function ConsentPreferences() {
    const queryClient = useQueryClient();
    const [expandedPurpose, setExpandedPurpose] = useState<string | null>(null);
    const [showHistory, setShowHistory] = useState(false);
    const [showPolicy, setShowPolicy] = useState(false);
    const [showWithdrawAll, setShowWithdrawAll] = useState(false);

    const { data: consentStatus, isLoading } = useQuery<ConsentStatus>({
        queryKey: ['consent-status'],
        queryFn: getConsentStatus,
    });

    const { data: history } = useQuery<ConsentEvent[]>({
        queryKey: ['consent-history'],
        queryFn: () => getConsentHistory(50, 0),
        enabled: showHistory,
    });

    const { data: receipts } = useQuery<ConsentReceipt[]>({
        queryKey: ['consent-receipts'],
        queryFn: getConsentReceipts,
    });

    const { data: policy } = useQuery({
        queryKey: ['privacy-policy'],
        queryFn: () => getCurrentPrivacyPolicy(),
        enabled: showPolicy,
    });

    const grantMutation = useMutation({
        mutationFn: (codes: string[]) => grantConsent(codes),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['consent-status'] }),
    });

    const withdrawMutation = useMutation({
        mutationFn: (codes: string[]) => withdrawConsent(codes),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['consent-status'] }),
    });

    const handleToggle = (code: string, currentlyGranted: boolean, isRequired: boolean) => {
        if (isRequired) return; // Can't toggle required purposes
        if (currentlyGranted) {
            withdrawMutation.mutate([code]);
        } else {
            grantMutation.mutate([code]);
        }
    };

    const handleWithdrawAll = () => {
        if (!consentStatus) return;
        const optionalGranted = consentStatus.purposes
            .filter(p => !p.is_required && p.granted)
            .map(p => p.code);
        if (optionalGranted.length > 0) {
            withdrawMutation.mutate(optionalGranted);
        }
        setShowWithdrawAll(false);
    };

    if (isLoading) {
        return (
            <AppLayout>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
                    <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                </div>
            </AppLayout>
        );
    }

    return (
        <AppLayout>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32 }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Shield size={24} style={{ color: 'var(--accent)' }} />
                        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Privacy Settings</h1>
                    </div>
                    <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 8, marginBottom: 0 }}>
                        Manage how ContraRed processes your data. Under India's DPDP Act, you have the right to control each purpose independently.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                    <Button variant="ghost" size="sm" onClick={() => setShowPolicy(true)}>
                        View Privacy Policy
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setShowHistory(!showHistory)}>
                        <Clock size={14} /> History
                    </Button>
                </div>
            </div>

            {/* Consent Purposes */}
            <div style={sectionStyle}>
                <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                    Data Processing Purposes
                </h2>

                {consentStatus?.purposes.map((purpose) => {
                    const isExpanded = expandedPurpose === purpose.code;
                    return (
                        <div key={purpose.code} style={{
                            ...purposeCardStyle,
                            borderColor: purpose.granted ? 'var(--accent)' : 'var(--border)',
                            opacity: grantMutation.isPending || withdrawMutation.isPending ? 0.7 : 1,
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                        <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                                            {purpose.name}
                                        </span>
                                        {purpose.is_required && (
                                            <Badge variant="neutral">Required</Badge>
                                        )}
                                        {purpose.granted && (
                                            <Badge variant="neutral">
                                                <Check size={10} /> Active
                                            </Badge>
                                        )}
                                    </div>
                                    <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0, maxWidth: 600 }}>
                                        {purpose.description}
                                    </p>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <button
                                        onClick={() => setExpandedPurpose(isExpanded ? null : purpose.code)}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--text-muted)' }}
                                    >
                                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                    </button>

                                    <div
                                        style={toggleStyle(purpose.granted)}
                                        onClick={() => handleToggle(purpose.code, purpose.granted, purpose.is_required)}
                                        role="switch"
                                        aria-checked={purpose.granted}
                                        aria-label={`Toggle ${purpose.name}`}
                                    >
                                        <div style={toggleDotStyle(purpose.granted)} />
                                    </div>
                                </div>
                            </div>

                            {/* Expanded details */}
                            {isExpanded && (
                                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 13 }}>
                                        <div>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 6 }}>
                                                Data Categories
                                            </span>
                                            {purpose.personal_data_categories.map(cat => (
                                                <span key={cat} style={chipStyle}>{cat}</span>
                                            ))}
                                        </div>
                                        <div>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 6 }}>
                                                Third Parties
                                            </span>
                                            {purpose.third_parties.length > 0 ? (
                                                purpose.third_parties.map(tp => (
                                                    <span key={tp} style={chipStyle}>{tp}</span>
                                                ))
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)' }}>None</span>
                                            )}
                                        </div>
                                        <div>
                                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 6 }}>
                                                Retention Period
                                            </span>
                                            <span style={{ color: 'var(--text-muted)' }}>
                                                {purpose.retention_period || 'Not specified'}
                                            </span>
                                        </div>
                                        {purpose.granted_at && (
                                            <div>
                                                <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 6 }}>
                                                    Consented On
                                                </span>
                                                <span style={{ color: 'var(--text-muted)' }}>
                                                    {new Date(purpose.granted_at).toLocaleDateString('en-IN', {
                                                        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
                                                    })}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
                <Button variant="ghost" size="sm" onClick={() => setShowWithdrawAll(true)}>
                    <AlertTriangle size={14} /> Withdraw All Optional Consents
                </Button>
                {receipts && receipts.length > 0 && (
                    <Button variant="ghost" size="sm" onClick={() => {
                        const blob = new Blob([JSON.stringify(receipts, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'consent-receipts.json';
                        a.click();
                        URL.revokeObjectURL(url);
                    }}>
                        <Download size={14} /> Download Receipts (ISO 27560)
                    </Button>
                )}
            </div>

            {/* Consent History */}
            {showHistory && (
                <div style={sectionStyle}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
                        Consent History
                    </h2>
                    {history && history.length > 0 ? (
                        <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                            {history.map((event, i) => (
                                <div key={event.id} style={{
                                    padding: '12px 16px',
                                    borderBottom: i < history.length - 1 ? '1px solid var(--border)' : 'none',
                                    display: 'flex', alignItems: 'center', gap: 12,
                                    backgroundColor: 'var(--bg-secondary)',
                                }}>
                                    <div style={{
                                        width: 8, height: 8, borderRadius: '50%',
                                        backgroundColor: event.event_type === 'granted' ? 'var(--green)' :
                                            event.event_type === 'withdrawn' ? 'var(--red)' : 'var(--text-muted)',
                                        flexShrink: 0,
                                    }} />
                                    <div style={{ flex: 1 }}>
                                        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                                            {event.event_type.replace('_', ' ').toUpperCase()}
                                        </span>
                                        {event.purpose_code && (
                                            <span style={{ ...chipStyle, marginLeft: 8 }}>{event.purpose_code}</span>
                                        )}
                                    </div>
                                    <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>
                                        {new Date(event.created_at).toLocaleDateString('en-IN', {
                                            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                                        })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>No consent events recorded yet.</p>
                    )}
                </div>
            )}

            {/* Withdraw All Modal */}
            {showWithdrawAll && (
                <Modal open={true} title="Withdraw All Optional Consents" onClose={() => setShowWithdrawAll(false)}>
                    <div style={{ padding: 24 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                            <AlertTriangle size={24} style={{ color: 'var(--red)' }} />
                            <p style={{ fontSize: 14, color: 'var(--text-primary)', margin: 0 }}>
                                This will withdraw consent for all optional purposes. AI-powered features
                                (contract analysis, drafting, risk assessment) will stop working.
                            </p>
                        </div>
                        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
                            Your account will remain active. You can re-enable any purpose at any time.
                        </p>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <Button variant="ghost" onClick={() => setShowWithdrawAll(false)}>Cancel</Button>
                            <Button variant="danger" onClick={handleWithdrawAll}>Withdraw All</Button>
                        </div>
                    </div>
                </Modal>
            )}

            {/* Privacy Policy Modal */}
            {showPolicy && (
                <Modal open={true} title="Privacy Policy" onClose={() => setShowPolicy(false)}>
                    <div style={{ padding: 24, maxHeight: '60vh', overflowY: 'auto' }}>
                        {policy ? (
                            <>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                                    <span>Version {policy.version}</span>
                                    <span>Effective: {new Date(policy.effective_from).toLocaleDateString('en-IN')}</span>
                                </div>
                                <pre style={{
                                    whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7,
                                    color: 'var(--text-primary)', fontFamily: 'inherit',
                                }}>
                                    {policy.content}
                                </pre>
                            </>
                        ) : (
                            <p style={{ color: 'var(--text-muted)' }}>Loading privacy policy...</p>
                        )}
                    </div>
                </Modal>
            )}
        </AppLayout>
    );
}
