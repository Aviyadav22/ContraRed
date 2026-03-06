# ContraRed Feature Roadmap — Building Toward Smriti

> ContraRed → Smriti Contracts: From standalone redlining tool to the contract intelligence layer of India's legal OS.

*March 2026 | Aligned with [CURSOR_FOR_LAW.md](./CURSOR_FOR_LAW.md)*

---

## Current State (What's Built & Live)

| Component | Status | Key Features |
|---|---|---|
| **Backend** | LIVE on Render | Auth (JWT), AI analysis (Gemini), rule-based + AI-first scanning, ZDR mode, redline OOXML generation, playbook CRUD, billing (Razorpay), team management, audit logs |
| **Dashboard** | LIVE on Netlify | Login/register, stats dashboard, playbook editor, team management, billing page, audit logs |
| **Word Add-in** | LIVE on Netlify | Login, playbook selector, AI-first document scan, risk cards (RED/YELLOW), highlight in Word, apply Track Changes redlines, executive summary |

**Core flow works end-to-end:** Upload/paste contract → AI analyzes against playbook → highlights risks → applies Track Changes fixes in Word.

---

## Phase A: "Strengthen the Core" (Month 1 — March/April 2026)

Before converging with Smriti, ContraRed needs to be rock-solid as a contract tool. These are table-stakes features that make users stay.

### A1. Bulk Highlight + "Accept All" Flow
| Detail | |
|---|---|
| **What** | After scan, one-click "Highlight All Risks" (already partial) + "Apply All Fixes" button that sequentially applies all suggested redlines |
| **Why** | Lawyers review 20-50 page contracts. Clicking "Fix" 30 times is painful. |
| **Effort** | 3-4 days |
| **Builds toward** | Phase C intelligence layer — bulk operations need to work before we add clause risk scores |

### A2. Risk Filtering & Sorting in Word Add-in
| Detail | |
|---|---|
| **What** | Filter risks by: risk level (RED/YELLOW), clause type (indemnity, liability, termination), deal-breaker flag. Sort by position in document. |
| **Why** | Associates triage — they fix RED deal-breakers first, then YELLOW. Currently all risks shown in a flat list. |
| **Effort** | 2-3 days |

### A3. Export Risk Report (PDF/DOCX)
| Detail | |
|---|---|
| **What** | "Export Report" button → generates a PDF/DOCX with: executive summary, all risks with explanations, suggested fixes, playbook used |
| **Why** | Associates send risk reports to partners/clients. Currently they'd have to screenshot the add-in. |
| **Effort** | 4-5 days |
| **Builds toward** | Phase B "Auto-Research Brief" needs document generation infrastructure |

### A4. Clause Library (User-Saved Clauses)
| Detail | |
|---|---|
| **What** | Users can save preferred clause language (e.g., "Our standard indemnity cap clause"). When a risk is flagged, show "Use saved clause" option alongside AI suggestion. |
| **Why** | Every firm has standard fallback language. AI suggestions are good but lawyers want THEIR language. |
| **Effort** | 5-6 days (model exists, needs CRUD endpoints + UI) |
| **Builds toward** | Phase C "Playbook x Case Law" — saved clauses become the firm's institutional knowledge |



---

## Phase B: "Connect the Islands" (Month 2-3 — April/May 2026)

*Aligned with CURSOR_FOR_LAW.md Phase A. This is where ContraRed starts becoming Smriti Contracts.*

### B1. Unified Auth — One Login for Smriti + ContraRed
| Detail | |
|---|---|
| **What** | Shared JWT auth between Smriti Search backend and ContraRed backend. Single user table, single login. User logs into Word add-in → has access to both contract and research features. |
| **Why** | "One login. One subscription. One brain." — the foundation for everything else. |
| **Technical** | Options: (a) shared auth microservice, (b) one backend validates tokens from the other, (c) merge into single backend. Recommend (a) for clean separation. |
| **Effort** | 1-2 weeks |
| **Critical path** | Every bridge feature depends on this |

### B2. "Research This Clause" — The Killer Bridge
| Detail | |
|---|---|
| **What** | Select a flagged clause in the risk card → "Research" button → calls Smriti Search API → shows SC/HC cases where similar clauses were litigated. Results appear in a slide-out panel in the Word add-in. |
| **Why** | **Nobody has this.** Jhana can't inject into Word. No competitor connects contract review to case law. This is the feature that makes lawyers say "holy shit." |
| **Technical** | Word add-in calls Smriti's `/search` API with clause text as query + clause_type as filter. Returns top 5 relevant cases with ratio decidendi. |
| **Effort** | 1-2 weeks |
| **Builds toward** | Phase D "Clause Risk Score" — once we can search case law per clause, we can score clauses |

