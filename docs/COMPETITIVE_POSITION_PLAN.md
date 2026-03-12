# ContraRed: Competitive Position Plan (4/10 to 10/10)

> Agent 10 Analysis | March 2026
> Current Score: 4/10 | Target: 10/10 by Q1 2027

---

## Executive Summary

ContraRed has a **working product** (rare at this stage) with a sharp India-first wedge and a Word Add-in that competitors lack. But the competitive position is fragile: no distribution channel, no moat, no social proof, and no integrations. The good news is that the Indian legal tech market is still in the "land grab" phase — Harvey has not localized, CoCounsel has no India play, and SpotDraft is CLM-focused (not redlining). There is a 12-18 month window to become the default contract review tool for Indian lawyers before Western players enter.

**The strategy**: Dominate India through AppSource distribution, playbook network effects, and deep Indian law specialization. Then expand.

---

## 1. Microsoft AppSource Listing

**Why this is the #1 priority**: AppSource is the largest distribution channel for Word Add-ins. Right now ContraRed requires manual sideloading or Netlify URL — a non-starter for enterprise. Listing on AppSource means:
- Discoverable by 1.4B+ Office users
- IT departments can approve and deploy centrally
- Credibility signal (Microsoft-validated)
- Free marketing via AppSource search

### 1.1 Certification Requirements

Microsoft's Office Add-in certification has specific technical and business requirements:

**Technical Requirements:**
| Requirement | Current Status | Action Needed |
|---|---|---|
| Manifest validation (schema v1.1+) | DONE (manifest.xml validates) | None |
| HTTPS everywhere | DONE (Netlify HTTPS) | None |
| WordApi 1.3+ requirement | DONE (manifest specifies 1.3) | None |
| No external scripts from CDN (except office.js) | VERIFY | Audit webpack bundle for external CDN loads |
| Privacy policy URL | MISSING | Create privacy policy page |
| Support URL | PARTIAL (points to Netlify root) | Create dedicated support page |
| Content does not include advertising | OK | None |
| Works offline gracefully | MISSING | Add offline error state |
| Responsive taskpane (320px min width) | VERIFY | Test at 320px width |
| No use of `eval()` or dynamic code injection | VERIFY | Audit codebase |
| SSL/TLS 1.2+ for all API calls | DONE (Render enforces TLS 1.2) | None |
| Age rating / content declaration | MISSING | Fill out during submission |

**Business Requirements:**
| Requirement | Status | Action |
|---|---|---|
| Microsoft Partner Center account | MISSING | Register at partner.microsoft.com ($19 one-time fee) |
| Publisher display name verification | MISSING | Verify "ContraRed" or company entity name |
| Valid contact email (not @gmail) | MISSING | Set up hello@contrared.ai or similar domain email |
| Logo assets (300x300, 96x96, 48x48) | PARTIAL | Create all required sizes |
| Screenshots (1280x800 or 1366x768) | MISSING | Capture 3-5 screenshots of add-in in action |
| Short + long description | MISSING | Write AppSource listing copy |
| End-user license agreement (EULA) | MISSING | Draft EULA |

### 1.2 Submission Process

```
Step 1: Register on Microsoft Partner Center (partner.microsoft.com)
        - $19 one-time fee, personal or company account
        - Verify identity (takes 2-5 business days)

Step 2: Prepare manifest.xml for production
        - Ensure <Id> is a unique GUID (already have one: c7d8e9f0-...)
        - <Version> matches what you submit (currently 2.0.0.0)
        - <SupportUrl> points to a real support page
        - <AppDomains> includes all domains the add-in communicates with
        - Add <HighResolutionIconUrl> (64x64 PNG)

Step 3: Create marketing assets
        - App icon: 300x300 PNG (AppSource listing)
        - Screenshots: minimum 3, showing key workflows
        - Video (optional but highly recommended): 30-60s demo

Step 4: Submit via Partner Center
        - Upload manifest
        - Fill out app details, privacy policy, EULA
        - Select markets (India first, then Global)
        - Select pricing (Free with in-app subscription)

Step 5: Certification review (3-7 business days typically)
        - Microsoft tests: loads correctly, no crashes, privacy compliant
        - May get rejection with specific feedback — plan for 1-2 rounds

Step 6: Post-listing optimization
        - Respond to reviews
        - A/B test description and screenshots
        - Track install-to-activation conversion
```

### 1.3 Manifest Changes Needed

The current manifest at `ContraRed-PoC/manifest.xml` needs these additions for AppSource:

```xml
<!-- Add these elements -->
<HighResolutionIconUrl DefaultValue="https://contrared-addin.netlify.app/assets/logo-64.png"/>

<!-- Add Requirements section for minimum Office version -->
<Requirements>
  <Sets>
    <Set Name="WordApi" MinVersion="1.3"/>
  </Sets>
</Requirements>

<!-- Add FormSettings for different form factors -->
<FormSettings>
  <Form xsi:type="ItemRead">
    <DesktopSettings>
      <SourceLocation DefaultValue="https://contrared-addin.netlify.app/taskpane.html"/>
      <RequestedHeight>450</RequestedHeight>
    </DesktopSettings>
  </Form>
</FormSettings>
```

### 1.4 Timeline and Effort

| Task | Effort | Owner |
|---|---|---|
| Register Partner Center + verify identity | 1 hour + 2-5 day wait | Founder |
| Create privacy policy + support pages | 2 days | Founder |
| Create logo assets (all sizes) | 1 day | Designer/Founder |
| Capture screenshots + record demo video | 1 day | Founder |
| Audit codebase for certification compliance | 2 days | Dev |
| Add offline graceful degradation | 1 day | Dev |
| Write AppSource listing copy | 1 day | Founder |
| Draft EULA | 1 day | Founder (use template) |
| Submit + handle certification rounds | 1-2 weeks | Founder |
| **Total** | **~3 weeks** | |

**Complexity: M (Medium)**

---

## 2. India Market Strategy: First 10 Customers

### 2.1 Why India, Why Now

