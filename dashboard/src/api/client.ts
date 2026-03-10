/**
 * ContraRed Dashboard API Client
 * Shares authentication patterns with Word Add-in
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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
// Auth Storage
// ============================================================================

const TOKEN_KEY = 'contrared_tokens';
const USER_KEY = 'contrared_user';

export function getStoredTokens(): AuthTokens | null {
    try {
        const stored = localStorage.getItem(TOKEN_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch {
        return null;
    }
}

export function getStoredUser(): User | null {
    try {
        const stored = localStorage.getItem(USER_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch {
        return null;
    }
}

export function saveAuth(tokens: AuthTokens, user: User): void {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
    return !!getStoredTokens()?.access_token;
}

export function isAdmin(): boolean {
    const user = getStoredUser();
    return user?.role === 'admin' || user?.role === 'super_admin';
}

// ============================================================================
// API Request Helper
// ============================================================================

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const tokens = getStoredTokens();
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (tokens?.access_token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${tokens.access_token}`;
    }

    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
        if (response.status === 401) {
            const tokens = getStoredTokens();
            if (tokens?.refresh_token) {
                try {
                    const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
                    });
                    if (refreshResp.ok) {
                        const newTokens = await refreshResp.json();
                        const user = getStoredUser();
                        if (user) saveAuth(newTokens, user);
                        // Retry original request
                        const retryHeaders: Record<string, string> = { ...options.headers as any };
                        retryHeaders['Authorization'] = `Bearer ${newTokens.access_token}`;
                        const retryResp = await fetch(url, { ...options, headers: retryHeaders });
                        if (retryResp.ok || retryResp.status !== 401) {
                            if (retryResp.status === 204) return undefined as T;
                            return retryResp.json();
                        }
                    }
                } catch {}
            }
            clearAuth();
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const detail = error.detail;
        const message = typeof detail === 'object' && detail?.message
            ? detail.message
            : typeof detail === 'string' ? detail : `HTTP ${response.status}`;
        throw new Error(message);
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
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    saveAuth({ access_token: data.access_token, refresh_token: data.refresh_token }, data.user);
    return { user: data.user };
}

export function logout(): void {
    clearAuth();
    window.location.href = '/';
}

export async function register(name: string, email: string, password: string): Promise<{ user: User }> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
        throw new Error(error.detail || 'Registration failed');
    }

    // Auto-login after successful registration
    return login(email, password);
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
    return request('/team/members');
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
    return request('/playbooks/');
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
// Clause Library
// ============================================================================

export async function listClauses(clauseType?: string): Promise<ClauseLibraryItem[]> {
    const qs = clauseType ? `?clause_type=${encodeURIComponent(clauseType)}` : '';
    return request(`/clauses/${qs}`);
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
