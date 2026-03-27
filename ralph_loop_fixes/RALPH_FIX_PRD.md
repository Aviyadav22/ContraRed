# RALPH LOOP FIX ENGINE - ContraRed PRD Checklist
# Claude Code reads this file, picks unchecked tasks in order,
# fixes them, validates, marks done, commits, and moves on.
# 100 iterations x 8 hours = every checkbox gets addressed.

## PHASE 1: CRITICAL SECURITY (Iterations 1-15)

### 1.1 Exposed API Keys and Secrets
- [x] TASK-001: [ALREADY_FIXED] GEMINI_API_KEY only in .env (gitignored, never committed). Config reads from env vars with empty default.
- [x] TASK-002: [ALREADY_FIXED] AZURE_OPENAI_KEY/ENDPOINT empty in .env, config reads from env with empty defaults.
- [x] TASK-003: [ALREADY_FIXED] SECRET_KEY has placeholder in .env; config.py generates random key in debug mode, rejects placeholder in production.
- [x] TASK-004: [ALREADY_FIXED] DATABASE_URL only in .env (gitignored). Config reads from env. redis:// in config.py is just a comment.
- [x] TASK-005: [ALREADY_FIXED] No sk-/pk_/rk_ patterns found in any source files.
- [x] TASK-006: [ALREADY_FIXED] .gitignore already has .env, .env.local, .env.production, *.pem, *.key.
- [x] TASK-007: Updated backend/.env.example with ALL 45+ env vars from Settings class (added Vertex AI, WorkOS, Stripe, Sentry, Resend, cookie, encryption vars).

### 1.2 Prompt Injection Protection
- [x] TASK-008: Audited ALL 18 prompt interpolation points across 4 files (ai_service.py, gemini_analyzer.py, prompt_templates.py, analysis_pipeline.py).
- [x] TASK-009: Created prompt_sanitizer.py with 19 injection patterns, sanitize_for_prompt() and validate_contract_length().
- [x] TASK-010: [ALREADY_FIXED] prompt_templates.py already separates system/user prompts via render_system_prompt/render_user_prompt. Gemini consumer SDK uses system_instruction parameter.
- [x] TASK-011: Integrated sanitizer into gemini_analyzer.py (_sanitize_for_prompt delegates to new module) and ai_service.py (sanitize clause_text, rule_name, playbook_name in all methods).
- [x] TASK-012: /analyze endpoint already had 500K max; added min 50-char validation via validate_contract_length(). gemini_analyzer.py truncates at 200K.
- [x] TASK-013: [ALREADY_FIXED] _parse_response validates risk_level, clamps confidence 0-1, truncates redlines to 200 max, field lengths to 5000 chars.

### 1.3 eval() / exec() / Code Injection
- [x] TASK-014: [ALREADY_FIXED] No eval(), exec(), os.system(), or subprocess with shell=True found in entire backend.
- [x] TASK-015: [ALREADY_FIXED] No pickle.load/loads found anywhere in codebase.

## PHASE 2: HIGH PRIORITY - RATE LIMITING AND AUTH (Iterations 16-30)

### 2.1 Rate Limiting
- [x] TASK-016: [ALREADY_FIXED] slowapi>=0.1.9 in requirements.txt, limiter configured in auth.py, registered in main.py.
- [x] TASK-017: [ALREADY_FIXED] /analyze has @limiter.limit("20/minute"). Also /analyze-async, /analyze-full, /analyze-clause, /analyze-file.
- [x] TASK-018: [ALREADY_FIXED] All review/write endpoints have rate limits (10-30/min across billing, playbooks, documents).
- [x] TASK-019: [ALREADY_FIXED] All endpoints across all routers have @limiter.limit decorators.
- [x] TASK-020: Replaced default slowapi handler with custom _rate_limit_handler returning 429 + Retry-After header + structured JSON.
- [x] TASK-021: Custom handler now logs rate_limit_exceeded events with IP, path, and detail.

