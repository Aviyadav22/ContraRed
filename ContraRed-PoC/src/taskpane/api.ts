/**
 * ContraRed API Client
 * Handles communication with the FastAPI backend
 */

// @ts-expect-error process.env injected by webpack DefinePlugin
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8008/api/v1';

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
    redline_type?: string;  // "violation" or "missing"
}

// AI-First Analysis Types (for /analyze-full endpoint)
interface AIRedlineItem {
    id: string;
    risk_level: 'RED' | 'YELLOW';
    rule_name: string;
    original_text: string;  // Exact text from contract for search
    explanation: string;
    recommendation: string;  // Lawyer-readable guidance (not exact replacement text)
    redline_type: 'violation' | 'missing';
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

// Clause Library types
interface ClauseLibraryItem {
    id: string;
    clause_type: string;
    name: string;
    approved_text: string;
    is_mandatory: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

// Template Library types
interface TemplateListItem {
    id: string;
    name: string;
    description: string | null;
    category: string;
    is_premium: boolean;
    download_count: number;
    paired_playbook_id: string | null;
    paired_playbook_name: string | null;
}

// Document list (scan history)
interface DocumentListItem {
    id: string;
    filename: string;
    status: string;
    total_risks: number;
    risk_summary: { red: number; yellow: number } | null;
    created_at: string;
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
            // No stored tokens — fresh session
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

    private getStoredTokens(): AuthTokens | null {
        try {
            const stored = localStorage.getItem('contrared_tokens');
            if (stored) return JSON.parse(stored);
        } catch { /* ignore */ }
        return null;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...(options.headers as Record<string, string>),
        };

        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const method = options.method || 'GET';
        const body = options.body;

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (response.status === 204) {
            return undefined as T;
        }

        if (response.status === 401) {
            // Try refresh
            const tokens = this.getStoredTokens();
            if (tokens?.refresh_token) {
                try {
                    const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
                    });
                    if (refreshResp.ok) {
                        const newTokens = await refreshResp.json();
                        this.accessToken = newTokens.access_token;
                        this.refreshToken = newTokens.refresh_token;
                        localStorage.setItem('contrared_tokens', JSON.stringify(newTokens));
                        // Retry with new token
                        headers['Authorization'] = `Bearer ${newTokens.access_token}`;
                        const retryResp = await fetch(url, { method, headers, body: body as BodyInit | undefined });
                        if (retryResp.ok) {
                            if (retryResp.status === 204) return undefined as T;
                            return retryResp.json();
                        }
                    }
                } catch { /* refresh failed, fall through */ }
            }
            throw new Error(`Authentication failed: ${response.status}`);
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            const detail = error.detail;
            const message = typeof detail === 'object' && detail?.message
                ? detail.message
                : typeof detail === 'string' ? detail : `HTTP ${response.status}`;
            throw new Error(message);
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
     * List user's scanned documents (scan history).
     * Returns metadata only (no contract text).
     */
    async listDocuments(limit: number = 5): Promise<DocumentListItem[]> {
        return this.request(`/documents/list?limit=${limit}`);
    }

    /**
     * Generate redline in ZDR mode (no database lookup).
     * Use when document text was analyzed but not persisted.
     */
    async generateRedlineZDR(
        documentId: string,
        riskId: string,
        originalText: string,
        suggestedText: string,
        paragraphHash?: string,
        redlineType: string = 'violation'
    ): Promise<RedlineResponse> {
        return this.request('/documents/redline', {
            method: 'POST',
            body: JSON.stringify({
                document_id: documentId,
                risk_id: riskId,
                original_text: originalText,
                suggested_text: suggestedText,
                paragraph_hash: paragraphHash,
                redline_type: redlineType,
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

    /**
     * Research relevant Indian case law for a clause.
     */
    async researchClause(clauseText: string, clauseType?: string): Promise<{
        cases: Array<{ case_name: string; citation: string; year: number; court: string; holding: string; relevance: string }>;
        legal_principle: string;
        disclaimer: string;
    }> {
        return this.request('/documents/research-clause', {
            method: 'POST',
            body: JSON.stringify({ clause_text: clauseText, clause_type: clauseType }),
        });
    }

    /**
     * Generate a contract clause using AI.
     * Returns generated clause text + reasoning.
     */
    async generateClause(clauseType: string, playbookId?: string, contractContext?: string): Promise<{ clause_text: string; reasoning: string }> {
        return this.request('/documents/generate-clause', {
            method: 'POST',
            body: JSON.stringify({
                clause_type: clauseType,
                playbook_id: playbookId,
                contract_context: contractContext,
            }),
        });
    }

    /**
     * Generate exact replacement/insertion text for a specific risk.
     * Takes recommendation (guidance) and produces exact text for Word insertion.
     */
    async generateFix(params: {
        originalText: string;
        recommendation: string;
        ruleName: string;
        redlineType?: string;
        surroundingContext?: string;
        playbookId?: string;
    }): Promise<{ fix_text: string; reasoning: string }> {
        return this.request('/documents/generate-fix', {
            method: 'POST',
            body: JSON.stringify({
                original_text: params.originalText,
                recommendation: params.recommendation,
                rule_name: params.ruleName,
                redline_type: params.redlineType || 'violation',
                surrounding_context: params.surroundingContext,
                playbook_id: params.playbookId,
            }),
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
    // Export
    // ========================================================================

    /**
     * Export risk analysis as a DOCX report.
     * Returns a Blob for download.
     */
    async exportReport(analysisResult: AIAnalysisResult): Promise<Blob> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const response = await fetch(`${API_BASE_URL}/documents/export-report`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                filename: analysisResult.filename,
                executive_summary: analysisResult.executive_summary,
                redlines: analysisResult.redlines.map(r => ({
                    risk_level: r.risk_level,
                    rule_name: r.rule_name,
                    original_text: r.original_text,
                    explanation: r.explanation,
                    recommendation: r.recommendation,
                })),
                risk_summary: analysisResult.risk_summary,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Export failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.blob();
    }

    // ========================================================================
    // Clause Library
    // ========================================================================

    async listClauses(clauseType?: string, search?: string): Promise<ClauseLibraryItem[]> {
        const params = new URLSearchParams();
        if (clauseType) params.set('clause_type', clauseType);
        if (search) params.set('search', search);
        const qs = params.toString() ? `?${params.toString()}` : '';
        return this.request(`/clauses/${qs}`);
    }

    async createClause(data: { clause_type: string; name: string; approved_text: string; is_mandatory?: boolean }): Promise<ClauseLibraryItem> {
        return this.request('/clauses/', { method: 'POST', body: JSON.stringify(data) });
    }

    // ========================================================================
    // Templates
    // ========================================================================

    async listTemplates(category?: string): Promise<TemplateListItem[]> {
        const qs = category ? `?category=${encodeURIComponent(category)}` : '';
        return this.request(`/templates/${qs}`);
    }

    async downloadTemplate(templateId: string): Promise<{ id: string; name: string; template_content: string; paired_playbook_id: string | null }> {
        return this.request(`/templates/${templateId}/download`);
    }

    // ========================================================================
    // Health check
    // ========================================================================

    async healthCheck(): Promise<{ status: string; version: string }> {
        const baseUrl = API_BASE_URL.replace('/api/v1', '');
        const response = await fetch(`${baseUrl}/health`);
        if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
        return response.json();
    }
}

// Export singleton instance
export const api = new ContraRedAPI();
export type { User, RedlineResponse, Playbook, PlaybookRule, PlaybookDetail, AIRedlineItem, AIAnalysisResult, ClauseLibraryItem, DocumentListItem, TemplateListItem };
