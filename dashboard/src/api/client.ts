/**
 * ContraRed Dashboard API Client
 * Shares authentication patterns with Word Add-in
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Warn if API URL is not configured (app still loads, API calls will fail gracefully)
if (!API_BASE_URL) {
    console.error('VITE_API_URL is not configured. API calls will fail.');
}

// Warn if localhost is used in production (HTTPS context)
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && API_BASE_URL.includes('localhost')) {
    console.error('VITE_API_URL points to localhost in production. Set the environment variable to the production API URL.');
}

// ============================================================================
// Types
// ============================================================================

export interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    subscription_tier: string;
}

export interface AuthTokens {
    access_token: string;
    refresh_token: string;
}

export interface Playbook {
    id: string;
    name: string;
    description?: string;
    category: string;
    is_public: boolean;
    is_default: boolean;
    version: number;
    rules_count: number;
    /** True when the requesting user owns this playbook — drives Edit/Delete UI. */
    is_owner?: boolean;
}

export interface PlaybookRule {
    id: string;
    clause_type: string;
    primary_position: string;
    fallback_position?: string;
    risk_level: string;
    is_deal_breaker: boolean;
    detection_patterns: string[];
    match_type: string;
    suggested_language?: string;
    order_index: number;
    detection_mode: string;
    risk_description?: string;
    acceptable_position?: string;
    unacceptable_signals?: string[];
    acceptable_signals?: string[];
    clause_context?: string;
}

export interface PlaybookDetail extends Playbook {
    rules: PlaybookRule[];
}

export interface CreatePlaybookData {
    name: string;
    description?: string;
    category?: string;
    is_public?: boolean;
}

export interface CreateRuleData {
    clause_type: string;
    primary_position: string;
    fallback_position?: string;
    risk_level?: string;
    is_deal_breaker?: boolean;
    detection_patterns?: string[];
    match_type?: string;
    suggested_language?: string;
    detection_mode?: string;
    risk_description?: string;
    acceptable_position?: string;
    unacceptable_signals?: string[];
    acceptable_signals?: string[];
    clause_context?: string;
}

export interface ClauseLibraryItem {
    id: string;
    clause_type: string;
    name: string;
    approved_text: string;
    is_mandatory: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface CreateClauseData {
    clause_type: string;
    name: string;
    approved_text: string;
    is_mandatory?: boolean;
}

// ============================================================================
// Redline Analysis Types
// ============================================================================

export interface RedlineItem {
    id: string;
    risk_level: 'RED' | 'YELLOW' | 'GREEN';
    rule_name: string;
    clause_text: string;
    clause_type: string;
    explanation: string;
    recommendation: string;
    suggested_fix?: string;
    fix_edits?: Array<{ find: string; replace: string }>;
    fix_reasoning?: string;
    fix_verified?: boolean;
    fix_warnings?: string[];
    redline_type: 'violation' | 'missing';
    confidence?: number;
    confidence_level?: string;
    confidence_breakdown?: Record<string, number>;
    verification_status?: string;
    is_deal_breaker: boolean;
    cross_references?: string[];
    statutory_references?: string[];
    paragraph_index?: number;
}

export interface AnalysisResult {
    document_id: string;
    filename: string;
    executive_summary: string[];
    risks: RedlineItem[];
    total_risks: number;
    risk_summary: { red: number; yellow: number; green: number };
    tokens_used: number;
    jurisdiction?: string;
    jurisdiction_name?: string;
    pipeline_partial: boolean;
    ai_used?: boolean;
    hallucination_stats?: Record<string, unknown>;
    compliance_scores?: Record<string, Record<string, unknown>>;
}

export interface GenerateFixResponse {
    fix_text: string;
    fix_edits?: Array<{ find: string; replace: string }>;
    reasoning: string;
    fix_verified: boolean;
    fix_warnings?: string[];
    fix_source?: 'clause_library' | 'clause_library_adapted' | 'ai_generated';
}

// ============================================================================
// Auth Storage (cookies for tokens, localStorage for user profile only)
// ============================================================================

const USER_KEY = 'contrared_user';

function getCsrfToken(): string {
    // sessionStorage so the token doesn't outlive the tab (B7).
    // Migrate any prior localStorage value on first read.
    let stored = sessionStorage.getItem('contrared_csrf');
    if (!stored) {
        const legacy = localStorage.getItem('contrared_csrf');
        if (legacy) {
            sessionStorage.setItem('contrared_csrf', legacy);
            localStorage.removeItem('contrared_csrf');
            stored = legacy;
        }
    }
    if (stored) return stored;
    // Fallback: try cookie (same-origin scenarios)
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
}

function setCsrfToken(token: string): void {
    sessionStorage.setItem('contrared_csrf', token);
}

export function getStoredTokens(): AuthTokens | null {
    // Tokens are in HttpOnly cookies (not accessible to JS).
    // Return a sentinel so isAuthenticated() checks user profile instead.
    const user = getStoredUser();
    return user ? { access_token: '__httponly__', refresh_token: '__httponly__' } : null;
}

export function getStoredUser(): User | null {
    try {
        // Try sessionStorage first, migrate from localStorage if needed
        const stored = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
        if (!stored) return null;
        const user = JSON.parse(stored);
        // Migrate from localStorage to sessionStorage
        if (localStorage.getItem(USER_KEY)) {
            sessionStorage.setItem(USER_KEY, stored);
            localStorage.removeItem(USER_KEY);
        }
        return user;
    } catch {
        return null;
    }
}

export function saveAuth(_tokens: AuthTokens, user: User): void {
    // Tokens are stored in HttpOnly cookies by the server.
    // Only store non-sensitive user profile in sessionStorage (ephemeral).
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
    sessionStorage.removeItem(USER_KEY);
    localStorage.removeItem(USER_KEY);  // Clean up any legacy data
    sessionStorage.removeItem('contrared_csrf');
    localStorage.removeItem('contrared_csrf');  // Clean up any legacy data
}

export function isAuthenticated(): boolean {
    return !!getStoredUser();
}

// AUDIT M4 VERIFIED: This is a UI-only gate for showing/hiding admin controls.
// All admin data and actions are enforced server-side via require_admin/require_permission.
// Tampering with localStorage role gives no access to protected data or operations.
export function isAdmin(): boolean {
    const user = getStoredUser();
    return user?.role === 'admin' || user?.role === 'super_admin';
}

// ============================================================================
// API Request Helper
// ============================================================================

// Mutex for token refresh — prevents thundering-herd refreshes when many
// requests fire and all hit 401 simultaneously (B8).
let inFlightRefresh: Promise<boolean> | null = null;

async function refreshAuth(): Promise<boolean> {
    if (inFlightRefresh) return inFlightRefresh;
    inFlightRefresh = (async () => {
        try {
            const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            });
            if (refreshResp.ok) {
                const data = await refreshResp.clone().json().catch(() => ({}));
                if (data?.csrf_token) setCsrfToken(data.csrf_token);
                return true;
            }
            return false;
        } catch {
            return false;
        } finally {
            inFlightRefresh = null;
        }
    })();
    return inFlightRefresh;
}

