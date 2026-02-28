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
    window.location.href = '/login';
}

export async function getCurrentUser(): Promise<User> {
    return request('/auth/me');
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
