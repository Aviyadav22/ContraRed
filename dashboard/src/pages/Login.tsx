import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { login } from '@/api/client';

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
                    <div className="text-center mb-8">
                        <Link to="/" className="inline-block mb-4">
                            <img src="/logo.png" alt="ContraRed" className="h-7 mx-auto" />
                        </Link>
                        <p className="text-[13px]" style={{ color: '#8A8885' }}>Sign in to your account</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="email" className="block text-[13px] font-medium mb-1.5" style={{ color: '#6B6966' }}>
                                Email
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
                                maxLength={128}
                            />
                        </div>

                        <div className="flex justify-end -mt-2">
                            <Link to="/forgot-password" className="text-[13px] font-medium" style={{ color: '#C0392B' }}>
                                Forgot your password?
                            </Link>
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
                                'Sign In'
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-[13px]" style={{ color: '#8A8885' }}>
                            Don't have an account?{' '}
                            <Link to="/register" className="font-medium" style={{ color: '#C0392B' }}>
                                Create one
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
