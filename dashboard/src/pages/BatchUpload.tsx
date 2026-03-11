import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    listPlaybooks,
    batchAnalyze,
    getBatchStatus,
    type Playbook,
    type BatchStatusResponse,
    type BatchFileStatus,
} from '@/api/client';
import AppHeader from '@/components/AppHeader';

const MAX_FILES = 10;
const ACCEPTED_EXT = '.docx';
const POLL_INTERVAL = 3000;

const styles = {
    page: {
        minHeight: '100vh',
        background: '#FAFAF9',
    },
    main: {
        maxWidth: '960px',
        margin: '0 auto',
        padding: '32px 24px',
    },
    heading: {
        fontSize: '24px',
        fontWeight: 700,
        color: '#1a1a1a',
        margin: 0,
    },
    subheading: {
        fontSize: '14px',
        color: '#6B6760',
        marginTop: '4px',
    },
    section: {
        marginTop: '24px',
    },
    dropZone: (isDragOver: boolean) => ({
        border: `2px dashed ${isDragOver ? '#C0392B' : '#E8E5E0'}`,
        borderRadius: '12px',
        padding: '48px 24px',
        textAlign: 'center' as const,
        cursor: 'pointer',
        background: isDragOver ? '#fdf2f2' : '#fff',
        transition: 'border-color 0.2s, background 0.2s',
    }),
    dropIcon: {
        fontSize: '40px',
        color: '#8A8885',
        marginBottom: '8px',
    },
    dropText: {
        fontSize: '15px',
        fontWeight: 500,
        color: '#1a1a1a',
    },
    dropHint: {
        fontSize: '13px',
        color: '#8A8885',
        marginTop: '4px',
    },
    fileList: {
        marginTop: '16px',
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '8px',
    },
    fileItem: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#fff',
        border: '1px solid #E8E5E0',
        borderRadius: '8px',
        padding: '10px 14px',
    },
    fileName: {
        fontSize: '14px',
        color: '#1a1a1a',
        fontWeight: 500,
    },
    fileSize: {
        fontSize: '12px',
        color: '#8A8885',
        marginLeft: '8px',
    },
    removeBtn: {
        background: 'none',
        border: 'none',
        fontSize: '18px',
        color: '#8A8885',
        cursor: 'pointer',
        padding: '0 4px',
        lineHeight: 1,
    },
    row: {
        display: 'flex',
        alignItems: 'flex-end',
        gap: '16px',
        marginTop: '20px',
    },
    fieldGroup: {
        display: 'flex',
        flexDirection: 'column' as const,
        flex: 1,
        maxWidth: '300px',
    },
    label: {
        fontSize: '12px',
        fontWeight: 500,
        color: '#6B6760',
        marginBottom: '4px',
    },
    select: {
        padding: '8px 12px',
        border: '1px solid #E8E5E0',
        borderRadius: '8px',
        fontSize: '14px',
        color: '#1a1a1a',
        background: '#fff',
    },
    uploadBtn: (disabled: boolean) => ({
        padding: '9px 24px',
        background: disabled ? '#ddd' : '#C0392B',
        color: disabled ? '#999' : '#fff',
        border: 'none',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
    }),
    errorBox: {
        marginTop: '16px',
        padding: '12px 16px',
        background: '#fdf2f2',
        border: '1px solid #f5c6cb',
        borderRadius: '8px',
        color: '#C0392B',
        fontSize: '14px',
    },
    progressContainer: {
        marginTop: '24px',
        background: '#fff',
        border: '1px solid #E8E5E0',
        borderRadius: '12px',
        padding: '24px',
    },
    progressHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
    },
    progressTitle: {
        fontSize: '16px',
        fontWeight: 600,
        color: '#1a1a1a',
    },
    progressBadge: (status: string) => ({
        fontSize: '12px',
        fontWeight: 600,
        padding: '3px 10px',
        borderRadius: '12px',
        background: status === 'completed' ? '#e6f4ec' : status === 'partial_failure' ? '#fdf2f2' : '#fff8e6',
        color: status === 'completed' ? '#1A7A4A' : status === 'partial_failure' ? '#C0392B' : '#B7770D',
    }),
    progressBarOuter: {
        width: '100%',
        height: '8px',
        background: '#E8E5E0',
        borderRadius: '4px',
        overflow: 'hidden' as const,
        marginBottom: '20px',
    },
    progressBarInner: (pct: number) => ({
        width: `${pct}%`,
        height: '100%',
        background: '#C0392B',
        borderRadius: '4px',
        transition: 'width 0.4s ease',
    }),
    fileGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '12px',
    },
    fileCard: (status: string) => ({
        border: `1px solid ${status === 'error' ? '#f5c6cb' : status === 'completed' ? '#c3e6cb' : '#E8E5E0'}`,
        borderRadius: '10px',
        padding: '14px',
        background: status === 'error' ? '#fdf2f2' : status === 'completed' ? '#f0faf4' : '#fff',
    }),
    fileCardName: {
        fontSize: '13px',
        fontWeight: 600,
        color: '#1a1a1a',
        marginBottom: '6px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap' as const,
    },
    fileCardStatus: (status: string) => ({
        fontSize: '12px',
        fontWeight: 500,
        color: status === 'completed' ? '#1A7A4A' : status === 'error' ? '#C0392B' : status === 'processing' ? '#B7770D' : '#8A8885',
    }),
    riskRow: {
        display: 'flex',
        gap: '8px',
        marginTop: '8px',
    },
    riskPill: (color: string) => ({
        fontSize: '11px',
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: '10px',
        background: color === 'red' ? '#fdf2f2' : color === 'yellow' ? '#fff8e6' : '#f0faf4',
        color: color === 'red' ? '#C0392B' : color === 'yellow' ? '#B7770D' : '#1A7A4A',
    }),
    errorText: {
        fontSize: '12px',
        color: '#C0392B',
        marginTop: '4px',
    },
    newBatchBtn: {
        marginTop: '20px',
        padding: '9px 20px',
        background: '#fff',
        color: '#1a1a1a',
        border: '1px solid #E8E5E0',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: 500,
        cursor: 'pointer',
    },
};

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

    const { data: playbooks } = useQuery({
        queryKey: ['playbooks'],
        queryFn: listPlaybooks,
    });

    // Polling for batch status
    useEffect(() => {
        if (!batchId) return;

        const poll = async () => {
            try {
                const status = await getBatchStatus(batchId);
                setBatchStatus(status);
                if (status.status !== 'processing') {
                    if (pollRef.current) {
                        clearInterval(pollRef.current);
                        pollRef.current = null;
                    }
                }
            } catch {
                // silently retry on next interval
            }
        };

        poll(); // immediate first fetch
        pollRef.current = setInterval(poll, POLL_INTERVAL);

        return () => {
            if (pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        };
    }, [batchId]);

    const addFiles = useCallback((incoming: FileList | File[]) => {
        const arr = Array.from(incoming).filter(f => f.name.toLowerCase().endsWith(ACCEPTED_EXT));
        if (arr.length === 0) {
            setError('Only .docx files are accepted.');
            return;
        }
        setFiles(prev => {
            const combined = [...prev, ...arr];
            if (combined.length > MAX_FILES) {
                setError(`Maximum ${MAX_FILES} files allowed.`);
                return combined.slice(0, MAX_FILES);
            }
            setError(null);
            return combined;
        });
    }, []);

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files.length) {
            addFiles(e.dataTransfer.files);
        }
    }, [addFiles]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setIsDragOver(false);
    }, []);

    const handleUpload = async () => {
        if (files.length === 0) return;
        setUploading(true);
        setError(null);
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
        setFiles([]);
        setPlaybookId('');
        setBatchId(null);
        setBatchStatus(null);
        setError(null);
    };

    return (
        <div style={styles.page}>
            <AppHeader />
            <main style={styles.main}>
                <div>
                    <h1 style={styles.heading}>Batch Upload</h1>
                    <p style={styles.subheading}>
                        Upload multiple contracts for parallel AI analysis (max {MAX_FILES} files)
                    </p>
                </div>

                {/* Upload Section - shown when no batch is active */}
                {!batchId && (
                    <div style={styles.section}>
                        {/* Drop Zone */}
                        <div
                            style={styles.dropZone(isDragOver)}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div style={styles.dropIcon}>&#128196;</div>
                            <div style={styles.dropText}>
                                Drop .docx files here or click to browse
                            </div>
                            <div style={styles.dropHint}>
                                Up to {MAX_FILES} Word documents
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept={ACCEPTED_EXT}
                                multiple
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                    if (e.target.files) addFiles(e.target.files);
                                    e.target.value = '';
                                }}
                            />
                        </div>

                        {/* File List */}
                        {files.length > 0 && (
                            <div style={styles.fileList}>
                                {files.map((f, i) => (
                                    <div key={`${f.name}-${i}`} style={styles.fileItem}>
                                        <div>
                                            <span style={styles.fileName}>{f.name}</span>
                                            <span style={styles.fileSize}>{formatSize(f.size)}</span>
                                        </div>
                                        <button
                                            style={styles.removeBtn}
                                            onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                            title="Remove file"
                                        >
                                            &times;
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Controls */}
                        <div style={styles.row}>
                            <div style={styles.fieldGroup}>
                                <label style={styles.label}>Playbook (optional)</label>
                                <select
                                    style={styles.select}
                                    value={playbookId}
                                    onChange={(e) => setPlaybookId(e.target.value)}
                                >
                                    <option value="">No playbook</option>
                                    {playbooks?.map((p: Playbook) => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                style={styles.uploadBtn(files.length === 0 || uploading)}
                                disabled={files.length === 0 || uploading}
                                onClick={handleUpload}
                            >
                                {uploading ? 'Uploading...' : `Analyze ${files.length} File${files.length !== 1 ? 's' : ''}`}
                            </button>
                        </div>

                        {error && <div style={styles.errorBox}>{error}</div>}
                    </div>
                )}

                {/* Progress Section - shown when batch is active */}
                {batchId && (
                    <div style={styles.progressContainer}>
                        <div style={styles.progressHeader}>
                            <span style={styles.progressTitle}>
                                Batch Analysis
                            </span>
                            {batchStatus && (
                                <span style={styles.progressBadge(batchStatus.status)}>
                                    {batchStatus.status === 'completed' ? 'Completed' :
                                     batchStatus.status === 'partial_failure' ? 'Partial Failure' :
                                     'Processing'}
                                </span>
                            )}
                        </div>

                        {/* Progress Bar */}
                        <div style={styles.progressBarOuter}>
                            <div style={styles.progressBarInner(batchStatus?.overall_progress ?? 0)} />
                        </div>

                        {!batchStatus && (
                            <div style={{ textAlign: 'center', color: '#8A8885', fontSize: '14px', padding: '20px 0' }}>
                                Starting batch analysis...
                            </div>
                        )}

                        {/* File Status Grid */}
                        {batchStatus && (
                            <div style={styles.fileGrid}>
                                {batchStatus.files.map((f) => (
                                    <div key={f.filename} style={styles.fileCard(f.status)}>
                                        <div style={styles.fileCardName} title={f.filename}>
                                            {f.filename}
                                        </div>
                                        <div style={styles.fileCardStatus(f.status)}>
                                            {statusLabel(f.status)}
                                        </div>
                                        {f.status === 'completed' && f.risk_summary && (
                                            <div style={styles.riskRow}>
                                                <span style={styles.riskPill('red')}>
                                                    {f.risk_summary.red} Red
                                                </span>
                                                <span style={styles.riskPill('yellow')}>
                                                    {f.risk_summary.yellow} Yellow
                                                </span>
                                                <span style={styles.riskPill('green')}>
                                                    {f.risk_summary.total - f.risk_summary.red - f.risk_summary.yellow} Green
                                                </span>
                                            </div>
                                        )}
                                        {f.status === 'error' && f.error && (
                                            <div style={styles.errorText}>{f.error}</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        {batchStatus && batchStatus.status !== 'processing' && (
                            <button style={styles.newBatchBtn} onClick={handleReset}>
                                New Batch Upload
                            </button>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
