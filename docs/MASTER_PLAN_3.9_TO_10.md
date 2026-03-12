# ContraRed Master Plan: 3.9/10 to 10/10
## Compiled from 10-Agent Opus Deep Analysis

**Generated**: 2026-03-11
**Methodology**: 10 specialized Opus agents independently analyzed the codebase and produced dimension-specific plans. This document synthesizes all 10 into a unified, phased roadmap.

---

## EXECUTIVE SUMMARY

ContraRed scores 3.9/10 today -- a strong technical foundation but a prototype, not a product lawyers would trust with real deals. This plan addresses **all 15 critical issues** and **97 specific features** across 10 dimensions to reach 10/10.

**The 5 existential blockers** (fix these or nothing else matters):
1. Privileged text sent to Gemini with no DPA (waives attorney-client privilege)
2. No SSO/SAML (every law firm requires it)
3. No MFA (cybersecurity insurance requires it)
4. Free-tier quota bypass bug (unlimited free scans)
5. Enterprise tier gets fewer scans than Pro (tier inversion)

**The 3 strategic bets**:
1. Own India first (Indian law + DPDP Act specialization before Harvey/CoCounsel localize)
2. Double down on Word Add-in (the distribution advantage -- "Grammarly for contracts")
3. Build the playbook flywheel (switching costs = moat)

---

## 10 PHASES OVERVIEW

| Phase | Dimension | Current | Target | Effort | Priority |
|-------|-----------|:-------:|:------:|--------|----------|
| 1 | Security for Legal | 3/10 | 10/10 | ~45 days | P0 CRITICAL |
| 2 | Architecture for Legal | 3.7/10 | 10/10 | ~40 days | P0 CRITICAL |
| 3 | Billing Model | 3/10 | 10/10 | ~45 days | P0 CRITICAL |
| 4 | AI Output Quality | 4.5/10 | 10/10 | ~50 days | P0 HIGH |
| 5 | Contract Coverage | 4/10 | 10/10 | ~75 days | P0 HIGH |
| 6 | Playbook System | 4/10 | 10/10 | ~60 days | P1 HIGH |
| 7 | Output Format | 5/10 | 10/10 | ~35 days | P1 HIGH |
| 8 | Lawyer UX Flow | 5/10 | 10/10 | ~30 days | P1 MEDIUM |
| 9 | Analytics Value | 3/10 | 10/10 | ~40 days | P2 MEDIUM |
| 10 | Competitive Position | 4/10 | 10/10 | ~50 days | P2 STRATEGIC |

**Total estimated effort**: ~470 developer-days (cross-phase parallelism reduces calendar time significantly)

---

## PHASE 1: SECURITY FOR LEGAL (3/10 → 10/10)
*"Without this, no law firm procurement team will sign off"*

### The Existential Issue: Attorney-Client Privilege
Contract text (potentially privileged) is sent to Google's consumer Gemini API via `google.generativeai` (line 234, `gemini_analyzer.py`). Consumer API terms allow Google to use data for model training = third-party disclosure = potential privilege waiver.

### Implementation Stages

**Stage 1.1: Stop the Bleeding (Weeks 1-4) → Score 3→6**
| Item | Description | Complexity | Files |
|------|-------------|-----------|-------|
| Vertex AI migration | Replace `google.generativeai` with `google-cloud-aiplatform` + executed DPA | XL | `gemini_analyzer.py`, `ai_service.py`, `config.py` |
| Leakage vector fixes | Redis: stop caching contract content; Logs: add `SensitiveDataFilter`; Audit: enforce `details` validation; Errors: global exception handler strips PII | M | `cache_service.py`, `main.py`, `audit_log.py` |
| Token revocation | Redis-backed token blacklist for forced logout | S | `security.py`, new `token_service.py` |

**Stage 1.2: Enterprise Readiness (Weeks 4-8) → Score 6→8**
| Item | Description | Complexity | Files |
|------|-------------|-----------|-------|
| SSO/SAML | Integrate WorkOS for SAML/OIDC brokering (Azure AD, Okta, Google Workspace). Fields `sso_enabled` + `entra_tenant_id` already exist in `organization.py` but are unused | L | new `sso.py`, `auth.py`, `organization.py` |
| MFA (TOTP) | `pyotp` for TOTP, encrypted secret storage, backup codes, org-level enforcement | M | new `mfa_service.py`, `auth.py`, `user.py` |
| RBAC overhaul | Expand from 3-tier to 5-tier (Viewer/Reviewer/Manager/Admin/SuperAdmin) with 20+ granular permissions | M | `dependencies.py`, new `permissions.py` |

