# ContraRed — Architectural Decisions Requiring Human Input

Three key architectural decisions that cannot be resolved by code changes alone. Each requires strategic trade-off evaluation by the founding team.

---

## Decision 1: Regex vs AI Migration

### The Question
Should ContraRed migrate its 78-rule regex engine to AI-primary detection, and if so, how aggressively?

### Current State
- **78 rules** in `rules_library.py` with ~390 regex patterns
- **44 rules (56%)** classified as REPLACE-WITH-AI (risk assessment requiring legal judgment)
- **34 rules (44%)** classified as KEEP (structural/boilerplate detection)
- **140 template rules** across 5 playbook templates, ALL hardcoded with regex
- Rule engine runs in Stage 2 (~100ms), AI runs in Stage 3 (~10-60s)

### Options

**Option A: Aggressive Migration (8 weeks)**
- Replace all 44 REPLACE-WITH-AI rules with AI-only detection
- Keep 34 KEEP rules as regex pre-filters
- Detection mode: `ai_with_keywords` (regex pre-filter + AI evaluation)
- Risk: Some edge cases caught by regex but missed by AI during transition
- Cost impact: ~20% more AI tokens (regex pre-filtering saves tokens)

**Option B: Gradual Hybrid (12 weeks)**
- Phase 1: Add `risk_description` field to all rules (schema extension)
- Phase 2: AI evaluates rules that have `risk_description`; regex for the rest
- Phase 3: Progressively fill `risk_description` for more rules
- Risk: Two code paths to maintain; complexity doubles during transition
- Cost impact: Neutral (existing regex stays, AI added incrementally)

**Option C: Keep Regex, Enhance AI Prompt (4 weeks)**
- Keep regex engine as-is
- Improve AI prompts to catch what regex misses
- Add `risk_description` as supplementary context in prompts
- Risk: Regex false negatives persist; AI and regex may conflict
- Cost impact: Minimal

### Recommendation
**Option B (Gradual Hybrid)** — safest for a production launch. Existing regex rules continue working while AI-native rules are built alongside. The `detection_mode` field (proposed in PLAYBOOK-7) enables per-rule routing. No breaking changes.

### Key Data Points
- Industry benchmark: LLMs achieve >90% accuracy vs 60-80% for regex in contract analysis
- ContraRed's regex false negative rate: unknown (no tracking) — should measure before deciding
- AI cost per scan: $0.04-0.10 — affordable at current pricing
- The 34 KEEP rules (structural detection) are genuinely better as regex — AI would be slower and less reliable for section splitting, defined terms, governing law detection

### Human Input Needed
1. What accuracy threshold justifies full migration? (90%? 95%? 99%?)
2. Is the ~20% AI cost increase acceptable for better accuracy?
3. Should existing customer playbooks be auto-migrated or grandfathered?

---

## Decision 2: Playbook Schema Migration

### The Question
How should the `PlaybookRule.detection_patterns` JSONB field evolve to support AI-native rule definitions?

### Current Schema
```json
{
  "patterns": ["regex1", "regex2"],
  "match_type": "exact|fuzzy|regex",
  "negative_patterns": [...],
  "escalation_conditions": [...]
}
```

### Proposed New Fields (from PLAYBOOK-7)
```
risk_description: str        — "What makes this risky?" (natural language)
acceptable_position: str     — "What does a good clause look like?"
unacceptable_signals: JSONB  — ["One-sided liability", "No cap"]
acceptable_signals: JSONB    — ["Mutual cap at 12 months"]
clause_context: str          — "Limitation of liability provisions"
detection_mode: str          — "ai_only" | "ai_with_keywords" | "keywords_only"
example_risky_clauses: JSONB — Real examples from clause library
example_acceptable_clauses: JSONB
```

### Migration Strategy
1. **All new fields are nullable** — existing playbooks continue working unchanged
2. **`detection_patterns` stays** — never removed, becomes optional optimization
3. **Version snapshots are schema-agnostic** — confirmed in PLAYBOOK-4 audit
4. **Dashboard UX**: Replace pattern chip input with risk description textarea + detection mode toggle
5. **140 template rules**: Auto-populate `risk_description` from existing `primary_position` text

### Backward Compatibility Guarantees
- Old playbooks with only `detection_patterns` → `detection_mode` defaults to `ai_with_keywords`
- If `risk_description` is empty, system falls back to regex-only behavior
- Existing API contracts unchanged — `RuleCreate`/`RuleUpdate` schemas extended, not replaced
- `from_playbook_rules()` checks new fields before old ones

### Human Input Needed
1. Should the dashboard show BOTH regex patterns AND natural language fields simultaneously, or switch UX based on detection_mode?
2. Should auto-generated `risk_description` text be reviewed by a legal expert before deployment?
3. Timeline: Can the schema migration deploy before or only after the Intellect Design Arena pilot?

---

## Decision 3: Text Replacement Fix

### The Question
How should ContraRed apply AI-suggested fixes to Word documents without destroying paragraph content?

### Root Cause (from OOXML-1 through OOXML-10)
1. `findTextInDocument()` Tier 3 returns paragraph-level range (entire paragraph)
2. `insertOoxml(replace)` replaces the entire range with OOXML covering only the changed words
3. Surrounding paragraph text is permanently destroyed (not recoverable by undo)
4. Track Changes double-tracking: Word's live tracking wraps OOXML's embedded marks

### Options (detailed in REPLACEMENT_FIX_PROPOSAL.md)

**Option A: Surgical Search+Replace (RECOMMENDED)**
- `paragraph.search(oldWord)` → `insertText(newWord, "Replace")` with Track Changes ON
- Word natively handles revision marks — only changed words show as tracked
- Effort: 16 hours
- Pros: Eliminates root cause, works in Word Online, simplest architecture
- Cons: Multiple API calls per fix (~200-500ms), no custom author name, no custom colors

**Option B: Improved OOXML with Tighter Range**
- Fix `findTextInDocument()` to narrow Tier 3 range + disable live Track Changes
- Effort: 8 hours
- Pros: Single API call, custom author name "ContraRed AI"
- Cons: Still fragile for long clauses, OOXML has Word Online issues

**Option C: Hybrid (route by complexity)**
- Simple word swaps → Option A; complex rewrites → Option B
- Effort: 24 hours
- Pros: Best of both worlds
- Cons: Two code paths, inconsistent UX (native colors vs custom colors)

### Recommendation
**Option A (Surgical Search+Replace)** — eliminates the root cause entirely. The cons (no custom author, multiple API calls) are manageable: comments provide attribution, 200-500ms per fix is acceptable for one-at-a-time lawyer review.

### Human Input Needed
1. Is losing "ContraRed AI" as the Track Changes author name acceptable? (Comments preserve attribution)
2. Is the 200-500ms per-fix delay acceptable vs the current ~100ms (but broken) approach?
3. Should we implement Option A now and Option B as a future enhancement, or vice versa?

---

## Decision Timeline

| Decision | Blocking Launch? | Recommended Timeline |
|----------|-----------------|---------------------|
| 1. Regex vs AI | No — current regex works | Start Week 1, complete by Week 8-12 |
| 2. Playbook Schema | No — schema extension is additive | Deploy schema Week 1-2, UX by Week 5-6 |
| 3. Text Replacement | **YES** — P0 paragraph destruction bug | Fix before first enterprise deployment |