**The Window:**
- Harvey AI: US-focused, $5K/seat/month, no Indian law training, no localization plans announced
- CoCounsel (Thomson Reuters): Westlaw-dependent, Indian case law coverage is thin
- SpotDraft: Indian company but CLM-focused (workflow/signature), not AI redlining
- Kira Systems (Litera): Document review for M&A due diligence, not contract negotiation
- No competitor has: Indian law playbooks + Word Add-in + DPDP Act expertise

**India Legal Market Size:**
- 1.7M+ registered advocates (Bar Council of India)
- ~70,000 law firms (mostly 1-5 lawyers)
- Top 100 firms: 50-500+ lawyers each (Tier 1: AZB, Cyril Amarchand, Khaitan, Trilegal, Shardul Amarchand, JSA)
- Corporate legal departments: every company with >Rs 100Cr revenue has in-house counsel
- Legal tech spend growing 25-30% YoY in India

### 2.2 Ideal Customer Profile (ICP) for First 10

**Primary ICP: Mid-size Indian law firms (10-50 lawyers)**
- Why: Big enough to have contract volume, small enough to adopt new tools fast
- Contract volume: 50-200 contracts/month
- Pain: Associates spend 60-70% of time on contract review
- Budget: Rs 50K-2L/month for tech tools
- Decision maker: Managing Partner or Head of Corporate/M&A practice
- Examples: Argus Partners, Lakshmikumaran & Sridharan, Economic Laws Practice, IndusLaw, Nishith Desai Associates (mid-tier practices)

**Secondary ICP: In-house legal teams at Indian startups/scaleups**
- Why: Tech-savvy, high contract velocity, price-sensitive (ContraRed fits budget)
- Contract volume: 20-100 contracts/month (vendor, employment, NDA)
- Pain: 1-3 person legal team drowning in routine contracts
- Budget: Rs 20K-50K/month
- Decision maker: General Counsel or Head of Legal
- Examples: Razorpay, Zerodha, CRED, Meesho, PhonePe legal teams

**Tertiary ICP: Individual practitioners / boutique firms**
- Why: Easy to onboard, become evangelists, low support burden
- Contract volume: 5-20 contracts/month
- Pain: No associates to delegate to, doing everything themselves
- Budget: Rs 2K-10K/month
- Examples: Independent corporate lawyers, contract specialists on LinkedIn

### 2.3 Pricing for India

**Current global pricing will not work in India.** The market expects:
- Free tier that is actually usable (not just 5 scans)
- Monthly pricing in INR
- No annual lock-in initially
- Payment via UPI/Razorpay (already integrated)

**Proposed India Pricing:**

| Tier | Price (INR/month) | Price (USD equiv) | Scans/month | Features |
|---|---|---|---|---|
| **Free** | Rs 0 | $0 | 10 scans | Basic AI scan, 3 playbooks, no export |
| **Solo** | Rs 1,999 | ~$24 | 50 scans | All playbooks, clause library, export, research |
| **Professional** | Rs 4,999 | ~$60 | 200 scans | + Compare, Generate, Templates, Priority support |
| **Team** | Rs 14,999 | ~$180 | 500 scans | + 5 seats, Analytics, Custom playbooks, Audit logs |
| **Enterprise** | Custom | Custom | Unlimited | + SSO, API, ZDR, White-label, Dedicated support |

**Why these numbers:**
- SpotDraft charges Rs 5-15K/month for CLM (workflow, not AI)
- Harvey charges $500/seat/month (US pricing, not India-viable)
- Indian SaaS median: Rs 2-5K/month for professional tools
- The Solo tier at Rs 1,999 is an impulse buy for a lawyer billing Rs 5-15K/hour
- ROI pitch: "Save 10 hours/month of associate time = Rs 50K-1.5L value for Rs 5K"

**Annual Discount:** 20% off (2 months free) to improve retention

### 2.4 Customer Acquisition: First 10

**Channel 1: Direct outreach via LinkedIn (Weeks 1-4)**
- Target: 50 Managing Partners and GCs at ICP firms
- Message: "We built an AI that does contract redlining inside Word. It knows Indian Contract Act, DPDP 2023, and generates Track Changes. Free to try."
- Offer: 30-day free Professional trial (no credit card)
- Goal: 20 trials, 5 paying customers
- Cost: Rs 0 (founder time only)

**Channel 2: Indian legal tech communities (Weeks 2-6)**
- Legit.quest (Indian legal tech newsletter)
- Bar & Bench (Indian legal news — sponsored post Rs 50-75K)
- LiveLaw (Indian legal news)
- NASSCOM Legal Tech meetups
- BHive / LegalTech India WhatsApp groups
- Post on LinkedIn about "How AI handles Section 27 Indian Contract Act non-compete clauses" — demonstrate domain expertise
- Goal: 200 signups, 3 paying customers

**Channel 3: Law school partnerships (Weeks 4-8)**
- NLUs (National Law Universities): NLSIU Bangalore, NALSAR Hyderabad, NLU Delhi, WBNUJS Kolkata
- Offer: Free access for students + faculty
- Why: Students become associates at target firms, bring the tool with them
- Run a "Contract Redlining with AI" workshop at 2-3 NLUs
- Goal: 500 student signups, 2 firm trials from faculty referrals

**Channel 4: Conference presence (Month 2-3)**
- ILTA (India Legal Technology Association) events
- CII Legal & Regulatory summit
- FICCI Legal Conclave
- Not as a sponsor (too expensive) — attend, demo in hallway conversations
- Goal: 10 warm leads, 2 paying customers

### 2.5 Indian Law Specialization (The Wedge)

What ContraRed already knows that no competitor does:

| Indian Law Area | ContraRed Coverage | Competitor Coverage |
|---|---|---|
| Section 27 Indian Contract Act (non-compete) | DEEP — flags non-competes as unenforceable, suggests non-solicitation instead | None |
| DPDP Act 2023 | BUILT-IN — DPA playbook, cross-border transfer flags | None (too new) |
| Indian Arbitration Act | In playbooks — prefers arbitration over litigation | Generic |
| Stamp duty implications | NOT YET | None |
| FEMA compliance for cross-border contracts | NOT YET | None |
| Companies Act 2013 (related party transactions) | NOT YET | None |
| GST implications in service agreements | NOT YET | None |
| RBI regulations (fintech contracts) | NOT YET | None |

