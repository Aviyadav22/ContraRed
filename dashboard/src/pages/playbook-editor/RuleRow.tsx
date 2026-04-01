import { useState } from 'react';
import { type PlaybookRule, type RuleTier } from '@/api/client';
import { RISK_LEVELS, TIER_LABELS, inputClass } from './constants';

export interface RuleRowProps {
    rule: PlaybookRule;
    riskLevel: { value: string; label: string; className: string };
    isExpanded: boolean;
    tiersLoading: boolean;
    tiers: RuleTier[] | undefined;
    tierDrafts: Record<number, { position_text: string; guidance_notes: string; risk_level_at_tier: string }>;
    onToggleExpand: () => void;
    onEdit: () => void;
    onDelete: () => void;
    onSyncTiers: () => void;
    onTierChange: (level: number, field: string, value: string) => void;
    onSaveTiers: () => void;
    tiersSaving: boolean;
}

export function RuleRow({
    rule, riskLevel, isExpanded, tiersLoading, tiers, tierDrafts,
    onToggleExpand, onEdit, onDelete, onSyncTiers, onTierChange, onSaveTiers, tiersSaving,
}: RuleRowProps) {
    // Sync tier drafts when tiers finish loading
    const prevTiersRef = useState<RuleTier[] | undefined>(undefined);
    if (isExpanded && tiers && tiers !== prevTiersRef[0] && Object.keys(tierDrafts).length === 0) {
        prevTiersRef[0] = tiers;
        // schedule sync for next microtask to avoid setState during render
        Promise.resolve().then(onSyncTiers);
    }

    return (
        <>
            <tr
                className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${isExpanded ? 'bg-slate-50' : ''}`}
                onClick={onToggleExpand}
            >
                <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                        <svg
                            width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            className={`transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        <span className="font-semibold text-slate-900 text-sm">{rule.clause_type}</span>
                        {rule.is_deal_breaker && (
                            <span className="ml-1 text-[11px] font-bold bg-red-50 text-red-600 px-1.5 py-0.5 rounded">
                                DEAL BREAKER
                            </span>
                        )}
                        {rule.detection_mode && rule.detection_mode !== 'keywords_only' && (
                            <span className={`ml-1 px-1.5 py-0.5 text-xs rounded ${
                                rule.detection_mode === 'ai_only'
                                    ? 'bg-purple-50 text-purple-600'
                                    : 'bg-blue-50 text-blue-600'
                            }`}>
                                {rule.detection_mode === 'ai_only' ? 'AI' : 'AI+KW'}
                            </span>
                        )}
                    </div>
                </td>
                <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-semibold rounded-md ${riskLevel.className}`}>
                        {riskLevel.label}
                    </span>
                </td>
                <td className="px-6 py-4 text-[13px] text-slate-500">{rule.match_type}</td>
                <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1 max-w-[260px]">
                        {rule.detection_patterns.slice(0, 3).map((p, i) => (
                            <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{p}</span>
                        ))}
                        {rule.detection_patterns.length > 3 && (
                            <span className="text-xs text-slate-400">+{rule.detection_patterns.length - 3} more</span>
                        )}
                    </div>
                </td>
                <td className="px-6 py-4 text-right">
                    <button
                        onClick={(e) => { e.stopPropagation(); onEdit(); }}
                        className="text-[13px] font-semibold text-blue-600 bg-transparent border-none cursor-pointer hover:text-blue-700 mr-3"
                    >
                        Edit
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onDelete(); }}
                        className="text-[13px] font-semibold text-red-600 bg-transparent border-none cursor-pointer hover:text-red-700"
                    >
                        Delete
                    </button>
                </td>
            </tr>

            {/* Expanded Tier Accordion */}
            {isExpanded && (
                <tr>
                    <td colSpan={5} className="px-0 py-0">
                        <div className="bg-slate-50 border-b border-slate-200 px-10 py-6">
                            <h4 className="text-sm font-bold text-slate-900 mb-4">Negotiation Tiers</h4>
                            {tiersLoading ? (
                                <div className="flex items-center gap-2 py-4">
                                    <div className="w-4 h-4 border-2 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
                                    <span className="text-sm text-slate-500">Loading tiers...</span>
                                </div>
                            ) : (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {[1, 2, 3, 4].map(level => {
                                            const draft = tierDrafts[level] || { position_text: '', guidance_notes: '', risk_level_at_tier: 'green' };
                                            const tierLabel = TIER_LABELS[level - 1];
                                            const tierColors: Record<number, string> = {
                                                1: 'border-l-green-500',
                                                2: 'border-l-blue-500',
                                                3: 'border-l-amber-500',
                                                4: 'border-l-red-500',
                                            };
                                            return (
                                                <div key={level} className={`bg-white rounded-lg border border-slate-200 border-l-4 ${tierColors[level]} p-4`}>
                                                    <div className="flex items-center justify-between mb-3">
                                                        <span className="text-[13px] font-bold text-slate-900">{tierLabel}</span>
                                                        <select
                                                            value={draft.risk_level_at_tier}
                                                            onChange={(e) => onTierChange(level, 'risk_level_at_tier', e.target.value)}
                                                            className="px-2 py-1 text-xs rounded border border-slate-200 text-slate-700 outline-none bg-white focus:ring-1 focus:ring-slate-900"
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            {RISK_LEVELS.map(rl => (
                                                                <option key={rl.value} value={rl.value}>{rl.label}</option>
                                                            ))}
                                                        </select>
                                                    </div>
                                                    <div className="mb-3">
                                                        <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Position Text</label>
                                                        <textarea
                                                            value={draft.position_text}
                                                            onChange={(e) => onTierChange(level, 'position_text', e.target.value)}
                                                            onClick={(e) => e.stopPropagation()}
                                                            className={`${inputClass} min-h-[60px] text-xs`}
                                                            placeholder={`${tierLabel} position language...`}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Guidance Notes</label>
                                                        <textarea
                                                            value={draft.guidance_notes}
                                                            onChange={(e) => onTierChange(level, 'guidance_notes', e.target.value)}
                                                            onClick={(e) => e.stopPropagation()}
                                                            className={`${inputClass} min-h-[60px] text-xs`}
                                                            placeholder="Internal guidance for negotiators..."
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                    <div className="flex justify-end mt-4">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onSaveTiers(); }}
                                            disabled={tiersSaving}
                                            className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                                        >
                                            {tiersSaving ? 'Saving...' : 'Save Tiers'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}
