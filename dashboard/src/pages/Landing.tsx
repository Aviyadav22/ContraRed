import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  BookOpen,
  PenTool,
  Library,
  BarChart3,
  Users,
  Upload,
  Search,
  ArrowRight,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

/* -------------------------------------------------------------------------- */
/*  Data                                                                       */
/* -------------------------------------------------------------------------- */

const FEATURES = [
  {
    icon: Shield,
    title: 'AI Contract Review',
    description:
      'Analyze contracts in seconds with AI that understands legal nuance.',
  },
  {
    icon: BookOpen,
    title: 'Smart Playbooks',
    description:
      'Codify your firm\'s expertise into reusable review playbooks.',
  },
  {
    icon: PenTool,
    title: 'Live Redlining',
    description:
      'Generate and apply fixes directly in Microsoft Word.',
  },
  {
    icon: Library,
    title: 'Clause Library',
    description:
      'Build a library of approved language for consistent contracting.',
  },
  {
    icon: BarChart3,
    title: 'Risk Analytics',
    description:
      'Track risk exposure across your entire contract portfolio.',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description:
      'Collaborate with your team with role-based access and audit trails.',
  },
];

const STEPS = [
  {
    icon: Upload,
    title: 'Upload',
    description: 'Upload your contract or start from a template.',
  },
  {
    icon: Search,
    title: 'Review',
    description: 'AI analyzes every clause against your playbook.',
  },
  {
    icon: PenTool,
    title: 'Redline',
    description: 'Accept, modify, or reject suggestions with one click.',
  },
];

const STATS = [
  { value: '10,000+', label: 'Contracts Reviewed' },
  { value: '94%', label: 'Average Accuracy' },
  { value: '3x', label: 'Faster Review' },
  { value: '50+', label: 'Playbook Templates' },
];

const FOOTER_LINKS = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'Integrations', href: '#' },
  ],
  Resources: [
    { label: 'Documentation', href: '#' },
    { label: 'API Reference', href: '#' },
    { label: 'Blog', href: '#' },
  ],
  Company: [
    { label: 'About', href: '#about' },
    { label: 'Careers', href: '#' },
    { label: 'Contact', href: 'mailto:contact@contrared.ai' },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '#' },
    { label: 'Terms of Service', href: '#' },
    { label: 'Security', href: '#' },
  ],
};