**Stage 1.3: Hardening (Weeks 8-12) → Score 8→9**
| Item | Description | Complexity |
|------|-------------|-----------|
| Field-level AES-256 encryption | Fernet encryption for stored clause text (when ZDR is off) | M |
| Session management | Token rotation, concurrent session limits, IP-based anomaly detection | M |
| CI security scanning | Bandit, safety, trivy in GitHub Actions | S |
| CSP headers | Content Security Policy, HSTS, X-Frame-Options on all responses | S |

**Stage 1.4: Compliance (Months 3-9) → Score 9→10**
| Item | Description | Cost |
|------|-------------|------|
| SOC 2 Type II | Via Vanta/Drata automation (~₹8L/year) + audit (~₹8-15L) | ₹16-23L |
| Penetration testing | Annual pentest by certified firm | ₹5-15L/year |
| DPDP Act 2023 compliance | Data fiduciary obligations, DPA addendum, breach notification (72h) | Internal |
| Privacy policy + DPA template | Legal documents for customer contracts | ₹1-2L |

---

## PHASE 2: ARCHITECTURE FOR LEGAL (3.7/10 → 10/10)
*"What a 50-lawyer firm's IT team would require in due diligence"*

### 2.1 Document Versioning & Revision Chains
**Complexity: L** | Current: Flat `documents` table with no versioning

```sql
-- Key schema additions
ALTER TABLE documents ADD COLUMN parent_document_id UUID REFERENCES documents(id);
ALTER TABLE documents ADD COLUMN root_document_id UUID REFERENCES documents(id);
ALTER TABLE documents ADD COLUMN version_number INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64); -- SHA-256 for dedup
ALTER TABLE documents ADD COLUMN organization_id UUID REFERENCES organizations(id);
```

New tables: `document_versions` (immutable snapshots), `document_comparisons` (cached diffs)
API: `POST /documents/{id}/versions`, `GET /documents/{id}/diff?a=2&b=3`

### 2.2 Multi-Tenancy with PostgreSQL Row-Level Security
**Complexity: L** | Current: App-level `if` statements only

Three-layer isolation:
1. **PostgreSQL RLS**: `CREATE POLICY tenant_isolation ON documents USING (organization_id = current_setting('app.current_org_id')::uuid)`
2. **Middleware**: `TenantContextMiddleware` sets PG session variables from JWT
3. **Query-level**: SQLAlchemy mixin auto-adds `WHERE organization_id = :org_id`

### 2.3 Async Processing with ARQ Workers
**Complexity: L** | Current: Synchronous analysis blocks the request handler (10-30s)

- ARQ (async Redis queue) for background contract analysis
- API returns `202 Accepted` with `job_id`, frontend polls for results
- Render config: web (2-5 instances) + worker (1-3 instances)

### 2.4 Immutable Audit Trail
**Complexity: M** | Current: Mutable logs, exception-swallowing, no integrity proof

- Hash-chained audit entries (SHA-256 chain, `GENESIS` → entry₁ → entry₂ → ...)
- PostgreSQL trigger prevents UPDATE/DELETE on `audit_logs`
- Verification endpoint: `GET /audit-logs/verify` checks chain integrity

### 2.5 Infrastructure
- Deep health checks (`/health/deep` testing DB, Redis, AI provider)
- Sentry integration with PII-stripping `before_send` hook
- Disaster recovery: Supabase PITR (RPO 0, RTO <5min)
- 7 sequential migrations with zero-downtime protocol

---

## PHASE 3: BILLING MODEL (3/10 → 10/10)
*"Fix the two bugs first -- they're revenue-threatening"*

### 3.1 Critical Fixes (Day 1)
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| **Tier inversion** | `config.py:85-87`: Pro=-1 (unlimited), Enterprise=500 | Pro=200, Enterprise=-1 |
| **Free quota bypass** | `billing.py:315-341`: Solo users without org get `used=0` every time | Track per-user via `UsageLog` when no subscription exists |

### 3.2 Tier Redesign
| Tier | Monthly (INR) | Monthly (USD) | Scans | Seats |
|------|:---:|:---:|:---:|:---:|
| Free | ₹0 | $0 | 5 | 1 |
| Starter | ₹2,499 | $29 | 50 | 1 |
| Pro | ₹6,999 | $79 | 200 | 5 |
| Business | ₹14,999 | $149 | 1,000 | 20 |
| Enterprise | Custom | Custom | Unlimited | Unlimited |

