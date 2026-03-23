# CONTRARED PRODUCTION AUDIT PRD — Ralph Wiggum Loop

## SYSTEM CONTEXT

ContraRed is an AI-powered contract redlining SaaS with 3 components:
- **Backend**: FastAPI (Python 3.11), PostgreSQL (Supabase), Redis
- **Dashboard**: React 19 + Vite 7 + TailwindCSS 4
- **Word Add-in**: TypeScript + Office.js (Microsoft Word taskpane)

**Deployed at:**
- Backend: `https://contrared.onrender.com` (Render.com)
- Dashboard: `https://contrared.netlify.app` (Netlify)
- Word Add-in: `https://contrared-addin.netlify.app` (Netlify)
- Database: Supabase PostgreSQL (ap-south-1)

## THE CORE PROBLEMS

1. **Legacy regex engine still deeply embedded** — `rule_engine.py` (730 lines, 16+75 rules), `clause_classifier.py` (968 lines, 30 rules), `scope_analyzer.py`, `defined_terms_resolver.py`, `jurisdiction_detector.py` all use pure regex. These run in Stages 1-2 BEFORE AI touches the contract.

2. **Playbook system built on regex patterns** — `PlaybookRule.detection_patterns` stores regex with `match_type: exact|fuzzy|regex`. `RuleEngine.from_playbook_rules()` compiles these into regex matchers. Users create rules by writing regex in the dashboard.

3. **Text replacement replaces whole paragraphs** — OOXML generation in `redline_implementer.py` does word-level diffs via `SequenceMatcher`, but the Word add-in uses `insertOoxml(ooxml, Word.InsertLocation.replace)` which replaces the ENTIRE found range. If `findTextInDocument()` matches a whole paragraph, everything turns red/green even for a single word change.

4. **Confidence scoring biases toward regex** — `confidence_scorer.py` gives regex+AI agreement 1.0 but AI-only 0.8, penalizing novel AI-only findings.

## RULES

- ONE TASK per iteration. Check it off [x] when done.
- Commit after every task: `[CONTRARED-AUDIT] <description>`
- Append to progress.txt after every iteration: what you found, files read, patterns discovered.
- NEVER touch .env, API keys, secrets, or manifest.xml secrets.
- NEVER implement fixes in this loop — ANALYSIS AND DOCUMENTATION ONLY.
- Use web search when a task says WEB_SEARCH.
- Read ENTIRE files, not grep snippets. The bugs hide in the details.
- Think like an adversary: what would a pentester find? What would a demanding lawyer complain about?

---

## PHASE 1: REGEX/PATTERN ENGINE INVENTORY (10 tasks)

For each task, read the ENTIRE file. Classify every function/regex as KEEP (structural/preprocessing), REPLACE-WITH-AI (semantic/risk detection), or REMOVE (dead/redundant).

**Classification criteria:**
- **KEEP**: Section splitting, paragraph detection, defined term extraction, text normalization, citation patterns. These are fast, deterministic, correct. AI would be slower and less reliable.
- **REPLACE-WITH-AI**: Risk detection, scope analysis, clause type classification, obligation extraction. AI understands context and legal nuance that regex cannot.
- **REMOVE**: Dead code, unused fallbacks, patterns the AI already covers redundantly.

