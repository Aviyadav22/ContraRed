import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { browseMarketplace, forkPlaybook, ratePlaybook, type MarketplaceItem } from '@/api/client';
import AppHeader from '@/components/AppHeader';

const categoryStyles: Record<string, string> = {
    saas: 'bg-blue-50 text-blue-600',
    nda: 'bg-purple-50 text-purple-600',
    dpa: 'bg-green-50 text-green-600',
    employment: 'bg-orange-50 text-orange-600',
    msa: 'bg-indigo-50 text-indigo-600',
    custom: 'bg-slate-100 text-slate-600',
};

const CATEGORIES = [
    { value: '', label: 'All Categories' },
    { value: 'saas', label: 'SaaS' },
    { value: 'nda', label: 'NDA' },
    { value: 'dpa', label: 'DPA' },
    { value: 'employment', label: 'Employment' },
    { value: 'msa', label: 'MSA' },
    { value: 'custom', label: 'Custom' },
];

function StarRating({
    rating,
    interactive = false,
    onRate,
}: {
    rating: number;
    interactive?: boolean;
    onRate?: (value: number) => void;
}) {
    const [hovered, setHovered] = useState(0);

    return (
        <div className="flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((star) => {
                const filled = interactive ? star <= (hovered || rating) : star <= Math.round(rating);
                return (
                    <button
                        key={star}
                        type="button"
                        disabled={!interactive}
                        className={`p-0 border-none bg-transparent ${interactive ? 'cursor-pointer' : 'cursor-default'}`}
                        onMouseEnter={() => interactive && setHovered(star)}
                        onMouseLeave={() => interactive && setHovered(0)}
                        onClick={() => interactive && onRate?.(star)}
                        aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                    >
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill={filled ? '#f59e0b' : 'none'}
                            stroke={filled ? '#f59e0b' : '#cbd5e1'}
                            strokeWidth={2}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                            />
                        </svg>
                    </button>
                );
            })}
        </div>
    );
}

