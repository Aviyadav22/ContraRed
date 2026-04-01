import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '@/api/client';
import { AuthLayout } from '@/components/AuthLayout';
import { TextInput } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export default function Register() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        // Validate password strength (must match backend requirements)
        const passwordErrors: string[] = [];
        if (password.length < 8) passwordErrors.push('at least 8 characters');
        if (!/[A-Z]/.test(password)) passwordErrors.push('an uppercase letter');
        if (!/[a-z]/.test(password)) passwordErrors.push('a lowercase letter');
        if (!/\d/.test(password)) passwordErrors.push('a digit');
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) passwordErrors.push('a special character');

        if (passwordErrors.length > 0) {
            setError(`Password must contain ${passwordErrors.join(', ')}`);
            return;
        }

        setLoading(true);

        try {
            await register(name, email, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
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
                Create your account
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 32 }}>
                Start analyzing contracts in minutes
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <TextInput
                    label="Full Name"
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="John Doe"
                    required
                    maxLength={100}
                />

                <TextInput
                    label="Work Email"
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
                    placeholder="Min 8 chars, uppercase, number, symbol"
                    required
                    minLength={8}
                />

                <TextInput
                    label="Confirm Password"
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your password"
                    required
                    minLength={8}
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
                    Create Account
                </Button>
            </form>

            <p style={{ marginTop: 24, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                Already have an account?{' '}
                <Link
                    to="/login"
                    style={{ fontWeight: 500, color: 'var(--accent-text)', textDecoration: 'none' }}
                >
                    Sign In
                </Link>
            </p>

            <p style={{ marginTop: 16, textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                By creating an account, you agree to our{' '}
                <a
                    href="https://contrared-addin.netlify.app/terms.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--text-secondary)', textDecoration: 'underline' }}
                >
                    Terms of Service
                </a>{' '}
                and{' '}
                <a
                    href="https://contrared-addin.netlify.app/privacy.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--text-secondary)', textDecoration: 'underline' }}
                >
                    Privacy Policy
                </a>.
            </p>
        </AuthLayout>
    );
}
