import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '@/api/client';

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

    const inputStyle = {
        border: '1px solid #E8E5E0',
        color: '#1A1A19',
        background: '#FFFFFF',
    };

    const inputFocus = 'focus:ring-2 focus:border-transparent transition';

    return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: '#FAFAF9' }}>
            <div className="w-full max-w-md">
                <div
                    className="rounded-2xl p-8"
                    style={{ background: '#FFFFFF', border: '1px solid #E8E5E0', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}
                >
                    {/* Logo */}
                    <div className="text-center mb-8">
                        <Link to="/" className="inline-block mb-4">
                            <img src="/logo.png" alt="ContraRed" className="h-7 mx-auto" />
                        </Link>
                        <p className="text-[13px]" style={{ color: '#8A8885' }}>Create your account</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="name" className="block text-[13px] font-medium mb-1.5" style={{ color: '#6B6966' }}>
                                Full Name
                            </label>
                            <input
                                id="name"
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className={`w-full px-4 py-2.5 rounded-lg text-sm ${inputFocus}`}
                                style={{ ...inputStyle, '--tw-ring-color': '#C0392B40' } as React.CSSProperties}
                                placeholder="John Doe"
                                required
                                maxLength={100}
                            />
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-[13px] font-medium mb-1.5" style={{ color: '#6B6966' }}>
                                Work Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className={`w-full px-4 py-2.5 rounded-lg text-sm ${inputFocus}`}
                                style={{ ...inputStyle, '--tw-ring-color': '#C0392B40' } as React.CSSProperties}
                                placeholder="you@company.com"
                                required
                                maxLength={255}
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-[13px] font-medium mb-1.5" style={{ color: '#6B6966' }}>
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className={`w-full px-4 py-2.5 rounded-lg text-sm ${inputFocus}`}
                                style={{ ...inputStyle, '--tw-ring-color': '#C0392B40' } as React.CSSProperties}
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-[13px] font-medium mb-1.5" style={{ color: '#6B6966' }}>
                                Confirm Password
                            </label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className={`w-full px-4 py-2.5 rounded-lg text-sm ${inputFocus}`}
                                style={{ ...inputStyle, '--tw-ring-color': '#C0392B40' } as React.CSSProperties}
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        {error && (
                            <div className="p-3 rounded-lg text-sm" style={{ background: '#FDF2F1', color: '#C0392B' }}>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 px-4 font-medium text-sm rounded-lg transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 bg-[#C0392B] text-white hover:bg-[#A93226]"
                        >
                            {loading ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                'Create Account'
                            )}
                        </button>
                    </form>

                    {/* Sign In link */}
                    <div className="mt-6 text-center">
                        <p className="text-[13px]" style={{ color: '#8A8885' }}>
                            Already have an account?{' '}
                            <Link to="/login" className="font-medium" style={{ color: '#C0392B' }}>
                                Sign In
                            </Link>
                        </p>
                    </div>

                    {/* Terms */}
                    <p className="mt-4 text-xs text-center leading-relaxed" style={{ color: '#A09D98' }}>
                        By creating an account, you agree to our{' '}
                        <Link to="/terms" className="underline" style={{ color: '#8A8885' }}>Terms of Service</Link>{' '}
                        and{' '}
                        <Link to="/privacy" className="underline" style={{ color: '#8A8885' }}>Privacy Policy</Link>.
                    </p>
                </div>
            </div>
        </div>
    );
}