**Indian Law Features to Add (sorted by customer impact):**

1. **FEMA Compliance Scanner** (XL effort, HIGH impact)
   - Flag contracts with foreign parties that may need RBI approval
   - Check: FDI limits, current account vs capital account transactions
   - Why: Every cross-border deal needs FEMA review, currently done manually

2. **Stamp Duty Calculator** (M effort, MEDIUM impact)
   - Based on state + contract type + value, estimate stamp duty
   - Show: "This agreement in Maharashtra requires Rs X stamp duty"
   - Why: Unstamped agreements are inadmissible as evidence (Indian Evidence Act)

3. **GST Clause Checker** (S effort, MEDIUM impact)
   - Flag if service agreements missing GST provisions
   - Check: reverse charge applicability, place of supply rules
   - Why: Incorrect GST treatment = penalties

4. **RBI Circular Tracker** (L effort, HIGH impact for fintech clients)
   - When scanning fintech/lending/payment contracts, check against recent RBI circulars
   - Why: RBI issues 200+ circulars/year, fintech compliance is a nightmare

**Complexity: L (Large) — the market strategy is ongoing, not a one-time effort**

---

## 3. Integration Ecosystem

### 3.1 Integration Priority Matrix

```
HIGH VALUE TO CUSTOMERS
    |
    |  [1] DocuSign        [2] iManage
    |  (e-signature)       (DMS - Tier 1 firms)
    |
    |  [3] SpotDraft       [4] NetDocuments
    |  (CLM - Indian)      (DMS - global firms)
    |
    |  [5] Adobe Sign      [6] Ironclad
    |  (e-signature alt)   (CLM - US-focused)
    |
    |  [7] Leegality       [8] SharePoint
    |  (Indian e-sign)     (DMS - SMB)
    |
LOW |__________________________________ HIGH EFFORT
```

### 3.2 Phase 1 Integrations (Q2 2026)

**3.2.1 DocuSign Integration (M effort)**

Flow: Contract reviewed in ContraRed (Word) --> finalized --> send for signature via DocuSign directly from add-in.

Technical approach:
- Use DocuSign eSignature REST API v2.1
- OAuth 2.0 authorization code grant (user authenticates once)
- New endpoint: `POST /integrations/docusign/send`
  - Input: document_id (from ContraRed), signers (name, email, role)
  - Creates envelope in DocuSign, uploads the DOCX
  - Returns signing URL
- Word Add-in gets "Send for Signature" button after scan completion
- Webhook: `POST /integrations/docusign/webhook` for status updates

Backend changes needed:
```
backend/app/api/v1/endpoints/integrations.py  (new file)
backend/app/services/docusign_service.py       (new file)
backend/app/models/integration.py              (new model: IntegrationConnection)
backend/migrations/008_integrations.sql        (new table)
```

Config additions:
```python
# In config.py
DOCUSIGN_INTEGRATION_KEY: str = ""
DOCUSIGN_SECRET_KEY: str = ""
DOCUSIGN_BASE_URL: str = "https://demo.docusign.net/restapi"  # production: account.docusign.com
```

**3.2.2 Leegality Integration (S effort)**

Why Leegality first (alongside DocuSign): Leegality is the dominant e-signature platform in India (Aadhaar-based signing, legally valid under IT Act 2000). Indian customers will want this over DocuSign.

Flow: Same as DocuSign but using Leegality API.
- Leegality has a simpler API (REST + API key auth)
- Supports: Aadhaar e-sign, DSC, electronic signature
- New endpoint: `POST /integrations/leegality/send`

### 3.3 Phase 2 Integrations (Q3 2026)

**3.3.1 iManage Integration (L effort)**

Why: Every Tier 1 Indian law firm uses iManage for document management. If ContraRed cannot pull contracts from iManage and save results back, enterprise adoption is blocked.

Flow: Browse iManage workspace from Word Add-in --> select contract --> analyze --> save redlined version back to iManage.

Technical approach:
- iManage Work REST API (Cloud) or iManage Work Server API (on-prem)
- OAuth 2.0 for cloud, NTLM/Windows auth for on-prem
- Need to become an iManage Technology Partner (apply at imanage.com/partners)
- Partner program gives API access + test environment

**3.3.2 SpotDraft Integration (M effort)**

Why: SpotDraft is the most popular Indian CLM. Many target customers already use SpotDraft for contract lifecycle. ContraRed + SpotDraft = "review inside Word, manage in SpotDraft."

Flow: SpotDraft contract --> open in Word --> ContraRed scans --> results pushed back to SpotDraft as metadata/comments.

Technical approach:
- SpotDraft has a public API (api.spotdraft.com)
- Webhook-based: SpotDraft fires webhook when contract needs review
- ContraRed processes and returns risk assessment via API callback
- Could also be a SpotDraft "App" in their marketplace

### 3.4 Phase 3 Integrations (Q4 2026)

- **SharePoint/OneDrive**: Pull contracts from SharePoint document libraries (Microsoft Graph API)
- **NetDocuments**: REST API integration for global firms
- **Ironclad**: Webhook integration for US expansion
- **Adobe Sign**: e-signature alternative
- **Slack/Teams notifications**: "Contract X has 3 RED risks — review needed"

### 3.5 Integration Architecture

```
                    ContraRed API
                         |
              ┌──────────┼──────────┐
              |          |          |
         /integrations  /webhooks  /api/v1
              |          |          |
    ┌─────────┼─────────┐|         (existing endpoints)
    |         |         | |
 DocuSign  Leegality  iManage  SpotDraft
 Service   Service    Service  Service
    |         |         | |
    └─────────┼─────────┘|
              |          |
    IntegrationConnection model
    (user_id, provider, access_token,
     refresh_token, expires_at, metadata)
```

New database table:
```sql
CREATE TABLE integration_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id),
    provider VARCHAR(50) NOT NULL,          -- 'docusign', 'leegality', 'imanage', 'spotdraft'
    access_token TEXT,                       -- encrypted
    refresh_token TEXT,                      -- encrypted
    token_expires_at TIMESTAMPTZ,
    external_account_id VARCHAR(255),        -- provider's account/user ID
    metadata JSONB DEFAULT '{}',             -- provider-specific config
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);
```

