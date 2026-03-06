/**
 * ContraRed API Client
 * Handles communication with the FastAPI backend
 */

// @ts-expect-error process.env injected by webpack DefinePlugin
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/api/v1';

// ============================================================================
// Types - Matched to Phase 2 Backend Schema
// ============================================================================

interface AuthTokens {
    access_token: string;
    refresh_token: string;
}

interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    subscription_tier: string;
}

interface RedlineResponse {
    original_text: string;
    suggested_text: string;
    ooxml: string;
    match_confidence?: number;  // 0.0-1.0 confidence of text anchor match
    match_method?: string;  // "hash", "exact", or "fuzzy"
}

// AI-First Analysis Types (for /analyze-full endpoint)
interface AIRedlineItem {
    id: string;
    risk_level: 'RED' | 'YELLOW';
    rule_name: string;
    original_text: string;  // Exact text from contract for search
    explanation: string;
    suggested_fix: string;
}

interface AIAnalysisResult {
    document_id: string;
    filename: string;
    executive_summary: string[];
    redlines: AIRedlineItem[];
    total_risks: number;
    risk_summary: { red: number; yellow: number };
    tokens_used: number;
}

// Playbook types
interface Playbook {
    id: string;
    name: string;
    description?: string;
    category: string;
    is_public: boolean;
    is_default: boolean;
    version: number;
    rules_count: number;
}

interface PlaybookRule {
    id: string;
    clause_type: string;
    primary_position: string;
    fallback_position?: string;
    risk_level: 'red' | 'yellow' | 'green';
    is_deal_breaker: boolean;
    detection_patterns: string[];
    suggested_language?: string;
    order_index: number;
}

interface PlaybookDetail extends Playbook {
    rules: PlaybookRule[];
}

interface CreateRuleRequest {
    clause_type: string;
    primary_position: string;
    fallback_position?: string;
    risk_level?: string;
    is_deal_breaker?: boolean;
    detection_patterns?: string[];
    suggested_language?: string;
}

// ============================================================================
// API Client Class
// ============================================================================

class ContraRedAPI {
    private accessToken: string | null = null;
    private refreshToken: string | null = null;
    private currentUser: User | null = null;

    constructor() {
        // Try to load tokens from localStorage on init
        this.loadTokens();
    }

    private loadTokens(): void {
        try {
            const stored = localStorage.getItem('contrared_tokens');
            if (stored) {
                const tokens = JSON.parse(stored);
                this.accessToken = tokens.access_token;
                this.refreshToken = tokens.refresh_token;
            }
            const userStored = localStorage.getItem('contrared_user');
            if (userStored) {
                this.currentUser = JSON.parse(userStored);
            }
        } catch {
            console.log('[ContraRed] No stored tokens found');
        }
    }

    private saveTokens(tokens: AuthTokens, user?: User): void {
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        localStorage.setItem('contrared_tokens', JSON.stringify(tokens));
        if (user) {
            this.currentUser = user;
            localStorage.setItem('contrared_user', JSON.stringify(user));
        }
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.accessToken) {
            (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // ========================================================================
    // Auth endpoints
    // ========================================================================

    async register(email: string, name: string, password: string): Promise<User> {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, name, password }),
        });
    }

    async login(email: string, password: string): Promise<{ access_token: string; refresh_token: string; user: User }> {
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
        this.saveTokens({ access_token: data.access_token, refresh_token: data.refresh_token }, data.user);
        return data;
    }

    async getCurrentUser(): Promise<User> {
        return this.request('/auth/me');
    }

    isLoggedIn(): boolean {
        return !!this.accessToken;
    }

    getUser(): User | null {
        return this.currentUser;
    }

    logout(): void {
        this.accessToken = null;
        this.refreshToken = null;
        this.currentUser = null;
        localStorage.removeItem('contrared_tokens');
        localStorage.removeItem('contrared_user');
    }

    // ========================================================================
    // Document endpoints
    // ========================================================================

    /**
     * Generate redline in ZDR mode (no database lookup).
     * Use when document text was analyzed but not persisted.
     */
    async generateRedlineZDR(
        documentId: string,
        riskId: string,
        originalText: string,
        suggestedText: string,
        paragraphHash?: string
    ): Promise<RedlineResponse> {
        return this.request('/documents/redline', {
            method: 'POST',
            body: JSON.stringify({
                document_id: documentId,
                risk_id: riskId,
                original_text: originalText,
                suggested_text: suggestedText,
                paragraph_hash: paragraphHash,
            }),
        });
    }

    /**
     * AI-First full contract analysis.
     * Sends full contract text + playbook to Gemini for holistic analysis.
     * Returns executive summary and redlines with exact-match text anchors.
     */
    async analyzeWithAI(text: string, filename?: string, playbookId?: string): Promise<AIAnalysisResult> {
        return this.request('/documents/analyze-full', {
            method: 'POST',
            body: JSON.stringify({ text, filename, playbook_id: playbookId }),
        });
    }

    // ========================================================================
    // Playbook endpoints
    // ========================================================================

    async listPlaybooks(): Promise<Playbook[]> {
        return this.request('/playbooks/');
    }

    async getPlaybook(playbookId: string): Promise<PlaybookDetail> {
        return this.request(`/playbooks/${playbookId}`);
    }

    async createPlaybook(name: string, description?: string, category?: string): Promise<Playbook> {
        return this.request('/playbooks/', {
            method: 'POST',
            body: JSON.stringify({ name, description, category: category || 'custom' }),
        });
    }

    async updatePlaybook(playbookId: string, data: { name?: string; description?: string; category?: string }): Promise<Playbook> {
        return this.request(`/playbooks/${playbookId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deletePlaybook(playbookId: string): Promise<void> {
        await this.request(`/playbooks/${playbookId}`, { method: 'DELETE' });
    }

    async togglePlaybookPublish(playbookId: string): Promise<Playbook> {
        return this.request(`/playbooks/${playbookId}/publish`, { method: 'POST' });
    }

    async addRule(playbookId: string, rule: CreateRuleRequest): Promise<PlaybookRule> {
        return this.request(`/playbooks/${playbookId}/rules`, {
            method: 'POST',
            body: JSON.stringify(rule),
        });
    }

    async updateRule(playbookId: string, ruleId: string, data: Partial<CreateRuleRequest>): Promise<PlaybookRule> {
        return this.request(`/playbooks/${playbookId}/rules/${ruleId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteRule(playbookId: string, ruleId: string): Promise<void> {
        await this.request(`/playbooks/${playbookId}/rules/${ruleId}`, { method: 'DELETE' });
    }

    // ========================================================================
    // Health check
    // ========================================================================

    async healthCheck(): Promise<{ status: string; version: string }> {
        const baseUrl = API_BASE_URL.replace('/api/v1', '');
        const response = await fetch(`${baseUrl}/health`);
        return response.json();
    }
}

// Export singleton instance
export const api = new ContraRedAPI();
export type { User, RedlineResponse, Playbook, PlaybookRule, PlaybookDetail, AIRedlineItem, AIAnalysisResult };
