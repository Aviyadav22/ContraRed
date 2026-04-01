import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login } from '@/api/client';
import { AuthLayout } from '@/components/AuthLayout';
import { TextInput } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(email, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
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
                Sign in to ContraRed
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 32 }}>
                Enter your credentials to continue
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
                    maxLength={255}
                />

                <TextInput
                    label="Password"
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    maxLength={128}
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: -8 }}>
                    <Link
                        to="/forgot-password"
                        style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: 'var(--accent-text)',
                            textDecoration: 'none',
                        }}
                    >
                        Forgot your password?
                    </Link>
                </div>

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
                    Sign In
                </Button>
            </form>

            <p style={{ marginTop: 24, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                Don't have an account?{' '}
                <Link
                    to="/register"
                    style={{ fontWeight: 500, color: 'var(--accent-text)', textDecoration: 'none' }}
                >
                    Create one
                </Link>
            </p>
        </AuthLayout>
    );
}