export default function Marketplace() {
    const queryClient = useQueryClient();
    const [category, setCategory] = useState('');
    const [ratingTarget, setRatingTarget] = useState<string | null>(null);
    const [forkingId, setForkingId] = useState<string | null>(null);
    const [forkedMessage, setForkedMessage] = useState<string | null>(null);
    const [forkError, setForkError] = useState<string | null>(null);

    const { data: items, isLoading, error } = useQuery({
        queryKey: ['marketplace', category],
        queryFn: () => browseMarketplace(category || undefined),
    });

    const forkMutation = useMutation({
        mutationFn: forkPlaybook,
        onSuccess: (_data, marketplaceId) => {
            queryClient.invalidateQueries({ queryKey: ['playbooks'] });
            queryClient.invalidateQueries({ queryKey: ['marketplace'] });
            setForkingId(null);
            setForkError(null);
            setForkedMessage(marketplaceId);
            setTimeout(() => setForkedMessage(null), 3000);
        },
        onError: (err) => {
            setForkingId(null);
            setForkError(err instanceof Error ? err.message : 'Failed to fork playbook. Please try again.');
            setTimeout(() => setForkError(null), 5000);
        },
    });

    const rateMutation = useMutation({
        mutationFn: ({ id, rating }: { id: string; rating: number }) => ratePlaybook(id, rating),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['marketplace'] });
            setRatingTarget(null);
        },
    });

    const handleFork = (marketplaceId: string) => {
        setForkingId(marketplaceId);
        forkMutation.mutate(marketplaceId);
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <AppHeader />

            <main className="max-w-7xl mx-auto px-8 py-10">
                {/* Title row */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">Marketplace</h1>
                        <p className="text-sm text-slate-500 mt-1">
                            Browse and fork community playbooks to get started quickly.
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="px-3.5 py-2 rounded-lg border border-slate-200 text-sm text-slate-700 outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent bg-white"
                        >
                            {CATEGORIES.map((c) => (
                                <option key={c.value} value={c.value}>
                                    {c.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Fork success banner */}
                {forkedMessage && (
                    <div className="mb-6 bg-green-50 text-green-700 px-5 py-3 rounded-lg text-sm border border-green-200 flex items-center gap-2">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Playbook forked successfully! Check your Playbooks page.
                    </div>
                )}

                {/* Fork error banner */}
                {forkError && (
                    <div className="mb-6 bg-red-50 text-red-700 px-5 py-3 rounded-lg text-sm border border-red-200 flex items-center gap-2">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        {forkError}
                    </div>
                )}

                {/* Loading */}
                {isLoading && (
                    <div className="text-center py-16">
                        <div className="w-8 h-8 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto" />
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="bg-red-50 text-red-600 px-5 py-4 rounded-lg text-sm border border-red-200">
                        Error loading marketplace: {error instanceof Error ? error.message : 'Unknown error'}
                    </div>
                )}

                {/* Grid */}
                {items && items.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {items.map((item: MarketplaceItem) => {
                            const catStyle = categoryStyles[item.category] || categoryStyles.custom;
                            const isForking = forkingId === item.id;
                            const justForked = forkedMessage === item.id;

                            return (
                                <div
                                    key={item.id}
                                    className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col hover:shadow-md transition-shadow"
                                >
                                    {/* Header */}
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="text-sm font-semibold text-slate-900 truncate">
                                                    {item.playbook_name}
                                                </h3>
                                                {item.is_verified && (
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#3b82f6" className="flex-shrink-0" aria-label="Verified">
                                                        <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                                    </svg>
                                                )}
                                            </div>
                                            <span className={`inline-block px-2.5 py-0.5 text-xs font-semibold rounded-md ${catStyle}`}>
                                                {item.category}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Description */}
                                    <p className="text-[13px] text-slate-500 mb-4 line-clamp-2 flex-1">
                                        {item.description || 'No description provided.'}
                                    </p>

                                    {/* Tags */}
                                    {item.tags && item.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5 mb-4">
                                            {item.tags.slice(0, 4).map((tag) => (
                                                <span
                                                    key={tag}
                                                    className="px-2 py-0.5 text-[11px] font-medium text-slate-500 bg-slate-50 rounded-md border border-slate-100"
                                                >
                                                    {tag}
                                                </span>
                                            ))}
                                            {item.tags.length > 4 && (
                                                <span className="px-2 py-0.5 text-[11px] font-medium text-slate-400">
                                                    +{item.tags.length - 4} more
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Stats row */}
                                    <div className="flex items-center gap-4 mb-4 text-[13px] text-slate-500">
                                        <div className="flex items-center gap-1">
                                            <StarRating rating={item.avg_rating} />
                                            <span className="ml-1">
                                                {item.avg_rating.toFixed(1)}
                                            </span>
                                            <span className="text-slate-400">
                                                ({item.rating_count})
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                            </svg>
                                            {item.download_count}
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
                                        <button
                                            onClick={() => handleFork(item.id)}
                                            disabled={isForking || justForked}
                                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-60"
                                        >
                                            {isForking ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                    Forking...
                                                </>
                                            ) : justForked ? (
                                                <>
                                                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                    Forked
                                                </>
                                            ) : (
                                                <>
                                                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                                    </svg>
                                                    Fork
                                                </>
                                            )}
                                        </button>
                                        <button
                                            onClick={() => setRatingTarget(ratingTarget === item.id ? null : item.id)}
                                            className="px-3 py-2 text-sm font-medium text-slate-600 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
                                            aria-label="Rate this playbook"
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                                                />
                                            </svg>
                                        </button>
                                    </div>

                                    {/* Rating picker */}
                                    {ratingTarget === item.id && (
                                        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2">
                                            <span className="text-[13px] text-slate-500">Your rating:</span>
                                            <StarRating
                                                rating={0}
                                                interactive
                                                onRate={(value) => rateMutation.mutate({ id: item.id, rating: value })}
                                            />
                                            {rateMutation.isPending && (
                                                <div className="w-4 h-4 border-2 border-slate-200 border-t-slate-600 rounded-full animate-spin" />
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Empty State */}
                {items && items.length === 0 && (
                    <div className="text-center py-16 px-8 bg-white rounded-xl border border-slate-200">
                        <svg width="48" height="48" fill="none" stroke="#cbd5e1" viewBox="0 0 24 24" className="mx-auto mb-4">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                        <h3 className="text-lg font-semibold text-slate-900 mb-2">No playbooks in the marketplace</h3>
                        <p className="text-sm text-slate-500">
                            {category
                                ? `No playbooks found in the "${category}" category. Try a different category.`
                                : 'No public playbooks have been published yet. Check back later!'}
                        </p>
                    </div>
                )}
            </main>
        </div>
    );
}
