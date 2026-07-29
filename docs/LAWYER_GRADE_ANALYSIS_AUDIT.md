# ContraRed Lawyer-Grade Contract Analysis Audit

Date: 27 July 2026

## Executive verdict

The main quality problem was not simply the AI model. The selected playbook was not reliably controlling the review.

Before this audit, the deterministic classification stage ran the generic rule library but ignored the serialized rules from the selected playbook. The serializer also omitted the playbook's detection patterns. Later, the AI path could remove explicitly selected rules through a generic contract-type filter, and the fallback path could treat a semantic keyword candidate as a proven breach. Finally, two de-duplication steps could delete separate legal issues merely because they appeared in the same clause.

Those defects explain the observed pattern of incomplete, inconsistent, or legally inverted analysis: a good playbook could exist in the database and still not be faithfully evaluated.

The critical wiring and fidelity defects identified in this audit have been corrected. The system now produces an auditable playbook-coverage ledger, preserves distinct same-clause issues, respects the playbook's review side, blocks publication of structurally unusable playbooks, and exposes incomplete coverage to the user. This materially improves reliability, but no AI system should be represented as equivalent to final lawyer sign-off without a measured contract test set and verified legal sources.

## The flow a professional contract lawyer follows

1. **Establish the mandate.** Identify the client, the side represented, the deal objective, leverage, risk appetite, transaction value, counterparty type, governing law, deadline, and non-negotiables.
2. **Orient to the document.** Confirm contract type, parties, effective date, hierarchy, defined terms, incorporated documents, exhibits, order forms, schedules, and missing attachments.
3. **Build a clause and obligation inventory.** Locate each expected topic, identify omissions, and map duties, rights, remedies, exceptions, thresholds, time periods, and survival.
4. **Apply the playbook rule by rule.** For every applicable rule, record compliant, violation, missing, or not applicable; cite the source text; compare it with the preferred, acceptable, fallback, and walk-away positions.
5. **Issue-spot beyond the playbook.** Review legal enforceability, regulatory exposure, drafting ambiguity, operational feasibility, and unusual transaction-specific risks.
6. **Review interactions.** Test definitions and cross-references, liability-cap carve-outs, indemnity and defense mechanics, termination and transition, data and security obligations, payment and suspension, precedence, and inconsistent schedules.
7. **Verify authority and evidence.** Confirm that each quoted provision exists in the contract and that each statutory or case-law proposition is supported by a current, jurisdiction-appropriate source.
8. **Form a negotiation position.** Prioritize deal-breakers, required changes, fallback language, business-owner questions, and acceptable residual risk.
9. **Perform final quality control.** Confirm every playbook rule and material clause was reviewed, unresolved items are visible, redlines preserve document meaning, and no advice is stated from the wrong party's perspective.

## What the software was doing before the fixes

The product extracted text and document structure, detected defined terms and jurisdiction, ran a generic regex library, applied negotiation tiers and conditions, sent the full contract to Gemini in one large assessment call, verified quoted contract text, scored confidence, and returned redlines.

The important deviations from lawyer workflow were:

- The selected playbook's detection patterns were omitted from the rule dictionaries and never run during classification.
- Explicit playbook rules could be filtered out before the AI review based on a coarse contract-type mapping.
- There was no one-row-per-rule proof that the model assessed every selected playbook rule.
- Keyword hits for `ai_with_keywords` rules became violations during AI fallback even though those keywords were meant only to locate candidate text.
- Findings from different rules were removed when their text was identical or overlapping, even when they represented different legal issues.
- Cache entries ignored requested fields and returned mutable dictionaries, allowing one request's negotiation overrides to contaminate another request.
- The Word add-in defaulted silently to India and buyer; the dashboard also defaulted to buyer. A wrong represented side can invert indemnity, liability, termination, IP, and payment advice.
- Mutual and unilateral NDAs were not reliably disambiguated, and specialist DPA, healthcare, fintech, and IT-services packs were not all available for automatic selection.
- Custom clause concepts were collapsed to `unknown`, weakening rule identity, analytics, and stable AI matching.
- Statutory references requested from the model were discarded before reaching the user.
- Jurisdiction metadata was only retained when a regex risk happened to match.
- The file-upload endpoint used stale response fields and did not return the same legal audit metadata as text analysis.

## Corrections made

### Playbook fidelity