### B3. "Cite in Word" — From Smriti Search to Word
| Detail | |
|---|---|
| **What** | Found a case in Smriti Search (browser)? One click → inserts formatted citation + ratio decidendi into your Word document via the add-in. |
| **Why** | Lawyers draft in Word. They research in browser. This bridge eliminates copy-paste. |
| **Technical** | Smriti Search web app gets a "Cite in Word" button. Uses Office.js `document.body.insertText()` or a clipboard-based approach with custom formatting. Could also use a shared "citation queue" that the Word add-in polls. |
| **Effort** | 1 week |

### B4. "Check If Good Law" — Citation Intelligence in Word
| Detail | |
|---|---|
| **What** | Hover/click on a case citation in Word → Smriti checks if it's overruled, distinguished, or affirmed. Shows status badge inline. |
| **Why** | Lawyers cite cases in contracts and opinions. Citing an overruled case is malpractice-level embarrassing. |
| **Technical** | Word add-in has a "Check Citations" mode that scans document for citation patterns (regex: `AIR \d{4} SC \d+`, `(\d{4}) \d+ SCC \d+`, etc.) → batch query to Smriti's citation graph API → highlight with status colors. |
| **Effort** | 1-2 weeks (depends on Smriti citation graph API readiness) |

### B5. Rebrand — ContraRed → Smriti Contracts
| Detail | |
|---|---|
| **What** | Update Word add-in manifest, dashboard, all UI to say "Smriti Contracts" (powered by ContraRed engine). New logo, consistent with Smriti brand. Dashboard becomes a tab within Smriti's main dashboard. |
| **Why** | One brand. Users should never think "is this a different product?" |
| **Effort** | 3-4 days |

---

## Phase C: "Smriti Draft Integration" (Month 4-5 — June/July 2026)

*Aligned with CURSOR_FOR_LAW.md Phase B. ContraRed's redline engine powers the drafting module.*

### C1. Contract Clause Generation from Playbooks
| Detail | |
|---|---|
| **What** | Instead of just flagging bad clauses, generate entire clause alternatives. "Your NDA has no non-solicitation clause. Here's one based on your playbook + Indian Contract Act." |
| **Why** | Moves from reactive (flag problems) to proactive (suggest additions). |
| **Technical** | New endpoint: `POST /documents/generate-clause` — takes clause_type + playbook_id + contract_context → Gemini generates clause grounded in playbook rules + legal principles. |
| **Effort** | 1 week |
| **Builds toward** | Smriti Draft uses same clause generation engine |

### C2. Template Library — Pre-Built Indian Contract Templates
| Detail | |
|---|---|
| **What** | Library of Indian-law-specific contract templates: NDA (mutual/unilateral), SaaS agreement, employment agreement, freelancer agreement, MSA. Each template is a playbook + starting DOCX. |
| **Why** | Junior lawyers don't start from scratch. Templates with built-in playbooks = instant value. |
| **Effort** | 2-3 weeks (legal content creation + UI) |
| **Revenue** | Premium templates for firm tier |

### C3. Contract Comparison (Diff View)
| Detail | |
|---|---|
| **What** | Upload two versions of a contract → side-by-side diff showing what changed, with AI commentary on whether changes help or hurt your position. |
| **Why** | Negotiation is iterative. Counterparty sends back a revised contract. Associates spend hours comparing manually. |
| **Technical** | Backend diff engine (paragraph-level, using existing SHA-256 hashing) + Gemini analysis of changes against playbook positions. |
| **Effort** | 2-3 weeks |

### C4. Smriti Draft ↔ Contracts Bridge
| Detail | |
|---|---|
| **What** | When Smriti Draft generates a legal notice or agreement, it can be auto-scanned by Smriti Contracts before the lawyer finalizes. "Draft → Review → Finalize" in one flow. |
| **Why** | The circular workflow: draft produces contracts, contracts module reviews them, review insights improve future drafts. |
| **Technical** | Smriti Draft's "Finalize" button calls ContraRed's analyze-full endpoint. Results shown inline. |
| **Effort** | 1 week (once both Draft and Contracts share auth) |

---

