# ContraRed Regex/Pattern Engine Inventory

## Summary

| Metric | Count |
|---|---|
| **Total regex-containing service files** | 9 |
| **Total individual regex patterns** | ~500+ |
| **Total rules (rules_library.py)** | 78 (documented as 75) |
| **Default rules (rule_engine.py)** | 13 (documented as 16) |
| **Classifier rules (clause_classifier.py)** | 30 |
| **Definition extraction patterns** | 7 |
| **Jurisdiction detection patterns** | 8 |
| **Overbroad definition signals** | 9 |
| **Scope analysis pattern categories** | 6 |
| **Hallucination guard tiers** | 4 |

## Classification Summary

| Classification | Count | Percentage |
|---|---|---|
| **KEEP** | 39 rules + 5 service files | ~50% of patterns |
| **REPLACE-WITH-AI** | 44 rules + 2 service modules | ~50% of patterns |
| **REMOVE** | 0 | 0% |

## Detailed File Inventory

### 1. rule_engine.py (730 lines) — MIXED
- **13 DEFAULT_RULES** with 42 regex patterns
- **RuleEngine class**: pattern compilation, evaluation, deduplication, sentence expansion
- **SmartRule system**: negative patterns, escalation/de-escalation (sophisticated)
- **`from_playbook_rules()`**: converts user playbook rules to regex — **ReDoS vulnerability (P0)**
- **KEEP**: Engine infrastructure, dedup, SmartRule architecture
- **REPLACE**: 8/13 default rules need AI for contextual risk assessment

### 2. rules_library.py (1634 lines) — MIXED
- **78 rules** across 11 categories (5+7+8+8+7+8+6+5+6+11+7)
- 40 RulePattern (simple) + 38 SmartRule (with escalation)
- ~390+ individual regex patterns
- **KEEP**: 34 rules (44%) — structural/boilerplate detection
- **REPLACE**: 44 rules (56%) — risk assessment requiring legal judgment
- **High-value content**: `primary_position` legal advice worth preserving regardless

### 3. clause_classifier.py (968 lines) — KEEP
- **30 classifier rules** with heading + body patterns
- Two-tier scoring: heading match (0.6) + body matches (0.2 each, max 0.6)
- AI fallback for confidence < 0.5
- **Issue**: Taxonomy gap (30 types vs 78 rules), body-only scoring too low for inline clauses
- **Verdict**: Clause CATEGORIZATION is well-suited to keyword matching

### 4. scope_analyzer.py (451 lines) — REPLACE (mostly)
- 5-dimension scope analysis: breadth, mutuality, financial exposure, duration, trigger
- **Critical bug**: Party name hardcoding (only 5 labels per side)
- **Critical bug**: `irrevocable` classified as `perpetual` (legal error)
- **KEEP**: Duration/trigger detection, scoring model weights
- **REPLACE**: Breadth, mutuality, financial exposure — need semantic understanding

### 5. defined_terms_resolver.py (456 lines) — KEEP
- 7 extraction patterns for "Term" means... definitions
- Recursive cross-reference resolution (depth 3)
- 9 overbroad definition signals
- **Issue**: Inline definition boundary bug, 80-char term name limit
- **Verdict**: Textbook regex use case — definitions follow predictable syntax

### 6. jurisdiction_detector.py (1203 lines) — KEEP
- 13 jurisdiction profiles with high-quality legal citations
- 8 detection patterns + 65 aliases + 25 rule overrides
- **Bug**: ADGM maps to onshore UAE (wrong legal system)
- **Bug**: Substring matching causes collisions
- **Verdict**: Governing law detection is a perfect regex task

### 7. text_normalizer.py (140 lines) — KEEP
- 10 categories of Word artifact normalization
- Smart quotes, zero-width chars, dashes, whitespace, Unicode NFC
- **Verdict**: Essential preprocessing, no AI needed

### 8. structure_extractor.py (299 lines) — KEEP
- DOCX parsing with python-docx, SHA-256 drift hashing
- Smart paragraph splitting for raw text
- **Issue**: Table content not extracted from DOCX (P1)
- **Verdict**: Structural extraction is deterministic

### 9. confidence_scorer.py (339 lines) — KEEP (rebalance)
- 5-factor weighted scoring model
- **Issue**: AI-only findings penalized 12.5% vs regex+AI
- **Proposed**: Increase AI-only from 0.5→0.7, rebalance weights
- **Verdict**: Framework is sound, weights need AI-first adjustment

### 10. hallucination_guard.py (423 lines) — KEEP
- 4-tier verification: exact → normalized → fuzzy → rejected
- **Issue**: 0.80 fuzzy threshold may accept wrong party names
- **Issue**: `_find_actual_text()` position mapping offset bug
- **Verdict**: Most important quality gate — KEEP and refine

## Priority-Ordered Migration Plan

### P0 — Must Fix Before Production (Security/Correctness)
| Item | File | Issue | Effort |
|---|---|---|---|
| ReDoS vulnerability | rule_engine.py:663 | User-supplied regex compiled without protection | 4h |
| ADGM alias mapping | jurisdiction_detector.py:678 | Maps to wrong legal system (civil vs common law) | 1h |
| Table content extraction | structure_extractor.py:90 | DOCX tables invisible to analysis | 8h |