async function request<T>(endpoint: string, options: RequestInit = {}, retryCount: number = 0, timeoutMs: number = 120000): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
    };

    // Add CSRF token for state-changing requests (cookie-based auth)
    const method = (options.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
        const csrf = getCsrfToken();
        if (csrf) headers['X-CSRF-Token'] = csrf;
    }

    const url = `${API_BASE_URL}${endpoint}`;

    // AbortController timeout: configurable, default 2 minutes
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    let response: Response;
    try {
        response = await fetch(url, {
            ...options,
            headers,
            credentials: 'include',
            signal: controller.signal,
        });
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof DOMException && err.name === 'AbortError') {
            const mins = Math.round(timeoutMs / 60000);
            throw new Error(`Request timed out after ${mins} minute${mins > 1 ? 's' : ''}. The server may be slow or unreachable.`);
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }

    // Retry on 429 or 5xx with exponential backoff (max 2 retries)
    const MAX_RETRIES = 2;
    if (retryCount < MAX_RETRIES && (response.status === 429 || response.status >= 500)) {
        const delay = Math.pow(2, retryCount) * 1000; // 1s, 2s
        await new Promise(resolve => setTimeout(resolve, delay));
        return request<T>(endpoint, options, retryCount + 1, timeoutMs);
    }

    if (!response.ok) {
        if (response.status === 401) {
            // Cookie-based refresh, deduped via mutex (B8).
            const refreshed = await refreshAuth();
            if (refreshed) {
                const retryHeaders: Record<string, string> = { ...headers };
                const newCsrf = getCsrfToken();
                if (newCsrf) retryHeaders['X-CSRF-Token'] = newCsrf;
                const retryResp = await fetch(url, {
                    ...options,
                    headers: retryHeaders,
                    credentials: 'include',
                });
                if (retryResp.ok || retryResp.status !== 401) {
                    if (retryResp.status === 204) return undefined as T;
                    return retryResp.json();
                }
            }
            clearAuth();
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));

        // Intercept 403 consent_required — prompt user and retry on grant
        if (response.status === 403 && error?.error === 'consent_required' && Array.isArray(error.required_purposes)) {
            const { requestConsent } = await import('./consentPrompt');
            await requestConsent(error.required_purposes);
            // User granted consent — retry the original request
            return request<T>(endpoint, options, 0, timeoutMs);
        }

        // Sanitize error messages to prevent backend detail leakage
        const MAX_ERROR_LENGTH = 200;
        const rawDetail = typeof error === 'object' && error !== null ? (error as any).detail : String(error);
        let detailStr: string;
        if (typeof rawDetail === 'string') {
            detailStr = rawDetail;
        } else if (typeof rawDetail === 'object' && rawDetail !== null && typeof (rawDetail as any).message === 'string') {
            // Structured error payload (e.g. quota_exceeded) — surface the human-readable message
            detailStr = (rawDetail as any).message;
        } else {
            detailStr = 'An unexpected error occurred';
        }
        const err = new Error(detailStr.substring(0, MAX_ERROR_LENGTH));
        // Attach structured payload so callers can branch on error_code (quota_exceeded, etc.)
        if (typeof rawDetail === 'object' && rawDetail !== null) {
            (err as any).detail = rawDetail;
            (err as any).status = response.status;
        }
        throw err;
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

// ============================================================================
// Auth API
// ============================================================================

export async function login(email: string, password: string): Promise<{ user: User }> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    // Store CSRF token from response body (cross-origin cookies aren't readable via JS)
    if (data.csrf_token) {
        setCsrfToken(data.csrf_token);
    }
    // Server sets HttpOnly cookies; only store user profile locally
    saveAuth({ access_token: '', refresh_token: '' }, data.user);
    return { user: data.user };
}

export async function logout(): Promise<void> {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'X-CSRF-Token': getCsrfToken(),
            },
        });
    } catch { /* best-effort server logout */ }
    clearAuth();
    window.location.href = '/login';
}

export async function register(name: string, email: string, password: string): Promise<{ user: User }> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name, email, password }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
        throw new Error(error.detail || 'Registration failed');
    }

    // Auto-login after successful registration
    return login(email, password);
}

export async function forgotPassword(email: string): Promise<void> {
    await request('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
    });
}

export async function getCurrentUser(): Promise<User> {
    return request('/auth/me');
}

export async function validateSession(): Promise<User | null> {
    try {
        const user = await request<User>('/auth/me');
        const tokens = getStoredTokens();
        if (tokens && user) saveAuth(tokens, user);
        return user;
    } catch {
        return null;
    }
}

// ============================================================================
// Dashboard Stats API
// ============================================================================

export interface DashboardStats {
    documents_analyzed: number;
    total_risks_detected: number;
    redlines_applied: number;
    red_risks: number;
    yellow_risks: number;
    green_risks: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
    return request('/users/me/stats');
}

export async function getOrgStats(): Promise<DashboardStats> {
    return request('/users/org/stats');
}

// ============================================================================
// Audit Log API
// ============================================================================

export interface AuditLogEntry {
    id: string;
    user_email: string;
    action: string;
    resource_type: string;
    resource_name: string;
    timestamp: string;
    ip_address: string | null;
    status: string;
    risk_count: number | null;
    details: string | null;
}

export interface AuditLogPage {
    items: AuditLogEntry[];
    total: number;
    page: number;
    page_size: number;
}

export async function getAuditLogs(params?: {
    page?: number;
    page_size?: number;
    action?: string;
    user_email?: string;
    date_from?: string;
    date_to?: string;
}): Promise<AuditLogPage> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.action) searchParams.set('action', params.action);
    if (params?.user_email) searchParams.set('user_email', params.user_email);
    if (params?.date_from) searchParams.set('date_from', params.date_from);
    if (params?.date_to) searchParams.set('date_to', params.date_to);
    const qs = searchParams.toString();
    return request(`/audit-logs/${qs ? '?' + qs : ''}`);
}

// ============================================================================
// Team API
// ============================================================================

export interface TeamMember {
    id: string;
    email: string;
    name: string;
    role: string;
    last_login: string | null;
    is_active: boolean;
}

export async function getTeamMembers(): Promise<TeamMember[]> {
    const res = await request<{ items: TeamMember[] }>('/team/members');
    return Array.isArray(res) ? res : (res.items ?? []);
}

