interface CertificateProps {
  userName: string
  completionDate: string
  bookTitle: string
}

export default function Certificate({
  userName,
  completionDate,
  bookTitle,
}: CertificateProps) {
  const handleDownload = () => {
    window.print()
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Certificate card */}
      <div
        id="certificate"
        className="relative w-full max-w-2xl overflow-hidden rounded-lg"
        style={{
          backgroundColor: '#1A1A1A',
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E")`,
        }}
      >
        {/* Gold border frame via SVG */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          preserveAspectRatio="none"
        >
          {/* Outer frame */}
          <rect
            x="8"
            y="8"
            width="calc(100% - 16px)"
            height="calc(100% - 16px)"
            rx="4"
            fill="none"
            stroke="#C5A880"
            strokeWidth="2"
            style={{ width: 'calc(100% - 16px)', height: 'calc(100% - 16px)' }}
          />
          {/* Inner frame */}
          <rect
            x="16"
            y="16"
            rx="2"
            fill="none"
            stroke="#8B7355"
            strokeWidth="0.5"
            style={{ width: 'calc(100% - 32px)', height: 'calc(100% - 32px)' }}
          />
        </svg>

        <div className="relative px-12 py-16 text-center">
          {/* NeetiQ logo text */}
          <div
            className="text-xs font-mono tracking-[0.3em] uppercase mb-8"
            style={{ color: '#8B7355' }}
          >
            NeetiQ
          </div>

          {/* Certificate heading */}
          <h2
            className="text-sm font-mono tracking-widest uppercase mb-6"
            style={{ color: '#6B6B6B' }}
          >
            Certificate of Completion
          </h2>

          {/* Decorative line */}
          <div
            className="mx-auto mb-6"
            style={{ width: 60, height: 1, backgroundColor: '#C5A880' }}
          />

          {/* Book title */}
          <h3
            className="text-2xl font-serif mb-8"
            style={{ color: '#C5A880', fontFamily: 'Georgia, serif' }}
          >
            {bookTitle}
          </h3>

          {/* Presented to */}
          <div
            className="text-xs font-mono uppercase tracking-wider mb-2"
            style={{ color: '#6B6B6B' }}
          >
            Presented to
          </div>

          {/* User name */}
          <div
            className="text-3xl font-serif mb-8"
            style={{ color: '#E8E8E8', fontFamily: 'Georgia, serif' }}
          >
            {userName}
          </div>

          {/* Decorative line */}
          <div
            className="mx-auto mb-6"
            style={{ width: 120, height: 1, backgroundColor: '#1E1E1E' }}
          />

          {/* Completion date */}
          <div
            className="text-xs font-mono"
            style={{ color: '#6B6B6B' }}
          >
            Completed on {completionDate}
          </div>

          {/* Decorative corner accents */}
          <svg className="absolute top-4 left-4 w-6 h-6" viewBox="0 0 24 24" fill="none">
            <path d="M0 12 L0 0 L12 0" stroke="#C5A880" strokeWidth="1" />
          </svg>
          <svg className="absolute top-4 right-4 w-6 h-6" viewBox="0 0 24 24" fill="none">
            <path d="M12 0 L24 0 L24 12" stroke="#C5A880" strokeWidth="1" />
          </svg>
          <svg className="absolute bottom-4 left-4 w-6 h-6" viewBox="0 0 24 24" fill="none">
            <path d="M0 12 L0 24 L12 24" stroke="#C5A880" strokeWidth="1" />
          </svg>
          <svg className="absolute bottom-4 right-4 w-6 h-6" viewBox="0 0 24 24" fill="none">
            <path d="M12 24 L24 24 L24 12" stroke="#C5A880" strokeWidth="1" />
          </svg>
        </div>
      </div>

      {/* Download button */}
      <button
        onClick={handleDownload}
        className="px-6 py-2.5 rounded-lg font-mono text-sm tracking-wide transition-all"
        style={{
          backgroundColor: 'transparent',
          color: '#C5A880',
          border: '1px solid #C5A880',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(197,168,128,0.1)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
        }}
      >
        Download Certificate
      </button>
    </div>
  )
}