- [x] REGEX-1: Read `backend/app/services/rule_engine.py` (all 730 lines). Document every regex pattern and rule. Classify each as KEEP/REPLACE/REMOVE. Pay special attention to: how `from_playbook_rules()` compiles playbook rules into regex matchers, how `apply_rules()` runs regex before AI, which of the 16 built-in rules overlap with what AI already detects. Write findings to progress.txt.
- [x] REGEX-2: Read `backend/app/services/rules_library.py` (all 75 rules). Document every rule definition. For each rule: what legal risk does it detect, does it use regex patterns or keyword lists, could AI detect this more accurately with context? Write findings to progress.txt.
- [x] REGEX-3: Read `backend/app/services/clause_classifier.py` (all 968 lines, 30 rules). This is the clause type classifier — it determines whether a clause is "indemnification" vs "limitation of liability" etc. Document: does it use keyword lists, regex patterns, or AI? What happens when a clause doesn't match any pattern? Write findings to progress.txt.
- [x] REGEX-4: Read `backend/app/services/scope_analyzer.py` (all 406 lines). This analyzes the scope/coverage of contract obligations. Document: is scope analysis done by regex or AI? Can regex understand "This agreement covers all services provided globally" vs "This agreement is limited to services in Maharashtra"? Write findings to progress.txt.
- [x] REGEX-5: Read `backend/app/services/defined_terms_resolver.py` (all 434 lines). This extracts defined terms like "Confidential Information means..." Document: is regex appropriate here? (Defined terms follow predictable patterns like quoted terms, capitalized terms, "means" definitions). Classify as KEEP if regex is genuinely better. Write findings to progress.txt.
- [x] REGEX-6: Read `backend/app/services/jurisdiction_detector.py` (full file). Document how it detects governing law and jurisdiction clauses. Classify as KEEP if pattern-based ("governed by the laws of [State]") or REPLACE if it needs to understand complex multi-jurisdiction provisions. Write findings to progress.txt.
- [x] REGEX-7: Read `backend/app/services/text_normalizer.py` and `backend/app/services/structure_extractor.py` (full files). These are preprocessing steps. Document what they do. Almost certainly KEEP — normalization and structure extraction are regex-appropriate. Confirm this. Write findings to progress.txt.
- [x] REGEX-8: Read `backend/app/services/confidence_scorer.py` (all 250+ lines). Document the scoring formula. Specifically: the regex+AI=1.0 vs AI-only=0.8 bias. In an AI-first system, should AI-only findings be downgraded? Propose a new scoring model. Write findings to progress.txt.
- [x] REGEX-9: Read `backend/app/services/hallucination_guard.py` (all 370 lines). Document: how does it verify AI findings against the actual contract text? Is the 0.80 fuzzy threshold (rapidfuzz Levenshtein) correct? What happens when AI quotes text slightly wrong (common with LLMs)? Are deal-breaker rules kept at confidence 0.3 — is this dangerous? Write findings to progress.txt.
- [x] REGEX-10: WEB_SEARCH — Search for "LLM vs regex for contract analysis 2025 2026" and "agentic document analysis best practices". Then create REGEX_INVENTORY.md summarizing: total regex instances found, classification (KEEP/REPLACE/REMOVE counts), priority-ordered migration plan, estimated effort per migration item. Write findings to progress.txt.

---

## PHASE 2: PLAYBOOK SYSTEM AUDIT (8 tasks)

- [x] PLAYBOOK-1: Read `backend/app/models/playbook.py` (all 259 lines). Document the PlaybookRule schema completely. Specifically: what is `detection_patterns` (JSONB)? What fields exist for AI (`requires_ai_verification`, `verification_prompt`)? Are AI fields being used or are they dead? Write findings to progress.txt.
- [x] PLAYBOOK-2: Read `backend/app/api/v1/endpoints/playbooks.py` (all 1200+ lines). Trace how playbook rules are created, stored, retrieved, and applied. Document the full CRUD lifecycle. Write findings to progress.txt.
- [x] PLAYBOOK-3: Read `backend/app/services/playbook_cache.py` (all 158 lines) and `backend/app/services/playbook_conditions_engine.py` (all 650 lines). Document how playbook conditions are evaluated at runtime. Is this regex-based or AI-based? Write findings to progress.txt.
- [x] PLAYBOOK-4: Read `backend/app/services/playbook_versioning.py` (all 650 lines). Document the versioning system. If we migrate the schema from regex to AI-native, how does versioning handle backward compatibility? Write findings to progress.txt.
- [x] PLAYBOOK-5: Read `dashboard/src/pages/PlaybookEditor.tsx` (all 1000+ lines) and `dashboard/src/pages/Playbooks.tsx` (all 200+ lines). Document the current UX for creating rules. Users currently enter regex patterns — what should they enter instead? (Natural language descriptions, risk criteria, acceptable positions, fallback language). Write findings to progress.txt.
- [x] PLAYBOOK-6: Check if playbook templates (`/templates/browse` endpoint) are hardcoded with regex patterns. Document which templates exist and whether they need migration. Write findings to progress.txt.
- [x] PLAYBOOK-7: Design the AI-first playbook rule schema. Propose what replaces `detection_patterns`. Consider: `risk_description` (natural language), `acceptable_position` (what client wants), `fallback_language` (pre-approved alternative), `severity`, `clause_context` (what type of clause this applies to). Document in progress.txt with full proposed schema.
- [x] PLAYBOOK-8: WEB_SEARCH — Search for "AI-native playbook systems legal tech" and "LLM-based contract rule engines 2025 2026". Document industry patterns. Then propose: tiered evaluation (regex pre-filter for speed + AI for accuracy), backward compatibility (keep old rules working during migration), dashboard UX (natural language rule editor). Write full proposal to progress.txt.

