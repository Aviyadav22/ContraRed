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
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
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
        const oversized = arr.filter(f => f.size > MAX_FILE_SIZE);
        const valid = arr.filter(f => f.size <= MAX_FILE_SIZE);
        if (oversized.length > 0) {
            setError(`${oversized.length} file(s) exceed 20MB limit and were excluded.`);
        }
        if (valid.length === 0) {
            return;
        }
        setFiles(prev => {
            const combined = [...prev, ...valid];
            if (combined.length > MAX_FILES) {
                setTimeout(() => setError(`Maximum ${MAX_FILES} files allowed.`), 0);
                return combined.slice(0, MAX_FILES);
            }
            if (oversized.length === 0) {
                setTimeout(() => setError(null), 0);
            }
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
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
        setFiles([]);
        setPlaybookId('');
        setBatchId(null);
        setBatchStatus(null);
        setError(null);
    };

    return (
        <div className="min-h-screen" style={{ background: '#FAFAF9' }}>
            <AppHeader />
            <main className="max-w-[960px] mx-auto px-6 py-8">
                <div>
                    <h1 className="text-2xl font-bold text-[#1a1a1a] m-0">Batch Upload</h1>
                    <p className="text-sm text-[#6B6760] mt-1">
                        Upload multiple contracts for parallel AI analysis (max {MAX_FILES} files)
                    </p>
                </div>

                {/* Upload Section - shown when no batch is active */}
                {!batchId && (
                    <div className="mt-6">
                        {/* Drop Zone */}
                        <div
                            className={`border-2 border-dashed rounded-xl py-12 px-6 text-center cursor-pointer transition-colors ${
                                isDragOver ? 'border-[#C0392B] bg-red-50' : 'border-[#E8E5E0] bg-white'
                            }`}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div className="text-[40px] text-[#8A8885] mb-2">&#128196;</div>
                            <div className="text-[15px] font-medium text-[#1a1a1a]">
                                Drop .docx files here or click to browse
                            </div>
                            <div className="text-[13px] text-[#8A8885] mt-1">
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
                            <div className="mt-4 flex flex-col gap-2">
                                {files.map((f, i) => (
                                    <div key={`${f.name}-${i}`} className="flex items-center justify-between bg-white border border-[#E8E5E0] rounded-lg px-3.5 py-2.5">
                                        <div>
                                            <span className="text-sm font-medium text-[#1a1a1a]">{f.name}</span>
                                            <span className="text-xs text-[#8A8885] ml-2">{formatSize(f.size)}</span>
                                        </div>
                                        <button
                                            className="bg-transparent border-none text-lg text-[#8A8885] cursor-pointer px-1 leading-none"
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
                        <div className="flex items-end gap-4 mt-5">
                            <div className="flex flex-col flex-1 max-w-[300px]">
                                <label className="text-xs font-medium text-[#6B6760] mb-1">Playbook (optional)</label>
                                <select
                                    className="px-3 py-2 border border-[#E8E5E0] rounded-lg text-sm text-[#1a1a1a] bg-white"
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
                                className={`px-6 py-2 rounded-lg text-sm font-semibold border-none ${
                                    files.length === 0 || uploading
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-[#C0392B] text-white cursor-pointer'
                                }`}
                                disabled={files.length === 0 || uploading}
                                onClick={handleUpload}
                            >
                                {uploading ? 'Uploading...' : `Analyze ${files.length} File${files.length !== 1 ? 's' : ''}`}
                            </button>
                        </div>

                        {error && <div className="mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-[#C0392B] text-sm">{error}</div>}
                    </div>
                )}

                {/* Progress Section - shown when batch is active */}
                {batchId && (
                    <div className="mt-6 bg-white border border-[#E8E5E0] rounded-xl p-6">
                        <div className="flex justify-between items-center mb-4">
                            <span className="text-base font-semibold text-[#1a1a1a]">
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
                        <div className="w-full h-2 bg-[#E8E5E0] rounded overflow-hidden mb-5">
                            <div
                                className="h-full bg-[#C0392B] rounded transition-all duration-400"
                                style={{ width: `${batchStatus?.overall_progress ?? 0}%` }}
                            />
                        </div>

                        {!batchStatus && (
                            <div className="text-center text-[#8A8885] text-sm py-5">
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
                            <button
                                className="mt-5 px-5 py-2 bg-white text-[#1a1a1a] border border-[#E8E5E0] rounded-lg text-sm font-medium cursor-pointer hover:bg-slate-50"
                                onClick={handleReset}
                            >
                                New Batch Upload
                            </button>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
