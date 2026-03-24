---
title: "#29 AI-Primary Rule Migration"
date: 2026-03-24
status: approved
---

# #29 AI-Primary Rule Migration Design

## Goal
Migrate 44 playbook rules from regex-only detection to AI-primary detection, enabling Gemini to catch novel/paraphrased contract risks that regex patterns miss.

## Schema Changes

6 new nullable columns on `playbook_rules`:

| Column | Type | Purpose |
|--------|------|---------|
| `detection_mode` | String(30), default `keywords_only` | `ai_only` / `ai_with_keywords` / `keywords_only` |
| `risk_description` | Text | Natural language risk description for AI |
| `acceptable_position` | Text | What's OK (prevents false positives) |
| `unacceptable_signals` | JSONB | Red flags list |
| `acceptable_signals` | JSONB | Green flags list |
| `clause_context` | Text | Background context for nuanced rules |

## Pipeline Changes

1. **playbook_cache.py** — include new fields in cached dict
2. **gemini_analyzer.py → format_playbook_rules()** — inject risk_description + signals for AI-enabled rules
3. **rule_engine.py → from_playbook_rules()** — skip regex for `ai_only` rules

## Dashboard UX Changes

PlaybookEditor.tsx:
- Detection Mode toggle (3 options)
- Risk Description textarea (visible when mode includes AI)
- Conditional pattern chips visibility based on mode

## Rule Content

54 rules get risk_description + signals (context-dependent rules like liability, IP, indemnification).
62 rules stay keywords_only (boilerplate like governing law, jurisdiction).

## Out of Scope
- Gemini system prompt changes
- A/B testing infrastructure
- SmartRule structure changes beyond detection_mode
- Tiers, conditions, dependencies
