interface ScanDividerProps {
  className?: string
}

export default function ScanDivider({ className = '' }: ScanDividerProps) {
  return <div className={`scan-divider ${className}`} />
}
