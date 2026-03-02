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

    const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

    if (!response.ok) {
        if (response.status === 401) {
            clearAuth();
            window.location.href = '/login';
        }
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
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