### 3.3 Dual Payment Gateway
- **Razorpay** for INR (existing, enhanced)
- **Stripe** for USD/EUR/GBP (new)
- Unified `BillingEngine` with adapter pattern
- GST 18% auto-calculated for Indian customers

### 3.4 Additional Features
- Usage-based overage billing (soft cap for paid tiers)
- Pay-per-scan credits (₹149/scan for no-subscription users)
- Seat-based pricing with bulk discounts (10% for 6-15, 15% for 16-30, 20% for 31-50)
- 14-day free trial on Pro with card on file
- Dunning management (4-retry schedule over 21 days)
- Invoice generation with GST breakdown + PDF download
- Revenue analytics dashboard (MRR, ARR, churn, LTV)

### Schema
New tables: `plans`, `invoices`, `overage_records`, `scan_credits`, `enterprise_contracts`
New models: `Plan`, `Invoice`, `OverageRecord`, `ScanCredit`, `EnterpriseContract`

---

## PHASE 4: AI OUTPUT QUALITY (4.5/10 → 10/10)
*"The difference between a prototype and a product lawyers trust"*

### 4.1 Multi-Stage Analysis Pipeline
Replace single-shot Gemini call with 5-stage pipeline:

```
Stage 1: EXTRACTION → ContractMap + DefinedTerms + JurisdictionHint
         (deterministic, no AI cost)

Stage 2: CLASSIFICATION → ClauseInventory (what exists, what's missing)
         (Gemini Flash-Lite, cheap + fast)

Stage 3: RISK ASSESSMENT → RawRedlines with confidence scores
         (Gemini Pro, high quality)

Stage 4: VERIFICATION → VerifiedRedlines (hallucinations killed)
         (deterministic fuzzy matching, no AI cost)

Stage 5: ENRICHMENT → FinalRedlines with cross-references
         (Gemini Flash-Lite per-redline)
```

### 4.2 Hallucination Guard (P0)
New `hallucination_guard.py`: Post-generation verification of `original_text` against source document.
- Exact match → pass
- Normalized match (case/whitespace) → pass with 0.99 confidence
- Fuzzy match (≥0.80 Levenshtein) → correct the quote, pass with reduced confidence
- No match (<0.70) → **REJECT entirely** (log as hallucination)
- For DEAL-BREAKER rules that fail: re-query AI with explicit "copy verbatim" instruction

### 4.3 Jurisdiction System
New `jurisdiction_detector.py`: Auto-detect governing law from contract text via regex patterns.
- 10+ jurisdiction profiles (India, Delaware, New York, California, England, Singapore, UAE-DIFC, etc.)
- Dynamic prompt injection: replaces hardcoded "Indian commercial law" with detected jurisdiction
- User override via API: `jurisdiction` field on `AnalyzeRequest`
- Each profile includes: key statutes, indemnification standard, non-compete enforceability, arbitration framework

### 4.4 Confidence Scoring
Every redline gets a `ConfidenceScore` (HIGH/MEDIUM/LOW) based on 5 weighted factors:
- Text verification (30%) — did the quote match?
- Rule corroboration (25%) — did both regex AND AI agree?
- Playbook alignment (20%) — how specific was the playbook rule?
- Model confidence (15%) — AI's self-reported certainty
- Cross-references (10%) — do other clauses corroborate?

**Impact on UX**: HIGH = auto-show, MEDIUM = show with verification badge, LOW = collapsed by default

### 4.5 Defined Terms Resolution
New `defined_terms_resolver.py`: Extract definitions from contract, inject into AI prompt.
- Regex extraction of `"Term" means ...` patterns
- Recursive resolution (nested definitions)
- Overbroad definition flagging ("Confidential Information" = "all information" is itself a risk)

### 4.6 Prompt Engineering 2.0
Complete rewrite of `CONTRARED_SYSTEM_PROMPT`:
- Structured 4-step reasoning: ORIENT → TERMS CHECK → RULE-BY-RULE → CROSS-CLAUSE
- Explicit risk level criteria (RED = unlimited exposure / deal-breaker; YELLOW = negotiable; GREEN = skip)
- Mandatory `confidence` field per redline
- `original_text` must be VERBATIM copy-paste (not paraphrased)
- 2-3 worked few-shot examples with reasoning chains