---

## PHASE 3: TEXT REPLACEMENT / OOXML PIPELINE (10 tasks)

This is the critical "whole paragraph turns red" bug.

- [x] OOXML-1: Read `backend/app/services/redline_implementer.py` (all 525 lines). Document EXACTLY how the OOXML is generated. Focus on: how `SequenceMatcher` diffs original vs replacement at word level, how `<w:del>` and `<w:ins>` tags are generated, whether the generated OOXML itself is correct (word-level diffs look right). Write findings to progress.txt.
- [x] OOXML-2: Read `ContraRed-PoC/src/taskpane/taskpane.ts` — focus on `findTextInDocument()` (~lines 884-963). Document the 3-tier search strategy: Tier 1 (exact text via `body.search()`), Tier 2 (paragraph iteration + includes check), Tier 3 (Fuse.js fuzzy on paragraphs). Document: when does each tier activate? What range precision does each return? Write findings to progress.txt.
- [x] OOXML-3: Read `ContraRed-PoC/src/taskpane/taskpane.ts` — focus on `applyAIRedline()` (~lines 2329-2428). Document EXACTLY how the OOXML gets inserted into Word. The key call is `range.insertOoxml(ooxml, Word.InsertLocation.replace)`. Document: what is the `range` at this point? Is it the exact clause or the whole paragraph? Write findings to progress.txt.
- [x] OOXML-4: Identify the ROOT CAUSE of "whole paragraph turns red". Trace the exact failure path: (a) `findTextInDocument()` returns a paragraph-level range (Tier 2 or 3), (b) `insertOoxml(..., replace)` replaces the ENTIRE range, (c) even though the OOXML has word-level `<w:del>`/`<w:ins>`, Word treats the entire replaced range as a revision if Track Changes is on. Document the root cause precisely in progress.txt.
- [x] OOXML-5: Document the `body.search()` 255-character limit issue. When quotes are longer than 255 chars, what happens? Does the search truncate? Does it match the wrong text? How does this interact with the range precision problem? Write findings to progress.txt.
- [x] OOXML-6: Read `ContraRed-PoC/src/taskpane/taskpane.ts` — focus on `undoRedlineFix()` (~lines 2228-2285). Document how undo works. If the replacement was paragraph-level, can undo restore the original precisely? Write findings to progress.txt.
- [x] OOXML-7: Read `ContraRed-PoC/src/taskpane/api.ts` — focus on `generateRedlineZDR()` and `generateFix()`. Document what the backend sends back and what the frontend does with it. Is the original_text sent to the backend the same as what Word has? (If Track Changes are already present, `paragraph.text` may include deleted text). Write findings to progress.txt.
- [ ] OOXML-8: WEB_SEARCH — Search for "Office.js insertOoxml precision track changes" and "Word API range.insertText vs insertOoxml for redlining" and "Office.js search 255 character limit workaround". Document best practices found. Write to progress.txt.
- [ ] OOXML-9: WEB_SEARCH — Search for "Office.js Range.search find replace specific words track changes" and "Word OOXML del ins tags best practices". The correct approach is: `paragraph.search(exactOldPhrase)` to get a tight Range of ONLY the changing text, then `range.insertText(newPhrase, "Replace")`. With Track Changes enabled, Word marks ONLY the searched phrase as changed. Document this approach with pros/cons vs the current OOXML approach. Write to progress.txt.
- [ ] OOXML-10: Create REPLACEMENT_FIX_PROPOSAL.md documenting 3 solution options with trade-offs:
  - **Option A: Surgical search+replace** — For each word-level diff, use `paragraph.search(oldWord/Phrase)` to find exact Range, then `range.insertText(newPhrase, "Replace")`. Pros: Word natively handles Track Changes, only changed words go red. Cons: Multiple API calls per fix, Word search has quirks (255 limit, regex needed for special chars).
  - **Option B: Improved OOXML with tighter range** — Keep OOXML generation but fix `findTextInDocument()` to ALWAYS return the tightest possible range (sentence-level, not paragraph-level). Search for the exact sentence containing the change. Pros: Single API call. Cons: OOXML + Track Changes interaction is still fragile.
  - **Option C: Hybrid** — Use OOXML for complex multi-word changes, use search+insertText for simple word swaps. Route based on diff complexity.
  
  Recommend the best option with reasoning. Write to progress.txt.