**Complexity: XL (Extra Large) — ecosystem building is a multi-quarter effort**

---

## 4. Playbook Marketplace

### 4.1 Vision

The playbook is ContraRed's **moat**. A firm that has spent weeks customizing playbooks with 50+ rules, firm-specific clause language, and deal-breaker thresholds will never switch to a competitor. But to make the playbook a moat, it needs to be:

1. **Easy to create** (current: OK, wizard exists)
2. **Easy to share** (current: within org only)
3. **Valuable enough to accumulate** (current: 10 defaults, no community)
4. **A marketplace** where the best playbooks surface

### 4.2 Marketplace Tiers

**Tier 1: Community Playbooks (Free)**
- Any user can publish their playbook to the community
- Moderated: ContraRed team reviews before publishing
- Discoverable: search by category, jurisdiction, contract type
- Stats: download count, rating, "used in X scans"
- Examples: "DPDP Act DPA — reviewed by Privacy Law firm", "Startup-friendly MSA"

**Tier 2: Expert Playbooks (Paid)**
- Created by verified legal experts or law firms
- Revenue share: 70% creator / 30% ContraRed
- Price: Rs 999-4,999 per playbook
- Includes: detailed documentation, quarterly updates, support
- Examples: "M&A Due Diligence Checklist by [Top Firm]", "Fintech Regulatory Playbook"

**Tier 3: Firm-Private Playbooks (Team/Enterprise)**
- Shared within organization only
- Version controlled (already have versioning)
- Audit trail (who changed what rule, when)
- Role-based access (already have admin/user roles)

### 4.3 Technical Implementation

**New endpoints needed:**

```
POST   /playbooks/marketplace/publish          -- publish to community
GET    /playbooks/marketplace                    -- browse marketplace
GET    /playbooks/marketplace/{id}               -- view details + preview
POST   /playbooks/marketplace/{id}/install       -- copy to user's playbooks
POST   /playbooks/marketplace/{id}/rate          -- rate (1-5 stars)
GET    /playbooks/marketplace/categories         -- list categories
GET    /playbooks/marketplace/popular            -- top downloaded
GET    /playbooks/marketplace/new                -- recently published
```

**New database additions:**

```sql
-- Add to playbooks table
ALTER TABLE playbooks ADD COLUMN marketplace_status VARCHAR(20) DEFAULT 'private';
    -- 'private', 'pending_review', 'published', 'expert', 'rejected'
ALTER TABLE playbooks ADD COLUMN marketplace_price INTEGER DEFAULT 0;  -- in paise (INR)
ALTER TABLE playbooks ADD COLUMN download_count INTEGER DEFAULT 0;
ALTER TABLE playbooks ADD COLUMN avg_rating FLOAT DEFAULT 0;
ALTER TABLE playbooks ADD COLUMN rating_count INTEGER DEFAULT 0;
ALTER TABLE playbooks ADD COLUMN forked_from UUID REFERENCES playbooks(id);
ALTER TABLE playbooks ADD COLUMN author_display_name VARCHAR(200);
ALTER TABLE playbooks ADD COLUMN marketplace_description TEXT;

-- Playbook ratings
CREATE TABLE playbook_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(playbook_id, user_id)
);

-- Playbook installs (tracking)
CREATE TABLE playbook_installs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_playbook_id UUID NOT NULL REFERENCES playbooks(id),
    installed_playbook_id UUID NOT NULL REFERENCES playbooks(id),
    user_id UUID NOT NULL REFERENCES users(id),
    installed_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Dashboard UI: New "Marketplace" page**
- Grid of playbook cards with: name, author, category, rating, downloads, price
- Filter: category, jurisdiction, free/paid, rating
- Preview: see rules (names only, not full detection patterns — protect IP)
- Install: one-click copy to user's playbooks
- Publish flow: select playbook --> add description --> submit for review

### 4.4 Monetization Math

Assumptions (Year 1):
- 50 community playbooks published
- 10 expert playbooks at avg Rs 2,500
- 500 total installs of paid playbooks
- Revenue: 500 x Rs 2,500 x 0.30 = Rs 3,75,000 (~$4,500) — modest but builds ecosystem

The real value is **retention**: users with 5+ installed playbooks have ~3x higher retention.

### 4.5 Network Effects

```
More users --> More playbooks created --> Better playbooks available
    ^                                            |
    |                                            v
    +---- More users attracted by playbook quality ----+
```

This is the same flywheel that made Notion templates and Figma Community valuable.

**Complexity: L (Large)**

---

## 5. API Strategy

### 5.1 Public API Design

ContraRed already has a well-structured internal API (`/api/v1/`). The public API wraps the same endpoints with:
- API key authentication (instead of JWT)
- Rate limiting per key
- Usage tracking and billing
- OpenAPI/Swagger documentation
- Webhook support for async operations

### 5.2 Public API Endpoints

```
Authentication:
  X-API-Key header (issued per organization)

Core Analysis:
  POST /api/v1/public/analyze
    Input: { text: string, playbook_id?: string }
    Output: { risks: [...], summary: string, scan_id: string }
    Rate: 10 req/min (Pro), 100 req/min (Enterprise)

  POST /api/v1/public/analyze-async
    Input: same as above
    Output: { job_id: string, status_url: string }
    Webhook: POST to callback_url when complete

  GET /api/v1/public/analyze/{scan_id}
    Output: full scan results

Clause Operations:
  POST /api/v1/public/generate-clause
    Input: { clause_type: string, context?: string, jurisdiction?: string }
    Output: { clause_text: string, reasoning: string }

  POST /api/v1/public/research-clause
    Input: { clause_text: string, clause_type?: string }
    Output: { cases: [...], legal_principle: string }

Comparison:
  POST /api/v1/public/compare
    Input: { text_a: string, text_b: string, playbook_id?: string }
    Output: { changes: [...], summary: object }

Playbooks (read-only for API users):
  GET /api/v1/public/playbooks
  GET /api/v1/public/playbooks/{id}

Usage:
  GET /api/v1/public/usage
    Output: { calls_used: int, calls_limit: int, period_end: string }
