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
- [ ] TASK-016: Install slowapi (pip install slowapi) or create custom rate limiter middleware for FastAPI
- [ ] TASK-017: Add rate limiting to /analyze endpoint - max 10 requests/minute per user (this calls Azure OpenAI)
- [ ] TASK-018: Add rate limiting to /review endpoint - max 10 requests/minute per user
- [ ] TASK-019: Add rate limiting to ALL other endpoints - max 60 requests/minute per user as default
- [ ] TASK-020: Add rate limit exceeded response handler that returns proper 429 status with Retry-After header
- [ ] TASK-021: Add rate limit logging - log every rate limit hit with user identifier and endpoint

### 2.2 Auth and CORS Hardening
- [ ] TASK-022: Find CORS configuration - replace allow_origins=["*"] with specific Word Add-in origin URLs
- [ ] TASK-023: Verify EVERY non-health endpoint has auth middleware (Depends(get_current_user) or equivalent)
- [ ] TASK-024: Add auth to any unprotected endpoints found in audit
- [ ] TASK-025: Verify JWT token validation includes: expiry check, signature verification, issuer validation
- [ ] TASK-026: Add request ID middleware - generate unique ID per request for tracing

## PHASE 3: HIGH PRIORITY - AZURE OPENAI RESILIENCE (Iterations 31-45)

### 3.1 Timeout and Retry
- [ ] TASK-027: Add timeout parameter to EVERY Azure OpenAI API call - default 30 seconds for analysis, 60 seconds for review
- [ ] TASK-028: Install tenacity (pip install tenacity) and create a retry decorator for Azure OpenAI calls - exponential backoff, max 3 retries, retry on RateLimitError and APIConnectionError
- [ ] TASK-029: Apply retry decorator to ALL Azure OpenAI call functions
- [ ] TASK-030: Add circuit breaker pattern - if 5 consecutive Azure OpenAI failures, return cached/fallback response for 60 seconds

### 3.2 Token Counting
- [ ] TASK-031: Install tiktoken (pip install tiktoken) and create a token_counter.py utility
- [ ] TASK-032: Add token counting BEFORE every LLM call - calculate system_tokens + user_tokens, reject if exceeds model max minus buffer
- [ ] TASK-033: Add token usage logging - log input_tokens, output_tokens, total_cost per request
- [ ] TASK-034: Add contract text chunking - if document exceeds token limit, split into sections and analyze separately

### 3.3 Error Handling for LLM Calls
- [ ] TASK-035: Wrap EVERY Azure OpenAI call in try/except catching: openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError, openai.BadRequestError, Exception
- [ ] TASK-036: Return structured error responses from LLM failures - never expose raw OpenAI errors to frontend
- [ ] TASK-037: Add fallback behavior when LLM is down - return "analysis unavailable" with cached basic rules from playbook
- [ ] TASK-038: Move hardcoded model names to config/env - AZURE_OPENAI_MODEL=gpt-4o or similar

## PHASE 4: HIGH PRIORITY - OFFICE.JS AND TRACK CHANGES (Iterations 46-60)

### 4.1 Office.js API Fixes
- [ ] TASK-039: Find ALL Office.initialize usage - replace with Office.onReady()
- [ ] TASK-040: Find ALL Word API operations (insertText, insertParagraph, insertOoxml, delete) - verify each has await context.sync() after it
- [ ] TASK-041: Find ALL Word property reads (.text, .value, .font, .style) - verify each has .load() before context.sync() before read
- [ ] TASK-042: Find ALL Word.run() blocks - verify each has .catch() or try/catch with user-facing error message
- [ ] TASK-043: Add batch size limits to Word API collection operations (.paragraphs, .contentControls, .search) - process in chunks of 50

### 4.2 Track Changes Integrity
- [ ] TASK-044: Create an undo buffer system - before any document modification, save the original text/range to an undo stack
- [ ] TASK-045: Before any .delete() or .clear() operation, preserve the original content in the undo buffer
- [ ] TASK-046: Add a "Revert All Changes" function that walks the undo stack and restores original content
- [ ] TASK-047: Verify Track Changes uses word-level insertOoxml (not paragraph-level replace) - find any paragraph.insertText replacements and convert to surgical word-level edits

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
# LAST_COMPLETED: TASK-015
# TOTAL_FIXED: 15/68
# HEALTH_SCORE_BEFORE: 53.9
# HEALTH_SCORE_CURRENT: 53.9
