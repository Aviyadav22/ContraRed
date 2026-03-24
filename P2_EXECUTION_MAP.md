# P2 Execution Map — ContraRed

## Status: 17/17 Done — ALL SPRINTS COMPLETE

### Already Fixed (by parallel agents)
- ~~#35: API retry logic~~ ✅ (Agent 6 — exponential backoff in both API clients)
- ~~#39: Silent mutation errors~~ ✅ (Agent 5 — onError handlers on all 7 mutations)
- ~~#41: Override priority bug~~ ✅ (Agent 3 — modified_indices first-write-wins)
- ~~#42: SQL injection in templates~~ ✅ (Agent 3 — json.dumps replaces str().replace())

---

## Sprint Plan: 4 Sprints over 4 Weeks

### Sprint 1: Cost & Performance (Week 1) — 18h
*Focus: Reduce AI costs and improve response times. Immediate ROI.*

| # | Task | Effort | Impact | Dependencies |
|---|------|--------|--------|-------------|
| 30 | **Configure Redis (Upstash)** | 2h | 20-40% AI cost savings | None |
| | - Sign up Upstash free tier ($0/month) | | | |
| | - Add REDIS_URL to Render env vars | | | |
| | - Verify CacheService connects and caches analysis results | | | |
| | - Test: scan same document twice → second is instant | | | |
| 31 | **Pre-filter playbook rules by contract type** | 8h | 50-70% token savings | None |
| | - Add contract type detection in Stage 1 (NDA/SaaS/employment/MSA/M&A) | | | |
| | - Map each rule to applicable contract types | | | |
| | - Filter rules in `render_user_prompt()` before injection | | | |
| | - Fallback: send all rules if type uncertain | | | |
| 40 | **Upgrade Render to paid tier** | 1h ($7/mo) | No cold starts | None |
| | - Switch from free to Starter plan on Render dashboard | | | |
| | - Verify always-on behavior (no spin-down) | | | |
| 38 | **Add dependency scanning to CI** | 4h | OWASP A03 compliance | None |
| | - Add `pip-audit` to requirements.txt | | | |
| | - Add CI step: `pip-audit --requirement requirements.txt` | | | |
| | - Add `npm audit` for dashboard and add-in | | | |
| | - Generate SBOM with `pip-audit --format json > sbom.json` | | | |
| | - Document in README: how to run security scans | | | |
| | - Add to .github/workflows/ci.yml | | | |

**Sprint 1 deliverables:** Redis caching live, 50-70% prompt token savings, no cold starts, CI security scanning.

---

### Sprint 2: Playbook Intelligence (Week 2) — 28h
*Focus: Smarter playbook system. Directly improves analysis quality.*

| # | Task | Effort | Impact | Dependencies |
|---|------|--------|--------|-------------|
| 32 | **Expand clause classifier taxonomy** | 8h | Classifier covers all rule types | None |
| | - Add missing types: sla_terms, data_portability, security_standards, api_rights, acceptable_use (SaaS) | | | |
| | - Add: anti_bribery, sanctions, regulatory_compliance (Compliance) | | | |
| | - Add: assignment, change_of_control, subcontracting (Operational) | | | |
| | - Add heading + body patterns for each new type | | | |
| | - Update weight multipliers | | | |
| | - Test: classifier now covers all 78 rules_library types | | | |
| 33 | **Expand cross-reference corroboration map** | 8h | Better confidence scoring | #32 |
| | - Analyze all 78 rules for logical pairs | | | |
| | - Add corroboration pairs (bidirectional): | | | |
| |   - data_protection ↔ breach_notification | | | |
| |   - sla_terms ↔ sla_credits | | | |
| |   - termination_for_convenience ↔ transition_assistance | | | |
| |   - ip_assignment ↔ ip_ownership | | | |
| |   - auto_renewal ↔ termination_for_convenience | | | |
| |   - ... (target: 30+ pairs) | | | |
| | - Make map bidirectional (A corroborates B AND B corroborates A) | | | |
| | - Use rule IDs instead of names for matching | | | |
| 36 | **Fork copies conditions + dependencies** | 4h | Forked playbooks are complete | None |
| | - In `fork_playbook()` (playbooks.py:397-424), after copying rules+tiers: | | | |
| | - Copy PlaybookConditions with new UUIDs | | | |
| | - Copy PlaybookRuleOverrides (re-mapping rule_id to new rule UUIDs) | | | |
| | - Copy PlaybookRuleDependencies (re-mapping source/target rule_ids) | | | |
| | - Test: fork a playbook with conditions → verify all copied | | | |
| 43 | **Add auth to 4 accidentally public routes** | 2h | No unauthenticated access | None |
| | - `/billing/plans`: Add `Depends(get_current_user)` | | | |
| | - `/documents/manifest`: Add `Depends(get_current_user)` | | | |
| | - `/documents/installer`: Add `Depends(get_current_user)` | | | |
| | - `/playbooks/templates/browse`: Add `Depends(get_current_user)` | | | |
| 44 | **MFA per-token attempt limiting** | 4h | Prevent brute-force | None |
| | - Track failed MFA attempts per `mfa_challenge_token` JTI in Redis/memory | | | |
| | - After 5 failures: reject the token (force re-login) | | | |
| | - Return remaining attempts in error message | | | |
| | - Clear counter on successful verification | | | |