---

## PHASE 4: AI PROMPT QUALITY AUDIT (6 tasks)

- [ ] PROMPT-1: Read `backend/app/services/prompt_templates.py` (full file). Document every prompt template. Evaluate: is the V2 structured framework (ORIENT → TERMS CHECK → RULE-BY-RULE → CROSS-CLAUSE) effective? Are risk level criteria (RED/YELLOW/GREEN) well-calibrated for production legal use? Write findings to progress.txt.
- [ ] PROMPT-2: Read `backend/app/services/gemini_analyzer.py` (full file). Document the AI analysis pipeline. Evaluate: how does the system handle the contract text + playbook rules + analysis instructions in a single prompt? Is the context window being used efficiently? Write findings to progress.txt.
- [ ] PROMPT-3: Read `backend/app/services/analysis_pipeline.py` (full file). Trace the 5-stage analysis pipeline end-to-end. For each stage: what runs (regex or AI or both), what does it produce, what feeds into the next stage. Document the full flow in progress.txt.
- [ ] PROMPT-4: Evaluate prompt edge cases: What happens with an empty contract? Non-English contract? Contract with no risks (all GREEN)? Partial document? Amendments referencing a master agreement? A 50-page contract that exceeds context window? Document findings in progress.txt.
- [ ] PROMPT-5: Evaluate `temperature: 0.1` — is this optimal for legal analysis? Too deterministic may miss creative risk interpretations. Too creative may hallucinate risks. What do industry best practices say? Evaluate fix generation prompts: are they producing legally sound replacement language? Write findings to progress.txt.
- [ ] PROMPT-6: Evaluate the party perspective handling. Does the prompt correctly handle buyer vs seller vs neutral perspective? ContraRed reviews contracts FROM the client's perspective (usually the vendor/seller receiving a buyer's contract). Is this correctly baked into prompts? Write findings to progress.txt.

---

## PHASE 5: WORD ADD-IN PRODUCTION STABILITY (8 tasks)