export async function changeTeamMemberRole(userId: string, role: string): Promise<TeamMember> {
    return request(`/team/members/${userId}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role }),
    });
}

export async function removeTeamMember(userId: string): Promise<void> {
    return request(`/team/members/${userId}`, { method: 'DELETE' });
}

// ============================================================================
// Playbook API
// ============================================================================

export async function listPlaybooks(): Promise<Playbook[]> {
    const res = await request<{ items: Playbook[] }>('/playbooks/');
    return Array.isArray(res) ? res : (res.items ?? []);
}

export async function getPlaybook(id: string): Promise<PlaybookDetail> {
    return request(`/playbooks/${id}`);
}

export async function createPlaybook(data: CreatePlaybookData): Promise<Playbook> {
    return request('/playbooks/', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function updatePlaybook(id: string, data: Partial<CreatePlaybookData>): Promise<Playbook> {
    return request(`/playbooks/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function deletePlaybook(id: string): Promise<void> {
    return request(`/playbooks/${id}`, { method: 'DELETE' });
}

export async function togglePlaybookPublish(id: string): Promise<Playbook> {
    return request(`/playbooks/${id}/publish`, { method: 'POST' });
}

// ============================================================================
// Rule API
// ============================================================================

export async function addRule(playbookId: string, data: CreateRuleData): Promise<PlaybookRule> {
    return request(`/playbooks/${playbookId}/rules`, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function updateRule(playbookId: string, ruleId: string, data: Partial<CreateRuleData>): Promise<PlaybookRule> {
    return request(`/playbooks/${playbookId}/rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function deleteRule(playbookId: string, ruleId: string): Promise<void> {
    return request(`/playbooks/${playbookId}/rules/${ruleId}`, { method: 'DELETE' });
}

export async function reorderRules(playbookId: string, ruleIds: string[]): Promise<PlaybookRule[]> {
    return request(`/playbooks/${playbookId}/rules/reorder`, {
        method: 'POST',
        body: JSON.stringify({ rule_ids: ruleIds }),
    });
}

// ============================================================================
// Phase 6: Negotiation Tiers
// ============================================================================

export interface RuleTier {
    id: string;
    tier_level: number;
    position_text: string;
    guidance_notes?: string;
    risk_level_at_tier: string;
}

export async function listTiers(playbookId: string, ruleId: string): Promise<RuleTier[]> {
    return request(`/playbooks/${playbookId}/rules/${ruleId}/tiers`);
}

export async function upsertTiers(playbookId: string, ruleId: string, tiers: Omit<RuleTier, 'id'>[]): Promise<RuleTier[]> {
    return request(`/playbooks/${playbookId}/rules/${ruleId}/tiers`, {
        method: 'PUT',
        body: JSON.stringify(tiers),
    });
}

// ============================================================================
// Phase 6: Conditions & Overrides
// ============================================================================

export interface PlaybookCondition {
    id: string;
    name: string;
    description?: string;
    condition_type: string;
    operator: string;
    condition_value: Record<string, unknown>;
    is_active: boolean;
    priority: number;
    overrides_count: number;
}

export interface RuleOverride {
    id: string;
    condition_id: string;
    rule_id: string;
    override_risk_level?: string;
    override_position_text?: string;
    override_is_deal_breaker?: boolean;
    override_tier_level?: number;
    suppress_rule: boolean;
    notes?: string;
}

export async function listConditions(playbookId: string): Promise<PlaybookCondition[]> {
    return request(`/playbooks/${playbookId}/conditions`);
}

export async function createCondition(playbookId: string, data: Omit<PlaybookCondition, 'id' | 'overrides_count'>): Promise<PlaybookCondition> {
    return request(`/playbooks/${playbookId}/conditions`, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function deleteCondition(playbookId: string, conditionId: string): Promise<void> {
    return request(`/playbooks/${playbookId}/conditions/${conditionId}`, { method: 'DELETE' });
}

export async function addOverride(playbookId: string, conditionId: string, data: Omit<RuleOverride, 'id' | 'condition_id'>): Promise<RuleOverride> {
    return request(`/playbooks/${playbookId}/conditions/${conditionId}/overrides`, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function deleteOverride(playbookId: string, conditionId: string, overrideId: string): Promise<void> {
    return request(`/playbooks/${playbookId}/conditions/${conditionId}/overrides/${overrideId}`, { method: 'DELETE' });
}

// ============================================================================
// Phase 6: Cross-Clause Dependencies
// ============================================================================

export interface RuleDependency {
    id: string;
    source_rule_id: string;
    target_rule_id: string;
    trigger_condition: string;
    effect: string;
    effect_params?: Record<string, unknown>;
    is_active: boolean;
}

export async function listDependencies(playbookId: string): Promise<RuleDependency[]> {
    return request(`/playbooks/${playbookId}/dependencies`);
}

export async function createDependency(playbookId: string, data: Omit<RuleDependency, 'id'>): Promise<RuleDependency> {
    return request(`/playbooks/${playbookId}/dependencies`, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function deleteDependency(playbookId: string, depId: string): Promise<void> {
    return request(`/playbooks/${playbookId}/dependencies/${depId}`, { method: 'DELETE' });
}

// ============================================================================
// Phase 6: Version Control
// ============================================================================

export interface PlaybookVersionSummary {
    id: string;
    version_number: number;
    change_summary?: string;
    created_by?: string;
    created_at: string;
}

export interface PlaybookVersionDetail extends PlaybookVersionSummary {
    snapshot: Record<string, unknown>;
}

export interface PlaybookDiff {
    rules_added: Record<string, unknown>[];
    rules_removed: Record<string, unknown>[];
    rules_modified: Record<string, unknown>[];
    conditions_added: Record<string, unknown>[];
    conditions_removed: Record<string, unknown>[];
    dependencies_added: Record<string, unknown>[];
    dependencies_removed: Record<string, unknown>[];
}

export async function listVersions(playbookId: string): Promise<PlaybookVersionSummary[]> {
    return request(`/playbooks/${playbookId}/versions`);
}

export async function createVersionSnapshot(playbookId: string, changeSummary: string): Promise<PlaybookVersionSummary> {
    return request(`/playbooks/${playbookId}/versions?change_summary=${encodeURIComponent(changeSummary)}`, { method: 'POST' });
}

export async function getVersionDetail(playbookId: string, versionId: string): Promise<PlaybookVersionDetail> {
    return request(`/playbooks/${playbookId}/versions/${versionId}`);
}

export async function diffVersions(playbookId: string, versionAId: string, versionBId: string): Promise<PlaybookDiff> {
    return request(`/playbooks/${playbookId}/versions/diff/${versionAId}/${versionBId}`);
}

export async function rollbackToVersion(playbookId: string, versionId: string): Promise<PlaybookVersionSummary> {
    return request(`/playbooks/${playbookId}/versions/${versionId}/rollback`, { method: 'POST' });
}

// ============================================================================
// Phase 6: Marketplace
// ============================================================================

export interface MarketplaceItem {
    id: string;
    playbook_id: string;
    playbook_name: string;
    category: string;
    description?: string;
    is_verified: boolean;
    download_count: number;
    avg_rating: number;
    rating_count: number;
    tags: string[];
}

export async function browseMarketplace(category?: string): Promise<MarketplaceItem[]> {
    const qs = category ? `?category=${encodeURIComponent(category)}` : '';
    const res = await request<{ items: MarketplaceItem[] }>(`/playbooks/marketplace/browse${qs}`);
    return Array.isArray(res) ? res : (res.items ?? []);
}

export async function publishToMarketplace(playbookId: string, tags: string[]): Promise<MarketplaceItem> {
    return request(`/playbooks/${playbookId}/marketplace/publish`, {
        method: 'POST',
        body: JSON.stringify({ tags }),
    });
}

export async function forkPlaybook(marketplaceId: string): Promise<Playbook> {
    return request(`/playbooks/marketplace/${marketplaceId}/fork`, { method: 'POST' });
}

export async function ratePlaybook(marketplaceId: string, rating: number, review?: string): Promise<void> {
    return request(`/playbooks/marketplace/${marketplaceId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ rating, review }),
    });
}

// ============================================================================
// Clause Library
// ============================================================================

export async function listClauses(clauseType?: string): Promise<ClauseLibraryItem[]> {
    const qs = clauseType ? `?clause_type=${encodeURIComponent(clauseType)}` : '';
    const res = await request<{ items: ClauseLibraryItem[] }>(`/clauses/${qs}`);
    return Array.isArray(res) ? res : (res.items ?? []);
}

export async function createClause(data: CreateClauseData): Promise<ClauseLibraryItem> {
    return request('/clauses/', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateClause(id: string, data: Partial<CreateClauseData>): Promise<ClauseLibraryItem> {
    return request(`/clauses/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export async function deleteClause(id: string): Promise<void> {
    await request(`/clauses/${id}`, { method: 'DELETE' });
}

// ============================================================================
// Templates API
// ============================================================================

export interface TemplateListItem {
    id: string;
    name: string;
    description: string | null;
    category: string;
    is_premium: boolean;
    download_count: number;
    paired_playbook_id: string | null;
    paired_playbook_name: string | null;
}

export interface TemplateDetail extends TemplateListItem {
    template_content: string | null;
    created_at: string;
}

export async function listTemplates(category?: string): Promise<TemplateListItem[]> {
    const qs = category ? `?category=${encodeURIComponent(category)}` : '';
    return request(`/templates/${qs}`);
}

export async function getTemplate(id: string): Promise<TemplateDetail> {
    return request(`/templates/${id}`);
}

export async function downloadTemplate(id: string): Promise<{ id: string; name: string; template_content: string; paired_playbook_id: string | null }> {
    return request(`/templates/${id}/download`);
}

// ============================================================================
// Contract Comparison API
// ============================================================================

export interface DiffChange {
    change_type: 'added' | 'removed' | 'modified';
    text_a: string;
    text_b: string;
    position: number;
    similarity: number;
    ai_assessment: string | null;
}

export interface CompareResponse {
    changes: DiffChange[];
    total_changes: number;
    paragraphs_a: number;
    paragraphs_b: number;
    summary: string;
}

export async function compareContracts(textA: string, textB: string, playbookId?: string): Promise<CompareResponse> {
    return request('/documents/compare', {
        method: 'POST',
        body: JSON.stringify({ text_a: textA, text_b: textB, playbook_id: playbookId }),
    });
}

// ============================================================================
// Clause Generation API
// ============================================================================

export interface GenerateClauseResponse {
    clause_text: string;
    reasoning: string;
}

export async function generateClause(clauseType: string, playbookId?: string, contractContext?: string): Promise<GenerateClauseResponse> {
    return request('/documents/generate-clause', {
        method: 'POST',
        body: JSON.stringify({ clause_type: clauseType, playbook_id: playbookId, contract_context: contractContext }),
    });
}

// ============================================================================
// Analytics API
// ============================================================================

export interface AnalyticsOverview {
    documents_analyzed: number;
    total_risks: number;
    red_risks: number;
    yellow_risks: number;
    active_users: number;
    period_days: number;
}

export interface RiskBreakdownItem {
    risk_level: string;
    red: number;
    yellow: number;
    green: number;
    total: number;
}

export interface UserActivityItem {
    user_id: string;
    email: string;
    name: string;
    scan_count: number;
    risks_found: number;
    last_scan: string | null;
}

export interface TrendDataPoint {
    period: string;
    scans: number;
    risks: number;
}

export async function getAnalyticsOverview(days?: number): Promise<AnalyticsOverview> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/overview${qs}`);
}

export async function getAnalyticsRisks(days?: number): Promise<RiskBreakdownItem[]> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/risks${qs}`);
}

export async function getAnalyticsUsers(days?: number): Promise<UserActivityItem[]> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/users${qs}`);
}

export async function getAnalyticsTrends(period?: string, weeks?: number): Promise<TrendDataPoint[]> {
    const params = new URLSearchParams();
    if (period) params.set('period', period);
    if (weeks) params.set('weeks', String(weeks));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/trends${qs}`);
}

export function getAnalyticsExportUrl(days?: number): string {
    const qs = days ? `?days=${days}` : '';
    return `${API_BASE_URL}/analytics/export${qs}`;
}

export async function analyticsExportBlob(days?: number): Promise<Blob> {
    const url = getAnalyticsExportUrl(days);
    const csrfToken = getCsrfToken();
    const headers: Record<string, string> = {
        'Accept': 'text/csv',
    };
    if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
    }
    const res = await fetch(url, {
        credentials: 'include',
        headers,
    });
    if (!res.ok) {
        if (res.status === 401) {
            clearAuth();
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        throw new Error(`Export failed: ${res.status}`);
    }
    return res.blob();
}

// ============================================================================
// Phase 9: Advanced Analytics API
// ============================================================================

export interface ROIData {
    period_days: number;
    documents_analyzed: number;
    total_risks_found: number;
    red_risks: number;
    yellow_risks: number;
    time_savings: {
        estimated_manual_hours: number;
        actual_ai_hours: number;
        hours_saved: number;
        monetary_value: number;
        currency: string;
    };
    risk_value: {
        red_risk_value: number;
        yellow_risk_value: number;
        total_risk_value_protected: number;
        currency: string;
    };
    total_roi_value: number;
    roi_multiplier: string;
    methodology: {
        pages_per_hour: number;
        minutes_per_risk: number;
        hourly_rate: number;
        risk_value_per_red: number;
        risk_value_per_yellow: number;
        words_per_page: number;
        note: string;
    };
}

export interface ExecutiveDashboard extends AnalyticsOverview {
    roi: ROIData;
    trends: TrendDataPoint[];
}

export interface PortfolioRisk {
    period_days: number;
    summary: {
        total_documents: number;
        avg_risk_score: number;
        total_risks: number;
        avg_risks_per_document: number;
    };
    risk_distribution: { red: number; yellow: number; green: number };
    by_contract_type: Array<{
        contract_type: string;
        document_count: number;
        avg_risk_score: number;
        total_risks: number;
    }>;
    high_risk_documents: Array<{
        document_id: string;
        filename: string;
        risk_score: number | null;
        total_risks: number;
        contract_type: string | null;
        counterparty: string | null;
    }>;
}

export interface TeamPerformanceItem {
    user_id: string;
    email: string;
    name: string;
    documents_reviewed: number;
    total_risks_found: number;
    avg_processing_ms: number;
    total_words_reviewed: number;
    avg_risks_per_doc: number;
}

export interface ClauseAnalyticsItem {
    risk_level: string;
    count: number;
    resolved_count: number;
    resolution_rate: number;
}

export interface BenchmarkResult {
    document_id: string;
    contract_type: string;
    risk_score: number;
    total_risks?: number;
    percentile: number | null;
    comparison: string;
    org_averages?: { avg_risk_score: number; avg_risks_per_doc: number };
    sample_size: number;
}

export interface GeneratedReport {
    id: string;
    report_type: string;
    title: string;
    format: string;
    created_at: string;
    parameters?: Record<string, unknown>;
    data?: Record<string, unknown>;
}

export async function getExecutiveDashboard(days?: number): Promise<ExecutiveDashboard> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/executive${qs}`);
}

export async function getAnalyticsROI(days?: number): Promise<ROIData> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/roi${qs}`);
}

export async function getPortfolioRisk(days?: number): Promise<PortfolioRisk> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/portfolio${qs}`);
}

