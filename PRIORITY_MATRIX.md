# ContraRed Production Audit — Priority Matrix

All findings from the 68-task production audit, organized by priority.

---

## P0 — Must Fix Before Production
Issues that will cause visible bugs, data loss, security holes, or user trust damage.

| # | Issue | Impact | Files | Effort | Source |
|---|-------|--------|-------|--------|--------|
| 1 | **Paragraph destruction on Tier 3 fix apply** — `findTextInDocument()` fuzzy returns `paragraph.getRange()`, `insertOoxml(replace)` destroys surrounding text | Data loss — 340+ chars permanently deleted, undo can't recover | taskpane.ts:955, 2378 | 16h | OOXML-4 |
| 2 | **Wrong clause instance modified** — `body.search()` always returns `items[0]`, modifies FIRST occurrence instead of flagged one | Modifies wrong clause in contract | taskpane.ts:900 | 8h | EDGE-5 |
| 3 | **255-char partial replacement** — long clauses truncated, only first 255 chars replaced, rest orphaned | Broken paragraphs in legal document | taskpane.ts:892-894 | 8h | OOXML-5 |
| 4 | **ReDoS via playbook regex** — user-supplied regex compiled without protection; `(a+)+$` pattern causes CPU exhaustion | Remote DoS on any user loading malicious playbook | rule_engine.py:663, playbooks.py:761 | 4h | REGEX-1 |
| 5 | **Track Changes double-tracking** — `changeTrackingMode=trackAll` + OOXML embedded `<w:del>/<w:ins>` = double revision marks | Confusing revision marks for lawyers | taskpane.ts:2360, 2378 | 4h | OOXML-3 |
| 6 | **Password reset missing complexity validation** — only `min_length=8`, no uppercase/digit/special | Weak passwords via reset flow | auth.py:988 | 1h | SEC-3 |
| 7 | **Password reset token reusable** — NOT blacklisted after use, valid for full 1-hour expiry | Attacker can reset password multiple times | auth.py:983-1025 | 1h | SEC-3 |
| 8 | **X-Forwarded-For trusted without proxy validation** — rate limits bypassable by spoofing header | All rate limits effectively disabled | auth.py:63-68 | 2h | SEC-3 |
| 9 | **DOCX table content not extracted** — `doc.paragraphs` misses tables, text boxes, headers | Fee schedules, SLA matrices invisible to analysis | structure_extractor.py:90 | 8h | REGEX-7 |

---

## P1 — First Sprint Post-Launch
Issues that cause UX friction or suboptimal results but don't break core functionality.

| # | Issue | Impact | Files | Effort | Source |
|---|-------|--------|-------|--------|--------|
| 10 | AI-only confidence penalty (12.5%) | Novel AI findings downgraded from HIGH to MEDIUM | confidence_scorer.py:250 | 2h | REGEX-8 |
| 11 | Party name hardcoding in scope analysis | Only 5 labels per side; misses Seller/Consultant/Contractor | scope_analyzer.py:166-171 | 4h | REGEX-4 |
| 12 | `irrevocable` classified as `perpetual` | Legal error — irrevocable licenses can have fixed terms | scope_analyzer.py:183 | 1h | REGEX-4 |
| 13 | Default party_side is "buyer" not "seller" | Target market (vendors) gets inverted risk perspective | prompt_templates.py:484, gemini_analyzer.py:223 | 1h | PROMPT-6 |
| 14 | Playbook.party_side stored but IGNORED | Playbook's perspective not used during analysis | analysis_pipeline.py, gemini_analyzer.py | 2h | PROMPT-6 |
| 15 | Fix prompts don't inject defined terms | AI may use wrong terminology in replacement text | prompt_templates.py:516-572 | 2h | PROMPT-5 |
| 16 | Non-English contracts: verification rejects valid findings | Regex misses all, hallucination guard rejects AI quotes | Multiple | 8h | EDGE-1 |
| 17 | Partial document: false positive storm | 15-20 "missing" warnings for clauses that exist elsewhere | analysis_pipeline.py | 4h | EDGE-1 |
| 18 | Silent truncation at 200K chars | Documents 200K-500K pass frontend but backend silently drops content | gemini_analyzer.py:261, taskpane.ts:984 | 2h | PROMPT-4 |
| 19 | Prompt injection via contract text | Unsanitized contract text in AI prompts | gemini_analyzer.py:261, 278 | 4h | PROMPT-1 |
| 20 | System+user prompt concatenated | Weakens system prompt authority vs Gemini native system instruction | gemini_analyzer.py:278 | 2h | PROMPT-2 |
| 21 | No edit capability for existing rules | Users must delete and re-create to change a rule | PlaybookEditor.tsx | 8h | PLAYBOOK-5 |
| 22 | `browseMarketplace()` missing unwrapping | Returns `{items, total}` object instead of array — crashes Marketplace.tsx | dashboard/api/client.ts:622 | 0.5h | DASH-1 |
| 23 | Cross-paragraph clauses unfindable | `body.search()` can't find text spanning paragraphs | taskpane.ts:884-963 | 8h | EDGE-5 |
| 24 | Existing Track Changes confuse AI | `body.text` includes deleted text, AI flags already-resolved issues | taskpane.ts:2580-2585 | 4h | EDGE-5 |
| 25 | ZIP bomb risk in batch upload | No decompression size limit; 10MB DOCX → 1GB+ in memory | documents.py:1089-1094 | 2h | SEC-8 |
| 26 | No React error boundaries | Rendering crash = white screen, no recovery | All dashboard pages | 4h | DASH-2 |
| 27 | Apply Fix has no loading indicator | 3-6s operation with no visual feedback | taskpane.ts:2346-2424 | 1h | ADDIN-2 |
| 28 | ADGM alias maps to wrong legal system | Common-law free zone mapped to civil-law onshore UAE | jurisdiction_detector.py:678 | 1h | REGEX-6 |

