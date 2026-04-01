import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { browseMarketplace, forkPlaybook, ratePlaybook, type MarketplaceItem } from '@/api/client';
import { AppLayout } from '@/components/layout';
import { Button, Card, Badge, SelectInput } from '@/components/ui';
import { Copy, Check, Star, X, ShieldCheck, Download, Package } from 'lucide-react';

const categoryToBadge: Record<string, 'saas' | 'nda' | 'dpa' | 'employment' | 'msa' | 'neutral'> = {
    saas: 'saas', nda: 'nda', dpa: 'dpa', employment: 'employment', msa: 'msa', custom: 'neutral',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {[1, 2, 3, 4, 5].map((star) => {
                const filled = interactive ? star <= (hovered || rating) : star <= Math.round(rating);
                return (
                    <button
                        key={star}
                        type="button"
                        disabled={!interactive}
                        style={{ padding: 0, border: 'none', background: 'transparent', cursor: interactive ? 'pointer' : 'default' }}
                        onMouseEnter={() => interactive && setHovered(star)}
                        onMouseLeave={() => interactive && setHovered(0)}
                        onClick={() => interactive && onRate?.(star)}
                        aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
                    >
                        <Star size={16} fill={filled ? '#f59e0b' : 'none'} stroke={filled ? '#f59e0b' : 'var(--text-muted)'} />
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
            setForkingId(null); setForkError(null);
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
        onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['marketplace'] }); setRatingTarget(null); },
    });

    const handleFork = (marketplaceId: string) => {
        setForkingId(marketplaceId);
        forkMutation.mutate(marketplaceId);
    };

    return (
        <AppLayout>
            {/* Title row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Marketplace</h1>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
                        Browse and fork community playbooks to get started quickly.
                    </p>
                </div>
                <div style={{ width: 200 }}>
                    <SelectInput value={category} onChange={(e) => setCategory(e.target.value)}>
                        {CATEGORIES.map((c) => (<option key={c.value} value={c.value}>{c.label}</option>))}
                    </SelectInput>
                </div>
            </div>

            {/* Fork success banner */}
            {forkedMessage && (
                <div style={{
                    marginBottom: 24, background: 'var(--risk-low-bg)', color: 'var(--risk-low)',
                    padding: '12px 20px', borderRadius: 'var(--radius-md)', fontSize: 14,
                    border: '1px solid var(--risk-low-border)', display: 'flex', alignItems: 'center', gap: 8,
                }}>
                    <Check size={16} /> Playbook forked successfully! Check your Playbooks page.
                </div>
            )}

            {/* Fork error banner */}
            {forkError && (
                <div style={{
                    marginBottom: 24, background: 'var(--risk-critical-bg)', color: 'var(--risk-critical)',
                    padding: '12px 20px', borderRadius: 'var(--radius-md)', fontSize: 14,
                    border: '1px solid var(--risk-critical-border)', display: 'flex', alignItems: 'center', gap: 8,
                }}>
                    <X size={16} /> {forkError}
                </div>
            )}

            {/* Loading */}
            {isLoading && (
                <div style={{ textAlign: 'center', padding: '64px 0' }}>
                    <div style={{
                        width: 32, height: 32, border: '2px solid var(--border)',
                        borderTopColor: 'var(--accent)', borderRadius: '50%',
                        animation: 'spin 1s linear infinite', margin: '0 auto',
                    }} />
                </div>
            )}

            {/* Error */}
            {error && (
                <div style={{
                    background: 'var(--risk-critical-bg)', color: 'var(--risk-critical)',
                    padding: '12px 20px', borderRadius: 'var(--radius-md)', fontSize: 14,
                    border: '1px solid var(--risk-critical-border)',
                }}>
                    Error loading marketplace: {error instanceof Error ? error.message : 'Unknown error'}
                </div>
            )}

            {/* Grid */}
            {items && items.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
                    {items.map((item: MarketplaceItem) => {
                        const badgeVariant = categoryToBadge[item.category] || 'neutral';
                        const isForking = forkingId === item.id;
                        const justForked = forkedMessage === item.id;

                        return (
                            <Card key={item.id} variant="interactive" style={{ display: 'flex', flexDirection: 'column' }}>
                                {/* Header */}
                                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                            <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {item.playbook_name}
                                            </h3>
                                            {item.is_verified && <ShieldCheck size={16} style={{ color: 'var(--info)', flexShrink: 0 }} />}
                                        </div>
                                        <Badge variant={badgeVariant}>{item.category}</Badge>
                                    </div>
                                </div>

                                {/* Description */}
                                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, flex: 1, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {item.description || 'No description provided.'}
                                </p>

                                {/* Tags */}
                                {item.tags && item.tags.length > 0 && (
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                                        {item.tags.slice(0, 4).map((tag) => (
                                            <span key={tag} style={{
                                                padding: '2px 8px', fontSize: 11, fontWeight: 500,
                                                color: 'var(--text-muted)', backgroundColor: 'var(--bg-elevated)',
                                                borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
                                            }}>
                                                {tag}
                                            </span>
                                        ))}
                                        {item.tags.length > 4 && (
                                            <span style={{ padding: '2px 8px', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)' }}>
                                                +{item.tags.length - 4} more
                                            </span>
                                        )}
                                    </div>
                                )}

                                {/* Stats row */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16, fontSize: 13, color: 'var(--text-muted)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <StarRating rating={item.avg_rating} />
                                        <span style={{ marginLeft: 4 }}>{item.avg_rating.toFixed(1)}</span>
                                        <span style={{ color: 'var(--text-muted)' }}>({item.rating_count})</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        <Download size={14} /> {item.download_count}
                                    </div>
                                </div>

                                {/* Actions */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                                    <Button
                                        onClick={() => handleFork(item.id)}
                                        disabled={isForking || justForked}
                                        loading={isForking}
                                        icon={justForked ? <Check size={14} /> : <Copy size={14} />}
                                        style={{ flex: 1 }}
                                    >
                                        {isForking ? 'Forking...' : justForked ? 'Forked' : 'Fork'}
                                    </Button>
                                    <Button
                                        variant="secondary"
                                        onClick={() => setRatingTarget(ratingTarget === item.id ? null : item.id)}
                                        icon={<Star size={16} />}
                                        aria-label="Rate this playbook"
                                    />
                                </div>

                                {/* Rating picker */}
                                {ratingTarget === item.id && (
                                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Your rating:</span>
                                        <StarRating rating={0} interactive onRate={(value) => rateMutation.mutate({ id: item.id, rating: value })} />
                                        {rateMutation.isPending && (
                                            <div style={{
                                                width: 16, height: 16, border: '2px solid var(--border)',
                                                borderTopColor: 'var(--accent)', borderRadius: '50%',
                                                animation: 'spin 1s linear infinite',
                                            }} />
                                        )}
                                    </div>
                                )}
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Empty State */}
            {items && items.length === 0 && (
                <div style={{
                    textAlign: 'center', padding: '64px 32px',
                    backgroundColor: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border)',
                }}>
                    <Package size={48} style={{ color: 'var(--text-muted)', marginBottom: 16 }} />
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>No playbooks in the marketplace</h3>
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                        {category
                            ? `No playbooks found in the "${category}" category. Try a different category.`
                            : 'No public playbooks have been published yet. Check back later!'}
                    </p>
                </div>
            )}
        </AppLayout>
    );
}
