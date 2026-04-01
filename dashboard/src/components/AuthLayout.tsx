import { type ReactNode, type CSSProperties } from 'react';

interface AuthLayoutProps {
    children: ReactNode;
}

const containerStyle: CSSProperties = {
    display: 'flex',
    minHeight: '100vh',
};

const brandPanelStyle: CSSProperties = {
    width: '50%',
    backgroundColor: '#0B1120',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 32px',
    position: 'relative',
};

const formPanelStyle: CSSProperties = {
    width: '50%',
    backgroundColor: 'var(--bg-surface)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '48px 24px',
};

const formInnerStyle: CSSProperties = {
    width: '100%',
    maxWidth: 400,
};

const logoContainerStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
};

const logoBoxStyle: CSSProperties = {
    width: 48,
    height: 48,
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--accent)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 24,
    fontWeight: 700,
    color: '#FFFFFF',
};

const logoTextStyle: CSSProperties = {
    fontSize: 28,
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.03em',
};

const taglineStyle: CSSProperties = {
    fontSize: 16,
    color: 'var(--text-secondary)',
    textAlign: 'center',
    maxWidth: 280,
};

const trustStyle: CSSProperties = {
    position: 'absolute',
    bottom: 32,
    fontSize: 12,
    color: 'var(--text-muted)',
    textAlign: 'center',
    lineHeight: 1.6,
};

export function AuthLayout({ children }: AuthLayoutProps) {
    return (
        <div style={containerStyle}>
            {/* Left brand panel — hidden on mobile via CSS class */}
            <div style={brandPanelStyle} className="auth-brand-panel">
                <div style={logoContainerStyle}>
                    <div style={logoBoxStyle}>C</div>
                    <span style={logoTextStyle}>ContraRed</span>
                </div>
                <p style={taglineStyle}>AI-Powered Contract Intelligence</p>
                <p style={trustStyle}>
                    Enterprise-grade security &middot; SOC 2 compliant &middot; GDPR ready
                </p>
            </div>

            {/* Right form panel */}
            <div style={formPanelStyle} className="auth-form-panel">
                <div style={formInnerStyle}>{children}</div>
            </div>
        </div>
    );
}
