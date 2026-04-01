import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    listPlaybooks,
    batchAnalyze,
    getBatchStatus,
    type Playbook,
    type BatchStatusResponse,
    type BatchFileStatus,
} from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Upload, X, RotateCcw } from 'lucide-react';

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

    const fileCardStyle = (status: string): CSSProperties => ({
        border: `1px solid ${status === 'error' ? 'var(--risk-critical-border)' : status === 'completed' ? 'var(--risk-low-border)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-md)', padding: 14,
        backgroundColor: status === 'error' ? 'var(--risk-critical-bg)' : status === 'completed' ? 'var(--risk-low-bg)' : 'var(--bg-surface)',
    });

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
                <Card style={{ marginTop: 24 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Batch Analysis</span>
                        {batchStatus && (
                            <Badge variant={statusBadgeVariant(batchStatus.status)}>
                                {batchStatus.status === 'completed' ? 'Completed' : batchStatus.status === 'partial_failure' ? 'Partial Failure' : 'Processing'}
                            </Badge>
                        )}
                    </div>

                    {/* Progress Bar */}
                    <div style={{ width: '100%', height: 8, backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', marginBottom: 20 }}>
                        <div style={{
                            height: '100%', backgroundColor: 'var(--accent)', borderRadius: 'var(--radius-sm)',
                            transition: 'width 0.4s ease', width: `${batchStatus?.overall_progress ?? 0}%`,
                        }} />
                    </div>

                    {!batchStatus && (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 14, padding: '20px 0' }}>
                            Starting batch analysis...
                        </div>
                    )}

                    {/* File Status Grid */}
                    {batchStatus && (
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
                    )}

                    {batchStatus && batchStatus.status !== 'processing' && (
                        <Button variant="secondary" onClick={handleReset} style={{ marginTop: 20 }} icon={<RotateCcw size={14} />}>
                            New Batch Upload
                        </Button>
                    )}
                </Card>
            )}
        </AppLayout>
    );
}
