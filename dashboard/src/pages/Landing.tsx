import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';

// ============================================================================
// SVG Icon Components
// ============================================================================

function ShieldIcon({ className = "w-6 h-6" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
        </svg>
    );
}

function SparklesIcon({ className = "w-6 h-6" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
        </svg>
    );
}

function DocumentIcon({ className = "w-6 h-6" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
    );
}

function BookOpenIcon({ className = "w-6 h-6" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
    );
}

function CheckCircleIcon({ className = "w-5 h-5" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
    );
}

function ArrowRightIcon({ className = "w-5 h-5" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>
    );
}

// ============================================================================
// Landing Page
// ============================================================================

// Download URL for the Word Add-in — set via env var during deployment
const ADDIN_DOWNLOAD_URL = import.meta.env.VITE_ADDIN_DOWNLOAD_URL || '/downloads/ContraRed-AddIn.xml';

function DownloadIcon({ className = "w-5 h-5" }: { className?: string }) {
    return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
    );
}

export default function Landing() {
    const [scrollY, setScrollY] = useState(0);

    useEffect(() => {
        const handleScroll = () => setScrollY(window.scrollY);
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden">
            {/* ============================================================ */}
            {/* NAVBAR */}
            {/* ============================================================ */}
            <nav
                className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrollY > 50
                    ? 'bg-slate-950/90 backdrop-blur-xl border-b border-white/5'
                    : 'bg-transparent'
                    }`}
            >
                <div className="max-w-7xl mx-auto px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16 lg:h-20">
                        {/* Logo */}
                        <div className="flex items-center gap-2.5">
                            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                                <DocumentIcon className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-bold tracking-tight">
                                Contra<span className="text-red-500">Red</span>
                            </span>
                        </div>

                        {/* Nav Links */}
                        <div className="hidden md:flex items-center gap-8">
                            <a href="#features" className="text-sm text-slate-400 hover:text-white transition">Features</a>
                            <a href="#how-it-works" className="text-sm text-slate-400 hover:text-white transition">How It Works</a>
                            <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition">Pricing</a>
                        </div>

                        {/* CTAs */}
                        <div className="flex items-center gap-3">
                            <Link
                                to="/login"
                                className="text-sm text-slate-300 hover:text-white transition font-medium px-4 py-2"
                            >
                                Sign In
                            </Link>
                            <Link
                                to="/register"
                                className="hidden sm:inline-flex text-sm text-slate-300 hover:text-white transition font-medium px-4 py-2"
                            >
                                Sign Up
                            </Link>
                            <a
                                href={ADDIN_DOWNLOAD_URL}
                                download
                                className="inline-flex items-center gap-1.5 text-sm font-semibold bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
                            >
                                <DownloadIcon className="w-4 h-4" />
                                Download Add-in
                            </a>
                        </div>
                    </div>
                </div>
            </nav>

            {/* ============================================================ */}
            {/* HERO SECTION */}
            {/* ============================================================ */}
            <section className="relative pt-32 pb-20 lg:pt-44 lg:pb-32">
                {/* Background effects */}
                <div className="absolute inset-0 overflow-hidden">
                    <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-blue-500/10 rounded-full blur-[120px] animate-pulse-slow" />
                    <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-red-500/8 rounded-full blur-[100px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(2,6,23,1)_70%)]" />
                </div>

                <div className="relative max-w-7xl mx-auto px-6 lg:px-8 text-center">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/20 bg-blue-500/5 mb-8 animate-fade-in">
                        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                        <span className="text-xs font-medium text-blue-300">AI-Powered Contract Intelligence</span>
                    </div>

                    {/* Headline */}
                    <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tight leading-tight animate-slide-up">
                        Review Contracts{' '}
                        <span className="bg-gradient-to-r from-blue-400 via-blue-300 to-cyan-300 bg-clip-text text-transparent">
                            10x Faster
                        </span>
                        <br />
                        <span className="text-slate-400 text-3xl sm:text-4xl lg:text-5xl font-semibold">
                            with Zero Risk of Missing Critical Clauses
                        </span>
                    </h1>

                    {/* Subheadline */}
                    <p className="mt-6 text-lg lg:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed animate-slide-up" style={{ animationDelay: '0.15s' }}>
                        ContraRed is a Microsoft Word Add-in powered by advanced AI that analyzes contracts, detects risky clauses, and generates precise redline suggestions — all while maintaining <strong className="text-slate-300">zero data retention</strong>.
                    </p>

                    {/* CTAs */}
                    <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: '0.3s' }}>
                        <a
                            href={ADDIN_DOWNLOAD_URL}
                            download
                            className="group inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold text-lg px-8 py-4 rounded-2xl shadow-xl shadow-blue-500/25 hover:shadow-blue-500/40 transition-all hover:-translate-y-0.5"
                        >
                            <DownloadIcon className="w-5 h-5" />
                            Download Word Add-in
                        </a>
                        <a
                            href="#how-it-works"
                            className="inline-flex items-center gap-2 text-slate-300 hover:text-white font-medium text-lg px-8 py-4 rounded-2xl border border-slate-700 hover:border-slate-500 bg-slate-800/50 hover:bg-slate-800 transition-all"
                        >
                            See How It Works
                        </a>
                    </div>

                    {/* Trust badges */}
                    <div className="mt-16 flex flex-wrap items-center justify-center gap-6 lg:gap-10 animate-fade-in" style={{ animationDelay: '0.5s' }}>
                        {[
                            { icon: '🔒', label: 'Zero Data Retention' },
                            { icon: '🏢', label: 'Enterprise Grade' },
                            { icon: '⚡', label: 'Real-Time Analysis' },
                            { icon: '📄', label: 'Native Word Integration' },
                        ].map(({ icon, label }) => (
                            <div key={label} className="flex items-center gap-2 text-sm text-slate-500">
                                <span className="text-lg">{icon}</span>
                                <span>{label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ============================================================ */}
            {/* FEATURES SECTION */}
            {/* ============================================================ */}
            <section id="features" className="py-24 lg:py-32 relative">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-900/50 to-transparent" />
                <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
                    {/* Section Header */}
                    <div className="text-center mb-16 lg:mb-20">
                        <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">Features</span>
                        <h2 className="mt-3 text-3xl lg:text-5xl font-bold tracking-tight">
                            Everything You Need for
                            <br />
                            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                                Smarter Contract Review
                            </span>
                        </h2>
                    </div>

                    {/* Feature Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
                        {/* Feature 1 - AI Analysis */}
                        <div className="group relative p-8 lg:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 hover:border-blue-500/30 transition-all duration-500 hover:-translate-y-1">
                            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <div className="relative">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center mb-6 ring-1 ring-blue-500/20">
                                    <SparklesIcon className="w-7 h-7 text-blue-400" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">AI-Powered Analysis</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Advanced language models perform holistic contract analysis — understanding context, not just keywords. Detects contradictions, missing clauses, and hidden risks across the entire document.
                                </p>
                                <ul className="mt-5 space-y-2">
                                    {['Holistic document review', 'Context-aware risk detection', 'Executive risk summaries'].map(item => (
                                        <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
                                            <CheckCircleIcon className="w-4 h-4 text-blue-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Feature 2 - Redlining */}
                        <div className="group relative p-8 lg:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 hover:border-red-500/30 transition-all duration-500 hover:-translate-y-1">
                            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-red-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <div className="relative">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-red-500/20 to-red-600/10 flex items-center justify-center mb-6 ring-1 ring-red-500/20">
                                    <DocumentIcon className="w-7 h-7 text-red-400" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Surgical Redlining</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Generate precise track-changes directly in Microsoft Word. Fuzzy matching ensures accurate text anchoring even when formatting differs across document versions.
                                </p>
                                <ul className="mt-5 space-y-2">
                                    {['Native Track Changes (OOXML)', 'Fuzzy text matching', 'AI-generated fix suggestions'].map(item => (
                                        <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
                                            <CheckCircleIcon className="w-4 h-4 text-red-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Feature 3 - Playbooks */}
                        <div className="group relative p-8 lg:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 hover:border-emerald-500/30 transition-all duration-500 hover:-translate-y-1">
                            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <div className="relative">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 flex items-center justify-center mb-6 ring-1 ring-emerald-500/20">
                                    <BookOpenIcon className="w-7 h-7 text-emerald-400" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Custom Playbooks</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Define your organization's contract standards with customizable rule sets. Pre-built templates for SaaS, NDA, DPA, Employment, and MSA agreements.
                                </p>
                                <ul className="mt-5 space-y-2">
                                    {['Rule-based clause detection', 'Pre-built contract templates', 'Approved language library'].map(item => (
                                        <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
                                            <CheckCircleIcon className="w-4 h-4 text-emerald-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Feature 4 - Security */}
                        <div className="group relative p-8 lg:p-10 rounded-3xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 hover:border-amber-500/30 transition-all duration-500 hover:-translate-y-1">
                            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-amber-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <div className="relative">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 flex items-center justify-center mb-6 ring-1 ring-amber-500/20">
                                    <ShieldIcon className="w-7 h-7 text-amber-400" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Enterprise Security</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Zero data retention ensures your documents are never stored — processed in RAM only. Full audit trail, JWT authentication, and multi-tenant isolation.
                                </p>
                                <ul className="mt-5 space-y-2">
                                    {['Zero data retention mode', 'Complete audit logging', 'Role-based access control'].map(item => (
                                        <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
                                            <CheckCircleIcon className="w-4 h-4 text-amber-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============================================================ */}
            {/* HOW IT WORKS SECTION */}
            {/* ============================================================ */}
            <section id="how-it-works" className="py-24 lg:py-32 relative">
                <div className="max-w-7xl mx-auto px-6 lg:px-8">
                    {/* Section Header */}
                    <div className="text-center mb-16 lg:mb-20">
                        <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">How It Works</span>
                        <h2 className="mt-3 text-3xl lg:text-5xl font-bold tracking-tight">
                            Three Steps to{' '}
                            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                                Bulletproof Contracts
                            </span>
                        </h2>
                    </div>

                    {/* Steps */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
                        {[
                            {
                                step: '01',
                                title: 'Open in Word',
                                description: 'Install the ContraRed Add-in and open any contract in Microsoft Word. Select a playbook that matches your contract type.',
                                gradient: 'from-blue-500 to-blue-600',
                                glow: 'shadow-blue-500/20',
                            },
                            {
                                step: '02',
                                title: 'AI Analyzes',
                                description: 'Our AI engine scans every clause against your playbook rules, identifies risks, contradictions, and missing protections in seconds.',
                                gradient: 'from-violet-500 to-purple-600',
                                glow: 'shadow-violet-500/20',
                            },
                            {
                                step: '03',
                                title: 'Review & Redline',
                                description: 'Review flagged issues with risk levels (RED/YELLOW/GREEN), accept AI-suggested fixes, and apply track changes directly in your document.',
                                gradient: 'from-emerald-500 to-green-600',
                                glow: 'shadow-emerald-500/20',
                            },
                        ].map(({ step, title, description, gradient, glow }) => (
                            <div key={step} className="relative text-center group">
                                {/* Step number */}
                                <div className={`inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br ${gradient} items-center justify-center shadow-xl ${glow} mb-6 group-hover:scale-110 transition-transform duration-300`}>
                                    <span className="text-xl font-bold text-white">{step}</span>
                                </div>
                                <h3 className="text-xl font-bold mb-3">{title}</h3>
                                <p className="text-slate-400 leading-relaxed">{description}</p>
                            </div>
                        ))}
                    </div>

                    {/* Connector lines (desktop only) */}
                    <div className="hidden md:flex justify-center mt-[-180px] mb-[120px] pointer-events-none">
                        <div className="flex items-center gap-0 w-[60%]">
                            <div className="flex-1 h-px bg-gradient-to-r from-blue-500/50 to-violet-500/50" />
                            <div className="flex-1 h-px bg-gradient-to-r from-violet-500/50 to-emerald-500/50" />
                        </div>
                    </div>
                </div>
            </section>

            {/* ============================================================ */}
            {/* PRICING SECTION */}
            {/* ============================================================ */}
            <section id="pricing" className="py-24 lg:py-32 relative">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-950/20 to-transparent" />
                <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
                    {/* Section Header */}
                    <div className="text-center mb-16 lg:mb-20">
                        <span className="text-sm font-semibold text-blue-400 uppercase tracking-wider">Pricing</span>
                        <h2 className="mt-3 text-3xl lg:text-5xl font-bold tracking-tight">
                            Simple, Transparent Pricing
                        </h2>
                        <p className="mt-4 text-lg text-slate-400 max-w-xl mx-auto">
                            Start free, upgrade when you need more power.
                        </p>
                    </div>

                    {/* Pricing Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 max-w-5xl mx-auto">
                        {/* Free Tier */}
                        <div className="relative p-8 rounded-3xl bg-slate-800/60 border border-slate-700/50 flex flex-col">
                            <div className="mb-6">
                                <h3 className="text-lg font-semibold text-slate-200">Free</h3>
                                <div className="mt-3 flex items-baseline gap-1">
                                    <span className="text-4xl font-extrabold">$0</span>
                                    <span className="text-slate-500">/month</span>
                                </div>
                                <p className="mt-2 text-sm text-slate-400">Perfect for trying out ContraRed</p>
                            </div>
                            <ul className="space-y-3 mb-8 flex-1">
                                {[
                                    '5 contract scans/month',
                                    'Basic AI analysis',
                                    'Public playbooks',
                                    'Community support',
                                ].map(item => (
                                    <li key={item} className="flex items-start gap-2 text-sm text-slate-300">
                                        <CheckCircleIcon className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                                        {item}
                                    </li>
                                ))}
                            </ul>
                            <Link
                                to="/register"
                                className="w-full text-center py-3 px-4 rounded-xl border border-slate-600 hover:border-slate-400 text-slate-300 hover:text-white font-medium transition-all"
                            >
                                Get Started
                            </Link>
                        </div>

                        {/* Pro Tier - Featured */}
                        <div className="relative p-8 rounded-3xl bg-gradient-to-b from-blue-900/40 to-slate-800/80 border border-blue-500/30 flex flex-col ring-1 ring-blue-500/20 shadow-xl shadow-blue-500/10">
                            {/* Popular badge */}
                            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                                <span className="bg-gradient-to-r from-blue-600 to-blue-500 text-white text-xs font-bold px-4 py-1 rounded-full shadow-lg">
                                    MOST POPULAR
                                </span>
                            </div>
                            <div className="mb-6">
                                <h3 className="text-lg font-semibold text-blue-300">Pro</h3>
                                <div className="mt-3 flex items-baseline gap-1">
                                    <span className="text-4xl font-extrabold">$49</span>
                                    <span className="text-slate-500">/month</span>
                                </div>
                                <p className="mt-2 text-sm text-slate-400">For teams that review contracts daily</p>
                            </div>
                            <ul className="space-y-3 mb-8 flex-1">
                                {[
                                    'Unlimited contract scans',
                                    'Full AI analysis + redlining',
                                    'Custom playbooks',
                                    'API access',
                                    'Priority support',
                                ].map(item => (
                                    <li key={item} className="flex items-start gap-2 text-sm text-slate-200">
                                        <CheckCircleIcon className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                                        {item}
                                    </li>
                                ))}
                            </ul>
                            <Link
                                to="/register"
                                className="w-full text-center py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold shadow-lg shadow-blue-500/25 transition-all"
                            >
                                Start Pro Trial
                            </Link>
                        </div>

                        {/* Enterprise Tier */}
                        <div className="relative p-8 rounded-3xl bg-slate-800/60 border border-slate-700/50 flex flex-col">
                            <div className="mb-6">
                                <h3 className="text-lg font-semibold text-slate-200">Enterprise</h3>
                                <div className="mt-3 flex items-baseline gap-1">
                                    <span className="text-4xl font-extrabold">Custom</span>
                                </div>
                                <p className="mt-2 text-sm text-slate-400">For large legal teams & firms</p>
                            </div>
                            <ul className="space-y-3 mb-8 flex-1">
                                {[
                                    '500+ scans included',
                                    'SSO integration (Azure AD, Okta)',
                                    'Custom playbook development',
                                    'Dedicated support & SLA',
                                    'On-premise deployment option',
                                    'Full audit & compliance logs',
                                ].map(item => (
                                    <li key={item} className="flex items-start gap-2 text-sm text-slate-300">
                                        <CheckCircleIcon className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                                        {item}
                                    </li>
                                ))}
                            </ul>
                            <a
                                href="mailto:hello@contrared.ai"
                                className="w-full text-center py-3 px-4 rounded-xl border border-slate-600 hover:border-slate-400 text-slate-300 hover:text-white font-medium transition-all"
                            >
                                Contact Sales
                            </a>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============================================================ */}
            {/* CTA SECTION */}
            {/* ============================================================ */}
            <section className="py-24 lg:py-32">
                <div className="max-w-4xl mx-auto px-6 lg:px-8 text-center">
                    <div className="relative p-12 lg:p-16 rounded-3xl overflow-hidden">
                        {/* Background */}
                        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl" />
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.1),transparent_50%)]" />

                        <div className="relative">
                            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                                Ready to Transform Your Contract Review?
                            </h2>
                            <p className="text-blue-100/80 text-lg mb-8 max-w-xl mx-auto">
                                Join legal teams who are reviewing contracts 10x faster with AI-powered precision and zero data retention.
                            </p>
                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                <a
                                    href={ADDIN_DOWNLOAD_URL}
                                    download
                                    className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold text-lg px-8 py-4 rounded-2xl hover:bg-blue-50 transition-all shadow-xl hover:-translate-y-0.5"
                                >
                                    <DownloadIcon className="w-5 h-5" />
                                    Download Add-in
                                </a>
                                <Link
                                    to="/register"
                                    className="inline-flex items-center gap-2 text-white font-medium text-lg px-8 py-4 rounded-2xl border border-white/30 hover:border-white/60 transition-all hover:-translate-y-0.5"
                                >
                                    Create Free Account
                                    <ArrowRightIcon className="w-5 h-5" />
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ============================================================ */}
            {/* FOOTER */}
            {/* ============================================================ */}
            <footer className="border-t border-slate-800 py-12 lg:py-16">
                <div className="max-w-7xl mx-auto px-6 lg:px-8">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-8 lg:gap-12">
                        {/* Brand */}
                        <div className="md:col-span-2">
                            <div className="flex items-center gap-2.5 mb-4">
                                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center">
                                    <DocumentIcon className="w-4 h-4 text-white" />
                                </div>
                                <span className="text-lg font-bold">
                                    Contra<span className="text-red-500">Red</span>
                                </span>
                            </div>
                            <p className="text-slate-500 text-sm max-w-sm leading-relaxed">
                                AI-powered contract redlining platform for legal teams who demand precision, security, and efficiency.
                            </p>
                        </div>

                        {/* Product Links */}
                        <div>
                            <h4 className="text-sm font-semibold text-slate-200 mb-4">Product</h4>
                            <ul className="space-y-2.5">
                                {[
                                    { label: 'Features', href: '#features' },
                                    { label: 'Pricing', href: '#pricing' },
                                    { label: 'How It Works', href: '#how-it-works' },
                                ].map(({ label, href }) => (
                                    <li key={label}>
                                        <a href={href} className="text-sm text-slate-500 hover:text-slate-300 transition">{label}</a>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Company Links */}
                        <div>
                            <h4 className="text-sm font-semibold text-slate-200 mb-4">Company</h4>
                            <ul className="space-y-2.5">
                                {[
                                    { label: 'Sign In', href: '/login' },
                                    { label: 'Sign Up', href: '/register' },
                                    { label: 'Contact Sales', href: 'mailto:hello@contrared.ai' },
                                ].map(({ label, href }) => (
                                    <li key={label}>
                                        <a href={href} className="text-sm text-slate-500 hover:text-slate-300 transition">{label}</a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Bottom Bar */}
                    <div className="mt-12 pt-8 border-t border-slate-800/50 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <p className="text-xs text-slate-600">
                            &copy; {new Date().getFullYear()} ContraRed. All rights reserved.
                        </p>
                        <div className="flex items-center gap-6">
                            <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition">Privacy Policy</a>
                            <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition">Terms of Service</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
