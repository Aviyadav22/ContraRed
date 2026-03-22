# ContraRed Disconnected Functions

Functions that exist but are not called from any user-reachable code path.

## Backend Services

### 1. `AIService.suggest_fix_with_playbook()` — ai_service.py:483
**What it does:** Generates AI-suggested revisions aligned with playbook language/position. Enhanced version of `suggest_fix()` that incorporates playbook context.
**Where it should plug in:** Should be called from `POST /documents/generate-fix` when the user has a playbook selected. Currently `gemini_analyzer.generate_fix()` handles this flow but doesn't use this playbook-aware variant.
**Best guess:** Wire into `analyze_full_ai()` or `generate_fix()` endpoint in documents.py when playbook_id is provided.

### 2. `ClauseClassifier.classify_batch()` — clause_classifier.py
**What it does:** Classifies multiple clause snippets in bulk (batch version of `classify()`).
**Where it should plug in:** Could be used during Stage 2 of the analysis pipeline to classify all extracted clauses in a single batch call rather than one at a time.
**Best guess:** Wire into `_stage2_classification()` in analysis_pipeline.py for efficiency.

### 3. `get_playbook_by_industry()` — playbook_templates.py
**What it does:** Returns industry-specific playbook template (Tech/Healthcare/Finance/Legal).
**Where it should plug in:** Should be called from `POST /playbooks/templates/{template_id}/create` endpoint or from the template browsing UI.
**Best guess:** Wire into the playbook templates browse/create-from-template flow in playbooks.py.

### 4. `get_default_playbook_data()` — playbook_templates.py
**What it does:** Returns default playbook template data.
**Where it should plug in:** Should be called when creating new playbooks with default rules, or when seeding the database.
**Best guess:** Already used by seed scripts. May also be used during playbook creation if no template is selected.

### 5. `HallucinationGuard.get_requery_instruction()` — hallucination_guard.py
**What it does:** Generates an instruction for re-prompting the AI when a quote can't be verified.
**Where it should plug in:** Should be called in Stage 4 of the pipeline when `needs_requery()` returns True, to automatically re-prompt the AI with better anchoring.
**Best guess:** Wire into `_stage4_verification()` in analysis_pipeline.py as a recovery mechanism.

### 6. `normalize_for_search()` — text_normalizer.py
**What it does:** Aggressive text normalization for search comparison (lowercase + whitespace collapse).
**Where it should plug in:** Could be used by `findTextInDocument()` in taskpane.ts or by `HallucinationGuard.verify_quote()` for better matching.
**Best guess:** The hallucination guard and redline_implementer already use `normalize_text()`. This more aggressive variant might be useful for edge cases but isn't critical.

## Word Add-in API Methods (Not called from taskpane.ts)

These exist in api.ts but are dashboard-only features. Intentionally not wired in the add-in:
- `getCurrentUser()` — user info via cached `getUser()` instead
- `generateClause()` — no clause generation UI in add-in
- `getPlaybook()` / `updatePlaybook()` / `deletePlaybook()` — playbook management is dashboard-only
- `togglePlaybookPublish()` — dashboard-only
- `addRule()` / `updateRule()` / `deleteRule()` — rule CRUD is dashboard-only
- `listClauses()` / `createClause()` — clause library is dashboard-only

## Dashboard API Functions (Not called from any component)

### ForgotPassword.tsx gap
The component exists but uses a setTimeout stub instead of calling the backend `POST /auth/forgot-password` endpoint. The API function `forgotPassword()` needs to be created in client.ts and called from ForgotPassword.tsx.
