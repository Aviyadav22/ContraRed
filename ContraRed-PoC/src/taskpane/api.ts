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
    // Confidence & verification fields (from backend pipeline stages 4-5)
    confidence?: number;           // 0.0-1.0 weighted score
    confidence_level?: string;     // "HIGH" | "MEDIUM" | "LOW"
    verification_status?: string;  // "exact" | "normalized" | "fuzzy_corrected"
    is_deal_breaker?: boolean;
    cross_references?: string[];
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

// Clause-level analysis (for selection scanning / re-scan)
interface ClauseAnalysisResult {
    risks: AIRedlineItem[];
    tokens_used: number;
    analysis_time_ms: number;
}

// Negotiation decision tracking
interface NegotiationDecision {
    risk_id: string;
    decision: 'accept' | 'counter' | 'escalate';
    counter_text?: string;
    timestamp: number;
}

interface NegotiationSession {
    started_at: number;
    notes: string;
    decisions: NegotiationDecision[];
    document_name: string;
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
    private currentUser: User | null = null;
    private isRefreshing = false;

    constructor() {
        this.loadUser();
    }

    private getCsrfToken(): string {
        const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    private loadUser(): void {
        try {
            const userStored = localStorage.getItem('contrared_user');
            if (userStored) {
                this.currentUser = JSON.parse(userStored);
            }
        } catch {
            // No stored user — fresh session
        }
    }

    private saveUser(user: User): void {
        this.currentUser = user;
        localStorage.setItem('contrared_user', JSON.stringify(user));
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

        // Add CSRF token for state-changing requests
        const method = (options.method || 'GET').toUpperCase();
        if (method !== 'GET' && method !== 'HEAD') {
            const csrf = this.getCsrfToken();
            if (csrf) headers['X-CSRF-Token'] = csrf;
        }

        const body = options.body;

        // AbortController timeout: 2 minutes
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

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
                throw new Error('Request timed out after 2 minutes. The server may be slow or unreachable.');
            }
            throw err;
        } finally {
            clearTimeout(timeoutId);
        }

        if (response.status === 204) {
            return undefined as T;
        }

        if (response.status === 401 && !this.isRefreshing) {
            // Try cookie-based refresh (server reads refresh_token from cookie)
            this.isRefreshing = true;
            try {
                const refreshResp = await fetch(`${API_BASE_URL}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                });
                if (refreshResp.ok) {
                    this.isRefreshing = false;
                    // Cookies updated by server, retry original request
                    const retryHeaders: Record<string, string> = { ...headers };
                    const newCsrf = this.getCsrfToken();
                    if (newCsrf) retryHeaders['X-CSRF-Token'] = newCsrf;
                    const retryResp = await fetch(url, {
                        method,
                        headers: retryHeaders,
                        credentials: 'include',
                        body: body as BodyInit | undefined,
                    });
                    if (retryResp.ok) {
                        if (retryResp.status === 204) return undefined as T;
                        return retryResp.json();
                    }
                }
            } catch {
                this.isRefreshing = false;
                this.logout();
                throw new Error('Session expired. Please log in again.');
            }
            this.isRefreshing = false;
            throw new Error('Session expired. Please log in again.');
        } else if (response.status === 401 && this.isRefreshing) {
            throw new Error('Session expired. Please log in again.');
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
            credentials: 'include',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        // Server sets HttpOnly cookies; only store user profile locally
        this.saveUser(data.user);
        return data;
    }

    async getCurrentUser(): Promise<User> {
        return this.request('/auth/me');
    }

    isLoggedIn(): boolean {
        // Tokens are in HttpOnly cookies (not accessible to JS).
        // Use presence of stored user profile as login indicator.
        // The server will validate the actual token on each request.
        return this.currentUser !== null;
    }

    getUser(): User | null {
        return this.currentUser;
    }

    async logout(): Promise<void> {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'X-CSRF-Token': this.getCsrfToken() },
            });
        } catch { /* best-effort server logout */ }
        this.currentUser = null;
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
    async analyzeWithAI(text: string, filename?: string, playbookId?: string, partySide?: string): Promise<AIAnalysisResult> {
        return this.request('/documents/analyze-full', {
            method: 'POST',
            body: JSON.stringify({ text, filename, playbook_id: playbookId, party_side: partySide || 'buyer' }),
        });
    }

    /**
     * Analyze a single clause/selection for risks.
     * Lighter-weight than full document scan — used for Scan Selection.
     */
    async analyzeClause(clauseText: string, playbookId?: string, jurisdiction?: string): Promise<ClauseAnalysisResult> {
        return this.request('/documents/analyze-clause', {
            method: 'POST',
            body: JSON.stringify({
                clause_text: clauseText,
                playbook_id: playbookId,
                jurisdiction,
            }),
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
        contractText?: string;
    }): Promise<{ fix_text: string; reasoning: string; fix_verified?: boolean; fix_warnings?: string[] }> {
        return this.request('/documents/generate-fix', {
            method: 'POST',
            body: JSON.stringify({
                original_text: params.originalText,
                recommendation: params.recommendation,
                rule_name: params.ruleName,
                redline_type: params.redlineType || 'violation',
                surrounding_context: params.surroundingContext,
                playbook_id: params.playbookId,
                contract_text: params.contractText,
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
        // WIRED_BY_REFACTOR: Replaced dead this.accessToken with cookie-based CSRF auth
        const csrf = this.getCsrfToken();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (csrf) headers['X-CSRF-Token'] = csrf;

        const response = await fetch(`${API_BASE_URL}/documents/export-report`, {
            method: 'POST',
            headers,
            credentials: 'include',
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
export type { User, RedlineResponse, Playbook, PlaybookRule, PlaybookDetail, AIRedlineItem, AIAnalysisResult, ClauseAnalysisResult, NegotiationDecision, NegotiationSession, ClauseLibraryItem, DocumentListItem, TemplateListItem };
