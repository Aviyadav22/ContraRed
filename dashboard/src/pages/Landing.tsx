import { Link } from 'react-router-dom';

const DOWNLOAD_URL = import.meta.env.VITE_ADDIN_DOWNLOAD_URL || '/Install-ContraRed.bat';

export default function Landing() {
    return (
        <div style={{ fontFamily: "'Inter', system-ui, sans-serif", color: '#0f172a' }}>
            {/* ================================================================
          NAVIGATION
          ================================================================ */}
            <nav
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    zIndex: 50,
                    backdropFilter: 'blur(20px)',
                    backgroundColor: 'rgba(255,255,255,0.85)',
                    borderBottom: '1px solid #e2e8f0',
                }}
            >
                <div
                    style={{
                        maxWidth: 1280,
                        margin: '0 auto',
                        padding: '0 32px',
                        height: 64,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                    }}
                >
                    <img src="/logo.png" alt="ContraRed" style={{ height: 80 }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 40 }}>
                        <a href="#features" style={{ fontSize: 14, fontWeight: 500, color: '#475569', textDecoration: 'none' }}>Features</a>
                        <a href="#how-it-works" style={{ fontSize: 14, fontWeight: 500, color: '#475569', textDecoration: 'none' }}>How It Works</a>
                        <a href="#contact" style={{ fontSize: 14, fontWeight: 500, color: '#475569', textDecoration: 'none' }}>Contact</a>
                        <Link
                            to="/login"
                            style={{
                                fontSize: 14,
                                fontWeight: 600,
                                color: '#ffffff',
                                backgroundColor: '#0f172a',
                                padding: '10px 24px',
                                borderRadius: 8,
                                textDecoration: 'none',
                            }}
                        >
                            Sign In
                        </Link>
                    </div>
                </div>
            </nav>

            {/* ================================================================
          HERO SECTION
          ================================================================ */}
            <section
                style={{
                    paddingTop: 100,
                    paddingBottom: 80,
                    textAlign: 'center',
                    backgroundColor: '#ffffff',
                    position: 'relative',
                    overflow: 'hidden',
                }}
            >
                {/* Subtle grid background */}
                <div
                    style={{
                        position: 'absolute',
                        inset: 0,
                        backgroundImage: 'radial-gradient(#e2e8f0 1px, transparent 1px)',
                        backgroundSize: '24px 24px',
                        opacity: 0.4,
                    }}
                />

                <div style={{ position: 'relative', maxWidth: 900, margin: '0 auto', padding: '0 32px' }}>

                    {/* Headline */}
                    <h1
                        style={{
                            fontSize: 72,
                            fontWeight: 800,
                            letterSpacing: -3,
                            lineHeight: 1.05,
                            margin: '0 0 24px',
                            color: '#0f172a',
                        }}
                    >
                        Catch liabilities
                        <br />
                        <span style={{ color: '#dc2626' }}>Before</span> you sign
                    </h1>

                    {/* Subtitle */}
                    <p
                        style={{
                            fontSize: 20,
                            lineHeight: 1.6,
                            color: '#64748b',
                            margin: '0 auto 40px',
                            maxWidth: 620,
                        }}
                    >
                        ContraRed detects risky clauses, generates precise redline suggestions,
                        and produces executive risk summaries — all inside Microsoft Word.
                    </p>

                    {/* CTA Buttons */}
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 16 }}>
                        <a
                            href={DOWNLOAD_URL}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 10,
                                backgroundColor: '#0f172a',
                                color: '#ffffff',
                                padding: '14px 32px',
                                borderRadius: 10,
                                fontSize: 15,
                                fontWeight: 600,
                                textDecoration: 'none',
                                border: '1px solid #0f172a',
                            }}
                        >
                            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                            Download Installer
                        </a>
                        <a
                            href="#features"
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: '#ffffff',
                                color: '#0f172a',
                                padding: '14px 32px',
                                borderRadius: 10,
                                fontSize: 15,
                                fontWeight: 600,
                                textDecoration: 'none',
                                border: '1px solid #e2e8f0',
                            }}
                        >
                            See How It Works →
                        </a>
                    </div>
                </div>

                {/* Hero Video */}
                <div
                    style={{
                        maxWidth: 1100,
                        margin: '64px auto 0',
                        padding: '0 32px',
                    }}
                >
                    <div
                        style={{
                            borderRadius: 16,
                            overflow: 'hidden',
                            boxShadow: '0 32px 80px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15,23,42,0.06)',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#0a0a0a',
                        }}
                    >
                        <video
                            autoPlay
                            loop
                            muted
                            playsInline
                            style={{
                                width: '100%',
                                display: 'block',
                            }}
                        >
                            <source src="/demo-video.mp4" type="video/mp4" />
                        </video>
                    </div>
                </div>
            </section>

            {/* ================================================================
          TRUST INDICATORS
          ================================================================ */}
            <section style={{ backgroundColor: '#f8fafc', borderTop: '1px solid #e2e8f0', borderBottom: '1px solid #e2e8f0' }}>
                <div
                    style={{
                        maxWidth: 1100,
                        margin: '0 auto',
                        padding: '48px 32px',
                        display: 'flex',
                        justifyContent: 'center',
                        gap: 64,
                    }}
                >
                    {[
                        { text: 'Zero data retention', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg> },
                        { text: 'Enterprise-grade security', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg> },
                        { text: 'Analysis in seconds', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> },
                        { text: 'Works inside Microsoft Word', icon: <svg width="18" height="18" fill="none" stroke="#0f172a" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> },
                    ].map((item) => (
                        <div key={item.text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            {item.icon}
                            <span style={{ fontSize: 14, fontWeight: 500, color: '#475569' }}>{item.text}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ================================================================
          FEATURES — Alternating Image/Text Sections
          ================================================================ */}
            <section id="features" style={{ paddingTop: 120, paddingBottom: 40, backgroundColor: '#ffffff' }}>
                <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 32px', textAlign: 'center', marginBottom: 80 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: '#dc2626', letterSpacing: 1.5, textTransform: 'uppercase', margin: '0 0 16px' }}>
                        CAPABILITIES
                    </p>
                    <h2 style={{ fontSize: 48, fontWeight: 800, letterSpacing: -2, margin: '0 0 16px', color: '#0f172a' }}>
                        Every clause. Every risk. Every fix.
                    </h2>
                    <p style={{ fontSize: 18, color: '#64748b', margin: 0, maxWidth: 600, marginLeft: 'auto', marginRight: 'auto' }}>
                        Purpose-built for legal teams who reviews dozens of contracts every week.
                    </p>
                </div>

                {/* Feature 1: Contract Analysis */}
                <div
                    style={{
                        maxWidth: 1200,
                        margin: '0 auto 120px',
                        padding: '0 32px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 80,
                    }}
                >
                    <div style={{ flex: 1 }}>
                        <div
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: 'rgba(239,68,68,0.08)',
                                color: '#dc2626',
                                padding: '6px 14px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: 0.8,
                                marginBottom: 20,
                            }}
                        >
                            Risk Detection
                        </div>
                        <h3 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -1, margin: '0 0 16px', color: '#0f172a' }}>
                            Full contract risk summary in seconds
                        </h3>
                        <p style={{ fontSize: 16, lineHeight: 1.7, color: '#64748b', margin: '0 0 24px' }}>
                            Every clause is analyzed against your playbook rules. Critical liabilities like unlimited indemnification,
                            auto-renewal traps, and weak security guarantees are flagged instantly — with severity scoring and clause-level citations.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {['Color-coded severity badges (Critical, Warning, Safe)', 'Clause-by-clause risk breakdown', 'Executive-ready risk summary with counts'].map((item) => (
                                <li key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, color: '#334155' }}>
                                    <svg width="18" height="18" fill="none" stroke="#22c55e" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 2 }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div style={{ flex: 1.2 }}>
                        <div
                            style={{
                                borderRadius: 16,
                                overflow: 'hidden',
                                boxShadow: '0 24px 60px rgba(15,23,42,0.15)',
                                border: '1px solid rgba(255,255,255,0.1)',
                            }}
                        >
                            <img
                                src="/feature-risk-summary.png"
                                alt="Risk Summary"
                                style={{ width: '100%', display: 'block' }}
                            />
                        </div>
                    </div>
                </div>

                {/* Feature 2: Surgical Redlining — reversed layout */}
                <div
                    style={{
                        maxWidth: 1200,
                        margin: '0 auto 120px',
                        padding: '0 32px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 80,
                        flexDirection: 'row-reverse',
                    }}
                >
                    <div style={{ flex: 1 }}>
                        <div
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: 'rgba(37,99,235,0.08)',
                                color: '#2563eb',
                                padding: '6px 14px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: 0.8,
                                marginBottom: 20,
                            }}
                        >
                            Precision Redlining
                        </div>
                        <h3 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -1, margin: '0 0 16px', color: '#0f172a' }}>
                            Detect, highlight, and fix — in one click
                        </h3>
                        <p style={{ fontSize: 16, lineHeight: 1.7, color: '#64748b', margin: '0 0 24px' }}>
                            Each risky clause comes with a precise replacement suggestion, drafted in legal language.
                            Red strikethrough marks the original, blue text shows the recommended fix — just like track changes.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {['Surgical clause-level replacements', 'Track-changes style visual diff', 'One-click accept or reject each suggestion'].map((item) => (
                                <li key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, color: '#334155' }}>
                                    <svg width="18" height="18" fill="none" stroke="#2563eb" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 2 }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div style={{ flex: 1.2 }}>
                        <div
                            style={{
                                borderRadius: 16,
                                overflow: 'hidden',
                                boxShadow: '0 24px 60px rgba(15,23,42,0.12)',
                                border: '1px solid #e2e8f0',
                            }}
                        >
                            <img
                                src="/feature-redline.png"
                                alt="Precision Redlining"
                                style={{ width: '100%', display: 'block' }}
                            />
                        </div>
                    </div>
                </div>


                {/* Feature 3: Custom Playbooks */}
                <div
                    style={{
                        maxWidth: 1200,
                        margin: '0 auto 120px',
                        padding: '0 32px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 80,
                    }}
                >
                    <div style={{ flex: 1 }}>
                        <div
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: 'rgba(34,197,94,0.08)',
                                color: '#16a34a',
                                padding: '6px 14px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: 0.8,
                                marginBottom: 20,
                            }}
                        >
                            Custom Playbooks
                        </div>
                        <h3 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -1, margin: '0 0 16px', color: '#0f172a' }}>
                            Your rules. Your risk framework.
                        </h3>
                        <p style={{ fontSize: 16, lineHeight: 1.7, color: '#64748b', margin: '0 0 24px' }}>
                            Define exactly what matters to your organization. Create custom playbooks with specific rules for
                            indemnification caps, IP ownership, data handling, termination clauses, and anything else your
                            legal team needs to enforce — then select the right playbook for each deal type.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {['Create unlimited custom rule sets', 'Switch playbooks per deal type (MSA, NDA, SaaS)', 'Enforce organization-wide compliance standards'].map((item) => (
                                <li key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, color: '#334155' }}>
                                    <svg width="18" height="18" fill="none" stroke="#16a34a" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 2 }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div style={{ flex: 1.2 }}>
                        <div
                            style={{
                                borderRadius: 16,
                                overflow: 'hidden',
                                boxShadow: '0 24px 60px rgba(15,23,42,0.15)',
                                border: '1px solid rgba(255,255,255,0.1)',
                            }}
                        >
                            <img
                                src="/feature-playbook.png"
                                alt="Custom Playbooks"
                                style={{ width: '100%', display: 'block' }}
                            />
                        </div>
                    </div>
                </div>

                {/* Feature 4: Word Integration — reversed */}
                <div
                    style={{
                        maxWidth: 1200,
                        margin: '0 auto 80px',
                        padding: '0 32px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 80,
                        flexDirection: 'row-reverse',
                    }}
                >
                    <div style={{ flex: 1 }}>
                        <div
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: 'rgba(99,102,241,0.08)',
                                color: '#6366f1',
                                padding: '6px 14px',
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: 0.8,
                                marginBottom: 20,
                            }}
                        >
                            Native Integration
                        </div>
                        <h3 style={{ fontSize: 36, fontWeight: 700, letterSpacing: -1, margin: '0 0 16px', color: '#0f172a' }}>
                            Lives inside Microsoft Word
                        </h3>
                        <p style={{ fontSize: 16, lineHeight: 1.7, color: '#64748b', margin: '0 0 24px' }}>
                            No context-switching. No uploads. ContraRed runs as a sidebar in Microsoft Word.
                            Open a contract, click "Scan Document," and get your risk report without leaving the document.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {['One-click installation via batch script', 'Works with .docx and .doc formats', 'Custom playbooks for different deal types'].map((item) => (
                                <li key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, color: '#334155' }}>
                                    <svg width="18" height="18" fill="none" stroke="#6366f1" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 2 }}><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div style={{ flex: 1.2 }}>
                        <div
                            style={{
                                borderRadius: 16,
                                overflow: 'hidden',
                                boxShadow: '0 24px 60px rgba(15,23,42,0.12)',
                                border: '1px solid #e2e8f0',
                            }}
                        >
                            <img
                                src="/feature-word-addin.png"
                                alt="Word Add-in"
                                style={{ width: '100%', display: 'block' }}
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
                style={{
                    padding: '120px 32px',
                    backgroundColor: '#f8fafc',
                    borderTop: '1px solid #e2e8f0',
                }}
            >
                <div style={{ maxWidth: 1100, margin: '0 auto' }}>
                    <div style={{ textAlign: 'center', marginBottom: 80 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', letterSpacing: 1.5, textTransform: 'uppercase', margin: '0 0 16px' }}>
                            PROCESS
                        </p>
                        <h2 style={{ fontSize: 48, fontWeight: 800, letterSpacing: -2, margin: 0, color: '#0f172a' }}>
                            Three steps to bulletproof contracts.
                        </h2>
                    </div>

                    <div style={{ display: 'flex', gap: 40 }}>
                        {[
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
                        ].map((item) => (
                            <div
                                key={item.step}
                                style={{
                                    flex: 1,
                                    padding: 40,
                                    backgroundColor: '#ffffff',
                                    borderRadius: 16,
                                    border: '1px solid #e2e8f0',
                                }}
                            >
                                <div
                                    style={{
                                        fontSize: 64,
                                        fontWeight: 800,
                                        color: '#e2e8f0',
                                        lineHeight: 1,
                                        marginBottom: 20,
                                    }}
                                >
                                    {item.step}
                                </div>
                                <h3 style={{ fontSize: 22, fontWeight: 700, margin: '0 0 12px', color: '#0f172a' }}>
                                    {item.title}
                                </h3>
                                <p style={{ fontSize: 15, lineHeight: 1.6, color: '#64748b', margin: 0 }}>
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
            <section
                style={{
                    padding: '80px 32px',
                    backgroundColor: '#0f172a',
                }}
            >
                <div
                    style={{
                        maxWidth: 1100,
                        margin: '0 auto',
                        display: 'flex',
                        justifyContent: 'space-around',
                    }}
                >
                    {[
                        { value: 'Fast', label: 'Analysis time' },
                        { value: '100%', label: 'Clauses checked' },
                        { value: 'Zero', label: 'Data retained' },
                        { value: 'one-click', label: 'Install' },
                    ].map((stat) => (
                        <div key={stat.label} style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 48, fontWeight: 800, color: '#ffffff', letterSpacing: -2 }}>
                                {stat.value}
                            </div>
                            <div style={{ fontSize: 14, color: '#94a3b8', marginTop: 8 }}>
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
                style={{
                    padding: '120px 32px',
                    backgroundColor: '#0f172a',
                    textAlign: 'center',
                    borderTop: '1px solid #1e293b',
                }}
            >
                <div style={{ maxWidth: 700, margin: '0 auto' }}>
                    <h2
                        style={{
                            fontSize: 48,
                            fontWeight: 800,
                            color: '#ffffff',
                            letterSpacing: -2,
                            margin: '0 0 16px',
                        }}
                    >
                        Ready to streamline your contract review?
                    </h2>
                    <p
                        style={{
                            fontSize: 18,
                            color: '#94a3b8',
                            margin: '0 0 48px',
                            lineHeight: 1.6,
                        }}
                    >
                        Join legal teams who are reducing contract review time and catching critical risks before they become liabilities.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 16 }}>
                        <a
                            href={DOWNLOAD_URL}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 10,
                                backgroundColor: '#ffffff',
                                color: '#0f172a',
                                padding: '16px 36px',
                                borderRadius: 10,
                                fontSize: 16,
                                fontWeight: 700,
                                textDecoration: 'none',
                            }}
                        >
                            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                            Download Installer
                        </a>
                        <a
                            href="mailto:contact@contrared.ai"
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 8,
                                backgroundColor: 'transparent',
                                color: '#ffffff',
                                padding: '16px 36px',
                                borderRadius: 10,
                                fontSize: 16,
                                fontWeight: 600,
                                textDecoration: 'none',
                                border: '1px solid #334155',
                            }}
                        >
                            Request a Demo →
                        </a>
                    </div>
                </div>
            </section>

            {/* ================================================================
          FOOTER
          ================================================================ */}
            <footer
                style={{
                    padding: '64px 32px 32px',
                    backgroundColor: '#0f172a',
                    borderTop: '1px solid #1e293b',
                }}
            >
                <div
                    style={{
                        maxWidth: 1100,
                        margin: '0 auto',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                    }}
                >
                    <div>
                        <img src="/logo.png" alt="ContraRed" style={{ height: 24, opacity: 0.7 }} />
                        <p style={{ fontSize: 13, color: '#64748b', marginTop: 16 }}>
                            Contract intelligence for enterprise legal teams.
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: 80 }}>
                        <div>
                            <h4 style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 16px' }}>Product</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                <a href="#features" style={{ fontSize: 14, color: '#64748b', textDecoration: 'none' }}>Features</a>
                                <a href={DOWNLOAD_URL} style={{ fontSize: 14, color: '#64748b', textDecoration: 'none' }}>Download</a>
                            </div>
                        </div>
                        <div>
                            <h4 style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 16px' }}>Company</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                <a href="#contact" style={{ fontSize: 14, color: '#64748b', textDecoration: 'none' }}>Contact</a>
                                <a href="mailto:contact@contrared.ai" style={{ fontSize: 14, color: '#64748b', textDecoration: 'none' }}>Email</a>
                            </div>
                        </div>
                    </div>
                </div>
                <div
                    style={{
                        maxWidth: 1100,
                        margin: '48px auto 0',
                        paddingTop: 24,
                        borderTop: '1px solid #1e293b',
                        fontSize: 13,
                        color: '#475569',
                    }}
                >
                    © 2026 ContraRed. All rights reserved.
                </div>
            </footer>
        </div>
    );
}