```

### 5.3 API Key Management

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL,          -- SHA-256 of actual key
    key_prefix VARCHAR(12) NOT NULL,        -- "cr_live_abc..." for display
    name VARCHAR(200) NOT NULL,             -- "Production", "Staging"
    permissions JSONB DEFAULT '["analyze"]', -- scope limiting
    rate_limit_per_minute INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ                   -- optional expiry
);

CREATE TABLE api_usage_logs (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    endpoint VARCHAR(200) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_api_usage_key_date ON api_usage_logs(api_key_id, created_at);
```

### 5.4 Webhook System

```python
# Webhook event types
WEBHOOK_EVENTS = [
    "scan.completed",       # Analysis finished
    "scan.failed",          # Analysis failed
    "risk.high_detected",   # RED risk found (for alerting)
    "comparison.completed", # Diff analysis done
]

# Webhook delivery
# - POST to registered URL with HMAC-SHA256 signature
# - Retry: 3 attempts with exponential backoff (1s, 10s, 60s)
# - Payload includes event_type, timestamp, data
```

### 5.5 API Documentation

- Auto-generated from FastAPI's OpenAPI spec (already available at `/docs`)
- Add: code examples in Python, Node.js, cURL
- Add: "Getting Started" guide
- Add: API changelog
- Host at: `docs.contrared.ai` or `contrared.ai/docs/api`

### 5.6 API Pricing

| Tier | Calls/month | Price |
|---|---|---|
| Free | 100 | Rs 0 |
| Starter | 1,000 | Rs 4,999/mo |
| Growth | 10,000 | Rs 14,999/mo |
| Enterprise | Unlimited | Custom |

Overage: Rs 5 per additional call (Starter/Growth)

**Complexity: M (Medium) — backend architecture already supports this cleanly**

---

## 6. Content and Brand Strategy

### 6.1 Thought Leadership Content Calendar

**Goal**: Become the "obvious expert" in Indian contract AI. When someone searches "AI contract review India", ContraRed should appear.

**Weekly cadence:**

| Day | Content Type | Channel | Topic Examples |
|---|---|---|---|
| Monday | LinkedIn post | LinkedIn | "One clause insight" — e.g., "Why non-competes are unenforceable in India (Section 27)" |
| Wednesday | Blog post | contrared.ai/blog | Deep dive — "DPDP Act 2023: 5 clauses every DPA must have" |
| Friday | LinkedIn post | LinkedIn | Product update or customer insight |
| Bi-weekly | Webinar/Video | YouTube + LinkedIn Live | "Live contract review with AI" — scan a real (anonymized) contract |

**Content Pillars (first 3 months):**

1. **Indian Contract Law Decoded** (for lawyers)
   - "The complete guide to limitation of liability in Indian MSAs"
   - "Stamp duty by state: What your agreement actually needs"
   - "FEMA compliance for cross-border SaaS agreements"
   - "How Indian courts treat arbitration clauses (5 recent SC decisions)"

2. **AI in Legal Practice** (for decision-makers)
   - "How AI redlining saves 15 hours/week for associates"
   - "AI vs. human: Comparing contract review accuracy"
   - "The ROI of AI contract review for a 20-lawyer firm"

3. **Product-Led Content** (for users)
   - "How to create a custom playbook for your firm"
   - "5 things ContraRed catches that manual review misses"
   - "From scan to signed: Contract review workflow with ContraRed"

4. **Community Building** (for ecosystem)
   - Guest posts from lawyer users
   - "Playbook of the month" — spotlight community playbooks
   - Interview series: "How [Firm] modernized their contract practice"

### 6.2 Case Studies (First 3)

**Case Study Format:**
```
Title: How [Firm/Company] Reduced Contract Review Time by X%

Challenge: [Specific pain point]
Solution: [How they use ContraRed]
Results:
  - X% faster contract review
  - Y hours saved per month
  - Z risks caught that manual review missed
Quote: "[Testimonial from user]"
```

**Target first 3 case studies from:**
1. A mid-size law firm (corporate practice)
2. A startup legal team
3. An individual practitioner

Offer: 3 months free Professional tier in exchange for a case study + testimonial.

### 6.3 SEO Strategy

**Target keywords (India-specific):**
- "contract review AI India" (low competition, high intent)
- "contract redlining tool" (medium competition)
- "AI legal assistant India" (growing search volume)
- "DPDP Act compliance tool" (very low competition, highly relevant)
- "Word add-in contract review" (low competition, exact match)
- "legal tech India" (informational, build authority)

**Technical SEO:**
- Create marketing site at contrared.ai (separate from app)
- Blog with schema markup for articles
- Landing pages per use case (NDA review, MSA review, DPA review)
- Landing page per integration (ContraRed + DocuSign, ContraRed + SpotDraft)

### 6.4 Community Presence

- **Legal tech India Slack/Discord**: Create or join
- **Reddit**: r/IndianLawyers, r/LegalTech (post thoughtfully, not spammy)
- **Twitter/X**: Follow Indian legal journalists, engage with legal tech discourse
- **Product Hunt**: Launch when AppSource listing is live

**Complexity: L (Large) — content is ongoing, not a project**

---

## 7. Partner Channel

### 7.1 Law Firm Technology Consultants

**Key firms in India that advise law firms on technology:**

| Consultant Type | Examples | How to Partner |
|---|---|---|
| Legal tech consultants | Teres Consulting, Vahura (legal recruitment + tech advisory) | Referral commission (15-20%) |
| IT consulting for law firms | Wipro Legal (legal BPO), TCS Legal | Integration partnership |
| Big 4 advisory | Deloitte Legal, EY Law, KPMG Legal | Technology alliance — they recommend tools to clients |
| Legal operations consultants | Independent consultants on LinkedIn | Affiliate program |

### 7.2 Partnership Models

**Model 1: Referral Partner (Simplest)**
- Partner refers customer, gets 15-20% of first year revenue
- No integration needed
- Agreement: simple 2-page referral agreement
- Track via: unique referral link + coupon code
- Target: Legal tech consultants, independent advisors

**Model 2: Technology Alliance (Medium)**
- Joint solution with CLM/DMS vendors
- "Works with SpotDraft" / "Works with iManage"
- Co-marketing: joint webinars, blog posts
- Listed in partner's marketplace/integrations page
- Target: SpotDraft, Leegality

