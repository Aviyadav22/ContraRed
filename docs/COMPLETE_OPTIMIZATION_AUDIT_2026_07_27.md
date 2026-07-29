# ContraRed Complete Quality and Cleanup Audit

Date: 27 July 2026

## Release verdict

The contract-analysis flow is materially safer and more lawyer-like than the
audited starting point. Selected playbooks now control the review, every rule
has an auditable assessment status, contract quotations are source-checked,
distinct legal issues survive de-duplication, and incomplete review is exposed
instead of being reported as complete. Synchronous, asynchronous, upload,
batch, dashboard, and Word add-in paths now carry the same material review
inputs.

The repository passes all available automated gates. This supports a staging
release after the three pending migrations are applied. It does **not** support
a claim that the product replaces professional legal sign-off: no production
model run against a privileged, lawyer-labelled contract corpus was part of
this audit.

## Highest-impact defects fixed

| Area | Audited defect | Current behavior |
| --- | --- | --- |
| Selected playbook | User-authored detection patterns were omitted and the generic library controlled classification | Selected patterns are serialized, compiled, evaluated, and sent to AI with stable rule IDs |
| Rule completeness | The model could silently skip selected obligations | One ledger row per rule records `compliant`, `violation`, `missing`, `not_applicable`, `unassessed`, or `unverified` |
| False positives | Semantic keywords became violations when AI failed | Only objective `keywords_only` rules can create deterministic findings; contextual candidates remain unassessed |
| Hallucinations | Invalid JSON and unanchored AI text could be accepted or hidden | Invalid AI output fails; findings and recovered ledger issues require verifiable contract evidence |
| De-duplication | Separate rules in the same clause could erase one another | Duplicate removal is scoped to the same stable rule; distinct legal issues survive |
| Perspective | Buyer/India defaults could invert advice | Explicit selection wins, then the playbook side, then neutral; jurisdiction is carried end to end |
| Playbook mechanics | Editor payloads did not match condition/dependency resolver keys | UI and API validate canonical operators, values, effects, cycles, tiers, and verification prompts |
| Failure behavior | Missing playbook/configuration could silently fall back | Requested playbooks, layers, conditions, dependencies, and tiers fail closed with explicit API errors |
| Async parity | Queue/file/batch paths dropped review inputs or compliance score context | All paths carry party side, jurisdiction, layers, tier/deal context, playbook rules, and coverage/scoring |
| Compliance scoring | Silent/unassessed rules could inflate readiness | Every effective obligation is included; unassessed/unverified rules reduce completeness |
| Research | Connector fallback could fabricate authority | Unsupported case-law output is no longer presented as verified research |
| Authentication | UUID token subjects broke queries; MFA setup scope was discarded | Subjects are validated UUIDs and MFA setup tokens cannot access general authenticated routes |

## Lawyer workflow now represented

1. Establish the represented side, governing context, contract family, deal
   inputs, and selected playbook.
2. Extract document structure, defined terms, jurisdiction indicators, and
   cross-references.
3. Build candidate clauses without treating contextual keywords as proof.
4. Apply every selected playbook and compliance rule with stable identity,
   preferred/fallback position, applicability, verification question, and
   source context.
5. Require an explicit rule-status ledger and preserve missing or unresolved
   obligations.
6. Verify quoted contract evidence, confidence, cross-clause interaction, and
   negotiation dependencies.
7. Return redlines, statutory research leads, review perspective, coverage,
   warnings, and compliance completeness consistently to each client.

## Playbook and legal-source quality

The DPDP compliance pack is now version 2 with 18 applicability-aware rules.
It records the official source, Gazette date, main substantive commencement
date, and last verification time. The DPA, SaaS, MSA, healthcare, fintech, and
IT-services defaults were also corrected so commercial controls such as audit
rights, sub-processor approval, indemnities, certification, SLA levels, and
internal notification clocks are not described as universal statutory text.

The versioned default seeder upgrades known clauses by `clause_type`, preserving
installed database rule IDs and therefore their tiers, dependencies, and
references. It does not delete additional installed rules. This behavior has a
regression test.

The DPDP timing and wording changes are based on the final Digital Personal
Data Protection Rules, 2025 and the Central Government commencement
notification. The main substantive provisions and corresponding Rules are
staged for 13 May 2027; Rule 7 separates notices required without delay from
specified Board details due within 72 hours unless the Board permits more time.

## Dead and stale code disposition

Proven duplicate/orphan implementations were removed only where a live
replacement and registration/caller trace existed. Persistence models,
historical migrations, compatibility routes, public helpers, and external API
surfaces were not classified as dead merely because a static search found no
direct call.

The complete backtrack gate, confirmed removals, retained candidates, production
data checks, and deprecation sequence are in
`docs/CODE_CLEANUP_BACKTRACK_REPORT_2026_07_27.md`.

The Word add-in no longer deploys its unused 913 KiB source logo. The manifest
uses purpose-sized 16, 32, and 80 pixel icons totaling about 4.1 KiB; the source
logo remains available and was not deleted. Browser compatibility data was
refreshed.

## Verification

- Backend Ruff: pass.
- Python bytecode compilation: pass.
- Backend test suite: **362 passed**.
- Dashboard ESLint: pass.
- Dashboard TypeScript/Vite production build: pass.
- Word add-in ESLint: zero errors, seven Office performance warnings.
- Word add-in TypeScript: pass.
- Word add-in production Webpack build using
  `https://contrared-api.onrender.com/api/v1`: pass.
- Office add-in manifest validation: pass.

## Deployment requirements

Apply these migrations in order before deploying the corresponding code:

1. `029_playbook_party_side_default.sql`
2. `030_batch_compliance_scores.sql`
3. `031_compliance_layer_legal_provenance.sql`

Then restart the API so the versioned seeders upgrade the DPDP layer and the
corrected system playbooks. Verify a staging scan for each supported contract
family, both represented sides, each compliance-layer option, the Redis worker
path, upload/batch paths, and Word insertion/undo against representative DOCX
files.

## Residual gates before a lawyer-equivalent claim

1. Run a privileged, anonymized, lawyer-labelled evaluation corpus and publish
   rule-level recall, precision, missing-clause recall, quote accuracy, side
   correctness, severity agreement, and accepted-redline rates.
2. Split long-document AI review into controlled inventory, rule-batch,
   beyond-playbook, and cross-clause passes with section-level coverage.
3. Add source-version and deterministic citation checks for every jurisdiction
   and sectoral pack, not only DPDP.
4. Prove referenced schedule, exhibit, order-form, and incorporated-document
   coverage.
5. Replace the live process-local drafting store with an approved encrypted or
   zero-retention multi-worker design before removing `DraftSession`.
6. Use production telemetry and a deprecation window before deleting retained
   helpers, compatibility routes, or dormant persistence models.
7. Build Word document regression fixtures before batching the seven remaining
   `context.sync()`/navigation warnings; those calls participate in anchoring,
   duplicate-clause disambiguation, and tracked-change safety.

The defensible current claim is: ContraRed now provides a substantially more
faithful, auditable, source-conscious first-pass contract review. Final legal
judgment and production-quality assurance still require the measured lawyer
benchmark above.