**Sprint 2 deliverables:** Classifier covers all 78 rule types, 30+ corroboration pairs, complete fork, auth on public routes, MFA hardened.

---

### Sprint 3: UX & Accessibility (Week 3) — 24h
*Focus: Lawyer-facing UX improvements. Trust and usability.*

| # | Task | Effort | Impact | Dependencies |
|---|------|--------|--------|-------------|
| 34 | **Structured condition/dependency editors** | 16h | Lawyers can configure playbooks | None |
| | - Replace raw JSON textarea for `condition_value` with structured form: | | | |
| |   - String fields: text input + operator dropdown (equals/contains/in) | | | |
| |   - Numeric fields: number input + operator (gt/lt/between) with min/max | | | |
| |   - Jurisdiction: searchable dropdown from jurisdiction_detector aliases | | | |
| | - Replace raw JSON textarea for `effect_params` with structured form: | | | |
| |   - Override risk level: dropdown (RED/YELLOW/GREEN) | | | |
| |   - Override position: textarea | | | |
| |   - Suppress rule: checkbox | | | |
| | - Add inline validation with error messages | | | |
| | - Preview panel: "When counterparty_type = fortune_500 AND deal_size > 1M" | | | |
| 45 | **Screen reader accessibility** | 8h | WCAG compliance | None |
| | - Add `aria-live="polite"` to `#riskList` container | | | |
| | - Add `tabindex="0"` + `role="article"` to risk cards | | | |
| | - Add `aria-label` to dynamic buttons (Generate Fix, Apply, Highlight, Research) | | | |
| | - Add `role="alert"` to notification toasts | | | |
| | - Add skip-to-content link at top of taskpane | | | |
| | - Improve color contrast on risk badges (test with WebAIM contrast checker): | | | |
| |   - Red badge: darken text to #B91C1C on #FEE2E2 (ratio 5.0+) | | | |
| |   - Yellow badge: darken text to #B45309 on #FEF3C7 (ratio 4.6+) | | | |
| |   - Green badge: darken text to #15803D on #DCFCE7 (ratio 4.5+) | | | |
| | - Test with Windows Narrator / NVDA | | | |

**Sprint 3 deliverables:** No-code condition builder, WCAG-compliant add-in.

---

### Sprint 4: AI Migration Foundation (Week 4) — 48h
*Focus: Begin the regex→AI transition. Largest effort item.*