- [ ] ADDIN-1: Read `ContraRed-PoC/src/taskpane/taskpane.ts` (all 2679 lines). Document: what happens when the backend is down? (500s, timeouts, network errors). Is there user-facing error handling or silent failure? Write findings to progress.txt.
- [ ] ADDIN-2: Audit loading states. Are ALL async operations showing spinners/progress? The 120-second timeout — is there user feedback during long scans? (Progress bar? Stage updates? "Analyzing clause 5 of 23"?) Or does it just show a spinner for 2 minutes? Write findings to progress.txt.
- [ ] ADDIN-3: Audit button debouncing and state management. Can users double-fire scans by clicking rapidly? What happens if user scans again while results are displayed? Is `currentAIAnalysis` / `fixedRisks` / `negotiationSession` state robust? Write findings to progress.txt.
- [ ] ADDIN-4: Audit large document handling. Memory issues with 50+ page contracts? Does `body.paragraphs.load()` choke? Are there pagination or chunking strategies? Write findings to progress.txt.
- [ ] ADDIN-5: Audit the negotiation mode. Is auto-scan-on-selection reliable? Does the 1.5s debounce cause missed selections? Is the flow intuitive for a lawyer using it in real-time? Write findings to progress.txt.
- [ ] ADDIN-6: Audit accessibility. Screen readers, keyboard navigation, ARIA labels, color contrast — are they production-ready? Write findings to progress.txt.
- [ ] ADDIN-7: Audit memory leaks. Are event listeners cleaned up? Are timers cleared? Are Office.js tracked objects released? Write findings to progress.txt.
- [ ] ADDIN-8: Read `ContraRed-PoC/src/taskpane/api.ts` (all 602 lines). Audit: token handling, error retry logic, request/response interceptors, timeout configuration. Is the API client production-ready? Write findings to progress.txt.

---

## PHASE 6: DASHBOARD AUDIT (5 tasks)

- [ ] DASH-1: Read `dashboard/src/api/client.ts` (all 1250+ lines). Audit the wrapped response pattern: which endpoints return `{ items: [], total: N }` vs plain arrays? Are ALL client functions handling this correctly? (4 were already fixed — are there more?) Write findings to progress.txt.
- [ ] DASH-2: Audit `dashboard/src/pages/PlaybookEditor.tsx` and `dashboard/src/pages/Playbooks.tsx`. Focus on: error boundaries, empty states, loading states, form validation. Can a user create an invalid playbook rule? What happens on save failure? Write findings to progress.txt.
- [ ] DASH-3: Audit `dashboard/src/pages/BatchUpload.tsx`, `Compare.tsx`, `Analytics.tsx`, `Dashboard.tsx`. For each page: error handling, empty states, loading states, data freshness (React Query stale time), pagination handling. Write findings to progress.txt.
- [ ] DASH-4: Audit TypeScript type safety. Are interfaces matching backend response schemas exactly? Any `as any` casts hiding type mismatches? Write findings to progress.txt.
- [ ] DASH-5: Audit race conditions. Can stale data from React Query cause UI glitches? What happens if user navigates away during a mutation? Write findings to progress.txt.

---

## PHASE 7: SECURITY & PRODUCTION HARDENING (8 tasks)

- [ ] SEC-1: Read `backend/app/core/config.py`. Audit: are any secrets hardcoded? Are there dangerous defaults (e.g., JWT_SECRET defaulting to "changeme")? Are all env vars validated on startup? Write findings to progress.txt.
- [ ] SEC-2: Read `backend/main.py`. Audit CORS configuration. Is it `*` (wildcard) or properly restricted to the dashboard and add-in origins? Are all middleware layers correct? Write findings to progress.txt.
- [ ] SEC-3: Read `backend/app/api/v1/endpoints/auth.py`. Audit the auth flow: JWT token generation, validation, expiry, refresh. Are tokens properly scoped? Can a user access another user's data? Write findings to progress.txt.
- [ ] SEC-4: Audit ALL API endpoints for authorization. Are there any accidentally public routes that should require auth? Any endpoints missing `current_user` dependency? Write findings to progress.txt.
- [ ] SEC-5: Audit input validation across all endpoints. SQL injection risk (raw SQL queries)? XSS risk (user content rendered in HTML)? Prompt injection (contract text sent to Gemini could contain "Ignore previous instructions...")? Write findings to progress.txt.
- [ ] SEC-6: Audit rate limiting. Are expensive AI endpoints rate-limited? Can someone burn through Gemini API credits by spamming scans? Write findings to progress.txt.
- [ ] SEC-7: WEB_SEARCH — Search for "OWASP top 10 SaaS 2025" and "FastAPI security best practices production". Cross-reference findings with the codebase. Write any new vulnerabilities found to progress.txt.
- [ ] SEC-8: Audit file upload handling in batch analysis. Are DOCX files sanitized? Can a malicious DOCX exploit the parser? Are file size limits enforced? Write findings to progress.txt.