/* -------------------------------------------------------------------------- */
/*  Component                                                                  */
/* -------------------------------------------------------------------------- */

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      style={{
        fontFamily: 'var(--font-sans, Inter, system-ui, sans-serif)',
        color: 'var(--text-primary)',
        background: 'var(--bg-app)',
        scrollBehavior: 'smooth',
      }}
    >
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
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background-color 0.3s, border-color 0.3s, backdrop-filter 0.3s',
          backgroundColor: scrolled ? 'var(--bg-surface)' : 'transparent',
          borderBottom: scrolled ? '1px solid var(--border)' : '1px solid transparent',
          backdropFilter: scrolled ? 'blur(12px)' : 'none',
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            width: '100%',
            padding: '0 32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                backgroundColor: 'var(--accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                fontWeight: 700,
                fontSize: 18,
              }}
            >
              C
            </div>
            <span style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
              ContraRed
            </span>
          </div>

          {/* Nav links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
            <a href="#features" style={navLinkStyle}>Features</a>
            <a href="#pricing" style={navLinkStyle}>Pricing</a>
            <a href="#about" style={navLinkStyle}>About</a>
            <Link
              to="/login"
              style={{
                ...navLinkStyle,
                color: 'var(--text-secondary)',
              }}
            >
              Sign In
            </Link>
            <Link to="/register">
              <Button variant="primary" size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* ================================================================
          HERO SECTION
          ================================================================ */}
      <section
        style={{
          position: 'relative',
          paddingTop: 160,
          paddingBottom: 120,
          textAlign: 'center',
          overflow: 'hidden',
          background: 'linear-gradient(180deg, #09090B 0%, #18181B 100%)',
        }}
      >
        {/* Subtle grid pattern */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.06,
            backgroundImage:
              'linear-gradient(var(--text-muted) 1px, transparent 1px), linear-gradient(90deg, var(--text-muted) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        <div style={{ position: 'relative', maxWidth: 900, margin: '0 auto', padding: '0 32px' }}>
          <h1
            style={{
              fontSize: 'clamp(36px, 5vw, 56px)',
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              color: 'var(--text-primary)',
              margin: '0 0 24px',
            }}
          >
            Contract Intelligence,{' '}
            <span style={{ color: 'var(--accent-text)' }}>Reimagined</span>
          </h1>

          <p
            style={{
              fontSize: 20,
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
              maxWidth: 600,
              margin: '0 auto 40px',
            }}
          >
            AI-powered contract review that thinks like your best attorney.
            Catch risks, generate redlines, and close deals faster.
          </p>

          {/* CTAs */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
            <Link to="/register">
              <Button
                variant="primary"
                size="lg"
                icon={<ArrowRight size={16} />}
                style={{
                  padding: '0 28px',
                  height: 44,
                  fontSize: 15,
                  boxShadow: '0 0 24px var(--accent-glow)',
                }}
              >
                Start Free Trial
              </Button>
            </Link>
            <a href="#features" style={{ textDecoration: 'none' }}>
              <Button variant="secondary" size="lg" style={{ padding: '0 28px', height: 44, fontSize: 15 }}>
                Watch Demo
              </Button>
            </a>
          </div>

          {/* Trust badge */}
          <div
            style={{
              marginTop: 56,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              color: 'var(--text-muted)',
              fontSize: 14,
            }}
          >
            <span>Built for legal teams that move fast and negotiate smarter.</span>
          </div>
        </div>
      </section>

      {/* ================================================================
          FEATURES SECTION
          ================================================================ */}
      <section
        id="features"
        style={{
          padding: '96px 32px',
          background: 'var(--bg-app)',
        }}
      >
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          {/* Section header */}
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <p
              style={{
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: 'var(--accent-text)',
                marginBottom: 12,
              }}
            >
              Capabilities
            </p>
            <h2
              style={{
                fontSize: 'clamp(28px, 3.5vw, 40px)',
                fontWeight: 700,
                letterSpacing: '-0.01em',
                color: 'var(--text-primary)',
                margin: 0,
              }}
            >
              Built for Legal Professionals
            </h2>
          </div>

          {/* Feature grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: 24,
            }}
          >
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title} variant="default" padding="spacious">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 10,
                        backgroundColor: 'var(--accent-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Icon size={22} style={{ color: 'var(--accent-text)' }} />
                    </div>
                    <h3
                      style={{
                        fontSize: 17,
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        margin: 0,
                      }}
                    >
                      {feature.title}
                    </h3>
                    <p
                      style={{
                        fontSize: 14,
                        lineHeight: 1.6,
                        color: 'var(--text-secondary)',
                        margin: 0,
                      }}
                    >
                      {feature.description}
                    </p>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* ================================================================
          HOW IT WORKS
          ================================================================ */}
      <section
        style={{
          padding: '96px 32px',
          backgroundColor: 'var(--bg-elevated)',
        }}
      >
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <p
              style={{
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: 'var(--accent-text)',
                marginBottom: 12,
              }}
            >
              Process
            </p>
            <h2
              style={{
                fontSize: 'clamp(28px, 3.5vw, 40px)',
                fontWeight: 700,
                letterSpacing: '-0.01em',
                color: 'var(--text-primary)',
                margin: 0,
              }}
            >
              How It Works
            </h2>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 32,
              position: 'relative',
            }}
          >
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.title}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    textAlign: 'center',
                    position: 'relative',
                  }}
                >
                  {/* Dotted connector line (between items) */}
                  {idx < STEPS.length - 1 && (
                    <div
                      style={{
                        position: 'absolute',
                        top: 32,
                        left: 'calc(50% + 40px)',
                        right: 'calc(-50% + 40px)',
                        height: 0,
                        borderTop: '2px dashed var(--border-strong)',
                      }}
                    />
                  )}
                  {/* Step number + icon */}
                  <div
                    style={{
                      width: 64,
                      height: 64,
                      borderRadius: 16,
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: 20,
                      position: 'relative',
                    }}
                  >
                    <Icon size={28} style={{ color: 'var(--accent-text)' }} />
                    <div
                      style={{
                        position: 'absolute',
                        top: -8,
                        right: -8,
                        width: 24,
                        height: 24,
                        borderRadius: '50%',
                        backgroundColor: 'var(--accent)',
                        color: '#FFFFFF',
                        fontSize: 12,
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {idx + 1}
                    </div>
                  </div>
                  <h3
                    style={{
                      fontSize: 18,
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      margin: '0 0 8px',
                    }}
                  >
                    {step.title}
                  </h3>
                  <p
                    style={{
                      fontSize: 14,
                      lineHeight: 1.6,
                      color: 'var(--text-secondary)',
                      margin: 0,
                      maxWidth: 280,
                    }}
                  >
                    {step.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ================================================================
          STATS SECTION
          ================================================================ */}
      <section
        style={{
          padding: '80px 32px',
          backgroundColor: 'var(--bg-sidebar)',
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 40,
            textAlign: 'center',
          }}
        >
          {STATS.map((stat) => (
            <div key={stat.label}>
              <div
                style={{
                  fontSize: 'clamp(32px, 4vw, 48px)',
                  fontWeight: 800,
                  letterSpacing: '-0.02em',
                  color: 'var(--accent-text)',
                  lineHeight: 1,
                }}
              >
                {stat.value}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: 'var(--text-secondary)',
                  marginTop: 8,
                }}
              >
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ================================================================
          PRICING / CTA SECTION
          ================================================================ */}
      <section
        id="pricing"
        style={{
          padding: '96px 32px',
          backgroundColor: 'var(--bg-app)',
          textAlign: 'center',
        }}
      >
        <div style={{ maxWidth: 640, margin: '0 auto' }}>
          <h2
            style={{
              fontSize: 'clamp(28px, 3.5vw, 40px)',
              fontWeight: 700,
              letterSpacing: '-0.01em',
              color: 'var(--text-primary)',
              margin: '0 0 16px',
            }}
          >
            Ready to transform your contract review?
          </h2>
          <p
            style={{
              fontSize: 17,
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
              margin: '0 0 40px',
            }}
          >
            Start your free trial today. No credit card required.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
            <Link to="/register">
              <Button
                variant="primary"
                size="lg"
                style={{
                  padding: '0 32px',
                  height: 48,
                  fontSize: 16,
                  boxShadow: '0 0 24px var(--accent-glow)',
                }}
              >
                Start Free Trial
              </Button>
            </Link>
            <a href="mailto:contact@contrared.ai" style={{ textDecoration: 'none' }}>
              <Button variant="secondary" size="lg" style={{ padding: '0 32px', height: 48, fontSize: 16 }}>
                Request a Demo
              </Button>
            </a>
          </div>
        </div>
      </section>

      {/* ================================================================
          FOOTER
          ================================================================ */}
      <footer
        id="about"
        style={{
          backgroundColor: 'var(--bg-sidebar)',
          padding: '64px 32px 32px',
          borderTop: '1px solid var(--border)',
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 40,
          }}
        >
          {/* Brand column */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 5,
                  backgroundColor: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  fontSize: 15,
                }}
              >
                C
              </div>
              <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
                ContraRed
              </span>
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-muted)', margin: 0 }}>
              Contract intelligence for enterprise legal teams.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([section, links]) => (
            <div key={section}>
              <h4
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  color: 'var(--text-muted)',
                  margin: '0 0 16px',
                }}
              >
                {section}
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {links.map((link) => (
                  <a
                    key={link.label}
                    href={link.href}
                    style={{
                      fontSize: 14,
                      color: 'var(--text-secondary)',
                      textDecoration: 'none',
                    }}
                  >
                    {link.label}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          style={{
            maxWidth: 1200,
            margin: '48px auto 0',
            paddingTop: 24,
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 16,
          }}
        >
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            &copy; 2026 ContraRed. All rights reserved.
          </span>
        </div>
      </footer>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Shared inline styles                                                       */
/* -------------------------------------------------------------------------- */

const navLinkStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 500,
  color: 'var(--text-muted)',
  textDecoration: 'none',
};
