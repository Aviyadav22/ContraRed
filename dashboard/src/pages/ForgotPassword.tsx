import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api/client';
import { AuthLayout } from '@/components/AuthLayout';
import { TextInput } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { CheckCircle } from 'lucide-react';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await forgotPassword(email);
            // Always show success to prevent email enumeration
            setSubmitted(true);
        } catch (err) {
            // Still show success to prevent email enumeration
            setSubmitted(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout>
            <h1
                style={{
                    fontSize: 22,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    marginBottom: 4,
                }}
            >
                Reset your password
            </h1>

            {submitted ? (
                <div style={{ textAlign: 'center', paddingTop: 24 }}>
                    <div
                        style={{
                            width: 48,
                            height: 48,
                            borderRadius: '50%',
                            backgroundColor: 'var(--risk-low-bg)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 16px',
                        }}
                    >
                        <CheckCircle size={24} style={{ color: 'var(--risk-low)' }} />
                    </div>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
                        Check your email
                    </h3>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>
                        If an account exists for <strong style={{ color: 'var(--text-secondary)' }}>{email}</strong>, we've sent password reset instructions.
                    </p>
                    <Link
                        to="/login"
                        style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: 'var(--accent-text)',
                            textDecoration: 'none',
                        }}
                    >
                        Back to Sign In
                    </Link>
                </div>
            ) : (
                <>
                    <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 32 }}>
                        Enter your email address and we'll send you instructions to reset your password.
                    </p>

                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                        <TextInput
                            label="Email"
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@company.com"
                            required
                        />

                        {error && (
                            <div
                                style={{
                                    padding: '10px 14px',
                                    borderRadius: 'var(--radius-sm)',
                                    fontSize: 14,
                                    backgroundColor: 'var(--risk-critical-bg)',
                                    color: 'var(--risk-critical)',
                                    border: '1px solid var(--risk-critical-border)',
                                }}
                            >
                                {error}
                            </div>
                        )}

                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            loading={loading}
                            style={{ width: '100%' }}
                        >
                            Send Reset Instructions
                        </Button>
                    </form>

                    <p style={{ marginTop: 24, textAlign: 'center' }}>
                        <Link
                            to="/login"
                            style={{
                                fontSize: 13,
                                fontWeight: 500,
                                color: 'var(--accent-text)',
                                textDecoration: 'none',
                            }}
                        >
                            Back to Sign In
                        </Link>
                    </p>
                </>
            )}
        </AuthLayout>
    );
}
