# #29 AI-Primary Rule Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate 54 playbook rules from regex-only to AI-primary detection so Gemini catches novel/paraphrased risks.

**Architecture:** Add 6 columns to playbook_rules table. Branch format_playbook_rules() based on detection_mode. Generate risk_description content for 54 context-dependent rules across 10 playbooks. Add Detection Mode toggle + Risk Description field to PlaybookEditor.

**Tech Stack:** PostgreSQL (raw SQL migration), Python/SQLAlchemy, TypeScript/React (dashboard)

---

## Task 1: Database Migration (019)

**Files:**
- Create: `backend/migrations/019_ai_primary_detection.sql`

**Steps:**

1. Create migration file `backend/migrations/019_ai_primary_detection.sql`:

```sql
-- Migration 019: AI-primary detection columns for playbook rules
-- Part of P2 #29: Migrate 44 rules to AI-primary detection

ALTER TABLE playbook_rules
    ADD COLUMN IF NOT EXISTS detection_mode VARCHAR(30) DEFAULT 'keywords_only',
    ADD COLUMN IF NOT EXISTS risk_description TEXT,
    ADD COLUMN IF NOT EXISTS acceptable_position TEXT,
    ADD COLUMN IF NOT EXISTS unacceptable_signals JSONB,
    ADD COLUMN IF NOT EXISTS acceptable_signals JSONB,
    ADD COLUMN IF NOT EXISTS clause_context TEXT;

-- Index for filtering by detection mode
CREATE INDEX IF NOT EXISTS idx_playbook_rules_detection_mode
    ON playbook_rules(detection_mode);

-- Constraint: detection_mode must be one of three values
ALTER TABLE playbook_rules
    ADD CONSTRAINT chk_detection_mode
    CHECK (detection_mode IN ('ai_only', 'ai_with_keywords', 'keywords_only'));
```

2. Apply to local DB:
```bash
cd backend && psql "$DATABASE_URL" -f migrations/019_ai_primary_detection.sql
```

3. Commit: `feat(db): migration 019 — AI-primary detection columns`

---

## Task 2: Update PlaybookRule Model

**Files:**
- Modify: `backend/app/models/playbook.py` (lines 47-75, PlaybookRule class)

**Steps:**

1. Add 6 new columns after the existing `tags` field (around line 72):

```python
    # P2 #29: AI-primary detection
    detection_mode: Mapped[str] = mapped_column(String(30), default="keywords_only")
    risk_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acceptable_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unacceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    acceptable_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    clause_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

2. Commit: `feat(model): add AI-primary detection fields to PlaybookRule`

---

## Task 3: Update Playbook Cache

**Files:**
- Modify: `backend/app/services/playbook_cache.py` (lines 64-97, get_cached_rules_dicts)

**Steps:**

1. In `get_cached_rules_dicts()`, add the new fields to the dict being built for each rule. After the existing fields, add:

```python
        d["detection_mode"] = rule.detection_mode or "keywords_only"
        d["risk_description"] = rule.risk_description or ""
        d["acceptable_position"] = rule.acceptable_position or ""
        d["unacceptable_signals"] = rule.unacceptable_signals or []
        d["acceptable_signals"] = rule.acceptable_signals or []
        d["clause_context"] = rule.clause_context or ""