### P1 — First Sprint Post-Launch (Quality)
| Item | File | Issue | Effort |
|---|---|---|---|
| AI-only confidence penalty | confidence_scorer.py:250 | 12.5% penalty on novel findings | 2h |
| Party name hardcoding | scope_analyzer.py:166 | Only 5 labels per side | 4h |
| Fuzzy threshold refinement | hallucination_guard.py:127 | 0.80 may accept wrong party names | 2h |
| Clause type taxonomy gap | clause_classifier.py | 30 types vs 78 rules | 8h |
| Inline definition boundary | defined_terms_resolver.py:113 | Multiple defs captured as one | 4h |
| irrevocable ≠ perpetual | scope_analyzer.py:183 | Legal error in duration detection | 1h |
| Substring matching collisions | jurisdiction_detector.py:907 | "new" matches multiple jurisdictions | 4h |

### P2 — First Month (Optimization)
| Item | File | Issue | Effort |
|---|---|---|---|
| Migrate 44 rules to AI-primary | rules_library.py | Risk assessment rules need context | 40h |
| Expand jurisdiction profiles | jurisdiction_detector.py | Missing: Canada, China, Switzerland, etc. | 16h |
| Cross-reference map expansion | confidence_scorer.py:317 | Only 9/78 rules have corroboration pairs | 8h |
| Body-only classifier scoring | clause_classifier.py:844 | Can't reach 0.5 threshold easily | 4h |
| Section splitting for Indian contracts | clause_classifier.py:886 | Misses (a), (b) sub-numbering | 4h |
| Term name length limit | defined_terms_resolver.py:111 | 80-char limit too short | 1h |

### P3 — Long-term (Architecture)
| Item | Scope | Description | Effort |
|---|---|---|---|
| AI-first playbook schema | Playbook system | Replace regex patterns with natural language rules | 80h |
| Agentic document workflow | Pipeline | Decompose into specialized agents per industry best practice | 120h |
| Confidence model rebalancing | Scoring system | Shift weights for AI-primary architecture | 8h |

## Industry Context (Web Research)

### LLM vs Regex in Contract Analysis (2025-2026)

Industry data shows LLMs achieving >90% accuracy in contract analysis vs 60-80% for rule-based approaches. One benchmark: AI reviewed complex supply agreements in <3 minutes at >90% accuracy vs 4 hours at 86% for qualified lawyers.

Key trend: **Explainable AI (XAI)** is becoming central to legal tech — AI must show WHY it flagged something, not just THAT it flagged it. ContraRed's confidence scoring and hallucination guard align with this trend.

### Agentic Document Analysis Best Practices

The industry is moving toward **Agentic Document Workflows (ADW)** — specialized agents for intake, classification, extraction, reasoning, verification, and audit. ContraRed's 5-stage pipeline (extraction → classification → AI analysis → verification → scoring) already follows this pattern, though not yet with independent agents.

Best practices:
1. Decompose into specialized agents with defined roles
2. Self-improving feedback loops (95-99.8% accuracy achievable)
3. Full transparency via AI citations linking back to source documents
4. Context management — focus agents on relevant context only
5. Security: ISO 27001, SOC 2 Type II for enterprise deployment

### Recommendation

ContraRed should adopt a **tiered hybrid approach**:
- **Layer 1 (Regex/Deterministic)**: KEEP for preprocessing, structure extraction, defined terms, jurisdiction detection, clause classification — fast, cheap, reliable
- **Layer 2 (AI-Primary)**: MIGRATE risk assessment, scope analysis, and playbook evaluation — AI understands context, nuance, and novel risks that regex cannot
- **Layer 3 (Verification)**: KEEP hallucination guard and confidence scorer as post-AI quality gates — but rebalance for AI-first weights

This preserves ContraRed's performance advantage (Stage 1-2 run in <1 second) while upgrading accuracy for the semantic tasks where regex fundamentally cannot compete.

## Sources
- [Best Open Source LLM for Contract Processing & Review 2026](https://www.siliconflow.com/articles/en/best-open-source-llm-for-contract-processing-review)
- [How LLMs Are Changing Contract Analysis](https://www.thoughtriver.com/resources/the-legal-data-boom-how-llms-are-changing-contract-analysis)
- [Trends 2025: AI in Contract Analysis](https://www.legartis.ai/blog/trends-ai-contract-analysis)
- [How Large Language Models Work in Contract Management](https://www.icertis.com/learn/how-do-large-language-models-work-in-contract-management/)
- [Agentic Document Workflows: A Practical Guide](https://www.llamaindex.ai/blog/introducing-agentic-document-workflows)
- [AI Document Analysis: Complete Guide 2025](https://www.v7labs.com/blog/ai-document-analysis-complete-guide)
- [Agentic AI for Complex Document Review](https://syllo.ai/white-paper-2025/)
- [Agentic Document Processing: Beyond Traditional IDP](https://idp-software.com/capabilities/agentic/)
