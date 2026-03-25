import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const inputStyle = {
        border: '1px solid #E8E5E0',
        color: '#1A1A19',
        background: '#FFFFFF',
    };

    const inputFocus = 'focus:ring-2 focus:border-transparent transition';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
            const response = await fetch(`${API_URL}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
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
                        <p className="text-[13px]" style={{ color: '#8A8885' }}>Reset your password</p>
                    </div>

                    {submitted ? (
                        <div className="text-center py-4">
                            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: '#F0F9F4' }}>
                                <svg width="24" height="24" fill="none" stroke="#1A7A4A" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <h3 className="text-base font-semibold mb-2" style={{ color: '#1A1A19' }}>Check your email</h3>
                            <p className="text-[13px] mb-6" style={{ color: '#8A8885' }}>
                                If an account exists for <strong>{email}</strong>, we've sent password reset instructions.
                            </p>
                            <Link
                                to="/login"
                                className="inline-block text-[13px] font-medium"
                                style={{ color: '#C0392B' }}
                            >
                                Back to Sign In
                            </Link>
                        </div>
                    ) : (
                        <>
                            <p className="text-[13px] mb-5" style={{ color: '#8A8885' }}>
                                Enter your email address and we'll send you instructions to reset your password.
                            </p>

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
                                        'Send Reset Instructions'
                                    )}
                                </button>
                            </form>

                            <div className="mt-6 text-center">
                                <Link to="/login" className="text-[13px] font-medium" style={{ color: '#C0392B' }}>
                                    Back to Sign In
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