**Model 3: Reseller/White-Label (Enterprise)**
- Big 4 resells ContraRed under their brand (or co-branded)
- ContraRed provides: API + customization + support
- Partner provides: sales, customer relationship, industry expertise
- Revenue: 50-60% to ContraRed, 40-50% to partner
- Target: Deloitte Legal, EY Law (18+ months out)

### 7.3 Big 4 Partnership Path

Getting a Big 4 partnership is a 12-18 month process:

```
Month 1-3:  Build relationship
            - Attend Deloitte/EY legal tech events
            - Connect with their Legal Advisory practice leads on LinkedIn
            - Offer a free pilot for one of their legal advisory projects

Month 4-6:  Prove value
            - Run pilot with 1-2 of their clients
            - Generate case study with ROI metrics
            - Get internal champion (usually a Senior Manager or Director)

Month 7-9:  Formal evaluation
            - Big 4 runs security assessment (need SOC 2 by this point)
            - Technical integration evaluation
            - Commercial terms negotiation

Month 10-12: Partnership agreement
            - Signed partnership
            - Joint go-to-market plan
            - Training for their consultants
```

### 7.4 NLU/Law School Partnerships

- **Objective**: Build brand awareness among future lawyers
- **Offer**: Free access for all students + faculty
- **Ask**: Logo on law school tech partner page, guest lecture slots
- **Long game**: When these students join firms, they request ContraRed

**Complexity: L (Large)**

---

## 8. Moat Building

### 8.1 Switching Cost Analysis

| Moat Type | Current State | Target State | How to Build |
|---|---|---|---|
| **Playbook investment** | 10 default playbooks | 50+ custom playbooks per firm, irreplaceable | Make playbooks richer: case law links, clause alternatives, negotiation history |
| **Clause library** | Basic CRUD | 500+ saved clauses per firm, firm's institutional memory | Auto-suggest saving clauses after edits, version tracking |
| **Scan history** | Basic metadata | Full audit trail required for compliance | Make scan history a compliance requirement (audit logs are already built) |
| **Team collaboration** | Basic team features | Workflows: assign, review, approve | Add review workflows that only work in ContraRed |
| **Integration depth** | None | Deep CLM+DMS+e-sign integration | Once connected, ripping out is painful |
| **Training data** | Generic | Firm-specific AI tuned to their drafting style | Use scan history to learn firm preferences (later) |

### 8.2 Network Effects

**Direct network effects (within a firm):**
- More lawyers using ContraRed --> shared playbooks get better --> more value per user
- Junior associates learn from playbooks --> institutional knowledge preserved

**Indirect network effects (cross-firm via marketplace):**
- More firms --> more community playbooks --> better playbook marketplace --> more firms
- More scans --> better AI training data --> more accurate analysis --> more scans

**Data network effects (longest-term):**
- More contracts scanned --> better understanding of market norms
- "82% of MSAs in India cap liability at 12 months fees" — this insight is only possible with scale
- Anonymized benchmarking: "Your indemnity cap is more aggressive than 70% of similar contracts"

### 8.3 Moat Priority Actions

1. **Make playbooks stickier** (Month 1-2): Add version history, fork tracking, usage stats per rule
2. **Auto-save clauses** (Month 2): After every "Fix" action, prompt "Save this clause to your library?"
3. **Firm-specific AI learning** (Month 6+): Use a firm's scan history to prioritize which clauses to flag
4. **Benchmarking data** (Month 9+): "This clause deviates from market standard" — only possible at scale
5. **Compliance lock-in** (Month 6+): Audit trail + scan history becomes part of the firm's compliance infrastructure

**Complexity: XL (Extra Large) — moat building is the multi-year strategic play**

---

## 9. Product Differentiation: Feature Matrix

### 9.1 Competitive Feature Matrix (March 2026)

| Feature | ContraRed | Harvey AI | CoCounsel | SpotDraft | Kira/Litera |
|---|---|---|---|---|---|
| **Core** | | | | | |
| AI contract analysis | YES | YES | YES | Basic | YES (extraction) |
| Word Add-in (native) | **YES** | No (web only) | No (Westlaw UI) | No (own editor) | Partial |
| Track Changes redlines | **YES** | No | No | No | No |
| Indian law knowledge | **DEEP** | None | Minimal | Some | None |
| DPDP Act 2023 | **YES** | No | No | No | No |
| Custom playbooks | YES | No (prompt-based) | No (pre-built) | No | Yes (limited) |
| Clause library | YES | No | No | No | Yes |
| | | | | | |
| **Differentiators** | | | | | |
| AI clause generation | YES | Yes | Yes | No | No |
| Case law research | YES (AI) | Yes (real) | Yes (Westlaw) | No | No |
| Contract comparison | YES | No | No | Yes | Yes |
| Template library | YES | No | No | Yes | No |
| Firm analytics | YES | No | No | Yes | Yes |
| | | | | | |
| **Enterprise** | | | | | |
| Zero Data Retention | **YES** | Unknown | No | No | No |
| SOC 2 certified | No | Yes | Yes | Yes | Yes |
| On-premise option | No | No | No | No | Yes |
| SSO/SAML | No | Yes | Yes | Yes | Yes |
| API | Partial | Yes | No | Yes | Yes |
| | | | | | |
| **Ecosystem** | | | | | |
| CLM integration | No | No | No | Native | Yes |
| DMS integration | No | No | Westlaw | No | Yes |
| E-signature | No | No | No | Yes | No |
| Marketplace | No | No | No | No | No |
| | | | | | |
| **Pricing** | | | | | |
| Starting price | Rs 1,999/mo | $500/seat/mo | Westlaw bundle | Rs 5,000/mo | Custom |
| Free tier | Yes (10 scans) | No | No | No | No |
| India pricing | **Yes (INR)** | No | No | Yes (INR) | No |

### 9.2 Positioning Statement

**Current (weak)**: "AI-powered contract redlining"
**Target (strong)**: "The only AI contract reviewer built for Indian law, inside Microsoft Word"

**Why this works:**
- "only" — creates category exclusivity
- "Indian law" — instant relevance for the target market
- "inside Microsoft Word" — where lawyers actually work (not another tab/app)