## Phase D: "The Intelligence Layer" (Month 6-8 — Aug-Oct 2026)

*Aligned with CURSOR_FOR_LAW.md Phase C. Features that only work because we have research + contracts + drafting.*

### D1. Clause Risk Score — Case Law Grounded
| Detail | |
|---|---|
| **What** | Every flagged clause gets a risk score backed by actual SC/HC judgments. "This indemnity clause (uncapped) has been struck down in 3/7 SC cases. Risk: 78/100." With links to the actual cases. |
| **Why** | Transforms opinions into evidence. Partner asks "why did you flag this?" → "Because the Supreme Court struck it down 3 times." |
| **Technical** | For each flagged clause: query Smriti citation graph for clause_type + outcome → compute score from (struck_down / total_cases). Cache scores per clause pattern. |
| **Effort** | 2-3 weeks |
| **Depends on** | Smriti's citation graph + case tagging by legal topic |

### D2. Playbook x Case Law Intelligence
| Detail | |
|---|---|
| **What** | "Your playbook says cap liability at 1x contract value. Here are 4 SC cases supporting this position, and 2 where courts allowed higher caps." Playbook rules auto-linked to supporting case law. |
| **Why** | Playbooks become evidence-based, not opinion-based. Firms can justify their positions to clients. |
| **Technical** | Background job: for each playbook rule, search Smriti for supporting/contradicting case law. Store as `rule.supporting_cases[]` and `rule.contradicting_cases[]`. |
| **Effort** | 2 weeks |

### D3. Judge Intelligence for Contracts
| Detail | |
|---|---|
| **What** | "This contract's arbitration clause names Bombay HC. Justice X at Bombay HC ruled against uncapped indemnity in 3 cases. Consider capping." |
| **Why** | Contract drafting should account for the actual judge who'll interpret it. Mind-blowing for lawyers. |
| **Technical** | Extract jurisdiction from contract → map to judges → query Smriti for judge's history on relevant clause types. |
| **Effort** | 3-4 weeks |
| **Depends on** | Smriti's judge metadata + HC ingestion |

### D4. Negotiation Playback
| Detail | |
|---|---|
| **What** | Track all versions of a contract through negotiation. Show timeline: "v1 → counterparty removed indemnity cap → v2 you added it back with 1x limit → v3 counterparty accepted." AI summary of negotiation dynamics. |
| **Why** | Partners want to see the negotiation arc, not just the final contract. |
| **Technical** | Uses C3's diff engine + version tracking. Store versions in DB with timestamps + party labels. |
| **Effort** | 2-3 weeks |

---

## Phase E: "Enterprise & Scale" (Month 9-12 — Nov 2026-Feb 2027)

### E1. Firm-Wide Playbook Analytics
| Detail | |
|---|---|
| **What** | Dashboard for firm admins: "Your firm reviewed 340 contracts this month. Top risk: uncapped indemnity (found in 67% of vendor contracts). Average resolution time: 2.3 days." |
| **Why** | Enterprise buyers need ROI metrics. "Smriti saved your associates 1,200 hours this quarter." |
| **Effort** | 2-3 weeks |

### E2. Multi-Party Contract Support
| Detail | |
|---|---|
| **What** | Contracts with 3+ parties (JVs, consortium agreements). Each party gets their own playbook perspective. |
| **Effort** | 3-4 weeks |

### E3. Due Diligence Module
| Detail | |
|---|---|
| **What** | Upload a bundle of company docs → AI checks compliance with Companies Act, FEMA, SEBI. Outputs DD report with flags. |
| **Why** | M&A lawyers spend weeks on DD. Automating the initial review is a Rs 5-15K/project revenue opportunity. |
| **Effort** | 4-6 weeks |
| **Revenue** | Per-project pricing or Enterprise tier |

### E4. API for Third-Party Integrations
| Detail | |
|---|---|
| **What** | Public API: `POST /api/v1/analyze` — any third-party tool can send a contract and get back risk analysis. |
| **Why** | Firms using other tools (CLMs, document management) can plug in Smriti's intelligence. |
| **Effort** | 2 weeks (mostly documentation + rate limiting + API keys) |

### E5. Compliance Tracker Integration
| Detail | |
|---|---|
| **What** | When RBI/SEBI issues a new circular, Smriti Contracts auto-checks existing playbook rules against new regulations and flags outdated positions. |
| **Why** | Regulations change. Playbooks that were correct last month may be wrong today. |
| **Effort** | 3-4 weeks |
| **Depends on** | Smriti's compliance tracker module |