---

## P2 — First Month
Optimization, cleanup, and nice-to-haves.

| # | Issue | Impact | Files | Effort | Source |
|---|-------|--------|-------|--------|--------|
| 29 | Migrate 44 rules to AI-primary detection | Regex can't detect paraphrased/novel risk language | rules_library.py | 40h | REGEX-2 |
| 30 | Configure Redis for result caching | 20-40% AI cost savings on re-scans | cache_service.py | 2h | PERF-2 |
| 31 | Pre-filter playbook rules by contract type | 50-70% prompt token savings | gemini_analyzer.py | 8h | PERF-1 |
| 32 | Clause type taxonomy gap (30 vs 78) | Classifier can't categorize SaaS/compliance/assignment | clause_classifier.py | 8h | REGEX-3 |
| 33 | Cross-reference map only covers 9/78 rules | Most rules get baseline corroboration score | confidence_scorer.py:317 | 8h | REGEX-8 |
| 34 | Raw JSON inputs for conditions/dependencies | Non-technical lawyers can't use condition builder | PlaybookEditor.tsx | 16h | PLAYBOOK-5 |
| 35 | No retry logic for API 429/5xx errors | Transient failures shown to user immediately | api.ts (both), gemini_analyzer.py | 4h | ADDIN-8 |
| 36 | Fork doesn't copy conditions/dependencies | Forked playbooks lose conditional logic | playbooks.py:397-424 | 4h | PLAYBOOK-2 |
| 37 | No negotiation decision export | Lawyers have no takeaway artifact | taskpane.ts | 8h | ADDIN-5 |
| 38 | No dependency scanning (pip-audit/SBOM) | OWASP A03 Software Supply Chain gap | CI/CD pipeline | 4h | SEC-7 |
| 39 | 6 dashboard mutations silently fail | Rollback, tier save, condition create — no error display | PlaybookEditor.tsx | 4h | DASH-2 |
| 40 | Render free tier cold start 15-30s | First request after inactivity times out | Infrastructure | 1h ($7/mo) | PERF-5 |
| 41 | Override priority bug — last wins not first | Lower-priority condition overrides overwrite higher-priority | playbook_conditions_engine.py | 2h | PLAYBOOK-3 |
| 42 | SQL injection risk in template creation | `str(dict).replace("'", '"')` for JSONB serialization | playbook_templates.py:907 | 1h | PLAYBOOK-6 |
| 43 | 4 accidentally public API routes | /billing/plans, /manifest, /installer, /templates/browse | Multiple endpoints | 2h | SEC-4 |
| 44 | MFA brute-force (50 attempts in 5 min) | No per-token attempt counter | auth.py:657-754 | 4h | SEC-3 |
| 45 | Screen reader support weak | No aria-live on risk list, dynamic buttons unlabeled | taskpane.html, taskpane.ts | 8h | ADDIN-6 |

---

## Total Effort Estimates

| Priority | Issues | Estimated Hours |
|----------|--------|-----------------|
| P0 | 9 | ~52h |
| P1 | 19 | ~53h |
| P2 | 17 | ~124h |
| **Total** | **45** | **~229h** |