### 9.3 Key Differentiators to Protect

1. **Word-native Track Changes**: No competitor applies actual OOXML Track Changes. This is technically hard to replicate.
2. **Indian law playbooks**: 10 default playbooks with 106 rules grounded in Indian statutes. Competitors would need 6+ months to build this.
3. **Playbook customization depth**: Detection patterns, primary/fallback positions, suggested language, deal-breaker flags. This is the most granular playbook system in the market.
4. **Zero Data Retention**: Enterprise differentiator. Contracts are processed in RAM, never stored. Critical for law firms handling M&A data.
5. **Price**: 10-50x cheaper than Harvey/CoCounsel. For the Indian market, this is not just a feature — it is market access.

**Complexity: M (Medium) — positioning is a strategic decision, not a build**

---

## 10. Growth Metrics

### 10.1 Core Metrics Dashboard

**Acquisition Metrics:**
| Metric | Current | Month 3 Target | Month 6 Target | Month 12 Target |
|---|---|---|---|---|
| Registered users | ~5 (team only) | 200 | 1,000 | 5,000 |
| AppSource installs | 0 | 100 | 500 | 2,000 |
| Organic search traffic | 0 | 500/mo | 2,000/mo | 10,000/mo |
| LinkedIn followers | 0 | 500 | 2,000 | 5,000 |

**Activation Metrics:**
| Metric | Current | Target |
|---|---|---|
| Registration to first scan | Unknown | <5 minutes |
| First scan to second scan | Unknown | >40% within 7 days |
| Free to paid conversion | N/A | 5-8% (industry avg for freemium SaaS) |

**Engagement Metrics:**
| Metric | Target |
|---|---|
| Scans per active user/week | >3 |
| Playbook rules per paying user | >15 (created/customized) |
| Clauses saved per user | >5 |
| Feature breadth (% of features used) | >40% (scan + fix + export + at least 1 other) |

**Revenue Metrics:**
| Metric | Month 3 | Month 6 | Month 12 |
|---|---|---|---|
| MRR (INR) | Rs 30K | Rs 2L | Rs 10L |
| Paying customers | 5 | 25 | 100 |
| ARPU (INR) | Rs 6,000 | Rs 8,000 | Rs 10,000 |
| Churn rate (monthly) | <10% | <7% | <5% |
| LTV:CAC ratio | >3:1 | >4:1 | >5:1 |

**Competitive Position Metrics:**
| Metric | How to Track | Target |
|---|---|---|
| Share of voice (Indian legal tech) | LinkedIn mentions + search rankings | Top 3 for "contract review AI India" |
| AppSource ranking | Partner Center analytics | Top 10 in Legal category |
| Integration partners | Count of active integrations | 3 by Month 6, 6 by Month 12 |
| Community playbooks | Marketplace count | 50 by Month 12 |
| Reference customers | Named, quotable customers | 5 by Month 6, 15 by Month 12 |
| NPS score | In-app survey | >40 |

### 10.2 Tracking Infrastructure

What to build:
1. **Mixpanel or PostHog** (free tier) for product analytics
   - Track: page views, scan initiated, scan completed, fix applied, export downloaded
   - Funnel: register --> first scan --> second scan --> paid conversion
2. **Stripe/Razorpay dashboard** for revenue metrics (already have Razorpay)
3. **Google Search Console** for SEO metrics
4. **Simple admin dashboard** showing key metrics (extend existing Analytics page)

**Complexity: M (Medium)**

---

## 11. Go-to-Market Timeline

### Q2 2026 (April-June): "Foundation"

**Theme: Get listed, get first 10 customers, establish presence**

| Week | Action | Owner | Deliverable |
|---|---|---|---|
| W1-2 | AppSource submission prep | Dev + Founder | Privacy policy, screenshots, EULA, manifest updates |
| W3 | Submit to AppSource | Founder | Submission ID |
| W2-4 | LinkedIn content launch | Founder | 8 posts (2/week), first blog post |
| W3-6 | Direct outreach to 50 ICPs | Founder | 20 free trials started |
| W4-6 | AppSource certification (wait + iterate) | Dev | Listed on AppSource |
| W5-8 | First 5 paying customers | Founder | Rs 30K+ MRR |
| W6-8 | First case study | Founder | Published on website |
| W8-10 | DocuSign integration (basic) | Dev | "Send for Signature" working |
| W10-12 | Leegality integration | Dev | Indian e-sign working |
| W12 | Playbook marketplace v1 (community only) | Dev | Browse + install working |

**Key milestones by end of Q2:**
- AppSource listed
- 10 paying customers
- 2 integrations live (DocuSign + Leegality)
- 200+ registered users
- Rs 50K+ MRR

### Q3 2026 (July-September): "Scale"

**Theme: Integrations, marketplace, content engine**

| Month | Action | Deliverable |
|---|---|---|
| July | iManage integration development | Technical partnership applied, integration in progress |
| July | SpotDraft integration | Webhook-based integration live |
| August | Expert playbook marketplace launch | 5 paid playbooks from partner firms |
| August | Public API v1 launch | API docs live, 3 API customers |
| August | NLU partnerships (2 law schools) | Free access for 500+ students |
| September | First conference presence | Demo at ILTA India or CII Legal |
| September | SOC 2 Type 1 audit started | Auditor engaged |
| September | FEMA compliance scanner | New Indian law feature |

**Key milestones by end of Q3:**
- 4+ integrations
- Playbook marketplace with 20+ playbooks
- Public API with paying customers
- Rs 2L+ MRR
- 1,000+ registered users

### Q4 2026 (October-December): "Establish"

**Theme: Enterprise readiness, partnerships, Series A preparation**

| Month | Action | Deliverable |
|---|---|---|
| October | SOC 2 Type 1 certification | Certificate received |
| October | SSO/SAML implementation | Enterprise auth working |
| November | Big 4 pilot (1 firm) | Running with 1 Deloitte/EY client |
| November | White-label API | Large firm can embed ContraRed |
| December | Stamp duty calculator | New Indian law feature |
| December | Series A materials prep | Deck, metrics, pipeline |