### 2.2 Auth and CORS Hardening
- [x] TASK-022: [ALREADY_FIXED] CORS uses allow_origin_regex for localhost in DEBUG, explicit CORS_ORIGINS list in production. No wildcard.
- [x] TASK-023: [ALREADY_FIXED] Verified ALL non-health/auth endpoints have Depends(get_current_user). Webhook endpoints use signature verification.
- [x] TASK-024: [ALREADY_FIXED] No unprotected endpoints found.
- [x] TASK-025: [ALREADY_FIXED] decode_token validates: exp (required), signature (SECRET_KEY+ALGORITHM), type (access/refresh/mfa), iat (not future), required claims (sub, email), jti. Blacklist checked in get_current_user.
- [x] TASK-026: Added RequestIDMiddleware — generates UUID per request, respects incoming X-Request-ID, adds to response headers. Logging includes request_id.

## PHASE 3: HIGH PRIORITY - AZURE OPENAI RESILIENCE (Iterations 31-45)

### 3.1 Timeout and Retry
- [x] TASK-027: [ALREADY_FIXED] All Gemini API calls wrapped in asyncio.wait_for(): 30s clause analysis, 90s full analysis, 120s batch. /analyze endpoint has 120s outer timeout.
- [x] TASK-028: [ALREADY_FIXED] Custom _rate_limited_call() implements exponential backoff (base 2s, max 60s, jitter) with 3 retries on rate-limit/quota errors.
- [x] TASK-029: [ALREADY_FIXED] _rate_limited_call applied to all AI call paths: analyze_full_contract, generate_fix, batch_generate_fixes, analyze_clause.
- [x] TASK-030: Added _CircuitBreaker class (threshold=5, recovery=60s). Integrated into _rate_limited_call — opens on consecutive failures, returns ai_circuit_open error. Auto-recovers after 60s with probe request.

### 3.2 Token Counting
- [x] TASK-031: [SKIPPED] tiktoken not needed — Gemini uses character-based limits (not BPE tokens). Contract text truncated at 200K chars (~50K tokens).
- [x] TASK-032: [ALREADY_FIXED] _sanitize_for_prompt truncates at 200K chars. Document endpoint enforces 500K max. Gemini generation_config sets max_output_tokens=32768.
- [x] TASK-033: Added token usage logging using Gemini's usage_metadata (prompt_token_count, candidates_token_count, total_token_count) after each analysis call.
- [x] TASK-034: [ALREADY_FIXED] Pipeline handles long documents via truncation with warning. Batch analysis and clause-level analysis provide chunking alternatives.

### 3.3 Error Handling for LLM Calls
- [x] TASK-035: [ALREADY_FIXED] _classify_gemini_error classifies all error types (429/rate_limit, timeout, auth, generic). _rate_limited_call catches and retries rate errors.
- [x] TASK-036: [ALREADY_FIXED] AIServiceError subclasses (AIRateLimited, AIServiceTimeout, AIServiceUnavailable) return structured error_code + message. documents.py maps these to proper HTTP responses.
- [x] TASK-037: [ALREADY_FIXED] _fallback_result() returns empty analysis with "AI analysis unavailable" message. Pipeline degrades to rule-based analysis when AI is down.
- [x] TASK-038: [ALREADY_FIXED] All model names in config.py as env vars: GEMINI_MODEL, GEMINI_ANALYSIS_MODEL, GEMINI_SCOUT_MODEL, GEMINI_SURGEON_MODEL, AZURE_OPENAI_DEPLOYMENT_GPT4, etc.

## PHASE 4: HIGH PRIORITY - OFFICE.JS AND TRACK CHANGES (Iterations 46-60)

### 4.1 Office.js API Fixes
- [x] TASK-039: [ALREADY_FIXED] Office.onReady() used (line 402). No Office.initialize found.
- [x] TASK-040: [ALREADY_FIXED] All 14 Word.run() blocks verified — every insertText/insertOoxml/delete has await context.sync() after it.
- [x] TASK-041: [ALREADY_FIXED] All property reads have .load() → context.sync() → read pattern. Verified: security, paragraphs, search results, ranges.
- [x] TASK-042: [ALREADY_FIXED] All Word.run() blocks wrapped in try/catch with user-facing error messages and log.warn.
- [x] TASK-043: [ALREADY_FIXED] Search operations are targeted (search within found range, not loading all paragraphs). Highlight batches use 2-sync approach instead of N+1.