- Selected playbook patterns are serialized, safely compiled, and run in classification alongside the general issue-spotting library.
- Every explicitly selected playbook rule is sent to the AI. Contract type no longer silently removes lawyer-authored rules.
- Stable rule IDs are included in the prompt and response, so changing a display label does not disconnect deal-breaker or position metadata.
- The AI response now includes one ledger row per rule with `compliant`, `violation`, `missing`, or `not_applicable` status.
- The API calculates and returns playbook coverage. Incomplete coverage is shown in both the dashboard and Word add-in instead of being presented as a complete review.
- A ledger violation or missing item with exact evidence can recover a finding that the model omitted from its redline array; it still passes the quote-verification guard.
- Draft playbooks now have a quality endpoint and a publish gate. Keyword modes require usable patterns; AI modes require a risk description; deal-breakers must be red. The editor shows blockers and drafting recommendations before publication.

### False negatives and false positives

- Cross-rule de-duplication now removes duplicates only within the same stable rule. Distinct issues in one clause survive.
- Final overlap de-duplication also preserves findings from separate legal rules.
- Semantic keyword candidates are no longer treated as violations when AI is unavailable. Only `keywords_only` rules create deterministic fallback findings.
- Custom clause labels keep stable normalized identities rather than collapsing to `unknown`.

### Context and perspective

- Buyer and India are no longer silent client defaults. An explicit user choice wins; otherwise the selected playbook's party side is used, with neutral review as the safe fallback.
- Party-side behavior is aligned across text, asynchronous, file-upload, dashboard, and Word add-in paths.
- Contract detection now covers more agreement families and distinguishes mutual from unilateral NDAs.
- Default specialist healthcare, fintech, and IT-services packs are included in startup seeding, with category normalization for the database enum.

### Traceability and consistency

- Rule cache keys include response shape, and cached rules are deep-copied so one scan cannot mutate a later scan.
- Statutory references and stable rule IDs now survive parsing, verification, enrichment, API mapping, and file analysis.
- Jurisdiction name, contract type, review perspective, selected playbook, and coverage are returned to the clients.
- The playbook editor now captures risk description, acceptable and unacceptable signals, clause context, fallback position, preferred position, and detection behavior.

### Regulatory and privacy accuracy

- DPDP guidance now models phased commencement rather than describing every obligation as already or simultaneously enforceable.
- Breach output separates the initial Board notice and affected-principal notice required without delay from the detailed Board update due within 72 hours unless extended. CERT-In output is expressly conditional on the incident falling within the specified reportable categories.
- A 90-day maximum is no longer presented as a universal data-rights deadline. Product rights and grievance targets are labelled as internal or published service targets.
- Seven-year consent-record retention is applied only when the deployment is a registered Consent Manager. Ordinary deployments use a configurable retention policy.
- Cross-border language no longer treats section 16 as a positive allowlist or assumes consent overrides a Government restriction or stricter sectoral law.
- Generated privacy notices, consent forms, DPAs, and clauses are labelled as drafts for legal and factual review. Security controls, indemnity treatment, and internal processor-notification clocks are not presented as automatic statutory terms.
- The statutory knowledge base identifies its text as verified paraphrase, not a substitute for the official Gazette.
- The live 18-rule DPDP compliance layer was upgraded to version 2 against the final Rules and commencement notification. It no longer uses the old section 8(4) security citation, a positive country allowlist, a fixed Rs 250 crore “per violation” formulation, or a 72-hour minimum for the initial Board notice.
- The DPA, SaaS, MSA, healthcare, fintech, and IT-services system playbooks now distinguish statutory duties from negotiated controls. Versioned startup upgrades update known rules by clause type while preserving installed rule IDs, tiers, dependencies, and unrecognized/custom rules.
- Compliance-layer responses and AI context now carry the official source URL, Gazette date, main effective date, and last verification time. Migration `031_compliance_layer_legal_provenance.sql` persists that provenance.

### Authentication and execution integrity

- JWT subject claims are parsed as UUIDs before database queries, fixing authenticated compliance requests on UUID-backed databases and rejecting malformed subjects.
- MFA setup tokens retain their token type after decoding and are blocked from general authenticated routes; they are limited to the setup and verification endpoints.
- Conditions, dependency effects, tiers, compliance layers, and explicitly selected playbooks fail closed when their requested configuration cannot be loaded. The UI now emits the same condition and dependency parameter shapes that the resolver consumes.
- Synchronous, queued, inline-async, file-upload, and batch analysis paths carry party side, jurisdiction, playbook rules, compliance layers, tier preference, and compliance scoring consistently.

## How to make each playbook genuinely useful

Each rule should be an operational decision, not just a topic label. At minimum it should contain:

