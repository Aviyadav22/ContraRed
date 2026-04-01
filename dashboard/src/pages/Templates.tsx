import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { listTemplates, downloadTemplate, type TemplateListItem } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Download, Eye, EyeOff, X } from 'lucide-react';

const CATEGORIES = [
    { value: '', label: 'All Categories' },
    { value: 'nda', label: 'NDA' },
    { value: 'msa', label: 'MSA' },
    { value: 'saas', label: 'SaaS' },
    { value: 'employment', label: 'Employment' },
    { value: 'custom', label: 'Other' },
];

const CATEGORY_BADGE: Record<string, 'nda' | 'msa' | 'saas' | 'employment' | 'neutral'> = {
    nda: 'nda',
    msa: 'msa',
    saas: 'saas',
    employment: 'employment',
    custom: 'neutral',
};

export default function Templates() {
    const [filterCategory, setFilterCategory] = useState('');
    const [previewId, setPreviewId] = useState<string | null>(null);
    const [previewContent, setPreviewContent] = useState<string | null>(null);
    const [downloading, setDownloading] = useState<string | null>(null);
    const [error, setError] = useState('');

    const { data: templates, isLoading } = useQuery({
        queryKey: ['templates', filterCategory],
        queryFn: () => listTemplates(filterCategory || undefined),
    });

    const handleDownload = async (template: TemplateListItem) => {
        setDownloading(template.id);
        try {
            const data = await downloadTemplate(template.id);
            const blob = new Blob([data.template_content || ''], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${template.name.replace(/[^a-zA-Z0-9]/g, '_')}.txt`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Download failed');
        } finally {
            setDownloading(null);
        }
    };

    const handlePreview = async (template: TemplateListItem) => {
        if (previewId === template.id) {
            setPreviewId(null);
            setPreviewContent(null);
            return;
        }
        setPreviewId(template.id);
        try {
            const data = await downloadTemplate(template.id);
            setPreviewContent(data.template_content || 'No content available');
        } catch (err) {
            setPreviewContent(err instanceof Error ? err.message : 'Failed to load preview');
        }
    };

    return (
        <AppLayout>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Template Library</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
                        Pre-built Indian contract templates paired with battle-tested playbooks
                    </p>
                </div>
                <div style={{ width: 200 }}>
                    <SelectInput value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
                        {CATEGORIES.map((cat) => (
                            <option key={cat.value} value={cat.value}>{cat.label}</option>
                        ))}
                    </SelectInput>
                </div>
            </div>

            {/* Error banner */}
            {error && (
                <div style={{
                    background: 'var(--risk-critical-bg)', border: '1px solid var(--risk-critical-border)',
                    color: 'var(--risk-critical)', padding: '10px 16px', borderRadius: 'var(--radius-md)',
                    marginBottom: 16, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                    <span>{error}</span>
                    <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--risk-critical)' }}>
                        <X size={16} />
                    </button>
                </div>
            )}

            {/* Loading */}
            {isLoading && (
                <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading templates...</div>
            )}

            {/* Empty State */}
            {!isLoading && (!templates || templates.length === 0) && (
                <div style={{ textAlign: 'center', padding: '48px 0' }}>
                    <h3 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text-secondary)' }}>No templates available</h3>
                    <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>
                        {filterCategory ? 'Try a different category filter' : 'Templates will appear here once created'}
                    </p>
                </div>
            )}

            {/* Templates Grid */}
            {templates && templates.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
                    {templates.map((template) => (
                        <Card key={template.id} variant="interactive">
                            {/* Category & Premium badges */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                <Badge variant={CATEGORY_BADGE[template.category] || 'neutral'}>
                                    {template.category.toUpperCase()}
                                </Badge>
                                {template.is_premium && <Badge variant="high">PREMIUM</Badge>}
                            </div>

                            {/* Name */}
                            <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
                                {template.name}
                            </h3>

                            {/* Description */}
                            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 16, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                {template.description || 'No description available'}
                            </p>

                            {/* Paired Playbook */}
                            {template.paired_playbook_name && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, fontSize: 14 }}>
                                    <span style={{ color: 'var(--text-muted)' }}>Paired with:</span>
                                    <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>{template.paired_playbook_name}</span>
                                </div>
                            )}

                            {/* Stats */}
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                                {template.download_count} downloads
                            </div>

                            {/* Actions */}
                            <div style={{ display: 'flex', gap: 8 }}>
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => handlePreview(template)}
                                    icon={previewId === template.id ? <EyeOff size={14} /> : <Eye size={14} />}
                                    style={{ flex: 1 }}
                                >
                                    {previewId === template.id ? 'Hide Preview' : 'Preview'}
                                </Button>
                                <Button
                                    size="sm"
                                    onClick={() => handleDownload(template)}
                                    loading={downloading === template.id}
                                    icon={<Download size={14} />}
                                    style={{ flex: 1 }}
                                >
                                    {downloading === template.id ? 'Downloading...' : 'Download'}
                                </Button>
                            </div>

                            {/* Preview panel */}
                            {previewId === template.id && previewContent && (
                                <div style={{
                                    marginTop: 16, padding: 12, borderTop: '1px solid var(--border)',
                                    backgroundColor: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
                                }}>
                                    <pre style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', maxHeight: 256, overflowY: 'auto', fontFamily: 'var(--font-mono)', margin: 0 }}>
                                        {previewContent}
                                    </pre>
                                </div>
                            )}
                        </Card>
                    ))}
                </div>
            )}
        </AppLayout>
    );
}