| # | Task | Effort | Impact | Dependencies |
|---|------|--------|--------|-------------|
| 29 | **Migrate 44 rules to AI-primary (Phase 1)** | 40h | AI catches novel/paraphrased risks | Sprint 1 (#30 Redis) |
| | **Week 4a — Schema + first 15 rules (20h):** | | | |
| | - Add new columns to PlaybookRule model (all nullable): | | | |
| |   - `risk_description` (Text) | | | |
| |   - `acceptable_position` (Text) | | | |
| |   - `unacceptable_signals` (JSONB) | | | |
| |   - `acceptable_signals` (JSONB) | | | |
| |   - `clause_context` (Text) | | | |
| |   - `detection_mode` (String, default "ai_with_keywords") | | | |
| | - Create Alembic migration for new columns | | | |
| | - Update `from_playbook_rules()` to check `detection_mode`: | | | |
| |   - "ai_only": skip regex, pass risk_description to AI | | | |
| |   - "ai_with_keywords": regex pre-filter + AI evaluation | | | |
| |   - "keywords_only": current behavior (backward compat) | | | |
| | - Auto-generate `risk_description` from `primary_position` for first 15 rules: | | | |
| |   - unlimited_liability, unilateral_termination, broad_indemnification | | | |
| |   - ip_assignment, assignment_restriction, non_compete, exclusive_dealing | | | |
| |   - non_solicitation, payment_terms, late_payment, set_off_rights | | | |
| |   - force_majeure, change_of_control, data_protection, confidentiality_obligations | | | |
| | - Update prompt template to inject `risk_description` when available | | | |
| | - A/B test: compare regex-only vs AI-with-keywords for accuracy | | | |
| | **Week 4b — Remaining 29 rules + dashboard UX (20h):** | | | |
| | - Generate `risk_description` for remaining 29 REPLACE-WITH-AI rules | | | |
| | - Add `unacceptable_signals` and `acceptable_signals` for all 44 rules | | | |
| | - Update PlaybookEditor UX: | | | |
| |   - Add "Risk Description" textarea (replaces pattern chips as primary) | | | |
| |   - Add "Detection Mode" toggle: AI Only / AI+Keywords / Keywords Only | | | |
| |   - Keep pattern chips visible when mode is "AI+Keywords" or "Keywords Only" | | | |
| | - Update 5 playbook templates with `risk_description` + `detection_mode` | | | |
| | - Measure: token usage before/after, accuracy before/after | | | |
| 37 | **Negotiation decision export** | 8h | Lawyers get takeaway document | None |
| | - Add "Export Decisions" button to negotiation panel | | | |
| | - Generate DOCX report with: | | | |
| |   - Contract name, date, elapsed time | | | |
| |   - Table: clause | risk level | decision (Accept/Counter/Escalate) | notes | | | |
| |   - Summary: X accepted, Y countered, Z escalated | | | |
| | - Use same python-docx approach as existing report export | | | |
| | - Download as "ContraRed_Negotiation_[date].docx" | | | |

**Sprint 4 deliverables:** 44 rules migrated to AI-primary detection, playbook UX with natural language, negotiation export.

---

## Execution Dependencies

```
Sprint 1 (parallel tasks — no dependencies):
  #30 Redis ──────────────────────────┐
  #31 Pre-filter rules                │
  #40 Render upgrade                  │
  #38 Dependency scanning             │
                                      ▼
Sprint 2 (mostly parallel):      Sprint 4 needs Redis
  #32 Taxonomy ──→ #33 Cross-refs
  #36 Fork copy
  #43 Auth routes
  #44 MFA limiting

Sprint 3 (parallel):
  #34 Condition UX
  #45 Accessibility

Sprint 4 (sequential within):
  #29a Schema + 15 rules ──→ #29b Remaining 29 + UX
  #37 Negotiation export (parallel)
```

## Success Metrics

| Sprint | Metric | Target |
|--------|--------|--------|
| 1 | AI cost per scan | -30% (Redis caching + rule pre-filtering) |
| 1 | Cold start time | 0s (Render paid tier) |
| 2 | Classifier coverage | 78/78 rule types (up from 30) |
| 2 | Corroboration pairs | 30+ (up from 9) |
| 3 | WCAG AA compliance | Pass for all risk card interactions |
| 4 | AI detection accuracy | >90% (vs 60-80% regex-only) |
| 4 | Rules with risk_description | 44/44 |

## Total Remaining Effort

| Sprint | Hours | Cost (at $50/hr) |
|--------|-------|-------------------|
| Sprint 1: Cost & Performance | 15h | $750 |
| Sprint 2: Playbook Intelligence | 26h | $1,300 |
| Sprint 3: UX & Accessibility | 24h | $1,200 |
| Sprint 4: AI Migration | 48h | $2,400 |
| **Total** | **113h** | **$5,650** |