| Field | Lawyer purpose |
| --- | --- |
| Stable rule ID and clause type | Keeps findings, analytics, and versions connected |
| Applicability | States when the rule applies and when it is not applicable |
| Client-side objective | Explains whose interest the rule protects and why |
| Preferred position | The opening redline position |
| Acceptable position | The lowest normally acceptable outcome |
| Fallback or walk-away position | The escalation boundary and approval requirement |
| Risk description | The legal, commercial, and operational consequence |
| Unacceptable signals | Concrete drafting patterns that indicate a likely problem |
| Acceptable signals | Language that prevents false positives |
| Detection mode | `keywords_only` only for objectively bad text; `ai_with_keywords` for contextual judgment; `ai_only` for semantic or missing-clause review |
| Suggested language | Jurisdiction- and party-side-appropriate drafting, ideally with variants |
| Verification question | A precise question the reviewer must answer from the contract |
| Priority and deal-breaker flag | Drives negotiation order and escalation |
| Dependencies | Captures interactions with caps, carve-outs, termination, definitions, and schedules |
| Jurisdiction source | Current authority, effective date, and last lawyer validation date |

Example: a liability-cap rule should not say only “cap liability.” It should specify the cap base and period, mutuality, excluded claims, super-caps, whether indemnities sit inside or outside the cap, the client side, acceptable fallback, and the exact conditions that require escalation.

## Remaining work before claiming lawyer-equivalent quality

These are product-quality gates, not cosmetic enhancements:

1. **Build a lawyer-labeled evaluation set.** Use representative NDAs, MSAs, SaaS agreements, DPAs, employment contracts, procurement terms, and specialist agreements. Measure rule-level recall, precision, missing-clause recall, quote accuracy, side correctness, severity agreement, and redline acceptance. Track results by contract type and jurisdiction.
2. **Split the single large AI assessment into controlled passes.** Use a clause-inventory pass, batched rule-by-rule playbook pass, beyond-playbook issue-spotting pass, and cross-clause consistency pass. Merge by stable rule and source anchors. This reduces long-document omission risk and makes retries targeted.
3. **Add deterministic citation validation.** Exact sections and case propositions should be checked against a maintained legal-source service or approved corpus before being shown as verified authority. Until then, statutory references should be treated as AI-suggested research leads.
4. **Prove schedule and attachment coverage.** Detect referenced but absent exhibits, analyze all uploaded schedules, and show section-level review completeness. Current rule coverage is not the same as document coverage.
5. **Add a review-intake panel.** Capture deal purpose, client role, leverage, value, key economics, risk tolerance, special instructions, required approvals, and known non-negotiables. Party side alone is not enough for professional advice.
6. **Version and validate playbooks.** Require owner, jurisdiction, effective date, approval status, last review date, sample passing/failing clauses, and regression tests before publishing a playbook version.
7. **Run a live model quality trial.** The automated tests validate software behavior, not the substantive correctness of the deployed model on real contracts. A privileged, anonymized, lawyer-scored trial is required before production quality claims.
8. **Extend source versioning beyond the DPDP layer.** The DPDP layer now records source and timing provenance. Apply the same authority, effective-date, last-review, and supersession controls to every other jurisdiction and sectoral rule pack before presenting those sources as current law.

## Verification performed in this audit

- Added regression tests for selected-playbook pattern execution, semantic-candidate fallback behavior, coverage completeness, stable IDs and statutory references, custom rule identity, specialist contract detection, seed-category normalization, cache shape isolation, mutation isolation, and same-clause multi-issue preservation.
- Added legal-accuracy regression checks for staged breach notification, cross-border wording, DPDP security-section numbering, privacy-policy consent language, Consent Manager retention, and phased commencement.
- The full backend suite passes: 362 tests. Backend application, scripts, entry points, and tests pass Ruff and bytecode compilation.
- Dashboard ESLint and production build pass.
- Word add-in ESLint has zero errors, TypeScript passes, the production build passes with the deployed API URL, and the Office manifest validates. Seven Office API performance warnings remain and are recorded in the cleanup report.
- The unused 913 KiB source logo is no longer shipped in the add-in bundle; the validated manifest uses 16, 32, and 80 pixel assets totaling approximately 4.1 KiB. The original source asset remains in the repository.
- Live Vertex/Azure model quality was not exercised because no production credentials or lawyer-labelled contract corpus were used in this audit.

## Release recommendation

Release the wiring and traceability fixes behind normal staging validation. Do not market the result as replacing professional legal review. The defensible claim after these changes is that ContraRed applies selected playbooks more faithfully, exposes incomplete review coverage, preserves source evidence, and produces a more consistent first-pass contract review. A lawyer-labeled benchmark and verified legal-source layer are still required for a professional-quality assurance claim.