export async function getTeamPerformance(days?: number): Promise<TeamPerformanceItem[]> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/team-performance${qs}`);
}

export async function getClauseAnalytics(days?: number): Promise<ClauseAnalyticsItem[]> {
    const qs = days ? `?days=${days}` : '';
    return request(`/analytics/clauses${qs}`);
}

export async function getDocumentBenchmark(documentId: string): Promise<BenchmarkResult> {
    return request(`/analytics/benchmark/${documentId}`);
}

export async function getBIExport(dataset: string, days?: number): Promise<Record<string, unknown>> {
    const params = new URLSearchParams();
    if (days) params.set('days', String(days));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/bi-export/${dataset}${qs}`);
}

export async function generateAnalyticsReport(
    reportType: string, days?: number, title?: string
): Promise<GeneratedReport> {
    const params = new URLSearchParams();
    params.set('report_type', reportType);
    if (days) params.set('days', String(days));
    if (title) params.set('title', title);
    return request(`/analytics/reports/generate?${params.toString()}`, { method: 'POST' });
}

export async function listAnalyticsReports(
    reportType?: string, limit?: number
): Promise<GeneratedReport[]> {
    const params = new URLSearchParams();
    if (reportType) params.set('report_type', reportType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/analytics/reports${qs}`);
}

export async function getAnalyticsReport(reportId: string): Promise<GeneratedReport> {
    return request(`/analytics/reports/${reportId}`);
}

export async function updateROIBenchmarks(config: {
    pages_per_hour?: number;
    minutes_per_risk?: number;
    hourly_rate?: number;
    currency?: string;
}): Promise<Record<string, unknown>> {
    const params = new URLSearchParams();
    if (config.pages_per_hour != null) params.set('pages_per_hour', String(config.pages_per_hour));
    if (config.minutes_per_risk != null) params.set('minutes_per_risk', String(config.minutes_per_risk));
    if (config.hourly_rate != null) params.set('hourly_rate', String(config.hourly_rate));
    if (config.currency) params.set('currency', config.currency);
    return request(`/analytics/roi/benchmarks?${params.toString()}`, { method: 'PUT' });
}

// ============================================================================
// Batch Processing (Phase 8)
// ============================================================================

export interface BatchFileStatus {
    filename: string;
    status: 'queued' | 'processing' | 'completed' | 'error';
    document_id?: string;
    risk_summary?: { red: number; yellow: number; total: number };
    error?: string;
    ai_fallback?: boolean;  // true = AI failed, results are rule-engine only
    executive_summary?: string[];
}

export interface BatchStatusResponse {
    batch_id: string;
    files: BatchFileStatus[];
    overall_progress: number;
    status: 'processing' | 'completed' | 'partial_failure';
}

export async function batchAnalyze(files: File[], playbookId?: string): Promise<{ batch_id: string; file_count: number }> {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    if (playbookId) formData.append('playbook_id', playbookId);

    const headers: Record<string, string> = {};
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;

    let res = await fetch(`${API_BASE_URL}/documents/batch-analyze`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: formData,
    });

    // Handle 401 with cookie-based refresh
    if (res.status === 401) {
        try {
            const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            });
            if (refreshResp.ok) {
                const refreshData = await refreshResp.json().catch(() => ({}));
                if (refreshData.csrf_token) {
                    setCsrfToken(refreshData.csrf_token);
                }
                const retryHeaders: Record<string, string> = {};
                const newCsrf = getCsrfToken();
                if (newCsrf) retryHeaders['X-CSRF-Token'] = newCsrf;
                res = await fetch(`${API_BASE_URL}/documents/batch-analyze`, {
                    method: 'POST',
                    headers: retryHeaders,
                    credentials: 'include',
                    body: formData,
                });
            } else {
                logout();
                throw new Error('Session expired. Please log in again.');
            }
        } catch (e) {
            if (e instanceof Error && e.message.includes('Session expired')) throw e;
            logout();
            throw new Error('Session expired. Please log in again.');
        }
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(typeof err.detail === 'string' ? err.detail : `HTTP ${res.status}`);
    }
    return res.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
    return request(`/documents/batch/${batchId}/status`);
}

export interface BatchFinding {
    id: string;
    rule_name: string | null;
    clause_type: string | null;
    redline_type: string | null;
    risk_level: string;
    clause_text: string;
    ai_explanation: string | null;
    suggested_fix: string | null;
    is_deal_breaker: boolean;
    confidence: number | null;
    is_resolved: boolean;
}

export interface BatchFullReport {
    batch_id: string;
    total_files: number;
    completed_files: number;
    failed_files: number;
    compliance_score: number;
    aggregate_risk_summary: { red: number; yellow: number; green: number; total: number; deal_breakers: number };
    top_risks: { rule: string; count: number }[];
    risk_heatmap: { clause_type: string; count: number }[];
    per_file: {
        filename: string;
        document_id: string | null;
        status: string;
        risk_summary: { red: number; yellow: number; green: number; total: number };
        findings: BatchFinding[];
        error: string | null;
        ai_fallback?: boolean;
    }[];
}

export async function getBatchFullReport(batchId: string): Promise<BatchFullReport> {
    return request(`/documents/batch/${batchId}/full-report`);
}

export async function getDocumentRisks(documentId: string): Promise<{
    document_id: string;
    filename: string;
    total_risks: number;
    findings: BatchFinding[];
}> {
    return request(`/documents/${documentId}/risks`);
}

export async function updateRiskStatus(documentId: string, riskId: string, action: 'accept' | 'dismiss' | 'resolve' | 'unresolve'): Promise<{ id: string; is_resolved: boolean }> {
    return request(`/documents/${documentId}/risks/${riskId}?action=${action}`, { method: 'PATCH' });
}

// ============================================================================
// Billing API
// ============================================================================

export interface SubscriptionInfo {
    plan: string;
    status: string;
    documents_used: number;
    documents_limit: number;
    seats_used: number;
    seats_limit: number;
    current_period_end: string | null;
    razorpay_subscription_id: string | null;
    stripe_subscription_id: string | null;
    overage_count: number;
    overage_cost: string | null;
}

export interface PlanInfo {
    id: string;
    name: string;
    price_inr: number;
    price_usd: number;
    scans_limit: number;
    seats_limit: number;
    features: string[];
    overage_price_inr: number;
    overage_price_usd: number;
}

export interface UsageStats {
    plan: string;
    scans_used: number;
    scans_limit: number;
    scans_remaining: number;
    overage_count: number;
    current_period_start: string | null;
    current_period_end: string | null;
    daily_usage: Array<{ date: string; count: number }>;
}

export interface InvoiceItem {
    id: string;
    amount: number;
    currency: string;
    status: string;
    plan: string;
    description: string;
    created_at: string;
    paid_at: string | null;
    gateway: string;
}

export async function getSubscription(): Promise<SubscriptionInfo> {
    return request('/billing/subscription');
}

export async function listPlans(): Promise<PlanInfo[]> {
    return request('/billing/plans');
}

export async function getUsageStats(): Promise<UsageStats> {
    return request('/billing/usage');
}

export async function createSubscription(plan: string, gateway: 'razorpay' | 'stripe' = 'razorpay', currency: 'INR' | 'USD' = 'INR'): Promise<{ gateway: string; subscription_id?: string; session_id?: string; short_url?: string; checkout_url?: string; status: string }> {
    return request('/billing/create-subscription', {
        method: 'POST',
        body: JSON.stringify({ plan, gateway, currency }),
    });
}

export async function verifyPayment(data: {
    gateway: 'razorpay' | 'stripe';
    razorpay_subscription_id?: string;
    razorpay_payment_id?: string;
    razorpay_signature?: string;
    stripe_session_id?: string;
}): Promise<{ status: string; plan: string; gateway: string }> {
    return request('/billing/verify', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function listInvoices(): Promise<InvoiceItem[]> {
    return request('/billing/invoices');
}

// ============================================================================
// SSO API
// ============================================================================

export interface SSOStatus {
    sso_enabled: boolean;
    sso_provider: string | null;
    workos_configured: boolean;
    sso_available: boolean;
    entra_tenant_id: string | null;
}

export async function getSSOStatus(orgId: string): Promise<SSOStatus> {
    return request(`/sso/status?org_id=${encodeURIComponent(orgId)}`);
}

export async function ssoAuthorize(orgId: string, redirectUri?: string): Promise<{ authorization_url: string }> {
    const params = new URLSearchParams({ org_id: orgId });
    if (redirectUri) params.set('redirect_uri', redirectUri);
    return request(`/sso/authorize?${params.toString()}`);
}

export async function ssoCallback(code: string, state?: string): Promise<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    user: Record<string, unknown>;
    is_new_user: boolean;
}> {
    return request('/sso/callback', {
        method: 'POST',
        body: JSON.stringify({ code, state }),
    });
}

export async function enableSSO(orgId: string, workosOrgId: string, ssoProvider: string): Promise<{ message: string; provider: string }> {
    return request('/sso/enable', {
        method: 'POST',
        body: JSON.stringify({ org_id: orgId, workos_org_id: workosOrgId, sso_provider: ssoProvider }),
    });
}

export async function disableSSO(orgId: string): Promise<{ message: string }> {
    return request('/sso/disable', {
        method: 'POST',
        body: JSON.stringify({ org_id: orgId }),
    });
}

// ============================================================================
// Feedback API
// ============================================================================

export interface FeedbackItem {
    id: string;
    feedback_type: string;
    clause_text: string | null;
    user_comment: string | null;
    suggested_risk_level: string | null;
    created_at: string;
}

export interface RuleEffectiveness {
    rule_id: string;
    clause_type: string;
    total_feedback: number;
    false_positives: number;
    false_negatives: number;
    correct_count: number;
    false_positive_rate: number;
    needs_review: boolean;
}

export async function submitFeedback(data: {
    playbook_rule_id: string;
    document_id?: string;
    feedback_type: 'false_positive' | 'false_negative' | 'correct' | 'needs_improvement';
    clause_text?: string;
    user_comment?: string;
    suggested_risk_level?: 'RED' | 'YELLOW' | 'GREEN';
}): Promise<FeedbackItem> {
    return request('/feedback/', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function listFeedback(params?: {
    playbook_rule_id?: string;
    feedback_type?: string;
    limit?: number;
    offset?: number;
}): Promise<FeedbackItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.playbook_rule_id) searchParams.set('playbook_rule_id', params.playbook_rule_id);
    if (params?.feedback_type) searchParams.set('feedback_type', params.feedback_type);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const qs = searchParams.toString();
    const res = await request<{ items: FeedbackItem[] }>(`/feedback/${qs ? '?' + qs : ''}`);
    return Array.isArray(res) ? res : (res.items ?? []);
}

export async function getRuleEffectiveness(needsReviewOnly?: boolean): Promise<RuleEffectiveness[]> {
    const qs = needsReviewOnly ? '?needs_review_only=true' : '';
    return request(`/feedback/stats${qs}`);
}

// ============================================================================
// Contract Drafting
// ============================================================================

export interface IntakeSchemaField {
    name: string;
    type: string;
    required?: boolean;
    default?: string;
    options?: string[];
    show_when?: string;
    placeholder?: string;
}

export interface IntakeSchemaStage {
    id: string;
    title: string;
    show_when?: string;
    fields: IntakeSchemaField[];
}

export interface IntakeSchema {
    stages: IntakeSchemaStage[];
}

export interface GenerateRequest {
    contract_type: string;
    drafting_perspective: string;
    risk_appetite: string;
    jurisdiction: string;
    party_1: { name: string; entity_type: string; jurisdiction: string; address?: string };
    party_2: { name: string; entity_type: string; jurisdiction: string; address?: string };
    term_months?: number;
    governing_law?: string;
    dispute_resolution?: string;
    venue?: string;
    effective_date?: string;
    nda_details?: {
        purpose: string;
        confidentiality_survival_years?: number;
        ci_categories?: string[];
        non_solicitation?: boolean;
        non_solicitation_months?: number;
        marking_requirement?: boolean;
    };
    saas_details?: {
        service_description: string;
        pricing_model: string;
        price_amount: number;
        billing_frequency: string;
        auto_renewal?: boolean;
        uptime_commitment?: number;
        liability_cap_months?: number;
        authorized_users?: number;
        compliance_frameworks?: string[];
        data_regions?: string[];
        support_tiers?: Record<string, string>;
    };
    // MSA / other free-form context piped into per-clause prompts
    negotiation_context?: string;
    // Employment-specific fields (flat for backend convenience)
    employee_title?: string;
    base_salary?: string;
    reporting_manager?: string;
    work_location?: string;
}

export interface GenerateResponse {
    draft_id: string;
    title: string;
    contract_type: string;
    overall_score: number;
    risk_alignment: number;
    compliance_score: number;
    qa_score: number;
    total_sections: number;
    annotations_applied: number;
    conflicts_flagged: number;
    open_items: number;
}

export interface DraftingPlaybookSummary {
    id: string;
    name: string;
    contract_type: string;
    jurisdiction: string;
    clause_count: number;
}

export async function getDraftingIntakeSchema(contractType: string): Promise<IntakeSchema> {
    return request(`/drafting/intake-schema?contract_type=${encodeURIComponent(contractType)}`);
}

export async function generateContract(
    data: GenerateRequest,
    externalSignal?: AbortSignal,
): Promise<GenerateResponse> {
    // Contract generation takes 2-5 minutes (AI drafts + reviews all sections).
    // Use a 10-minute timeout instead of the default 2-minute request() timeout.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000);
    // Propagate user-initiated cancellation (e.g. Cancel button) into this fetch.
    const userAborted = { flag: false };
    if (externalSignal) {
        if (externalSignal.aborted) {
            controller.abort();
            userAborted.flag = true;
        } else {
            externalSignal.addEventListener('abort', () => {
                userAborted.flag = true;
                controller.abort();
            }, { once: true });
        }
    }
    try {
        const csrfToken = getCsrfToken();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (csrfToken) {
            headers['X-CSRF-Token'] = csrfToken;
        }
        const res = await fetch(`${API_BASE_URL}/drafting/generate`, {
            method: 'POST',
            headers,
            credentials: 'include',
            body: JSON.stringify(data),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
            // Consent intercept — draftContract bypasses request() for the 10-min timeout,
            // so it needs to replicate the 403 consent_required handshake itself.
            if (res.status === 403 && err?.error === 'consent_required' && Array.isArray(err.required_purposes)) {
                const { requestConsent } = await import('./consentPrompt');
                await requestConsent(err.required_purposes);
                return generateContract(data, externalSignal);
            }
            throw new Error(err.detail || `Server error ${res.status}`);
        }
        return res.json();
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof DOMException && err.name === 'AbortError') {
            if (userAborted.flag) {
                throw new DOMException('Generation cancelled by user', 'AbortError');
            }
            throw new Error('Contract generation timed out after 10 minutes. Please try again.');
        }
        throw err;
    }
}

export async function downloadDraft(draftId: string): Promise<Blob> {
    const csrfToken = getCsrfToken();
    const headers: Record<string, string> = {};
    if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
    }
    const res = await fetch(`${API_BASE_URL}/drafting/download/${draftId}`, {
        credentials: 'include',
        headers,
    });
    if (!res.ok) throw new Error('Download failed');
    return res.blob();
}

export async function getDraftAddinPayload(draftId: string): Promise<Record<string, unknown>> {
    return request(`/drafting/addin-payload/${draftId}`);
}

export async function listDraftingPlaybooks(): Promise<DraftingPlaybookSummary[]> {
    return request('/drafting/playbooks');
}

// ============================================================================
// Consent Management API (DPDP Act)
// ============================================================================

export interface ConsentPurpose {
    code: string;
    name: string;
    description: string;
    is_required: boolean;
    personal_data_categories: string[];
    third_parties: string[];
    retention_period: string | null;
    translations: Record<string, { name: string; description: string }>;
}

export interface ConsentStatusPurpose extends ConsentPurpose {
    granted: boolean;
    granted_at: string | null;
    withdrawn_at: string | null;
}

export interface ConsentStatus {
    has_consent_record: boolean;
    consent_record_id?: string;
    status?: string;
    created_at?: string;
    updated_at?: string;
    purposes: ConsentStatusPurpose[];
}

export interface ConsentEvent {
    id: string;
    event_type: string;
    purpose_code: string | null;
    actor: string;
    details: Record<string, unknown>;
    created_at: string;
}

export interface ConsentReceipt {
    id: string;
    receipt_data: Record<string, unknown>;
    schema_version: string;
    digital_signature: string | null;
    issued_at: string;
    downloaded_at: string | null;
}

export interface PrivacyPolicy {
    id: string;
    version: number;
    title: string;
    content: string;
    language: string;
    checksum: string;
    effective_from: string;
}

export async function getConsentPurposes(): Promise<ConsentPurpose[]> {
    return request('/consent/purposes');
}

export async function getCurrentPrivacyPolicy(language = 'en'): Promise<PrivacyPolicy> {
    return request(`/consent/policy/current?language=${language}`);
}

export async function getConsentStatus(): Promise<ConsentStatus> {
    return request('/consent/status');
}

export async function grantConsent(purposeCodes: string[], policyChecksum?: string): Promise<{ consent_record_id: string; granted_purposes: string[] }> {
    return request('/consent/grant', {
        method: 'POST',
        body: JSON.stringify({
            purpose_codes: purposeCodes,
            privacy_policy_version: policyChecksum,
        }),
    });
}

export async function withdrawConsent(purposeCodes: string[], reason?: string): Promise<{ consent_record_id: string; withdrawn_purposes: string[] }> {
    return request('/consent/withdraw', {
        method: 'POST',
        body: JSON.stringify({
            purpose_codes: purposeCodes,
            reason,
        }),
    });
}

export async function getConsentHistory(limit = 50, offset = 0): Promise<ConsentEvent[]> {
    return request(`/consent/history?limit=${limit}&offset=${offset}`);
}

export async function getConsentReceipts(): Promise<ConsentReceipt[]> {
    return request('/consent/receipts');
}

export async function registerWithConsent(
    name: string, email: string, password: string,
    consentPurposes: string[], policyChecksum?: string,
): Promise<{ user: User }> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
            name, email, password,
            consent_purposes: consentPurposes,
            privacy_policy_accepted: true,
            privacy_policy_version: policyChecksum,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
        throw new Error(error.detail || 'Registration failed');
    }

    return login(email, password);
}

// ============================================================================
// DPDP Compliance Command Center API
// ============================================================================

export interface DPDPContractFinding {
    rule_id: string;
    section: string;
    risk_level: string;
    is_deal_breaker: boolean;
    title: string;
    description: string;
    clause_text: string;
    suggested_fix: string;
    confidence: number;
}

export interface DPDPScanResult {
    contract_name: string;
    contract_type: string;
    total_findings: number;
    red_findings: number;
    yellow_findings: number;
    green_findings: number;
    deal_breakers: number;
    compliance_score: number;
    findings: DPDPContractFinding[];
    scanned_at: string;
}

export interface DPDPPortfolioReport {
    total_contracts: number;
    average_compliance_score: number;
    contracts_with_deal_breakers: number;
    risk_heatmap: Record<string, number>;
    section_coverage: Record<string, string>;
    top_risks: string[];
    contract_results: DPDPScanResult[];
    generated_at: string;
}

export interface DPDPAssessmentQuestion {
    id: string;
    category: string;
    section: string;
    question: string;
    guidance: string;
    weight: number;
    is_critical: boolean;
}

export interface DPDPSectionScore {
    section: string;
    section_name: string;
    status: string;
    score: number;
    findings: string[];
    recommendations: string[];
    priority: string;
}

export interface DPDPGapAssessment {
    organization_name: string;
    overall_score: number;
    overall_status: string;
    section_scores: DPDPSectionScore[];
    critical_gaps: string[];
    action_items: string[];
    estimated_remediation_effort: string;
    deadline_risk: string;
    assessed_at: string;
}

export interface DPDPDeadline {
    title: string;
    description: string;
    deadline: string;
    section: string | null;
    status: string;
    days_remaining: number;
}

export interface DPDPAlert {
    alert_type: string;
    severity: string;
    title: string;
    description: string;
    action_required: string;
    created_at: string;
}

export interface DPDPDashboard {
    overall_score: number;
    status: string;
    contracts_scanned: number;
    active_findings: number;
    resolved_findings: number;
    pending_rights_requests: number;
    pending_grievances: number;
    upcoming_deadlines: DPDPDeadline[];
    recent_alerts: DPDPAlert[];
    section_scores: Record<string, number>;
    trend: Record<string, unknown>[];
}

export interface DPDPRemediationOutput {
    remediation_type: string;
    title: string;
    content: string;
    language: string;
    sections: { heading: string; content: string }[];
    applicable_dpdp_sections: string[];
    notes: string[];
    generated_at: string;
}

export interface DPDPBreachNotification {
    dpb_notification: string;
    principal_notification: string;
    cert_in_notification: string;
    timeline: Record<string, unknown>;
    recommended_actions: string[];
}

export async function dpdpScanContract(contractText: string, contractName = '', contractType = 'general'): Promise<DPDPScanResult> {
    return request('/dpdp/scan', {
        method: 'POST',
        body: JSON.stringify({ contract_text: contractText, contract_name: contractName, contract_type: contractType, jurisdiction: 'IN' }),
    });
}

export async function dpdpScanBulk(contracts: { contract_text: string; contract_name: string; contract_type: string }[]): Promise<DPDPPortfolioReport> {
    return request('/dpdp/scan/bulk', {
        method: 'POST',
        body: JSON.stringify({ contracts, generate_portfolio_report: true }),
    });
}

// dpdpGetAssessmentQuestions and dpdpRunAssessment are defined below with full type safety

export async function dpdpRemediate(data: Record<string, unknown>): Promise<DPDPRemediationOutput> {
    return request('/dpdp/remediate', { method: 'POST', body: JSON.stringify(data) });
}

export async function dpdpBreachNotification(data: Record<string, unknown>): Promise<DPDPBreachNotification> {
    return request('/dpdp/remediate/breach-notification', { method: 'POST', body: JSON.stringify(data) });
}

export async function dpdpGetTemplates(): Promise<{ templates: { type: string; name: string; description: string }[] }> {
    return request('/dpdp/remediate/templates');
}

export async function dpdpGetDashboard(): Promise<DPDPDashboard> {
    return request('/dpdp/dashboard');
}

export async function dpdpGetOverdue(): Promise<{ total_overdue: number; rights_requests: unknown[]; grievances: unknown[] }> {
    return request('/dpdp/overdue');
}

// DPDP Compliance Reports
export async function dpdpGenerateReport(): Promise<{
    report_id: string;
    title: string;
    summary: string;
    compliance_score: number;
    content: Record<string, unknown>;
    generated_at: string;
}> {
    return request('/dpdp/report', { method: 'POST' });
}

export async function dpdpGetReportHistory(): Promise<{
    id: string;
    title: string;
    summary: string;
    compliance_score: number;
    report_type: string;
    generated_at: string;
}[]> {
    return request('/dpdp/reports');
}

// DPDP Knowledge Base Search
export async function dpdpSearchRegulation(query: string, maxResults = 5): Promise<{
    source: string;
    section: string;
    title: string;
    summary: string;
    full_text: string;
    penalties: string | null;
    deadline: string | null;
}[]> {
    return request(`/dpdp/knowledge/search?q=${encodeURIComponent(query)}&max_results=${maxResults}`);
}

// DPDP Consent Health
export async function dpdpGetConsentHealth(): Promise<{
    health_score: number;
    active_consents: number;
    total_records: number;
    consent_rate: number;
    purpose_stats: { code: string; name: string; grant_count: number }[];
    recent_events: Record<string, number>;
}> {
    return request('/dpdp/consent-health');
}

// DPDP Gap Assessment
export interface DPDPAssessmentQuestion {
    id: string;
    category: string;
    section: string;
    question: string;
    guidance: string;
    weight: number;
    is_critical: boolean;
}

export async function dpdpGetAssessmentQuestions(params?: {
    processes_children_data?: boolean;
    is_significant_fiduciary?: boolean;
    has_cross_border?: boolean;
}): Promise<DPDPAssessmentQuestion[]> {
    const qs = new URLSearchParams();
    if (params?.processes_children_data) qs.set('processes_children_data', 'true');
    if (params?.is_significant_fiduciary) qs.set('is_significant_fiduciary', 'true');
    if (params?.has_cross_border) qs.set('has_cross_border', 'true');
    return request(`/dpdp/assessment/questions?${qs.toString()}`);
}

export async function dpdpRunAssessment(data: {
    org_name: string;
    industry?: string;
    answers: { question_id: string; answer: string; evidence?: string; notes?: string }[];
    processes_children_data?: boolean;
    is_significant_fiduciary?: boolean;
    has_cross_border?: boolean;
}): Promise<{
    overall_score: number;
    overall_status: string;
    section_scores: unknown[];
    critical_gaps: unknown[];
    action_items: unknown[];
    deadline_risk: number;
}> {
    return request('/dpdp/assessment', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

// ============================================================================
// Contract Redline Analysis API
// ============================================================================

export async function analyzeContract(text: string, options: {
    playbook_id?: string;
    party_side?: 'buyer' | 'seller' | 'neutral';
    jurisdiction?: string;
    filename?: string;
    tier_preference?: 'ideal' | 'acceptable' | 'walk_away' | 'escalate';
    counterparty_type?: string;
    deal_size?: number;
    contract_side?: 'vendor' | 'customer';
    compliance_layers?: string[];
} = {}): Promise<AnalysisResult> {
    return request('/documents/analyze', {
        method: 'POST',
        body: JSON.stringify({
            text,
            playbook_id: options.playbook_id || undefined,
            party_side: options.party_side || 'buyer',
            jurisdiction: options.jurisdiction || undefined,
            filename: options.filename || 'pasted-contract.txt',
            tier_preference: options.tier_preference || undefined,
            counterparty_type: options.counterparty_type || undefined,
            deal_size: options.deal_size ?? undefined,
            contract_side: options.contract_side || undefined,
            compliance_layers: options.compliance_layers && options.compliance_layers.length
                ? options.compliance_layers
                : undefined,
        }),
    }, 0, 600000); // 10 min — AI analysis with thinking model
}

export interface ComplianceLayerSummary {
    code: string;
    name: string;
    description?: string;
    jurisdiction?: string;
    rule_count: number;
}

export async function listComplianceLayers(): Promise<ComplianceLayerSummary[]> {
    return request('/documents/compliance-layers');
}

export async function analyzeClause(clause_text: string, options: {
    playbook_id?: string;
    jurisdiction?: string;
} = {}): Promise<{ risks: RedlineItem[]; tokens_used: number; analysis_time_ms: number }> {
    return request('/documents/analyze-clause', {
        method: 'POST',
        body: JSON.stringify({
            clause_text,
            playbook_id: options.playbook_id || undefined,
            jurisdiction: options.jurisdiction || undefined,
        }),
    }, 0, 300000); // 5 min — single clause AI analysis
}

export async function generateFix(params: {
    original_text: string;
    recommendation: string;
    rule_name: string;
    clause_type?: string;
    redline_type: 'violation' | 'missing';
    surrounding_context?: string;
    playbook_id?: string;
    contract_text?: string;
}): Promise<GenerateFixResponse> {
    return request('/documents/generate-fix', {
        method: 'POST',
        body: JSON.stringify(params),
    }, 0, 600000); // 10 min — AI fix generation with thinking model
}

export async function exportRedlineReport(params: {
    filename: string;
    executive_summary: string[];
    redlines: Record<string, unknown>[];
    risk_summary: { red: number; yellow: number; green: number };
}): Promise<Blob> {
    const csrfToken = getCsrfToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
    }
    const res = await fetch(`${API_BASE_URL}/documents/export-report`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error('Export failed');
    return res.blob();
}