```

2. Clear cache on import by bumping the cache version or ensuring stale entries don't persist.

3. Commit: `feat(cache): include AI detection fields in playbook rule cache`

---

## Task 4: Update format_playbook_rules() in Gemini Analyzer

**Files:**
- Modify: `backend/app/services/gemini_analyzer.py` (lines 186-215, format_playbook_rules)

**Steps:**

1. Replace the `format_playbook_rules()` method to branch based on `detection_mode`:

```python
def format_playbook_rules(self, playbook_rules: List[Dict]) -> str:
    if not playbook_rules:
        return "No specific playbook rules provided. Apply standard commercial contract best practices."

    lines = [f"Total rules to check: {len(playbook_rules)}. Evaluate EACH rule against the contract.\n"]
    for i, rule in enumerate(playbook_rules, 1):
        name = rule.get('name', rule.get('rule_name', 'Unknown'))
        risk = rule.get('risk_level', 'YELLOW')
        position = rule.get('primary_position', rule.get('description', 'Standard terms expected'))
        fallback = rule.get('fallback_position', '')
        deal_breaker = rule.get('is_deal_breaker', False)
        verification = rule.get('verification_prompt', '')
        detection_mode = rule.get('detection_mode', 'keywords_only')
        risk_description = rule.get('risk_description', '')
        acceptable_pos = rule.get('acceptable_position', '')
        unacceptable = rule.get('unacceptable_signals', [])
        acceptable = rule.get('acceptable_signals', [])
        clause_context = rule.get('clause_context', '')

        line = f"Rule #{i}: {name} | Risk: {risk}"
        if deal_breaker:
            line += " | DEAL-BREAKER (must flag if violated)"

        # AI-primary rules: inject natural language description
        if detection_mode in ('ai_only', 'ai_with_keywords') and risk_description:
            line += f"\n  RISK TO DETECT: {risk_description}"
            if clause_context:
                line += f"\n  CONTEXT: {clause_context}"
            if unacceptable:
                line += f"\n  RED FLAGS: {', '.join(unacceptable)}"
            if acceptable:
                line += f"\n  SAFE SIGNALS: {', '.join(acceptable)}"
            if acceptable_pos:
                line += f"\n  ACCEPTABLE IF: {acceptable_pos}"

        # Position info (always included)
        line += f"\n  Position: {position}"
        if fallback:
            line += f"\n  Fallback: {fallback}"
        if verification:
            line += f"\n  Check: {verification}"

        lines.append(line)

    return "\n".join(lines)
```

2. Commit: `feat(ai): format_playbook_rules branches on detection_mode`

---

## Task 5: Update Rule Engine for detection_mode

**Files:**
- Modify: `backend/app/services/rule_engine.py` (find `from_playbook_rules` or where SmartRule/RulePattern objects are built)

**Steps:**

1. In `from_playbook_rules()`, when building SmartRule objects from PlaybookRule ORM objects, check `detection_mode`:
   - `"ai_only"`: skip regex pattern compilation entirely, set `patterns = []`
   - `"ai_with_keywords"`: compile patterns as normal (used for pre-filtering, AI does final decision)
   - `"keywords_only"`: current behavior unchanged

2. Store `detection_mode` on the SmartRule/RuleMatch so downstream code can use it.

3. Commit: `feat(rules): rule engine respects detection_mode`

---

## Task 6: Update API Endpoints (Playbook CRUD)

**Files:**
- Modify: `backend/app/api/v1/endpoints/playbooks.py` (rule create/update endpoints)

**Steps:**

1. In the rule creation endpoint, accept the new fields in the request body:
   - `detection_mode` (optional, default "keywords_only")
   - `risk_description` (optional)
   - `acceptable_position` (optional)
   - `unacceptable_signals` (optional, list of strings)
   - `acceptable_signals` (optional, list of strings)
   - `clause_context` (optional)

2. In the rule update endpoint, allow updating these fields.

3. In the rule GET response, include these fields.

4. Commit: `feat(api): playbook rule CRUD includes AI detection fields`

---

## Task 7: Generate Rule Content — 44 Rules

**Files:**
- Modify: `backend/scripts/playbooks/msa.py`
- Modify: `backend/scripts/playbooks/saas.py`
- Modify: `backend/scripts/playbooks/employment.py`
- Modify: `backend/scripts/playbooks/nda_mutual.py`
- Modify: `backend/scripts/playbooks/nda_unilateral.py`
- Modify: `backend/scripts/playbooks/consulting.py`
- Modify: `backend/scripts/playbooks/dpa.py`
- Modify: `backend/scripts/playbooks/vendor.py`
- Modify: `backend/scripts/playbooks/joint_venture.py`
- Modify: `backend/scripts/playbooks/lease.py`
- Modify: `backend/scripts/seed_default_playbooks.py` (to pass new fields)

**Steps:**

1. Update the `_r()` helper in each playbook file to accept new parameters:
```python
def _r(clause_type, primary, risk, patterns, fallback=None, deal_breaker=False,
       ai_verify=True, prompt=None, order=0,
       detection_mode="keywords_only", risk_description=None,
       acceptable_position=None, unacceptable_signals=None,
       acceptable_signals=None, clause_context=None):
