import { Link } from 'react-router-dom';

const DOWNLOAD_URL = import.meta.env.VITE_ADDIN_DOWNLOAD_URL || '/Install-ContraRed.bat';

const TRUST_INDICATORS = [
    { text: 'Zero data retention', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg> },
    { text: 'Enterprise-grade security', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg> },
    { text: 'Analysis in seconds', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> },
    { text: 'Works inside Microsoft Word', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> },
];

const HOW_IT_WORKS_STEPS = [
    {
        step: '01',
        title: 'Install the Add-in',
        desc: 'Download the installer, run it, and ContraRed appears as a sidebar in Word. Takes under 60 seconds.',
    },
    {
        step: '02',
        title: 'Run the Analysis',
        desc: 'Open any contract and click "Scan Document." ContraRed reads every clause against your risk playbook.',
    },
    {
        step: '03',
        title: 'Review & Redline',
        desc: 'Review flagged clauses with explanations and suggested fixes. Accept suggestions to apply redlines directly.',
    },
];

const STATS = [
    { value: 'Fast', label: 'Analysis time' },
    { value: '100%', label: 'Clauses checked' },
    { value: 'Zero', label: 'Data retained' },
    { value: 'one-click', label: 'Install' },
];

const FEATURE_1_ITEMS = ['Color-coded severity badges (Critical, Warning, Safe)', 'Clause-by-clause risk breakdown', 'Executive-ready risk summary with counts'];
const FEATURE_2_ITEMS = ['Surgical clause-level replacements', 'Track-changes style visual diff', 'One-click accept or reject each suggestion'];
const FEATURE_3_ITEMS = ['Create unlimited custom rule sets', 'Switch playbooks per deal type (MSA, NDA, SaaS)', 'Enforce organization-wide compliance standards'];
const FEATURE_4_ITEMS = ['One-click installation via batch script', 'Works with .docx and .doc formats', 'Custom playbooks for different deal types'];