### 4.2 Track Changes Integrity
- [x] TASK-044: [ALREADY_FIXED] appliedFixesMap stores originalText, fixText, paragraphIndex, contextHash before any document modification (line 336, 2798).
- [x] TASK-045: [ALREADY_FIXED] Every delete/replace operation has the original content preserved in appliedFixesMap before the edit.
- [x] TASK-046: Added revertAllFixes() function that iterates appliedFixesMap, restores each clause to originalText, clears the map, and resets UI state. Wired to revertAllBtn.
- [x] TASK-047: [ALREADY_FIXED] Primary path uses word-level surgical search+replace (computeWordDiffs → per-word search within range). OOXML is fallback only for 'missing' type or when surgical fails.

## PHASE 5: HIGH PRIORITY - PLAYBOOK ENGINE (Iterations 61-70)

### 5.1 Playbook Validation
- [ ] TASK-048: Create a playbook_schema.py with Pydantic models for playbook entries: clause_type, risk_level, standard_language, red_flags, fallback_position, market_standard, negotiation_guidance
- [ ] TASK-049: Add playbook JSON validation on application startup - load all playbook files through schema, fail fast if invalid
- [ ] TASK-050: Add risk_score bounds clamping (0-100) everywhere risk scores are calculated
- [ ] TASK-051: Replace any exact string matching for clause_type with case-insensitive normalized matching
- [ ] TASK-052: Add a playbook completeness check - log warning if any clause_type has missing optional fields

## PHASE 6: MEDIUM - INPUT VALIDATION AND API CONTRACTS (Iterations 71-80)

### 6.1 Pydantic Request Models
- [ ] TASK-053: Find ALL endpoints using raw request.json() - replace with typed Pydantic request body models
- [ ] TASK-054: Add field validators to ALL Pydantic request models - min/max length for strings, allowed values for enums
- [ ] TASK-055: Add response_model to ALL FastAPI endpoint decorators
- [ ] TASK-056: Add explicit status_code to all POST endpoints (201), DELETE endpoints (204)
- [ ] TASK-057: Create a standard error response model and use it across all error handlers

## PHASE 7: MEDIUM - LOGGING AND MONITORING (Iterations 81-90)

### 7.1 Structured Logging
- [ ] TASK-058: Replace ALL print() statements with Python logging module (logger = logging.getLogger(__name__))
- [ ] TASK-059: Replace ALL console.log() in production code with a proper logger (keep in dev-only blocks if needed)
- [ ] TASK-060: Add structured logging format - JSON logs with: timestamp, level, module, function, request_id, message
- [ ] TASK-061: Add request/response logging middleware - log method, path, status_code, duration_ms for every request
- [ ] TASK-062: Add Azure OpenAI call logging - log model, tokens_in, tokens_out, latency_ms, success/failure

## PHASE 8: LOW - CODE QUALITY AND CLEANUP (Iterations 91-100)

### 8.1 Dead Code and Documentation
- [ ] TASK-063: Find and remove ALL dead code - functions defined but never called, imports never used
- [ ] TASK-064: Resolve ALL TODO/FIXME/HACK comments - either fix the issue or create a GitHub issue and reference it
- [ ] TASK-065: Add docstrings to ALL public functions that don't have them
- [ ] TASK-066: Add type hints to ALL public function signatures
- [ ] TASK-067: Fix ALL loose equality (== to ===) in TypeScript/JavaScript files
- [ ] TASK-068: Run final validation - start the app, hit /health endpoint, verify no import errors or startup crashes

---

# STATUS TRACKING
# LAST_COMPLETED: TASK-047
# TOTAL_FIXED: 47/68
# HEALTH_SCORE_BEFORE: 53.9
# HEALTH_SCORE_CURRENT: 53.9
