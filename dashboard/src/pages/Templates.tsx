import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { listTemplates, downloadTemplate, type TemplateListItem } from '@/api/client';
import AppHeader from '@/components/AppHeader';

const CATEGORIES = [
    { value: '', label: 'All Categories' },
    { value: 'nda', label: 'NDA' },
    { value: 'msa', label: 'MSA' },
    { value: 'saas', label: 'SaaS' },
    { value: 'employment', label: 'Employment' },
    { value: 'custom', label: 'Other' },
];

const CATEGORY_COLORS: Record<string, string> = {
    nda: 'bg-blue-100 text-blue-700',
    msa: 'bg-purple-100 text-purple-700',
    saas: 'bg-green-100 text-green-700',
    employment: 'bg-orange-100 text-orange-700',
    custom: 'bg-slate-100 text-slate-700',
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
            // Create a downloadable text file
            const blob = new Blob([data.template_content || ''], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${template.name.replace(/[^a-zA-Z0-9]/g, '_')}.docx`;
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
        <div className="min-h-screen bg-slate-50">
            <AppHeader />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Template Library</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            Pre-built Indian contract templates paired with battle-tested playbooks
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <select
                            value={filterCategory}
                            onChange={(e) => setFilterCategory(e.target.value)}
                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        >
                            {CATEGORIES.map((cat) => (
                                <option key={cat.value} value={cat.value}>{cat.label}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Error banner */}
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg mb-4 text-sm flex items-center justify-between">
                        <span>{error}</span>
                        <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-red-600 font-bold">&times;</button>
                    </div>
                )}

                {/* Loading */}
                {isLoading && (
                    <div className="text-center py-12 text-slate-400">Loading templates...</div>
                )}

                {/* Empty State */}
                {!isLoading && (!templates || templates.length === 0) && (
                    <div className="text-center py-12">
                        <div className="text-4xl mb-4">📄</div>
                        <h3 className="text-lg font-medium text-slate-600">No templates available</h3>
                        <p className="text-sm text-slate-400 mt-1">
                            {filterCategory ? 'Try a different category filter' : 'Templates will appear here once created'}
                        </p>
                    </div>
                )}

                {/* Templates Grid */}
                {templates && templates.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {templates.map((template) => (
                            <div
                                key={template.id}
                                className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
                            >
                                <div className="p-5">
                                    {/* Category & Premium badges */}
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[template.category] || CATEGORY_COLORS.custom}`}>
                                            {template.category.toUpperCase()}
                                        </span>
                                        {template.is_premium && (
                                            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                                                PREMIUM
                                            </span>
                                        )}
                                    </div>

                                    {/* Name */}
                                    <h3 className="text-lg font-semibold text-slate-900 mb-2">
                                        {template.name}
                                    </h3>

                                    {/* Description */}
                                    <p className="text-sm text-slate-500 mb-4 line-clamp-3">
                                        {template.description || 'No description available'}
                                    </p>

                                    {/* Paired Playbook */}
                                    {template.paired_playbook_name && (
                                        <div className="flex items-center gap-2 mb-4 text-sm text-slate-600">
                                            <span className="text-slate-400">Paired with:</span>
                                            <span className="font-medium">{template.paired_playbook_name}</span>
                                        </div>
                                    )}

                                    {/* Stats */}
                                    <div className="flex items-center justify-between text-xs text-slate-400 mb-4">
                                        <span>{template.download_count} downloads</span>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handlePreview(template)}
                                            className="flex-1 px-3 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
                                        >
                                            {previewId === template.id ? 'Hide Preview' : 'Preview'}
                                        </button>
                                        <button
                                            onClick={() => handleDownload(template)}
                                            disabled={downloading === template.id}
                                            className="flex-1 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                                        >
                                            {downloading === template.id ? 'Downloading...' : 'Download'}
                                        </button>
                                    </div>
                                </div>

                                {/* Preview panel */}
                                {previewId === template.id && previewContent && (
                                    <div className="border-t border-slate-200 bg-slate-50 p-4">
                                        <pre className="text-xs text-slate-600 whitespace-pre-wrap max-h-64 overflow-y-auto font-mono">
                                            {previewContent}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