### 4.7 Rule Engine 2.0
Replace flat regex with `SmartRule` dataclass:
- `trigger_patterns` + `negative_patterns` (match X, but NOT if Y in same clause)
- `context_window` (500 chars around match for negative pattern checking)
- `escalation_conditions` / `de_escalation_conditions`
- Per-rule `ai_verification_prompt` for ambiguous cases

**Indemnification fix**: Change base risk from RED→YELLOW. Only escalate to RED if one-sided AND (uncapped OR covers all losses). "Indemnify and hold harmless" alone is no longer flagged.

### New Files
`analysis_pipeline.py`, `hallucination_guard.py`, `jurisdiction_detector.py`, `defined_terms_resolver.py`, `clause_classifier.py`, `confidence_scorer.py`

---

## PHASE 5: CONTRACT COVERAGE (4/10 → 10/10)
*"13 rules covers ~15-20% of what a lawyer flags. Target: 90%+"*

### 5.1 Clause Taxonomy: 75 Categories (up from 13)
Organized by section:
- **Formation & Structure** (5): definitions, recitals, entire agreement, amendments, severability
- **Term & Termination** (7): duration, auto-renewal, termination for cause/convenience, cure period, survival, transition
- **Financial** (8): payment terms, late payment, price escalation, taxes, set-off, audit rights, MFN, currency
- **Liability & Indemnification** (8): liability cap, unlimited liability, consequential damages, indemnification scope/procedure, third-party claims, limitation period, insurance
- **IP** (7): ownership, assignment, license grant, background IP, IP indemnification, open source, moral rights
- **Confidentiality & Data** (8): obligations, exceptions, duration, return of materials, data protection (DPDP/GDPR), DPA, breach notification, cross-border transfer
- **Reps & Warranties** (6): general, AS-IS disclaimer, service level, authority, non-infringement, compliance
- **Restrictive Covenants** (5): non-compete, non-solicitation (employees/customers), exclusivity, reverse engineering
- **Governance & Disputes** (6): governing law, jurisdiction, arbitration, mediation, injunctive relief, jury waiver
- **Operational** (9): force majeure, assignment/change of control, subcontracting, notices, anti-bribery, sanctions, compliance, audit, business continuity
- **SaaS/Technology** (6): SLA, SLA credits, data portability, security standards, acceptable use, API rights

### 5.2 Three-Layer Detection System
```
Layer 1: Enhanced Regex (75 rules, presence + risk + safe patterns) → $0 cost
Layer 2: Deterministic Scope Analysis (breadth, mutuality, caps, duration) → $0 cost
Layer 3: AI Verification (only for ambiguous cases, ~30% of matches) → ~$0.001/clause
```

### 5.3 Scope Analyzer (`scope_analyzer.py`)
For each detected clause, analyze:
- **Breadth**: narrow / standard / broad / unlimited
- **Mutuality**: mutual / one-sided favorable / one-sided unfavorable
- **Financial exposure**: capped (amount) / uncapped
- **Duration**: fixed term / perpetual
- **Triggers**: material breach / any breach / negligence / gross negligence
- Composite `scope_score` (1-10) drives risk level

### 5.4 Jurisdiction Framework
Jurisdiction-specific rule overrides for India, US (CA, DE, NY), UK, Singapore:
- **India**: S.27 (non-compete void in employment), S.73/74 (liquidated damages limits), DPDP Act, FEMA, stamp duty
- **US-CA**: Non-compete unenforceable (BPC §16600)
- **UK**: Penalty doctrine (Cavendish v Makdessi)

### 5.5 Pre-Built Playbook Templates (5 Templates)
| Template | Rules | Focus |
|----------|:-----:|-------|
| NDA - Indian Law | 22 | Confidential info scope, S.27 non-compete, survival |
| SaaS Agreement | 35 | SLA, data ownership, liability caps, portability |
| Employment - India | 28 | S.27, POSH Act, PF/ESIC, non-solicitation |
| MSA / Services | 30 | SLA, change orders, subcontracting, insurance |
| M&A / SPA | 25 | MAC, reps & warranties, FEMA, CCI, earnouts |

