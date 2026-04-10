import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    listPlaybooks,
    batchAnalyze,
    getBatchStatus,
    getBatchFullReport,
    updateRiskStatus,
    type Playbook,
    type BatchStatusResponse,
    type BatchFileStatus,
    type BatchFullReport,
    type BatchFinding,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Upload, X, RotateCcw, Download, ChevronDown, ChevronRight, Check, AlertTriangle, FileText } from 'lucide-react';

const MAX_FILES = 10;
const ACCEPTED_EXT = '.docx';
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
const POLL_INTERVAL = 3000;

function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(s: BatchFileStatus['status']): string {
    switch (s) {
        case 'queued': return 'Queued';
        case 'processing': return 'Processing...';
        case 'completed': return 'Completed';
        case 'error': return 'Error';
        default: return s;
    }
}

function statusBadgeVariant(s: string): 'low' | 'critical' | 'high' | 'neutral' {
    if (s === 'completed') return 'low';
    if (s === 'error' || s === 'partial_failure') return 'critical';
    if (s === 'processing') return 'high';
    return 'neutral';
}

const fileCardStyle = (status: string): CSSProperties => ({
    border: `1px solid ${status === 'error' ? 'var(--risk-critical-border)' : status === 'completed' ? 'var(--risk-low-border)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-md)', padding: 14,
    backgroundColor: status === 'error' ? 'var(--risk-critical-bg)' : status === 'completed' ? 'var(--risk-low-bg)' : 'var(--bg-surface)',
});

export default function BatchUpload() {
    const [files, setFiles] = useState<File[]>([]);
    const [playbookId, setPlaybookId] = useState('');
    const [batchId, setBatchId] = useState<string | null>(null);
    const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const { data: playbooks = [] } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    useEffect(() => {
        if (!batchId) return;
        const poll = async () => {
            try {
                const status = await getBatchStatus(batchId);
                setBatchStatus(status);
                if (status.status !== 'processing') {
                    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
                }
            } catch { /* silently retry */ }
        };
        poll();
        pollRef.current = setInterval(poll, POLL_INTERVAL);
        return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    }, [batchId]);

    const addFiles = useCallback((incoming: FileList | File[]) => {
        const arr = Array.from(incoming).filter(f => f.name.toLowerCase().endsWith(ACCEPTED_EXT));
        if (arr.length === 0) { setError('Only .docx files are accepted.'); return; }
        const oversized = arr.filter(f => f.size > MAX_FILE_SIZE);
        const valid = arr.filter(f => f.size <= MAX_FILE_SIZE);
        if (oversized.length > 0) setError(`${oversized.length} file(s) exceed 20MB limit and were excluded.`);
        if (valid.length === 0) return;
        setFiles(prev => {
            const combined = [...prev, ...valid];
            if (combined.length > MAX_FILES) {
                setTimeout(() => setError(`Maximum ${MAX_FILES} files allowed.`), 0);
                return combined.slice(0, MAX_FILES);
            }
            if (oversized.length === 0) setTimeout(() => setError(null), 0);
            return combined;
        });
    }, []);

    const removeFile = (index: number) => setFiles(prev => prev.filter((_, i) => i !== index));

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault(); setIsDragOver(false);
        if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    }, [addFiles]);

    const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragOver(true); }, []);
    const handleDragLeave = useCallback(() => setIsDragOver(false), []);

    const handleUpload = async () => {
        if (files.length === 0) return;
        setUploading(true); setError(null);
        try {
            const result = await batchAnalyze(files, playbookId || undefined);
            setBatchId(result.batch_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const handleReset = () => {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        setFiles([]); setPlaybookId(''); setBatchId(null); setBatchStatus(null); setError(null);
    };

    return (
        <AppLayout>
            <div>
                <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Batch Upload</h1>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
                    Upload multiple contracts for parallel AI analysis (max {MAX_FILES} files)
                </p>
            </div>

            {/* Upload Section */}
            {!batchId && (
                <div style={{ marginTop: 24 }}>
                    {/* Drop Zone */}
                    <div
                        style={{
                            border: `2px dashed ${isDragOver ? 'var(--accent)' : 'var(--border)'}`,
                            borderRadius: 'var(--radius-lg)', padding: '48px 24px',
                            textAlign: 'center', cursor: 'pointer',
                            backgroundColor: isDragOver ? 'var(--risk-critical-bg)' : 'var(--bg-surface)',
                            transition: 'all var(--transition-fast)',
                        }}
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <Upload size={40} style={{ color: 'var(--text-muted)', marginBottom: 8 }} />
                        <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-primary)' }}>
                            Drop .docx files here or click to browse
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                            Up to {MAX_FILES} Word documents
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept={ACCEPTED_EXT}
                            multiple
                            style={{ display: 'none' }}
                            onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ''; }}
                        />
                    </div>

                    {/* File List */}
                    {files.length > 0 && (
                        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {files.map((f, i) => (
                                <div key={`${f.name}-${i}`} style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                    backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)', padding: '10px 14px',
                                }}>
                                    <div>
                                        <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{f.name}</span>
                                        <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 8 }}>{formatSize(f.size)}</span>
                                    </div>
                                    <button
                                        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0 4px' }}
                                        onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                        title="Remove file"
                                    >
                                        <X size={18} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Controls */}
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, marginTop: 20 }}>
                        <div style={{ flex: 1, maxWidth: 300 }}>
                            <SelectInput label="Playbook (optional)" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)}>
                                <option value="">No playbook</option>
                                {playbooks?.map((p: Playbook) => (
                                    <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                            </SelectInput>
                        </div>
                        <Button
                            disabled={files.length === 0 || uploading}
                            loading={uploading}
                            onClick={handleUpload}
                            icon={<Upload size={16} />}
                        >
                            {uploading ? 'Uploading...' : `Analyze ${files.length} File${files.length !== 1 ? 's' : ''}`}
                        </Button>
                    </div>

                    {error && (
                        <div style={{
                            marginTop: 16, padding: '12px 16px',
                            background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)',
                            borderRadius: 'var(--radius-md)', color: 'var(--risk-critical)', fontSize: 14,
                        }}>
                            {error}
                        </div>
                    )}
                </div>
            )}

            {/* Progress Section */}
            {batchId && (
                <BatchResultsSection
                    batchId={batchId}
                    batchStatus={batchStatus}
                    onReset={handleReset}
                />
            )}
        </AppLayout>
    );
}


/* =========================================================================
   BATCH RESULTS SECTION — Portfolio summary + inline expand + export
   ========================================================================= */

function BatchResultsSection({ batchId, batchStatus, onReset }: {
    batchId: string;
    batchStatus: BatchStatusResponse | null;
    onReset: () => void;
}) {
    const [report, setReport] = useState<BatchFullReport | null>(null);
    const [expandedFile, setExpandedFile] = useState<string | null>(null);
    const [loadingReport, setLoadingReport] = useState(false);

    const isComplete = batchStatus?.status === 'completed' || batchStatus?.status === 'partial_failure';

    // Load full report when batch completes
    useEffect(() => {
        if (isComplete && !report && !loadingReport) {
            setLoadingReport(true);
            getBatchFullReport(batchId)
                .then(setReport)
                .catch(() => {})
                .finally(() => setLoadingReport(false));
        }
    }, [isComplete, batchId, report, loadingReport]);

    const handleExport = async () => {
        if (!batchId) return;
        try {
            const API_BASE_URL = import.meta.env.VITE_API_URL || '';
            const res = await fetch(`${API_BASE_URL}/documents/batch/${batchId}/export-docx`, {
                credentials: 'include',
            });
            if (!res.ok) throw new Error('Export failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ContraRed-Portfolio-Report-${batchId.slice(0, 8)}.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Export failed:', err);
        }
    };

    const handleResolveRisk = async (docId: string, riskId: string) => {
        try {
            await updateRiskStatus(docId, riskId, 'resolve');
            // Refresh report
            const updated = await getBatchFullReport(batchId);
            setReport(updated);
        } catch {}
    };

    return (
        <Card style={{ marginTop: 24 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Batch Analysis</span>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {batchStatus && (
                        <Badge variant={statusBadgeVariant(batchStatus.status)}>
                            {batchStatus.status === 'completed' ? 'Completed' : batchStatus.status === 'partial_failure' ? 'Partial Failure' : 'Processing'}
                        </Badge>
                    )}
                </div>
            </div>

            {/* Progress Bar */}
            <div style={{ width: '100%', height: 8, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', marginBottom: 20 }}>
                <div style={{
                    height: '100%', borderRadius: 'var(--radius-sm)',
                    backgroundColor: batchStatus?.status === 'partial_failure' ? 'var(--risk-critical)' : 'var(--accent)',
                    transition: 'width 0.4s ease', width: `${batchStatus?.overall_progress ?? 0}%`,
                }} />
            </div>

            {/* Processing state */}
            {!isComplete && (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 14, padding: '20px 0' }}>
                    {!batchStatus ? 'Starting batch analysis...' : `Analyzing contracts... ${batchStatus.overall_progress}%`}
                </div>
            )}

            {/* ---- PORTFOLIO SUMMARY (shown after completion) ---- */}
            {report && (
                <>
                    {/* Summary Stats */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
                        <StatBox label="Compliance Score" value={`${report.compliance_score}%`} color={report.compliance_score >= 70 ? 'var(--risk-low)' : report.compliance_score >= 40 ? 'var(--risk-high)' : 'var(--risk-critical)'} />
                        <StatBox label="Total Findings" value={report.aggregate_risk_summary.total} color="var(--text-primary)" />
                        <StatBox label="Critical (Red)" value={report.aggregate_risk_summary.red} color="var(--risk-critical)" />
                        <StatBox label="Warnings (Yellow)" value={report.aggregate_risk_summary.yellow} color="var(--risk-high)" />
                        <StatBox label="Deal Breakers" value={report.aggregate_risk_summary.deal_breakers} color="var(--risk-critical)" />
                        <StatBox label="Files Analyzed" value={`${report.completed_files}/${report.total_files}`} color="var(--text-muted)" />
                    </div>

                    {/* Top Risks */}
                    {report.top_risks.length > 0 && (
                        <div style={{ marginBottom: 24 }}>
                            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                                Top Risks Across Portfolio
                            </h3>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {report.top_risks.map(r => (
                                    <span key={r.rule} style={{
                                        padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                                        backgroundColor: 'var(--risk-critical-bg)', color: 'var(--risk-critical)',
                                        border: '1px solid var(--risk-critical-border)',
                                    }}>
                                        {r.rule} ({r.count})
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Risk Heatmap by Clause Type */}
                    {report.risk_heatmap.length > 0 && (
                        <div style={{ marginBottom: 24 }}>
                            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                                Risk Heatmap by Clause Type
                            </h3>
                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                {report.risk_heatmap.map(h => {
                                    const intensity = Math.min(h.count / 5, 1);
                                    return (
                                        <span key={h.clause_type} style={{
                                            padding: '4px 10px', borderRadius: 6, fontSize: 12,
                                            backgroundColor: `rgba(239, 68, 68, ${0.1 + intensity * 0.3})`,
                                            color: intensity > 0.5 ? '#fff' : 'var(--risk-critical)',
                                            border: '1px solid var(--risk-critical-border)',
                                        }}>
                                            {h.clause_type} ({h.count})
                                        </span>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* ---- PER-FILE WITH INLINE EXPAND ---- */}
                    <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                        Contract Details
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                        {report.per_file.map((file) => {
                            const isExpanded = expandedFile === file.filename;
                            const rs = file.risk_summary || { red: 0, yellow: 0, green: 0, total: 0 };

                            return (
                                <div key={file.filename} style={{
                                    border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
                                    overflow: 'hidden', backgroundColor: 'var(--bg-surface)',
                                }}>
                                    {/* File Header (clickable) */}
                                    <div
                                        onClick={() => setExpandedFile(isExpanded ? null : file.filename)}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                                            cursor: 'pointer', transition: 'background 0.15s',
                                        }}
                                    >
                                        {isExpanded ? <ChevronDown size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronRight size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                                        <FileText size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                                        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {file.filename}
                                        </span>
                                        {file.status === 'error' ? (
                                            <Badge variant="critical">Error</Badge>
                                        ) : (
                                            <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                                                {file.ai_fallback && (
                                                    <span title="AI analysis failed — results are from rule engine only" style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: 'var(--risk-high)', fontWeight: 600 }}>
                                                        <AlertTriangle size={12} /> Rule-only
                                                    </span>
                                                )}
                                                {rs.red > 0 && <Badge variant="critical">{rs.red} Red</Badge>}
                                                {rs.yellow > 0 && <Badge variant="high">{rs.yellow} Yellow</Badge>}
                                                {(rs.total - rs.red - rs.yellow) > 0 && <Badge variant="low">{rs.total - rs.red - rs.yellow} Green</Badge>}
                                            </div>
                                        )}
                                    </div>

                                    {/* Expanded: Show all findings */}
                                    {isExpanded && file.findings && (
                                        <div style={{ borderTop: '1px solid var(--border)', padding: '0' }}>
                                            {file.ai_fallback && (
                                                <div style={{ padding: '10px 16px', backgroundColor: 'var(--risk-high-bg)', borderBottom: '1px solid var(--risk-high-border)', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--risk-high)' }}>
                                                    <AlertTriangle size={14} />
                                                    <span><strong>AI analysis failed for this file.</strong> Results shown are from rule-engine keyword matching only and may be less accurate. Re-analyze individually for full AI review.</span>
                                                </div>
                                            )}
                                            {file.error && (
                                                <div style={{ padding: 16, color: 'var(--risk-critical)', fontSize: 13 }}>{file.error}</div>
                                            )}
                                            {file.findings.length === 0 && !file.error && (
                                                <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 13, textAlign: 'center' }}>
                                                    No detailed findings stored for this file.
                                                </div>
                                            )}
                                            {file.findings.map((finding, fi) => (
                                                <FindingRow
                                                    key={finding.id}
                                                    finding={finding}
                                                    isLast={fi === file.findings.length - 1}
                                                    documentId={file.document_id}
                                                    onResolve={handleResolveRisk}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 8 }}>
                        <Button variant="secondary" onClick={handleExport} icon={<Download size={14} />}>
                            Export Report (.docx)
                        </Button>
                        <Button variant="secondary" onClick={onReset} icon={<RotateCcw size={14} />}>
                            New Batch Upload
                        </Button>
                    </div>
                </>
            )}

            {/* Still processing — show file cards */}
            {!report && batchStatus && (
                <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                        {batchStatus.files.map((f) => (
                            <div key={f.filename} style={fileCardStyle(f.status)}>
                                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={f.filename}>
                                    {f.filename}
                                </div>
                                <div style={{
                                    fontSize: 12, fontWeight: 500,
                                    color: f.status === 'completed' ? 'var(--risk-low)' : f.status === 'error' ? 'var(--risk-critical)' : f.status === 'processing' ? 'var(--risk-high)' : 'var(--text-muted)',
                                }}>
                                    {statusLabel(f.status)}
                                </div>
                                {f.status === 'completed' && f.risk_summary && (
                                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                                        <Badge variant="critical">{f.risk_summary.red} Red</Badge>
                                        <Badge variant="high">{f.risk_summary.yellow} Yellow</Badge>
                                        <Badge variant="low">{f.risk_summary.total - f.risk_summary.red - f.risk_summary.yellow} Green</Badge>
                                    </div>
                                )}
                                {f.status === 'error' && f.error && (
                                    <div style={{ fontSize: 12, color: 'var(--risk-critical)', marginTop: 4 }}>{f.error}</div>
                                )}
                            </div>
                        ))}
                    </div>
                    {isComplete && (
                        <Button variant="secondary" onClick={onReset} style={{ marginTop: 20 }} icon={<RotateCcw size={14} />}>
                            New Batch Upload
                        </Button>
                    )}
                </>
            )}
        </Card>
    );
}


/* ---- Individual Finding Row ---- */

function FindingRow({ finding, isLast, documentId, onResolve }: {
    finding: BatchFinding;
    isLast: boolean;
    documentId: string | null;
    onResolve: (docId: string, riskId: string) => void;
}) {
    const [expanded, setExpanded] = useState(false);
    const riskColor = finding.risk_level === 'RED' ? 'var(--risk-critical)' :
        finding.risk_level === 'YELLOW' ? 'var(--risk-high)' : 'var(--risk-low)';

    return (
        <div style={{
            padding: '12px 16px',
            borderBottom: isLast ? 'none' : '1px solid var(--border)',
            opacity: finding.is_resolved ? 0.5 : 1,
            backgroundColor: finding.is_resolved ? 'var(--bg-elevated)' : 'transparent',
        }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                {/* Risk indicator */}
                <div style={{
                    width: 10, height: 10, borderRadius: '50%', marginTop: 4, flexShrink: 0,
                    backgroundColor: riskColor,
                }} />

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                            {finding.rule_name || finding.clause_type || 'Finding'}
                        </span>
                        {finding.is_deal_breaker && (
                            <Badge variant="critical">Deal Breaker</Badge>
                        )}
                        {finding.redline_type && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                ({finding.redline_type})
                            </span>
                        )}
                        {finding.is_resolved && <Badge variant="low">Resolved</Badge>}
                    </div>

                    {/* Clause text */}
                    <div style={{
                        fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5,
                        backgroundColor: 'var(--bg-elevated)', padding: '8px 10px', borderRadius: 6,
                        borderLeft: `3px solid ${riskColor}`, marginBottom: 6,
                        maxHeight: expanded ? 'none' : 60, overflow: 'hidden',
                        cursor: 'pointer',
                    }} onClick={() => setExpanded(!expanded)}>
                        {finding.clause_text}
                    </div>

                    {/* Explanation */}
                    {finding.ai_explanation && (
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
                            <strong>Risk:</strong> {finding.ai_explanation}
                        </div>
                    )}

                    {/* Suggested fix */}
                    {finding.suggested_fix && (
                        <div style={{
                            fontSize: 12, color: 'var(--risk-low)', padding: '6px 10px',
                            backgroundColor: 'var(--risk-low-bg)', borderRadius: 6,
                            borderLeft: '3px solid var(--risk-low)',
                        }}>
                            <strong>Fix:</strong> {finding.suggested_fix}
                        </div>
                    )}
                </div>

                {/* Actions */}
                {!finding.is_resolved && documentId && (
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        <button
                            onClick={() => onResolve(documentId, finding.id)}
                            title="Mark as resolved"
                            style={{
                                background: 'none', border: '1px solid var(--border)', borderRadius: 6,
                                padding: '4px 8px', cursor: 'pointer', color: 'var(--text-muted)',
                                fontSize: 11, display: 'flex', alignItems: 'center', gap: 4,
                            }}
                        >
                            <Check size={12} /> Resolve
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}


/* ---- Stat Box ---- */

function StatBox({ label, value, color }: { label: string; value: string | number; color: string }) {
    return (
        <div style={{
            padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
            backgroundColor: 'var(--bg-surface)', textAlign: 'center',
        }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>
                {label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1.2 }}>
                {value}
            </div>
        </div>
    );
}