```

And include in the returned dict:
```python
    d["detection_mode"] = detection_mode
    d["risk_description"] = risk_description
    d["acceptable_position"] = acceptable_position
    d["unacceptable_signals"] = unacceptable_signals or []
    d["acceptable_signals"] = acceptable_signals or []
    d["clause_context"] = clause_context
```

2. For each of the 44 context-dependent rules, add `detection_mode="ai_with_keywords"` plus `risk_description`, `unacceptable_signals`, `acceptable_signals`, and optionally `acceptable_position` and `clause_context`.

**Rules to migrate by playbook:**

### MSA (10 of 15 rules):
- `limitation_of_liability` — risk_description: "Liability cap is missing, unlimited, or disproportionately high relative to contract value"
- `indemnification` — "Indemnification is one-sided, uncapped, or covers consequential/indirect damages"
- `ip_ownership` — "IP ownership clause assigns all IP (including pre-existing) to one party"
- `termination_for_convenience` — "Termination for convenience lacks adequate notice period or has no cure period"
- `termination_for_cause` — "Termination for cause has no cure/remedy period before termination"
- `confidentiality` — "Confidentiality obligation is perpetual or unreasonably long (>5 years)"
- `auto_renewal` — "Auto-renewal has no opt-out window or unreasonably short notice period"
- `data_protection` — "Data protection clause is missing or doesn't reference applicable law"
- `payment_terms` — "Payment terms exceed 45 days or lack late payment penalties"
- `force_majeure` — "Force majeure clause is one-sided or excludes common events"

### SaaS (8 of 13):
- `data_ownership` — "Vendor claims ownership or broad rights over customer data"
- `sla_uptime` — "SLA is missing, below 99.5%, or has no remedies for breach"
- `data_security` — "Security standards are vague with no specific certifications required"
- `termination_data_portability` — "No data export/portability provision on termination"
- `price_escalation` — "Price increases are uncapped or exceed reasonable thresholds (>10% annual)"
- `limitation_of_liability` — same pattern as MSA
- `indemnification` — same pattern as MSA
- `ip_ownership` — "Customer data ownership is ambiguous or vendor claims derivative rights"

### Employment (7 of 12):
- `non_compete` — "Non-compete clause present in employment contract (unenforceable under S.27 Indian Contract Act)"
- `non_solicitation` — "Non-solicitation period exceeds 12 months or scope is unreasonably broad"
- `ip_assignment` — "IP assignment covers personal projects or work done outside employment"
- `probation_period` — "Probation period exceeds 6 months"
- `notice_period` — "Notice period exceeds 3 months for non-senior roles"
- `restrictive_covenants` — "Geographic or temporal scope of restrictive covenants is unreasonable"
- `confidentiality` — "Post-termination confidentiality obligation exceeds 2 years"

### NDA Mutual (4 of 7):
- `definition_of_confidential_information` — "Definition is overly broad ('any and all information') without reasonable carve-outs"
- `confidentiality_term` — "Confidentiality obligation is perpetual with no sunset"
- `non_solicitation` — "Non-solicitation clause included in NDA (overreach)"
- `permitted_disclosures` — "No exceptions for legal/regulatory/court-ordered disclosures"

### NDA Unilateral (3 of 9, additional to mutual):
- `reverse_engineering` — "Reverse engineering prohibition is overly broad beyond the disclosed information"
- `non_compete` — "Non-compete clause in a simple NDA (significant overreach)"
- `ip_assignment` — "IP assignment clause in an NDA (should not transfer IP)"

### Consulting (5 of 10):
- `ip_ownership` — "Consultant retains all IP including work product paid for by client"
- `limitation_of_liability` — same pattern as MSA
- `indemnification` — "Indemnification is not mutual or exceeds fees paid"
- `non_compete` — "Non-compete for consultant (generally unenforceable in India)"
- `scope_of_work` — "Scope of work is vague or open-ended without clear deliverables"

### DPA (5 of 10):
- `data_breach_notification` — "Breach notification exceeds 72 hours or lacks specificity requirements"
- `cross_border_transfer` — "Personal data transferred outside India without adequate safeguards"
- `data_deletion` — "No data deletion/return clause on contract termination"
- `sub_processor_controls` — "No notification mechanism for adding sub-processors"
- `liability_indemnification` — "Processor has no indemnification obligation for data breaches"

### Vendor (4 of 10):
- `limitation_of_liability` — same pattern as MSA
- `indemnification` — "Vendor does not indemnify for defective goods or IP infringement"
- `warranties` — "Goods/services sold 'as-is' with no express warranties"
- `acceptance_criteria` — "No defined acceptance/rejection process or timeline"

### Joint Venture (5 of 10):
- `profit_loss_sharing` — "Profit/loss distribution is disproportionate to capital contribution or effort"
- `decision_making` — "One party has unilateral control over JV decisions"
- `ip_ownership` — "One party takes all JV-created IP regardless of contribution"
- `exit_buyout` — "No exit mechanism or buy-out formula defined"
- `deadlock_resolution` — "No deadlock resolution mechanism (risks permanent gridlock)"

### Lease (3 of 10):
- `lock_in_period` — "Lock-in period exceeds 3 years with no early exit option"
- `rent_escalation` — "Annual rent escalation exceeds 10% (standard in India is 5-8%)"
- `termination_early_exit` — "No early termination clause or exit requires full remaining rent"

**TOTAL: 54 rules** (some rules like limitation_of_liability appear in multiple playbooks but share similar descriptions)

3. Update `seed_default_playbooks.py` to write the new fields when inserting rules.

4. Commit: `feat(rules): AI-primary risk descriptions for 44 context-dependent rules`

---

## Task 8: Dashboard — PlaybookEditor UX

**Files:**
- Modify: `dashboard/src/pages/PlaybookEditor.tsx`
- Modify: `dashboard/src/api/client.ts`

**Steps:**

1. Update TypeScript interfaces in `client.ts`:

```typescript
export interface PlaybookRule {
    // ... existing fields ...
    detection_mode: string;
    risk_description?: string;
    acceptable_position?: string;
    unacceptable_signals?: string[];
    acceptable_signals?: string[];
    clause_context?: string;
}

