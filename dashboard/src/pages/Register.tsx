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

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="w-full max-w-md">
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
                    {/* Logo */}
                    <div className="text-center mb-8">
                        <Link to="/" className="inline-block mb-4">
                            <img src="/logo.png" alt="ContraRed" className="h-8 mx-auto" />
                        </Link>
                        <p className="text-slate-500 text-sm">Create your account</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Full Name
                            </label>
                            <input
                                id="name"
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-slate-900 focus:border-transparent transition placeholder:text-slate-400"
                                placeholder="John Doe"
                                required
                            />
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Work Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-slate-900 focus:border-transparent transition placeholder:text-slate-400"
                                placeholder="you@company.com"
                                required
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-slate-900 focus:border-transparent transition placeholder:text-slate-400"
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-1.5">
                                Confirm Password
                            </label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-slate-900 focus:border-transparent transition placeholder:text-slate-400"
                                placeholder="••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        {error && (
                            <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white font-medium text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
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
                        <p className="text-sm text-slate-500">
                            Already have an account?{' '}
                            <Link to="/login" className="text-slate-900 hover:text-slate-700 font-medium">
                                Sign In
                            </Link>
                        </p>
                    </div>

                    {/* Terms */}
                    <p className="mt-4 text-xs text-slate-400 text-center leading-relaxed">
                        By creating an account, you agree to our{' '}
                        <a href="#" className="underline hover:text-slate-600">Terms of Service</a>{' '}
                        and{' '}
                        <a href="#" className="underline hover:text-slate-600">Privacy Policy</a>.
                    </p>
                </div>
            </div>
        </div>
    );
}