---

## Convergence Architecture

How the two codebases merge over time:

```
MONTH 1-2 (Now)                    MONTH 3-4                         MONTH 6+
=============                      =========                         ========

┌──────────────┐                   ┌──────────────────────┐          ┌─────────────────────────┐
│ Smriti       │                   │ Smriti Gateway       │          │ Smriti Platform          │
│ (Next.js +   │                   │ (shared auth, routing)│          │ (unified backend)        │
│  FastAPI +   │                   │         │             │          │                          │
│  Pinecone +  │                   │    ┌────┴────┐        │          │  /search  /contracts     │
│  Neo4j)      │                   │    │         │        │          │  /draft   /compliance    │
│              │                   │ Search    Contracts   │          │  /cite    /analytics     │
│              │                   │ Service   Service     │          │                          │
└──────┬───────┘                   │ (Smriti)  (ContraRed) │          │  Shared: Auth, Billing,  │
       │ no connection             │         │             │          │  Citation Graph, Playbooks│
┌──────┴───────┐                   │    Shared DB layer    │          │                          │
│ ContraRed    │                   │    (user, billing,    │          │  Word Add-in shows ALL   │
│ (FastAPI +   │                   │     audit)            │          │  features in one panel   │
│  PostgreSQL) │                   └──────────────────────┘          └─────────────────────────┘
└──────────────┘
```

### Shared Infrastructure (Build in Phase B)

| Component | Current (Separate) | Target (Shared) |
|---|---|---|
| **Auth** | ContraRed JWT + Smriti JWT | Single auth service, one JWT |
| **User DB** | Separate user tables | Single user table with subscription + roles |
| **Billing** | ContraRed Razorpay | Single billing: Free (search) → Pro (search + contracts + draft) → Enterprise (all + team) |
| **Word Add-in** | ContraRed only | Smriti Add-in with tabs: Contracts / Research / Draft |
| **Dashboard** | Separate React apps | Single dashboard: smriti.app with /contracts, /research, /drafts routes |

---

## Priority Matrix

What to build first based on impact vs effort:

```
HIGH IMPACT
    │
    │  ★ B2: "Research This Clause"     ★ D1: Clause Risk Score
    │  ★ A5: Fix GEMINI_API_KEY         ★ C3: Contract Comparison
    │  ★ A1: Bulk Accept All            ★ D2: Playbook x Case Law
    │  ★ B1: Unified Auth
    │  ★ A3: Export Risk Report
    │
    │  ○ A2: Risk Filtering             ○ D3: Judge Intelligence
    │  ○ B3: Cite in Word               ○ E1: Firm Analytics
    │  ○ A4: Clause Library             ○ E3: Due Diligence
    │  ○ C1: Clause Generation
    │
LOW ├───────────────────────────────────────────── HIGH EFFORT
IMPACT
    │  △ B5: Rebrand                    △ E2: Multi-Party
    │  △ C4: Draft Bridge               △ E5: Compliance Tracker
    │
    │
```

★ = Do first (high impact, manageable effort)
○ = Do next (good impact, moderate effort)
△ = Do later (necessary but not urgent)

---

## Immediate Next Steps (This Week)

1. **A5: Add GEMINI_API_KEY to Render** — AI features are dead without this. 30 minutes.
2. **A1: Bulk "Apply All Fixes"** — Biggest UX pain point. 3-4 days.
3. **A2: Risk filtering in Word add-in** — Quick win, makes scanning usable for long contracts. 2-3 days.
4. **Start B1 planning**: Map out shared auth architecture between Smriti and ContraRed backends.

---

## Success Metrics by Phase

| Phase | Timeline | Key Metric | Target |
|---|---|---|---|
| **A: Strengthen Core** | Month 1 | User retention after first scan | >40% return within 7 days |
| **B: Connect Islands** | Month 2-3 | Users using BOTH search + contracts | >20% of paid users |
| **C: Draft Integration** | Month 4-5 | Drafts generated per user/month | >5 avg for Pro users |
| **D: Intelligence Layer** | Month 6-8 | Clause Risk Score engagement | >60% of users check scores |
| **E: Enterprise** | Month 9-12 | Firm deals closed | 3-5 firm subscriptions |

---

*This roadmap is a living document. Update monthly as priorities shift based on user feedback and Smriti Search development pace.*