---

## PHASE 8: PERFORMANCE & COST (5 tasks)

- [ ] PERF-1: Analyze AI token usage. How many tokens per contract scan? Estimate cost per scan at Gemini pricing. Can prompts be shortened without quality loss? Write findings to progress.txt.
- [ ] PERF-2: Audit caching. Is `CacheService` / `playbook_cache.py` effective? What's the cache hit rate potential? Are expensive computations (AI analysis, OOXML generation) being cached? Write findings to progress.txt.
- [ ] PERF-3: Audit database queries. Any N+1 queries? Missing indexes? Slow joins? Check the playbook queries especially — loading rules + conditions + versions. Write findings to progress.txt.
- [ ] PERF-4: Audit concurrent analysis. The batch endpoint runs 3 concurrent analyses — is this safe with Gemini rate limits? What happens if one fails? Write findings to progress.txt.
- [ ] PERF-5: Audit cold start and response times. Render.com spins down on inactivity — what's the cold start time? For long scans (90s+), should the system use SSE/WebSocket for progress instead of polling? Write findings to progress.txt.

---

## PHASE 9: EDGE CASE TESTING SCENARIOS (5 tasks)

- [ ] EDGE-1: Document what happens with: empty contract (0 text), non-English contract (Hindi contract with English legal terms), contract with NO risks (all GREEN), partial document (just one section pasted). Write expected vs actual behavior in progress.txt.
- [ ] EDGE-2: Document what happens with AI failures: Gemini returns malformed JSON, Gemini is rate-limited mid-analysis (429), Gemini returns empty response, Gemini hallucates a clause that doesn't exist in the contract. Write expected vs actual behavior in progress.txt.
- [ ] EDGE-3: Document what happens with concurrent usage: two users scan same document, user scans while previous scan is still running, user closes Word while scan is in progress. Write expected vs actual behavior in progress.txt.
- [ ] EDGE-4: Document what happens with playbook edge cases: playbook with 0 rules, playbook with 200 rules (performance), rule that matches every clause in the document (false positive storm), conflicting rules (one says GREEN, another says RED for same clause). Write expected vs actual behavior in progress.txt.
- [ ] EDGE-5: Document what happens with Word API edge cases: text that appears multiple times in document (which instance gets replaced?), very long clauses (>255 chars, Word search limit), clauses spanning multiple paragraphs, document with existing Track Changes from a previous review. Write expected vs actual behavior in progress.txt.

---

## PHASE 10: FINAL SYNTHESIS (3 tasks)

- [ ] FINAL-1: Create PRIORITY_MATRIX.md with all findings organized as:
  **P0 (Must fix before production):** issues that will cause visible bugs, data loss, security holes, or user trust damage.
  **P1 (First sprint post-launch):** issues that cause UX friction or suboptimal results but don't break functionality.
  **P2 (First month):** optimization, cleanup, nice-to-haves.
  For each issue: description, impact, estimated effort (hours), files affected, recommended approach.

- [ ] FINAL-2: Create ARCHITECTURAL_DECISIONS.md documenting the 3 key decisions that need human input:
  1. **Regex vs AI migration** — recommended approach, migration order, backward compatibility strategy, estimated cost/timeline.
  2. **Playbook schema migration** — new schema design, data migration plan, dashboard UX changes, backward compatibility.
  3. **Text replacement fix** — recommended option (A/B/C from OOXML-10), implementation plan, testing strategy.

- [ ] FINAL-3: Create PRODUCTION_READINESS_REPORT.md — a comprehensive report summarizing: total issues found per category, critical blockers, security status, performance baseline, recommended launch timeline. Final commit: `[CONTRARED-AUDIT] Complete production audit — see PRODUCTION_READINESS_REPORT.md`

If ALL tasks are checked [x], output <promise>COMPLETE</promise>.