### 5.6 Continuous Learning
New `rule_feedback` table: lawyers mark false positives/negatives per rule.
- Auto-flag rules with >30% FP rate for review
- Aggregate false negatives into suggested new rules
- Org-level learning (adjust priorities based on firm's feedback patterns)

---

## PHASE 6: PLAYBOOK SYSTEM (4/10 → 10/10)
*"A flat list of regex rules → a lawyer-grade negotiation platform"*

### 6.1 Negotiation Tier System
Replace binary primary/fallback positions with 4-tier ladder:

| Tier | Name | Purpose | Example (Liability Cap) |
|------|------|---------|------------------------|
| 1 | **Ideal** | Opening position | "Capped at 6 months fees" |
| 2 | **Acceptable** | Reasonable compromise | "Capped at 12 months fees" |
| 3 | **Walk-Away** | Absolute minimum | "Capped at total contract value" |
| 4 | **Escalate** | Instructions if walk-away rejected | "Escalate to GC. Do not sign." |

New table: `playbook_rule_tiers` (rule_id, tier_level, position_text, guidance_notes, risk_level_at_tier)
Migration: existing `primary_position` → tier 1, `fallback_position` → tier 3

### 6.2 Conditional Logic Engine
Rules adapt based on deal context:
- **Counterparty type**: Fortune 500 vs startup vs government
- **Deal size**: <$50K (low touch) vs $50K-$500K vs >$500K (high scrutiny)
- **Jurisdiction**: India vs US vs EU
- **Contract side**: vendor or customer

New tables: `playbook_conditions`, `playbook_rule_overrides`
Word Add-in: "Deal Context" panel before scanning (counterparty, deal size, jurisdiction, side)

### 6.3 Cross-Clause Dependencies
Rules interact: uncapped liability → escalate indemnification risk; no data portability → escalate termination risk.
New table: `playbook_rule_dependencies` (source_rule, target_rule, trigger_condition, effect)
Post-processing `DependencyResolver` runs after rule engine, cascades risk adjustments.

### 6.4 Playbook Templates, Marketplace, Versioning, Analytics
- **Template Gallery**: Browse pre-built playbooks, fork to org with one click
- **Marketplace**: Community playbooks with ratings, reviews, "Verified by ContraRed" badges
- **Version Control**: Full snapshots on every mutation, diff viewer, rollback
- **Analytics**: Rule trigger rates, fix acceptance rates, tier progression, false positive tracking

### 6.5 Dashboard Redesign
Tabbed editor: **Rules** | **Conditions** | **Dependencies** | **History** | **Analytics**
Each rule expands to show tier accordion (Ideal/Acceptable/Walk-Away/Escalate)

---

## PHASE 7: OUTPUT FORMAT (5/10 → 10/10)
*"OOXML redlines aren't real tracked changes -- the #1 credibility issue"*

### 7.1 Real Tracked Changes (P0)
**Root cause**: `redline_implementer.py` creates OOXML `<w:del>`/`<w:ins>` in an inserted package. Word treats them as decorative formatting, not revision marks. Review pane ignores them.

**Fix**: Toggle `document.changeTrackingMode = Word.ChangeTrackingMode.trackAll` before applying changes via `range.insertText()`. Word records real revisions. Requires bumping manifest to **WordApi 1.4** (supported in Word 2019+).

### 7.2 Excel/CSV Issues List Export (P0)
New `issues_exporter.py` using `openpyxl`:
- Columns: Issue #, Section Ref, Clause Type, Risk Level, Status, Description, Original Text, Recommended Action, Firm Position (blank), Client Response (blank), Resolution Notes (blank)
- Auto-filters, freeze panes, color-coded risk levels, Summary sheet

### 7.3 Additional Outputs
| Output | Complexity | Description |
|--------|-----------|-------------|
| PDF reports | L | `weasyprint` or `fpdf2`, branded templates with page numbers |
| Comment system | L | WordApi 1.4 `Range.insertComment()`, "Comment All" bulk action |
| Summary memo | M | AI-generated executive memo (RE:, Summary, Key Risks, Actions, Overall Rating) |
| Comparison view | M | Client-side word-level diff using `diff` npm package |
| Output customization | M | Per-org report templates (logo, colors, columns, header/footer) |

---

## PHASE 8: LAWYER UX FLOW (5/10 → 10/10)
*"Can the lawyer use this without losing their train of thought during a call?"*

### 8.1 Scan Selection (P0, Small)
Highlight text in Word → click "Scan Selection" (or Ctrl+Shift+S) → 3-5 second analysis of just that clause.
Uses `context.document.getSelection()`. No backend changes needed.

### 8.2 Keyboard Shortcuts (P0, Small)
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+S | Scan selection |
| Ctrl+Shift+D | Scan full document |
| Ctrl+Shift+N | Toggle negotiation mode |
| Alt+Up/Down | Navigate risk cards |
| Alt+H/G/A/R | Highlight / Generate fix / Apply / Research |

### 8.3 Quick Re-Scan (Medium)
After applying a fix, re-analyze just that clause. New endpoint `POST /documents/analyze-clause` returns single risk assessment in <3 seconds. Card updates in-place (may change RED→GREEN).

### 8.4 Live Negotiation Mode (Large — THE moat feature)
Ctrl+Shift+N activates compact view for live calls:
- Pinned quick-scan bar, auto-scan on text selection (1.5s debounce)
- Accept / Counter / Escalate action buttons on each risk card
- Session timer + notes field (localStorage)
- Negotiation decisions export with report

### 8.5 Quality of Life
- Real-time progress via SSE (parsing → playbook → analyzing → risks → complete)
- Persistent scan state (localStorage, survives taskpane close/reopen)
- Clause diff view (word-level diff with `diff-match-patch`)
- Smart tooltips for first-time users

### 8.6 Batch Processing (XL — Dashboard-based)
Dashboard multi-file upload → `POST /documents/batch-analyze` → concurrent processing (3 parallel) → aggregate results with cross-document risk patterns.

---

## PHASE 9: ANALYTICS VALUE (3/10 → 10/10)
*"Measures activity, not legal outcomes → Board-ready ROI metrics"*

### 9.1 Kill the Hardcoded "2 Hours Saved"
`Analytics.tsx:108` literally does `documents_analyzed * 2`. Replace with:
- Actual `processing_duration_ms` (measured)
- Estimated manual time: `(word_count / 250 pages) × (60 / pages_per_hour) + (risk_count × per_risk_minutes)`
- Configurable benchmarks per org (default: 5 pages/hour, 15 min/risk)
- Methodology always shown so numbers are defensible

### 9.2 New Analytics Capabilities
| Capability | What It Answers |
|------------|----------------|
| Clause analytics | "Which clause types cause the most risk?" |
| Portfolio risk dashboard | "Across 340 contracts, where is our aggregate exposure?" |
| Team performance | "Who reviews fastest? Who finds the most risks?" |
| Trend analysis | "Is our risk posture improving quarter-over-quarter?" |
| Internal benchmarking | "Is this NDA riskier than 78% of our historical NDAs?" |
| ROI calculator | "12.4x return: $847K time saved + $2.1M risk value protected" |
| Executive dashboard | Board-ready: 6 key metrics on one screen, large-font, no clutter |
| Custom reports | 4 templates: Executive Summary, GC Operations, Team Review, Risk Audit |
| BI export | Structured JSON/CSV per dataset, Power BI / Tableau ready |

### Schema Additions
New columns on `documents`: `word_count`, `page_count`, `processing_duration_ms`, `contract_type`, `risk_score`, `counterparty`, `contract_value`, `expiry_date`
New tables: `review_sessions`, `time_benchmarks`, `roi_config`, `benchmark_profiles`, `generated_reports`

---

## PHASE 10: COMPETITIVE POSITION (4/10 → 10/10)
*"Sharp wedge (Indian law + Word), no moat yet → Category leader in India"*

### 10.1 Microsoft AppSource (P0)
The #1 distribution action. Requires: Partner Center account ($19), privacy policy, support page, screenshots.
Current manifest is well-structured. Plan for 1-2 certification rounds over ~3 weeks.

### 10.2 India Market Strategy
- **Positioning**: "The only AI contract reviewer built for Indian law, inside Microsoft Word"
- **Pricing**: India-optimized tiers (₹1,999-₹14,999/mo) undercutting SpotDraft ($99+)
- **First 10 customers**: LinkedIn outreach to 50 managing partners/GCs, content on Bar & Bench / LiveLaw, NLU partnerships
- **Indian law specialization**: DPDP Act, Indian Contract Act, FEMA, Arbitration Act -- no competitor has this depth

### 10.3 Integration Ecosystem (XL)
Priority integrations:
- **e-Signature**: DocuSign, Leegality (India)
- **CLM/DMS**: SpotDraft, iManage, NetDocuments
- **Communication**: Slack, Teams notifications
New tables: `integration_connections`, `api_keys`

### 10.4 Playbook Marketplace (Network Effect)
Public playbooks ("NDA Playbook for Indian SaaS", "DPDP-compliant DPA template") attract new users.
Each shared playbook = content marketing + switching cost builder.

### 10.5 Content Engine
- Weekly LinkedIn posts on Indian contract law insights
- Bi-weekly blog posts using the 10 default playbooks (106 rules) as content source
- Conference presence: NASSCOM Legal Tech, IBA India, NLSIU events

### 10.6 What 10/10 Looks Like (Q1 2027)
- AppSource Top 10 in Legal category
- 100+ paying customers
- ₹10L+ MRR
- SOC 2 Type 1 certified
- 6+ integrations
- 100+ marketplace playbooks
- Recognized as default AI contract review tool in India

---

## CROSS-CUTTING DEPENDENCIES

```
Phase 1 (Security) ──┐
                      ├──→ Phase 2 (Architecture) ──→ Phase 3 (Billing)
Phase 4 (AI Quality) ┘         │
                               ├──→ Phase 6 (Playbooks)
Phase 5 (Coverage) ────────────┘         │
                                         ├──→ Phase 7 (Output)
Phase 8 (UX) ───────────────────────────┘         │
                                                   ├──→ Phase 9 (Analytics)
                                                   └──→ Phase 10 (Competitive)
```

**Phases 1+4 can start in parallel** (Security + AI Quality are independent)
**Phases 5+8 can start in parallel** (Coverage + UX are independent)
**Phase 10 runs continuously** alongside all other phases (GTM doesn't wait for product)

---

## UNIFIED MIGRATION PLAN

All database changes consolidated into sequential migrations:

| Migration | Phase | Tables/Changes |
|-----------|-------|---------------|
| 009 | Architecture | Document versioning columns, `document_versions`, `document_comparisons` |
| 010 | Architecture | Row-Level Security policies on all tenant tables |
| 011 | Architecture | Backfill `organization_id` on documents |
| 012 | Architecture | Immutable audit trail with hash chain |
| 013 | Billing | `plans`, `invoices`, `overage_records`, `scan_credits`, `enterprise_contracts` |
| 014 | Playbook | `playbook_rule_tiers`, `playbook_conditions`, `playbook_rule_overrides`, `playbook_rule_dependencies`, `playbook_versions`, `playbook_marketplace_listings`, `playbook_ratings`, `playbook_analytics` |
| 015 | Analytics | `review_sessions`, `time_benchmarks`, `roi_config`, `benchmark_profiles`, `generated_reports` + document column additions |
| 016 | Coverage | `rule_feedback` table, rule priority/jurisdiction fields on `playbook_rules` |
| 017 | Output | `report_templates` table |
| 018 | Security | MFA fields on `users`, permission tables |
| 019 | Competitive | `integration_connections`, `api_keys` |

---

## NEW FILES SUMMARY

### Backend (New Services)
| File | Phase | Purpose |
|------|-------|---------|
| `services/analysis_pipeline.py` | 4 | 5-stage AI pipeline orchestrator |
| `services/hallucination_guard.py` | 4 | Post-generation verification |
| `services/jurisdiction_detector.py` | 4,5 | Auto-detect governing law |
| `services/defined_terms_resolver.py` | 4,5 | Extract and resolve defined terms |
| `services/clause_classifier.py` | 4 | Clause inventory (Stage 2) |
| `services/confidence_scorer.py` | 4 | Multi-factor confidence scoring |
| `services/scope_analyzer.py` | 5 | Deterministic scope analysis |
| `services/playbook_templates.py` | 5,6 | Pre-built playbook templates |
| `services/billing/engine.py` | 3 | Unified billing orchestrator |
| `services/billing/stripe_adapter.py` | 3 | Stripe integration |
| `services/billing/razorpay_adapter.py` | 3 | Razorpay extraction |
| `services/billing/tax.py` | 3 | GST + global tax calculation |
| `services/billing/dunning.py` | 3 | Failed payment recovery |
| `services/issues_exporter.py` | 7 | Excel/CSV export |
| `services/pdf_report_generator.py` | 7 | PDF report generation |
| `services/mfa_service.py` | 1 | TOTP MFA |
| `services/token_service.py` | 1 | Redis-backed token revocation |
| `services/ai_data_protection.py` | 1 | PII redaction before AI calls |
| `services/roi_service.py` | 9 | ROI calculation |
| `services/benchmark_service.py` | 9 | Internal benchmarking |
| `core/encryption.py` | 1,2 | Field-level AES-256 |
| `core/permissions.py` | 1 | Granular RBAC |
| `middleware/tenant_context.py` | 2 | RLS session variables |
| `workers/tasks.py` | 2 | ARQ background tasks |

### Backend (New Endpoints)
| File | Phase | Routes |
|------|-------|--------|
| `endpoints/sso.py` | 1 | `/sso/authorize`, `/sso/callback` |
| `endpoints/feedback.py` | 5 | `/feedback/`, `/feedback/stats` |
| `endpoints/admin_billing.py` | 3 | `/analytics/mrr`, `/analytics/arr`, etc. |

### Dashboard (New Pages)
| File | Phase | Purpose |
|------|-------|---------|
| `pages/Executive.tsx` | 9 | Board-ready executive dashboard |
| `pages/Reports.tsx` | 9 | Custom report builder |
| `pages/AdminBilling.tsx` | 3 | Revenue analytics (super admin) |
| `pages/BatchUpload.tsx` | 8 | Multi-document batch processing |
| `components/analytics/*.tsx` | 9 | Clause, portfolio, team, ROI, trend charts |

---

## QUARTERLY EXECUTION TIMELINE

### Q1 (Months 1-3): Foundation
**Goal**: Fix blockers, become deployable to a real law firm

- [x] Phase 1 Stages 1.1-1.2 (Security: Vertex AI, leakage fixes, SSO, MFA)
- [x] Phase 2.1-2.2 (Architecture: versioning, multi-tenancy)
- [x] Phase 3.1-3.2 (Billing: fix bugs, tier redesign)
- [x] Phase 4.2 (AI: hallucination guard)
- [x] Phase 10.1 (Competitive: AppSource submission)

**Exit Score**: ~6.5/10

### Q2 (Months 4-6): Intelligence
**Goal**: AI quality that lawyers trust, comprehensive coverage

- [x] Phase 4 complete (AI pipeline, jurisdiction, confidence, prompts)
- [x] Phase 5 partial (40→60 rules, scope analyzer, Indian law overlay)
- [x] Phase 6.1-6.3 (Playbook: tiers, conditions, dependencies)
- [x] Phase 7.1-7.2 (Output: real tracked changes, Excel export)
- [x] Phase 8.1-8.3 (UX: scan selection, shortcuts, quick re-scan)
- [x] Phase 3.3 (Billing: Stripe integration)

**Exit Score**: ~8.0/10

### Q3 (Months 7-9): Scale
**Goal**: Enterprise-ready product with analytics and marketplace

- [x] Phase 5 complete (75 rules, 5 playbook templates, feedback loop)
- [x] Phase 6 complete (marketplace, versioning, analytics)
- [x] Phase 7 complete (PDF, comments, memo, customization)
- [x] Phase 8.4 (UX: live negotiation mode)
- [x] Phase 9 complete (analytics: ROI, portfolio, executive dashboard)
- [x] Phase 1.4 (Security: SOC 2 Type II)

**Exit Score**: ~9.5/10

### Q4 (Months 10-12): Dominate
**Goal**: Category leader in Indian legal tech

- [x] Phase 10 complete (integrations, partner channel, content engine)
- [x] Phase 8.6 (UX: batch processing)
- [x] Phase 9 extras (cross-org benchmarking, BI integrations)
- [x] All dimensions at 10/10

**Exit Score**: 10/10

---

## SUCCESS METRICS BY QUARTER

| Metric | Q1 | Q2 | Q3 | Q4 |
|--------|:---:|:---:|:---:|:---:|
| Overall Score | 6.5 | 8.0 | 9.5 | 10.0 |
| Paying Customers | 5 | 20 | 50 | 100+ |
| MRR (₹) | 50K | 2L | 5L | 10L+ |
| Clause Coverage | 40 | 60 | 75 | 75+ |
| Playbook Templates | 2 | 4 | 5 | 5+ community |
| AppSource Status | Submitted | Listed | Top 20 | Top 10 |
| Integrations | 0 | 2 | 4 | 6+ |
| SOC 2 | Started | In progress | Type II | Certified |
| Team Size Needed | 1-2 | 2-3 | 3-4 | 4-5 |

---

*This plan was generated by 10 specialized Opus agents analyzing the ContraRed codebase, each independently producing dimension-specific plans that were then synthesized into this unified roadmap.*