**Key milestones by end of Q4:**
- SOC 2 Type 1 certified
- 1 Big 4 pilot in progress
- Rs 5L+ MRR
- 50+ paying customers
- 3,000+ registered users

### Q1 2027 (January-March): "Dominate India"

**Theme: Market leadership, raise Series A**

| Month | Action | Deliverable |
|---|---|---|
| January | AppSource featured placement (apply) | Increased visibility |
| January | Benchmarking feature | "Your clause vs. market standard" |
| February | Series A fundraise | Pitch to Indian VCs (Blume, Kalaari, Elevation) |
| February | 5 law school partnerships | 2,000+ student users |
| March | 100 paying customers | Rs 10L+ MRR |
| March | Smriti integration (if ready) | Unified search + contracts |

**Key milestones by end of Q1 2027:**
- Rs 10L+ MRR ($12K+)
- 100+ paying customers
- 5,000+ registered users
- Series A closed or in progress
- Recognized as #1 AI contract review tool in India

---

## 12. Success Criteria: What 10/10 Looks Like

### 12.1 Competitive Position Scorecard

| Dimension | 4/10 (Now) | 7/10 (6 months) | 10/10 (12 months) |
|---|---|---|---|
| **Distribution** | Manual sideload only | AppSource listed, 500+ installs | AppSource Top 10 Legal, 2000+ installs |
| **Market Position** | Unknown | Known in Indian legal tech circles | Default choice for contract AI in India |
| **Integrations** | 0 | 3 (DocuSign, Leegality, SpotDraft) | 6+ (add iManage, SharePoint, API) |
| **Playbook Ecosystem** | 10 default playbooks | 30+ community playbooks | 100+ playbooks, active marketplace |
| **Social Proof** | 0 case studies | 3 case studies | 10+ case studies, named logos |
| **Content/Brand** | No content | Weekly blog, 2K LinkedIn followers | Thought leader, 5K+ followers, conference speaker |
| **Partners** | 0 | 2 referral partners | Big 4 pilot, 5+ partners |
| **Enterprise Ready** | No SOC 2, no SSO | SOC 2 in progress | SOC 2 Type 1, SSO, on-prem option |
| **Indian Law Depth** | 10 playbooks, 3 statutes | FEMA + stamp duty + GST | Comprehensive Indian law coverage |
| **Pricing** | Not India-optimized | INR pricing live, 3 tiers | Proven pricing, <5% churn |
| **API** | Internal only | Public API v1 | API with paying customers |
| **Moat** | No switching costs | Playbook investment = 3-6 months per firm | Playbook + data + integration lock-in |

### 12.2 The 10/10 Definition

ContraRed at 10/10 competitive position means:

1. **Any Indian lawyer searching for contract AI finds ContraRed first** (AppSource, Google, LinkedIn)
2. **No competitor can match the India-specific depth** (playbooks, statutes, case law, pricing)
3. **Switching from ContraRed is painful** (playbooks, clause library, scan history, integrations)
4. **Enterprise buyers see ContraRed as safe** (SOC 2, ZDR, audit logs, SSO)
5. **The ecosystem is self-reinforcing** (marketplace playbooks, community content, partner referrals)
6. **Revenue proves the model** (Rs 10L+ MRR, >100 paying customers, <5% churn)
7. **Word Add-in is the unbeatable UX** (no competitor has Track Changes redlining)
8. **The team has expanded** (from founder to 5-8 people covering product, engineering, sales, content)

---

## 13. Complexity Summary

| Component | Complexity | Estimated Effort | Priority |
|---|---|---|---|
| 1. Microsoft AppSource | **M** | 3 weeks | P0 (do now) |
| 2. India Market Strategy | **L** | Ongoing | P0 (do now) |
| 3. Integration Ecosystem | **XL** | 6+ months | P1 (start Q2) |
| 4. Playbook Marketplace | **L** | 4-6 weeks build + ongoing | P1 (start Q2) |
| 5. API Strategy | **M** | 3-4 weeks | P2 (Q3) |
| 6. Content & Brand | **L** | Ongoing | P0 (start now) |
| 7. Partner Channel | **L** | Ongoing | P2 (Q3) |
| 8. Moat Building | **XL** | Multi-year | P1 (start now, never stop) |
| 9. Product Differentiation | **M** | Positioning exercise | P0 (do now) |
| 10. Growth Metrics | **M** | 2-3 weeks setup | P1 (Q2) |
| 11. GTM Timeline | N/A | Execution plan | P0 (follow the plan) |
| 12. SOC 2 Certification | **L** | 3-6 months | P1 (start Q3) |
| 13. SSO/SAML | **M** | 2-3 weeks | P2 (Q4) |

### Priority Legend
- **P0**: Start this week. Blocking everything else.
- **P1**: Start within 4 weeks. Critical for the 6-month milestone.
- **P2**: Start within 3 months. Required for 12-month target.

---

## Appendix A: Competitive Intelligence Sources

Monitor these regularly:

| Source | What to Track | Frequency |
|---|---|---|
| Harvey AI blog/LinkedIn | Product launches, India mentions | Weekly |
| CoCounsel/Westlaw news | India legal content expansion | Monthly |
| SpotDraft blog/Product Hunt | New features, AI additions | Weekly |
| Ironclad blog | AI features, international expansion | Monthly |
| LegalTech News (ALM) | Industry trends | Weekly |
| Bar & Bench | Indian legal tech coverage | Daily |
| Tracxn / Crunchbase | Funding rounds in Indian legal tech | Monthly |
| Microsoft AppSource Legal category | New competitors listing | Weekly |

## Appendix B: First Week Action Items

1. Register on Microsoft Partner Center (partner.microsoft.com)
2. Set up hello@contrared.ai email (use Google Workspace or Zoho — Rs 75/mo)
3. Write privacy policy (use a template generator, customize for DPDP Act)
4. Start LinkedIn posting (Monday: first "Indian law clause insight" post)
5. Create list of 50 target ICP contacts on LinkedIn
6. Set up Mixpanel/PostHog free account
7. Update pricing page to show INR pricing
8. Begin AppSource manifest preparation

---

*This document should be reviewed and updated monthly. The Indian legal tech market is moving fast — first mover advantage is real but only if you move.*