export interface CreateRuleData {
    // ... existing fields ...
    detection_mode?: string;
    risk_description?: string;
    acceptable_position?: string;
    unacceptable_signals?: string[];
    acceptable_signals?: string[];
    clause_context?: string;
}
```

2. Add DETECTION_MODES constant in PlaybookEditor.tsx:

```typescript
const DETECTION_MODES = [
    { value: 'keywords_only', label: 'Keywords Only', hint: 'Regex pattern matching (current behavior)' },
    { value: 'ai_with_keywords', label: 'AI + Keywords', hint: 'AI detection with keyword pre-filtering' },
    { value: 'ai_only', label: 'AI Only', hint: 'Pure AI detection (best for context-dependent rules)' },
];
```

3. Update the rule form (around lines 609-710) to add:
   - Detection Mode select (after match_type, same styling)
   - Risk Description textarea (shown when detection_mode !== 'keywords_only')
   - Acceptable Position textarea (shown when detection_mode !== 'keywords_only')
   - Conditionally show detection_patterns input only when detection_mode !== 'ai_only'

4. Update initial state for newRule to include `detection_mode: 'keywords_only'`.

5. Update the RuleRow display to show detection_mode badge.

6. Commit: `feat(ui): PlaybookEditor detection mode toggle and risk description fields`

---

## Task 9: Final Commit & Verify

1. Verify all TypeScript compiles: `cd dashboard && npx tsc --noEmit`
2. Verify Python imports: `cd backend && python -c "from app.models.playbook import PlaybookRule; print('OK')"`
3. Run the updated seed script against local DB to verify new fields persist
4. Final commit if any fixups needed

---

## Parallelization Strategy

These tasks can be parallelized:
- **Agent A**: Tasks 1-2-3-4-5-6 (schema + backend pipeline) — sequential chain
- **Agent B**: Task 7 (rule content generation for all 10 playbook files) — independent, largest task
- **Agent C**: Task 8 (dashboard UX) — independent

Agent A must complete Task 2 (model) before Agent C can finalize types, but the dashboard work can start in parallel since the interface shape is known from the plan.