export default function Landing() {
    return (
        <div className="font-['Inter',system-ui,sans-serif] text-slate-900">
            {/* ================================================================
          NAVIGATION
          ================================================================ */}
            <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-white/85 border-b border-slate-200">
                <div className="max-w-7xl mx-auto px-8 h-16 flex items-center justify-between">
                    <img src="/logo.png" alt="ContraRed" className="h-20" />
                    <div className="flex items-center gap-4 md:gap-10">
                        <a href="#features" className="hidden md:block text-sm font-medium text-slate-600 no-underline hover:text-slate-900">Features</a>
                        <a href="#how-it-works" className="hidden md:block text-sm font-medium text-slate-600 no-underline hover:text-slate-900">How It Works</a>
                        <a href="#contact" className="hidden md:block text-sm font-medium text-slate-600 no-underline hover:text-slate-900">Contact</a>
                        <Link
                            to="/login"
                            className="text-sm font-semibold text-white bg-slate-900 px-6 py-2.5 rounded-lg no-underline hover:bg-slate-800 transition-colors"
                        >
                            Sign In
                        </Link>
                    </div>
                </div>
            </nav>

            {/* ================================================================
          HERO SECTION
          ================================================================ */}
            <section className="pt-24 pb-20 text-center bg-white relative overflow-hidden">
                {/* Subtle grid background */}
                <div
                    className="absolute inset-0 opacity-40"
                    style={{
                        backgroundImage: 'radial-gradient(#e2e8f0 1px, transparent 1px)',
                        backgroundSize: '24px 24px',
                    }}
                />

                <div className="relative max-w-[900px] mx-auto px-8">
                    {/* Headline */}
                    <h1 className="text-4xl md:text-7xl font-extrabold tracking-tight leading-none mb-6 text-slate-900">
                        Catch liabilities
                        <br />
                        <span className="text-red-600">Before</span> you sign
                    </h1>

                    {/* Subtitle */}
                    <p className="text-xl leading-relaxed text-slate-500 mx-auto mb-10 max-w-[620px]">
                        ContraRed detects risky clauses, generates precise redline suggestions,
                        and produces executive risk summaries — all inside Microsoft Word.
                    </p>

                    {/* CTA Buttons */}
                    <div className="flex justify-center gap-4">
                        <a
                            href={DOWNLOAD_URL}
                            className="inline-flex items-center gap-2.5 bg-slate-900 text-white px-8 py-3.5 rounded-lg text-[15px] font-semibold no-underline border border-slate-900 hover:bg-slate-800 transition-colors"
                        >
                            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                            Download Installer
                        </a>
                        <a
                            href="#features"
                            className="inline-flex items-center gap-2 bg-white text-slate-900 px-8 py-3.5 rounded-lg text-[15px] font-semibold no-underline border border-slate-200 hover:bg-slate-50 transition-colors"
                        >
                            See How It Works &rarr;
                        </a>
                    </div>
                </div>

                {/* Hero Video */}
                <div className="max-w-[1100px] mx-auto mt-16 px-8">
                    <div className="rounded-2xl overflow-hidden shadow-2xl border border-slate-200 bg-[#0a0a0a]">
                        <video
                            autoPlay
                            loop
                            muted
                            playsInline
                            className="w-full block"
                        >
                            <source src="/demo-video.mp4" type="video/mp4" />
                        </video>
                    </div>
                </div>
            </section>

            {/* ================================================================
          TRUST INDICATORS
          ================================================================ */}
            <section className="bg-slate-50 border-y border-slate-200">
                <div className="max-w-[1100px] mx-auto px-8 py-12 flex justify-center gap-6 md:gap-16 flex-wrap">
                    {TRUST_INDICATORS.map((item) => (
                        <div key={item.text} className="flex items-center gap-2.5">
                            {item.icon}
                            <span className="text-sm font-medium text-slate-600">{item.text}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ================================================================
          FEATURES — Alternating Image/Text Sections
          ================================================================ */}
            <section id="features" className="pt-28 pb-10 bg-white">
                <div className="max-w-[1100px] mx-auto px-8 text-center mb-20">
                    <p className="text-[13px] font-semibold text-red-600 tracking-widest uppercase mb-4">
                        CAPABILITIES
                    </p>
                    <h2 className="text-5xl font-extrabold tracking-tight mb-4 text-slate-900">
                        Every clause. Every risk. Every fix.
                    </h2>
                    <p className="text-lg text-slate-500 max-w-[600px] mx-auto">
                        Purpose-built for legal teams who review dozens of contracts every week.
                    </p>
                </div>

                {/* Feature 1: Contract Analysis */}
                <div className="max-w-[1200px] mx-auto mb-28 px-8 flex flex-col md:flex-row items-center gap-8 md:gap-20">
                    <div className="flex-1">
                        <div className="inline-flex items-center gap-2 bg-red-500/[0.08] text-red-600 px-3.5 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider mb-5">
                            Risk Detection
                        </div>
                        <h3 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
                            Full contract risk summary in seconds
                        </h3>
                        <p className="text-base leading-relaxed text-slate-500 mb-6">
                            Every clause is analyzed against your playbook rules. Critical liabilities like unlimited indemnification,
                            auto-renewal traps, and weak security guarantees are flagged instantly — with severity scoring and clause-level citations.
                        </p>
                        <ul className="list-none p-0 flex flex-col gap-3">
                            {FEATURE_1_ITEMS.map((item) => (
                                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-700">
                                    <svg width="18" height="18" fill="none" stroke="#22c55e" viewBox="0 0 24 24" className="shrink-0 mt-0.5"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="flex-[1.2]">
                        <div className="rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                            <img
                                src="/feature-risk-summary.png"
                                alt="Risk Summary"
                                className="w-full block"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                        </div>
                    </div>
                </div>

                {/* Feature 2: Surgical Redlining — reversed layout */}
                <div className="max-w-[1200px] mx-auto mb-28 px-8 flex flex-col md:flex-row-reverse items-center gap-8 md:gap-20">
                    <div className="flex-1">
                        <div className="inline-flex items-center gap-2 bg-blue-600/[0.08] text-blue-600 px-3.5 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider mb-5">
                            Precision Redlining
                        </div>
                        <h3 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
                            Detect, highlight, and fix — in one click
                        </h3>
                        <p className="text-base leading-relaxed text-slate-500 mb-6">
                            Each risky clause comes with a precise replacement suggestion, drafted in legal language.
                            Red strikethrough marks the original, blue text shows the recommended fix — just like track changes.
                        </p>
                        <ul className="list-none p-0 flex flex-col gap-3">
                            {FEATURE_2_ITEMS.map((item) => (
                                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-700">
                                    <svg width="18" height="18" fill="none" stroke="#2563eb" viewBox="0 0 24 24" className="shrink-0 mt-0.5"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="flex-[1.2]">
                        <div className="rounded-2xl overflow-hidden shadow-2xl border border-slate-200">
                            <img
                                src="/feature-redline.png"
                                alt="Precision Redlining"
                                className="w-full block"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                        </div>
                    </div>
                </div>


                {/* Feature 3: Custom Playbooks */}
                <div className="max-w-[1200px] mx-auto mb-28 px-8 flex flex-col md:flex-row items-center gap-8 md:gap-20">
                    <div className="flex-1">
                        <div className="inline-flex items-center gap-2 bg-green-500/[0.08] text-green-600 px-3.5 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider mb-5">
                            Custom Playbooks
                        </div>
                        <h3 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
                            Your rules. Your risk framework.
                        </h3>
                        <p className="text-base leading-relaxed text-slate-500 mb-6">
                            Define exactly what matters to your organization. Create custom playbooks with specific rules for
                            indemnification caps, IP ownership, data handling, termination clauses, and anything else your
                            legal team needs to enforce — then select the right playbook for each deal type.
                        </p>
                        <ul className="list-none p-0 flex flex-col gap-3">
                            {FEATURE_3_ITEMS.map((item) => (
                                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-700">
                                    <svg width="18" height="18" fill="none" stroke="#16a34a" viewBox="0 0 24 24" className="shrink-0 mt-0.5"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="flex-[1.2]">
                        <div className="rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                            <img
                                src="/feature-playbook.png"
                                alt="Custom Playbooks"
                                className="w-full block"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                        </div>
                    </div>
                </div>

                {/* Feature 4: Word Integration — reversed */}
                <div className="max-w-[1200px] mx-auto mb-20 px-8 flex flex-col md:flex-row-reverse items-center gap-8 md:gap-20">
                    <div className="flex-1">
                        <div className="inline-flex items-center gap-2 bg-indigo-500/[0.08] text-indigo-500 px-3.5 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider mb-5">
                            Native Integration
                        </div>
                        <h3 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
                            Lives inside Microsoft Word
                        </h3>
                        <p className="text-base leading-relaxed text-slate-500 mb-6">
                            No context-switching. No uploads. ContraRed runs as a sidebar in Microsoft Word.
                            Open a contract, click &quot;Scan Document,&quot; and get your risk report without leaving the document.
                        </p>
                        <ul className="list-none p-0 flex flex-col gap-3">
                            {FEATURE_4_ITEMS.map((item) => (
                                <li key={item} className="flex items-start gap-2.5 text-sm text-slate-700">
                                    <svg width="18" height="18" fill="none" stroke="#6366f1" viewBox="0 0 24 24" className="shrink-0 mt-0.5"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="flex-[1.2]">
                        <div className="rounded-2xl overflow-hidden shadow-2xl border border-slate-200">
                            <img
                                src="/feature-word-addin.png"
                                alt="Word Add-in"
                                className="w-full block"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* ================================================================
          HOW IT WORKS
          ================================================================ */}
            <section
                id="how-it-works"
                className="py-28 px-8 bg-slate-50 border-t border-slate-200"
            >
                <div className="max-w-[1100px] mx-auto">
                    <div className="text-center mb-20">
                        <p className="text-[13px] font-semibold text-slate-900 tracking-widest uppercase mb-4">
                            PROCESS
                        </p>
                        <h2 className="text-5xl font-extrabold tracking-tight text-slate-900">
                            Three steps to bulletproof contracts.
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                        {HOW_IT_WORKS_STEPS.map((item) => (
                            <div
                                key={item.step}
                                className="p-10 bg-white rounded-2xl border border-slate-200"
                            >
                                <div className="text-6xl font-extrabold text-slate-200 leading-none mb-5">
                                    {item.step}
                                </div>
                                <h3 className="text-[22px] font-bold mb-3 text-slate-900">
                                    {item.title}
                                </h3>
                                <p className="text-[15px] leading-relaxed text-slate-500">
                                    {item.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ================================================================
          STATS SECTION
          ================================================================ */}
            <section className="py-20 px-8 bg-slate-900">
                <div className="max-w-[1100px] mx-auto flex justify-around flex-wrap gap-8">
                    {STATS.map((stat) => (
                        <div key={stat.label} className="text-center">
                            <div className="text-5xl font-extrabold text-white tracking-tight">
                                {stat.value}
                            </div>
                            <div className="text-sm text-slate-400 mt-2">
                                {stat.label}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ================================================================
          CTA SECTION
          ================================================================ */}
            <section
                id="contact"
                className="py-28 px-8 bg-slate-900 text-center border-t border-slate-800"
            >
                <div className="max-w-[700px] mx-auto">
                    <h2 className="text-5xl font-extrabold text-white tracking-tight mb-4">
                        Ready to streamline your contract review?
                    </h2>
                    <p className="text-lg text-slate-400 mb-12 leading-relaxed">
                        Join legal teams who are reducing contract review time and catching critical risks before they become liabilities.
                    </p>
                    <div className="flex justify-center gap-4">
                        <a
                            href={DOWNLOAD_URL}
                            className="inline-flex items-center gap-2.5 bg-white text-slate-900 px-9 py-4 rounded-lg text-base font-bold no-underline hover:bg-slate-100 transition-colors"
                        >
                            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                            Download Installer
                        </a>
                        <a
                            href="mailto:contact@contrared.ai"
                            className="inline-flex items-center gap-2 bg-transparent text-white px-9 py-4 rounded-lg text-base font-semibold no-underline border border-slate-700 hover:border-slate-500 transition-colors"
                        >
                            Request a Demo &rarr;
                        </a>
                    </div>
                </div>
            </section>

            {/* ================================================================
          FOOTER
          ================================================================ */}
            <footer className="pt-16 pb-8 px-8 bg-slate-900 border-t border-slate-800">
                <div className="max-w-[1100px] mx-auto flex flex-col md:flex-row justify-between items-start gap-8">
                    <div>
                        <img src="/logo.png" alt="ContraRed" className="h-6 opacity-70" />
                        <p className="text-[13px] text-slate-500 mt-4">
                            Contract intelligence for enterprise legal teams.
                        </p>
                    </div>
                    <div className="flex gap-10 md:gap-20">
                        <div>
                            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Product</h4>
                            <div className="flex flex-col gap-2.5">
                                <a href="#features" className="text-sm text-slate-500 no-underline hover:text-slate-300">Features</a>
                                <a href={DOWNLOAD_URL} className="text-sm text-slate-500 no-underline hover:text-slate-300">Download</a>
                            </div>
                        </div>
                        <div>
                            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Company</h4>
                            <div className="flex flex-col gap-2.5">
                                <a href="#contact" className="text-sm text-slate-500 no-underline hover:text-slate-300">Contact</a>
                                <a href="mailto:contact@contrared.ai" className="text-sm text-slate-500 no-underline hover:text-slate-300">Email</a>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="max-w-[1100px] mx-auto mt-12 pt-6 border-t border-slate-800 text-[13px] text-slate-600">
                    &copy; 2026 ContraRed. All rights reserved.
                </div>
            </footer>
        </div>
    );
}
