export const RISK_LEVELS = [
    { value: 'red', label: 'Critical', className: 'bg-red-50 text-red-600' },
    { value: 'yellow', label: 'Warning', className: 'bg-amber-50 text-amber-600' },
    { value: 'green', label: 'Safe', className: 'bg-green-50 text-green-600' },
];

export const MATCH_TYPES = [
    { value: 'exact', label: 'Exact Match', hint: 'Auto-escapes for lawyers' },
    { value: 'fuzzy', label: 'Fuzzy Match', hint: 'Word boundary matching' },
    { value: 'regex', label: 'Regex', hint: 'For power users' },
];

export const DETECTION_MODES = [
    { value: 'keywords_only', label: 'Keywords Only', hint: 'Regex pattern matching' },
    { value: 'ai_with_keywords', label: 'AI + Keywords', hint: 'AI detection with keyword pre-filtering' },
    { value: 'ai_only', label: 'AI Only', hint: 'Pure AI detection for context-dependent rules' },
];

export const TIER_LABELS = ['Ideal', 'Acceptable', 'Walk-Away', 'Escalate'];

export const CONDITION_TYPES = [
    { value: 'counterparty_type', label: 'Counterparty Type' },
    { value: 'deal_size', label: 'Deal Size' },
    { value: 'jurisdiction', label: 'Jurisdiction' },
    { value: 'contract_side', label: 'Contract Side' },
];

export const OPERATORS = [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'in', label: 'In' },
    { value: 'greater_than', label: 'Greater Than' },
    { value: 'less_than', label: 'Less Than' },
    { value: 'between', label: 'Between' },
];

export const TRIGGER_CONDITIONS = [
    { value: 'source_is_red', label: 'Source is Red' },
    { value: 'source_is_yellow', label: 'Source is Yellow' },
    { value: 'source_missing', label: 'Source Missing' },
    { value: 'source_uncapped', label: 'Source Uncapped' },
    { value: 'source_deal_breaker', label: 'Source is Deal Breaker' },
];

export const EFFECTS = [
    { value: 'escalate_risk', label: 'Escalate Risk' },
    { value: 'add_flag', label: 'Add Flag' },
    { value: 'change_position', label: 'Change Position' },
    { value: 'suppress', label: 'Suppress' },
];

export const TABS = [
    { key: 'rules', label: 'Rules' },
    { key: 'conditions', label: 'Conditions' },
    { key: 'dependencies', label: 'Dependencies' },
    { key: 'history', label: 'History' },
    { key: 'analytics', label: 'Analytics' },
];

export const inputClass = "w-full px-3 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 outline-none bg-white focus:ring-2 focus:ring-slate-900 focus:border-transparent";
export const labelClass = "block text-[13px] font-semibold text-slate-700 mb-1.5";
