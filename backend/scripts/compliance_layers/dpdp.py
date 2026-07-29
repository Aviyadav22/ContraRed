"""Lawyer-reviewed DPDP contract-compliance layer.

The rules are drafting and issue-spotting aids, not verbatim law. They are
grounded in the DPDP Act 2023, the final DPDP Rules 2025, and the phased
commencement notifications published in the official Gazette.
"""


def _rule(
    *,
    clause_type: str,
    risk_level: str,
    primary_position: str,
    fallback_position: str,
    detection_patterns: list[str],
    risk_description: str,
    acceptable_position: str,
    unacceptable_signals: list[str],
    acceptable_signals: list[str],
    sort_order: int,
    is_deal_breaker: bool = False,
) -> dict:
    return {
        "clause_type": clause_type,
        "risk_level": risk_level,
        "is_deal_breaker": is_deal_breaker,
        "primary_position": primary_position,
        "fallback_position": fallback_position,
        "detection_patterns": detection_patterns,
        "detection_mode": "ai_with_keywords",
        "risk_description": risk_description,
        "acceptable_position": acceptable_position,
        "unacceptable_signals": unacceptable_signals,
        "acceptable_signals": acceptable_signals,
        "sort_order": sort_order,
    }


DPDP_LAYER = {
    "code": "dpdp",
    "name": "DPDP Act 2023 and Rules 2025 Compliance",
    "description": (
        "Contract-review aid grounded in the final DPDP Rules 2025 and official "
        "phased commencement. Applicability depends on the parties' actual "
        "processing roles and the subject matter of the agreement."
    ),
    "jurisdiction": "IN",
    "version": 2,
    "source_url": (
        "https://www.meity.gov.in/documents/act-and-policies/"
        "digital-personal-data-protection-rules-2025-gDOxUjMtQWa"
    ),
    "gazette_date": "2025-11-13",
    "effective_date": "2027-05-13",
    "last_verified_at": "2026-07-27T00:00:00+05:30",
    "rules": [
        _rule(
            clause_type="dpdp_consent_mechanism",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "Where processing relies on consent, the agreement must not "
                "require conduct that defeats Sections 5-6 or Rule 3. Define "
                "permitted purposes, necessary data, roles, and withdrawal "
                "support; identify any Section 7 legitimate use separately."
            ),
            fallback_position=(
                "Define permitted purposes and require each party to use an "
                "applicable basis under Sections 4, 6, or 7, without blanket "
                "or deemed consent."
            ),
            detection_patterns=[
                "consent", "personal data", "data principal",
                "lawful purpose", "processing",
            ],
            risk_description=(
                "If this contract governs consent-based processing, detect "
                "blanket, bundled, unnecessary, irrevocable, or unrelated "
                "consent. Mark not_applicable when the contract neither "
                "allocates nor obstructs consent responsibilities."
            ),
            acceptable_position=(
                "Specified purposes and necessary data, compliant notice and "
                "clear affirmative action, comparable withdrawal, and "
                "processor cessation support where applicable."
            ),
            unacceptable_signals=[
                "blanket consent", "deemed consent for unrelated purposes",
                "consent irrevocable", "bundled consent",
            ],
            acceptable_signals=[
                "specified purpose", "necessary personal data",
                "clear affirmative action", "comparable ease of withdrawal",
            ],
            sort_order=0,
        ),
        _rule(
            clause_type="dpdp_data_principal_rights",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "Where a processor or counterparty handles personal data for "
                "a Data Fiduciary, require cooperation sufficient to fulfil "
                "Sections 11-14: access information, correction and erasure, "
                "grievance support, and nomination workflows where relevant."
            ),
            fallback_position=(
                "Require timely assistance with applicable rights requests and "
                "do not contractually waive statutory rights."
            ),
            detection_patterns=[
                "data principal", "access request", "correction", "erasure",
                "grievance", "nomination",
            ],
            risk_description=(
                "For contracts governing processing on a Fiduciary's behalf, "
                "detect waiver, obstruction, unilateral refusal, or missing "
                "cooperation that prevents Sections 11-14 compliance. Do not "
                "require a consumer-facing rights clause in an unrelated deal."
            ),
            acceptable_position=(
                "Statutory rights are preserved and practical, time-bound "
                "assistance is allocated by processing role."
            ),
            unacceptable_signals=[
                "waiver of data principal rights", "no assistance with requests",
                "processor may refuse erasure at discretion",
            ],
            acceptable_signals=[
                "assist with access requests", "correction and erasure",
                "grievance support", "nomination",
            ],
            sort_order=1,
        ),
        _rule(
            clause_type="dpdp_fiduciary_obligations",
            risk_level="RED",
            primary_position=(
                "Preserve the Fiduciary's responsibility under Section 8(1), "
                "appropriate measures under Section 8(4), reasonable security "
                "safeguards under Section 8(5), applicable accuracy under "
                "Section 8(3), and erasure under Section 8(7)."
            ),
            fallback_position=(
                "The agreement must not disclaim or prevent the parties' "
                "applicable Section 8 obligations."
            ),
            detection_patterns=[
                "data fiduciary", "security safeguards", "data accuracy",
                "data deletion", "responsibility",
            ],
            risk_description=(
                "Where the agreement allocates Fiduciary or processor duties, "
                "detect disclaimers or terms that prevent applicable Section 8 "
                "compliance. Do not require every duty verbatim in every contract."
            ),
            acceptable_position=(
                "Roles and assistance enable applicable responsibility, "
                "accuracy, security, breach, erasure, contact, and grievance duties."
            ),
            unacceptable_signals=[
                "fiduciary has no responsibility", "no security obligations",
                "processor may retain forever",
            ],
            acceptable_signals=[
                "data fiduciary remains responsible",
                "reasonable security safeguards", "erase when required",
            ],
            sort_order=2,
        ),
        _rule(
            clause_type="dpdp_breach_notification",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "Enable notice to each affected Data Principal and an initial "
                "Board notice without delay, followed by the detailed Board "
                "update within 72 hours unless extended (Section 8(6), Rule 7). "
                "A processor's contractual notice must be prompt enough to "
                "enable those duties."
            ),
            fallback_position=(
                "Require processor notice without undue delay after awareness, "
                "immediate cooperation, and information for the detailed "
                "72-hour Board update."
            ),
            detection_patterns=[
                "personal data breach", "security incident",
                "data protection board", "affected data principal", "notify",
            ],
            risk_description=(
                "For personal-data processing contracts, detect incident terms "
                "that delay or block without-delay initial notices or the "
                "detailed Board update within 72 hours. Distinguish the "
                "processor's negotiated clock from the statutory clocks."
            ),
            acceptable_position=(
                "Prompt processor escalation, without-delay principal and "
                "initial Board notices, and detailed Board reporting within "
                "72 hours unless extended."
            ),
            unacceptable_signals=[
                "notice only after final investigation",
                "processor may withhold incident details",
                "breach notification at sole discretion",
            ],
            acceptable_signals=[
                "notify without undue delay", "initial board notice without delay",
                "notify affected data principals", "within 72 hours",
            ],
            sort_order=3,
        ),
        _rule(
            clause_type="dpdp_cross_border_transfer",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "Comply with any country or territory restriction notified "
                "under Section 16, any Rule 15 requirement concerning foreign-"
                "State access, and any stricter applicable Indian sectoral law. "
                "Document destinations and support current orders."
            ),
            fallback_position=(
                "Require destination transparency, notice of material changes, "
                "and compliance with current Section 16 notifications, Rule 15 "
                "orders, and stricter applicable Indian law."
            ),
            detection_patterns=[
                "cross-border", "data transfer", "outside India",
                "international transfer", "data localization",
            ],
            risk_description=(
                "Detect transfers that would proceed despite an applicable "
                "Government restriction or requirement, obscure destinations, "
                "or purport to override stricter Indian law. Do not invent a "
                "positive allowlist or universal adequacy requirement."
            ),
            acceptable_position=(
                "Transfers remain subject to current Government restrictions "
                "and requirements, destination transparency, and stricter "
                "sectoral controls where applicable."
            ),
            unacceptable_signals=[
                "transfer despite government restriction",
                "no destination information", "contract overrides Indian law",
                "unrestricted foreign-government access",
            ],
            acceptable_signals=[
                "section 16 restrictions", "rule 15 requirements",
                "documented destinations", "stricter applicable law",
            ],
            sort_order=4,
        ),
        _rule(
            clause_type="dpdp_consent_manager",
            risk_level="YELLOW",
            primary_position=(
                "If a party acts as a statutory Consent Manager, it must be "
                "registered with the Board and meet Section 6(7)-(9), Rule 4, "
                "and First Schedule obligations when that phase commences."
            ),
            fallback_position=(
                "Do not describe an ordinary consent tool as a registered "
                "Consent Manager; if the statutory role is used, require registration."
            ),
            detection_patterns=[
                "consent manager", "consent management platform",
                "data protection board registration",
            ],
            risk_description=(
                "Only for an entity acting as a statutory Consent Manager, "
                "detect missing registration or inconsistent obligations. "
                "Otherwise mark not_applicable."
            ),
            acceptable_position=(
                "The statutory role, registration, independence, recordkeeping, "
                "and First Schedule obligations are accurately stated."
            ),
            unacceptable_signals=[
                "unregistered consent manager", "consent manager reads personal data",
            ],
            acceptable_signals=[
                "registered with the board", "rule 4", "first schedule",
            ],
            sort_order=5,
        ),
        _rule(
            clause_type="dpdp_processor_agreement",
            risk_level="RED",
            primary_position=(
                "Where a Data Processor is engaged in the Section 8(2) context, "
                "use a valid contract defining the processing and appropriate "
                "Rule 6 security provisions. Calibrate instructions, purpose "
                "limits, incidents, rights, deletion, audit, and subprocessors "
                "to the actual risk."
            ),
            fallback_position=(
                "Document the processing relationship and appropriate security "
                "safeguards; prohibit unapproved use that changes agreed roles "
                "or purposes."
            ),
            detection_patterns=[
                "data processor", "processing agreement", "subprocessor",
                "on behalf of", "security safeguards",
            ],
            risk_description=(
                "For a processor engagement, detect no valid contract, missing "
                "appropriate security provisions, or operational terms that "
                "prevent the Fiduciary from complying."
            ),
            acceptable_position=(
                "A valid processing contract with appropriate security terms "
                "and fact-specific controls enabling the Fiduciary's duties."
            ),
            unacceptable_signals=[
                "no processing agreement", "processor may use data for any purpose",
                "no security safeguards",
            ],
            acceptable_signals=[
                "valid contract", "appropriate security safeguards",
                "permitted processing", "subprocessor controls",
            ],
            sort_order=6,
        ),
        _rule(
            clause_type="dpdp_childrens_data",
            risk_level="YELLOW",
            primary_position=(
                "If children's personal data is processed, apply Section 9 and "
                "Rules 10-12, including verifiable parental consent and the "
                "applicable restrictions, subject to class- and purpose-specific "
                "Fourth Schedule exemptions."
            ),
            fallback_position=(
                "Identify whether children are in scope and require the "
                "applicable age/identity, parental-consent, and restricted-use controls."
            ),
            detection_patterns=[
                "child", "children", "under 18", "parental consent",
                "targeted advertising", "behavioural monitoring",
            ],
            risk_description=(
                "Only where children's data is or may be processed, detect "
                "missing verifiable parental consent or prohibited tracking, "
                "monitoring, targeted advertising, or detrimental processing, "
                "while considering Rules 10-12 exemptions."
            ),
            acceptable_position=(
                "Verifiable parental consent and applicable child-protection "
                "controls are implemented with exemption checks."
            ),
            unacceptable_signals=[
                "children treated the same as adults",
                "targeted advertising to children",
                "behavioural monitoring of children",
            ],
            acceptable_signals=[
                "verifiable parental consent", "age and identity verification",
                "fourth schedule exemption",
            ],
            sort_order=7,
        ),
        _rule(
            clause_type="dpdp_purpose_limitation",
            risk_level="YELLOW",
            primary_position=(
                "Consent-based processing must remain within the specified "
                "purpose and necessary personal data under Section 6(1). A new "
                "consent-based purpose needs compliant notice and fresh "
                "affirmative consent; a Section 7 use or another Indian law "
                "must be assessed separately."
            ),
            fallback_position=(
                "Limit processing to documented permitted purposes and require "
                "a valid, documented basis before materially new use."
            ),
            detection_patterns=[
                "specified purpose", "secondary use", "future purposes",
                "additional processing", "any lawful purpose",
            ],
            risk_description=(
                "Detect vague or unlimited purposes and unsupported secondary "
                "use. Do not state that consent is always required where a "
                "fact-specific Section 7 use or another law applies."
            ),
            acceptable_position=(
                "Purposes are specific and bounded; any new processing is "
                "assessed and documented under the applicable DPDP basis."
            ),
            unacceptable_signals=[
                "any purpose deemed necessary", "all future purposes",
                "unrelated purposes without notice",
            ],
            acceptable_signals=[
                "specified purpose", "necessary personal data",
                "fresh consent", "section 7 legitimate use",
            ],
            sort_order=8,
        ),
        _rule(
            clause_type="dpdp_data_retention",
            risk_level="YELLOW",
            primary_position=(
                "Apply Section 8(7) erasure on consent withdrawal or when the "
                "specified purpose is no longer served unless law requires "
                "retention. Apply Rule 8's Third Schedule periods and 48-hour "
                "warning only to covered classes/purposes, and preserve "
                "applicable one-year records under Rules 6 and 8."
            ),
            fallback_position=(
                "Use purpose- and law-based retention, processor deletion, "
                "legal holds, and the specific Rule 6 or Rule 8 recordkeeping "
                "requirements that apply."
            ),
            detection_patterns=[
                "data retention", "retention period", "erasure",
                "delete", "legal hold", "processing logs",
            ],
            risk_description=(
                "Detect indefinite or uncontrolled retention and missing "
                "processor deletion support. Do not apply Rule 8's 48-hour "
                "warning or Third Schedule periods universally."
            ),
            acceptable_position=(
                "A documented schedule distinguishes operational data, legal "
                "holds, processor copies, and applicable one-year or Third "
                "Schedule requirements."
            ),
            unacceptable_signals=[
                "retain forever", "indefinite retention without purpose",
                "processor never deletes",
            ],
            acceptable_signals=[
                "erase when purpose no longer served", "legal retention",
                "one-year logs where applicable", "processor deletion",
            ],
            sort_order=9,
        ),
        _rule(
            clause_type="dpdp_significant_fiduciary",
            risk_level="YELLOW",
            primary_position=(
                "If notified as a Significant Data Fiduciary, appoint an India-"
                "based DPO and independent data auditor under Section 10 and "
                "perform the DPIA and audit at least once every twelve months "
                "under Rule 13, reporting significant observations to the Board."
            ),
            fallback_position=(
                "Apply these controls only if the entity has been notified as "
                "an SDF; otherwise record them as readiness measures, not current duties."
            ),
            detection_patterns=[
                "significant data fiduciary", "data protection officer",
                "DPIA", "independent data auditor", "annual audit",
            ],
            risk_description=(
                "Only for an entity notified as an SDF, detect missing Section "
                "10 or Rule 13 controls. Otherwise mark not_applicable."
            ),
            acceptable_position=(
                "An India-based DPO, independent auditor, annual DPIA/audit, "
                "required reporting, and applicable technical controls."
            ),
            unacceptable_signals=[
                "notified significant data fiduciary with no DPO",
                "no independent data auditor", "no annual DPIA",
            ],
            acceptable_signals=[
                "DPO based in India", "independent data auditor",
                "once every twelve months", "report significant observations",
            ],
            sort_order=10,
        ),
        _rule(
            clause_type="dpdp_penalty_indemnification",
            risk_level="RED",
            primary_position=(
                "Negotiate responsibility for losses caused by DPDP non-"
                "compliance, including investigation, notification, remediation, "
                "third-party claims, and regulatory amounts only where lawful. "
                "The Schedule has category-specific maxima, not a fixed "
                "Rs 250 crore amount per violation."
            ),
            fallback_position=(
                "Allocate by causation and control, decide cap/super-cap/carve-"
                "out treatment, and preserve non-excludable statutory responsibility."
            ),
            detection_patterns=[
                "DPDP penalty", "regulatory fine", "indemnity",
                "250 crore", "data protection liability",
            ],
            risk_description=(
                "Detect unclear or one-sided allocation, false 'Rs 250 crore "
                "per violation' statements, or terms purporting to bind the "
                "Board or transfer non-delegable statutory responsibility."
            ),
            acceptable_position=(
                "Allocation reflects role, causation, control, applicable caps, "
                "lawful recoverability, and non-excludable duties."
            ),
            unacceptable_signals=[
                "250 crore per violation", "all fines automatically indemnified",
                "contract eliminates statutory responsibility",
            ],
            acceptable_signals=[
                "lawfully recoverable regulatory amounts", "caused by breach",
                "data protection super-cap", "non-excludable liability",
            ],
            sort_order=11,
        ),
        _rule(
            clause_type="dpdp_notice_requirements",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "A consent request must be accompanied or preceded by the "
                "Section 5 notice. Rule 3 requires a standalone, clear notice "
                "itemising personal data, purposes, enabled goods/services or "
                "uses, and means to withdraw, exercise rights, and complain."
            ),
            fallback_position=(
                "Where consent is the basis, require the responsible party to "
                "deliver a clear Section 5 and Rule 3 notice before or with "
                "the consent request."
            ),
            detection_patterns=[
                "privacy notice", "consent notice", "itemised personal data",
                "withdraw consent", "complaint to the board",
            ],
            risk_description=(
                "Where the contract allocates consent or notice duties, detect "
                "terms that omit or contradict Section 5 and Rule 3. Do not "
                "require a complete consumer notice inside an unrelated contract."
            ),
            acceptable_position=(
                "The responsible party provides a standalone, clear, itemised "
                "notice before or with consent and maintains required routes."
            ),
            unacceptable_signals=[
                "consent without notice", "notice after consent",
                "purposes may change without notice",
            ],
            acceptable_signals=[
                "itemised personal data", "specified purposes",
                "withdrawal link", "complaint to the board",
            ],
            sort_order=12,
        ),
        _rule(
            clause_type="dpdp_lawful_purpose",
            risk_level="YELLOW",
            primary_position=(
                "Processing must be for a lawful purpose under Section 4 and "
                "be based on consent under Section 6 or a fact-specific "
                "legitimate use under Section 7."
            ),
            fallback_position=(
                "State permitted processing purposes and prohibit purposes "
                "expressly forbidden by law."
            ),
            detection_patterns=[
                "lawful purpose", "processing purpose", "consent",
                "legitimate use", "section 7",
            ],
            risk_description=(
                "Detect unlawful, undefined, or unlimited processing purposes "
                "and confusion between consent and Section 7 uses."
            ),
            acceptable_position=(
                "Permitted purposes and the applicable DPDP basis are accurately documented."
            ),
            unacceptable_signals=[
                "any purpose whatsoever", "purpose prohibited by law",
                "deemed consent",
            ],
            acceptable_signals=[
                "lawful purpose", "consent under section 6",
                "legitimate use under section 7",
            ],
            sort_order=13,
        ),
        _rule(
            clause_type="dpdp_data_accuracy",
            risk_level="YELLOW",
            primary_position=(
                "Require completeness, accuracy, and consistency where personal "
                "data is used to make a decision affecting the Data Principal "
                "or disclosed to another Data Fiduciary (Section 8(3))."
            ),
            fallback_position=(
                "Allocate reasonable correction and quality controls for the "
                "Section 8(3) situations that actually apply."
            ),
            detection_patterns=[
                "data accuracy", "data quality", "completeness",
                "consistency", "decision affecting",
            ],
            risk_description=(
                "Detect disclaimers or missing assistance that would prevent "
                "Section 8(3) accuracy in covered decision or disclosure use."
            ),
            acceptable_position=(
                "Accuracy controls are tied to covered decisions and disclosures, "
                "with correction cooperation by role."
            ),
            unacceptable_signals=[
                "no responsibility for data accuracy",
                "known inaccurate data may be used for decisions",
            ],
            acceptable_signals=[
                "complete accurate and consistent",
                "correction cooperation", "decision affecting data principal",
            ],
            sort_order=14,
        ),
        _rule(
            clause_type="dpdp_grievance_officer",
            risk_level="RED",
            is_deal_breaker=True,
            primary_position=(
                "Maintain a readily available grievance mechanism under "
                "Sections 8(10) and 13. Publish the DPO's or responsible "
                "business contact under Section 8(9) and Rule 9, plus a "
                "reasonable grievance period not exceeding 90 days under Rule 14(3)."
            ),
            fallback_position=(
                "Publish a responsible privacy contact, accessible grievance "
                "route, and response period within the Rule 14(3) ceiling."
            ),
            detection_patterns=[
                "grievance redressal", "privacy contact", "complaint mechanism",
                "response period", "data protection officer",
            ],
            risk_description=(
                "Where privacy operations are allocated, detect obstruction of "
                "the grievance mechanism, missing responsible contact, or a "
                "published period above 90 days. The Act does not universally "
                "require the title 'Grievance Officer'."
            ),
            acceptable_position=(
                "Accessible grievance redressal, published contact, and a "
                "reasonable published period not exceeding 90 days."
            ),
            unacceptable_signals=[
                "no grievance mechanism", "no privacy contact",
                "response period exceeds 90 days",
            ],
            acceptable_signals=[
                "grievance redressal", "business contact information",
                "published response period",
            ],
            sort_order=15,
        ),
        _rule(
            clause_type="dpdp_consent_withdrawal",
            risk_level="RED",
            primary_position=(
                "Under Section 6(4), consent may be withdrawn at any time with "
                "ease comparable to giving it. Under Section 6(6), the "
                "Fiduciary must within a reasonable time cease and cause "
                "processors to cease consent-based processing unless another "
                "DPDP or Indian-law basis permits continuation."
            ),
            fallback_position=(
                "Provide a comparably easy withdrawal route and timely "
                "cessation of processing that no longer has an applicable basis."
            ),
            detection_patterns=[
                "withdraw consent", "revoke consent", "opt out",
                "consent irrevocable", "cease processing",
            ],
            risk_description=(
                "Detect irrevocable consent, materially harder withdrawal, or "
                "terms allowing continued consent-based processing without "
                "another applicable basis. Do not claim all service consequences "
                "of withdrawal are prohibited."
            ),
            acceptable_position=(
                "Comparable withdrawal and timely cessation by the Fiduciary "
                "and processors, except where continued processing is authorised."
            ),
            unacceptable_signals=[
                "consent irrevocable", "cannot withdraw",
                "processor may ignore withdrawal",
            ],
            acceptable_signals=[
                "withdraw at any time", "comparable ease",
                "cease processing within a reasonable time",
            ],
            sort_order=16,
        ),
        _rule(
            clause_type="dpdp_data_principal_duties",
            risk_level="GREEN",
            primary_position=(
                "If the agreement describes Data Principal duties, state "
                "Section 15 accurately and do not use those duties to waive "
                "rights or excuse a Data Fiduciary's obligations."
            ),
            fallback_position=(
                "Omit this clause if unnecessary; absence is not a compliance gap."
            ),
            detection_patterns=[
                "data principal duties", "false complaint",
                "impersonate", "material information",
            ],
            risk_description=(
                "Informational only. Detect inaccurate or overbroad Data "
                "Principal duties that purport to waive rights. Missing text "
                "must be compliant or not_applicable, never a violation."
            ),
            acceptable_position=(
                "Any Section 15 summary is accurate and does not diminish "
                "Sections 11-14 or the Fiduciary's duties."
            ),
            unacceptable_signals=[
                "waives rights by making a mistake",
                "data fiduciary has no duty if information is inaccurate",
            ],
            acceptable_signals=[
                "comply with applicable law", "no impersonation",
                "no false or frivolous grievance",
            ],
            sort_order=17,
        ),
    ],
}
