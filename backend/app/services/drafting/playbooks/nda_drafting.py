"""
NDA Drafting Playbooks — Mutual and Unilateral
================================================
Each playbook contains clause-level templates at three negotiation tiers
(preferred / acceptable / fallback).  Placeholders use {{mustache}} syntax
and are resolved by the Draft Agent at generation time.

Placeholders common to both playbooks:
  {{party_1_name}}, {{party_2_name}}, {{party_1_entity_type}},
  {{party_1_jurisdiction}}, {{party_1_address}}, {{party_1_short_name}},
  {{party_2_entity_type}}, {{party_2_jurisdiction}}, {{party_2_address}},
  {{party_2_short_name}}, {{effective_date}}, {{term_months}},
  {{governing_law}}, {{dispute_resolution}}, {{venue}}, {{purpose}},
  {{confidentiality_survival_years}}, {{non_solicitation_months}},
  {{ci_categories_clause}}

Unilateral-only:
  {{disclosing_party_name}}, {{disclosing_party_short_name}},
  {{receiving_party_name}}, {{receiving_party_short_name}}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier(
    tone: str,
    template_text: str,
    guidance: str = "",
    key_terms: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "tone": tone,
        "template_text": template_text,
        "guidance": guidance,
        "key_terms": key_terms or {},
    }


def _clause(
    clause_type: str,
    heading: str,
    preferred: Dict[str, Any],
    acceptable: Dict[str, Any],
    fallback: Dict[str, Any],
    *,
    category: str = "general",
    required_defined_terms: Optional[List[str]] = None,
    cross_references: Optional[List[str]] = None,
    jurisdiction_variants: Optional[Dict[str, Any]] = None,
    is_required: bool = True,
    conditional_on: Optional[str] = None,
    drafting_notes: str = "",
    position: int = 0,
) -> Dict[str, Any]:
    return {
        "clause_type": clause_type,
        "section_heading": heading,
        "category": category,
        "position_in_order": position,
        "preferred": preferred,
        "acceptable": acceptable,
        "fallback": fallback,
        "drafting_notes": drafting_notes,
        "required_defined_terms": required_defined_terms or [],
        "cross_references": cross_references or [],
        "jurisdiction_variants": jurisdiction_variants or {},
        "is_required": is_required,
        "conditional_on": conditional_on,
    }


# ---------------------------------------------------------------------------
# Section order (shared)
# ---------------------------------------------------------------------------

_SECTION_ORDER: List[str] = [
    "preamble",
    "recitals",
    "confidential_info_definition",
    "ci_exclusions",
    "receiving_party_obligations",
    "permitted_disclosures",
    "compelled_disclosure",
    "term_and_duration",
    "return_destruction",
    "remedies",
    "no_license",
    "governing_law",
    "non_solicitation",
    "boilerplate",
    "signature_blocks",
]

# ===================================================================
#  MUTUAL NDA CLAUSES
# ===================================================================

_mutual_preamble = _clause(
    clause_type="preamble",
    heading="Preamble",
    category="boilerplate",
    position=0,
    drafting_notes="Identifies both parties symmetrically as mutual disclosers/recipients.",
    required_defined_terms=["Party", "Disclosing Party", "Receiving Party"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Mutual Non-Disclosure Agreement (this \"Agreement\") is entered into as of "
            "{{effective_date}} (the \"Effective Date\"), by and between {{party_1_name}}, "
            "a {{party_1_entity_type}} organized and existing under the laws of "
            "{{party_1_jurisdiction}}, with its principal place of business at "
            "{{party_1_address}} (\"{{party_1_short_name}}\"), and {{party_2_name}}, "
            "a {{party_2_entity_type}} organized and existing under the laws of "
            "{{party_2_jurisdiction}}, with its principal place of business at "
            "{{party_2_address}} (\"{{party_2_short_name}}\"). "
            "{{party_1_short_name}} and {{party_2_short_name}} are each referred to herein "
            "individually as a \"Party\" and collectively as the \"Parties.\" Each Party may "
            "act as both a Disclosing Party and a Receiving Party under this Agreement."
        ),
        guidance="Full legal identification with entity type and jurisdiction.",
        key_terms={"reciprocity": "full_mutual"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Mutual Non-Disclosure Agreement (\"Agreement\") is made as of "
            "{{effective_date}} by and between {{party_1_name}} "
            "(\"{{party_1_short_name}}\"), having its principal office at "
            "{{party_1_address}}, and {{party_2_name}} "
            "(\"{{party_2_short_name}}\"), having its principal office at "
            "{{party_2_address}} (each a \"Party\" and together the \"Parties\"). "
            "Each Party may disclose and receive Confidential Information under this Agreement."
        ),
        guidance="Standard identification without entity type details.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Agreement is entered into as of {{effective_date}} between "
            "{{party_1_name}} (\"{{party_1_short_name}}\") and {{party_2_name}} "
            "(\"{{party_2_short_name}}\"), collectively the \"Parties.\" "
            "Each Party may disclose Confidential Information to the other Party."
        ),
        guidance="Minimal preamble for low-formality contexts.",
    ),
)

_mutual_recitals = _clause(
    clause_type="recitals",
    heading="Recitals",
    category="boilerplate",
    position=1,
    drafting_notes="Establishes the purpose of disclosure and mutual intent.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "WHEREAS, the Parties wish to explore and evaluate a potential business "
            "relationship relating to {{purpose}} (the \"Purpose\"); and\n\n"
            "WHEREAS, in connection with the Purpose, each Party may find it necessary to "
            "disclose certain confidential and proprietary information to the other Party; and\n\n"
            "WHEREAS, the Parties desire to establish the terms and conditions under which "
            "such confidential information will be disclosed, received, and protected;\n\n"
            "NOW, THEREFORE, in consideration of the mutual covenants and agreements set forth "
            "herein, and for other good and valuable consideration, the receipt and sufficiency "
            "of which are hereby acknowledged, the Parties agree as follows:"
        ),
        guidance="Three-part recitals with full consideration language.",
        key_terms={"purpose_scope": "narrow"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "WHEREAS, the Parties intend to engage in discussions concerning {{purpose}} "
            "(the \"Purpose\"), and in connection therewith each Party may disclose to the "
            "other certain confidential or proprietary information;\n\n"
            "NOW, THEREFORE, in consideration of the mutual promises contained herein, "
            "the Parties agree as follows:"
        ),
        guidance="Consolidated recitals with standard consideration clause.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "The Parties wish to exchange confidential information in connection with "
            "{{purpose}} (the \"Purpose\") and agree to protect such information as follows:"
        ),
        guidance="Single-sentence lead-in for commercial agreements.",
    ),
)

_mutual_ci_definition = _clause(
    clause_type="confidential_info_definition",
    heading="Definition of Confidential Information",
    category="confidentiality",
    position=2,
    drafting_notes="Broadest-possible definition at preferred tier; marking requirement at fallback.",
    required_defined_terms=["Confidential Information"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "\"Confidential Information\" means any and all non-public, confidential, or "
            "proprietary information disclosed by or on behalf of a Disclosing Party to a "
            "Receiving Party, whether disclosed orally, in writing, electronically, or by any "
            "other means, and whether or not marked or designated as \"confidential,\" including "
            "but not limited to: (a) trade secrets, inventions, ideas, processes, formulae, "
            "source and object code, data, programs, software, know-how, and improvements thereto; "
            "(b) information regarding plans for research, development, new products, marketing and "
            "selling, business plans, budgets and unpublished financial statements, licenses, prices "
            "and costs, margins, discounts, credit terms, pricing and billing policies, quoting "
            "procedures, methods of obtaining business, forecasts, future plans and potential "
            "strategies, and financial projections; (c) information regarding the skills and "
            "compensation of employees, contractors, and agents of the Disclosing Party; "
            "(d) information regarding suppliers and customers of the Disclosing Party; "
            "(e) confidential or proprietary concepts, documentation, reports, data, "
            "specifications, computer software, source code, object code, flow charts, databases, "
            "and inventions; and (f) all other information that a reasonable person would understand "
            "to be confidential given the nature of the information and the circumstances of "
            "disclosure. {{ci_categories_clause}} Confidential Information also includes any "
            "notes, analyses, compilations, studies, summaries, and other material prepared by the "
            "Receiving Party that contain or are based upon, in whole or in part, any information "
            "included in the foregoing."
        ),
        guidance=(
            "No marking requirement; includes derivative works. Most protective for the "
            "disclosing party."
        ),
        key_terms={"marking_required": False, "includes_derivatives": True},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "\"Confidential Information\" means information disclosed by one Party (the "
            "\"Disclosing Party\") to the other Party (the \"Receiving Party\") that is "
            "designated as confidential or that, given the nature of the information or the "
            "circumstances surrounding its disclosure, reasonably should be considered as "
            "confidential. Confidential Information includes, without limitation, technical "
            "data, trade secrets, business plans, product plans, customer lists, financial "
            "information, software, and any other information of a similar nature, whether or "
            "not reduced to a tangible form. Information disclosed orally shall be considered "
            "Confidential Information if it is identified as confidential at the time of "
            "disclosure and confirmed in writing within thirty (30) days thereafter. "
            "{{ci_categories_clause}}"
        ),
        guidance="Balanced definition with 30-day oral confirmation window.",
        key_terms={"marking_required": "oral_confirmation_30_days"},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "\"Confidential Information\" means information that is disclosed by one Party "
            "to the other in written or tangible form and is clearly marked as \"Confidential\" "
            "or \"Proprietary\" at the time of disclosure. Information disclosed orally shall "
            "constitute Confidential Information only if (a) identified as confidential at the "
            "time of disclosure and (b) reduced to writing, marked as confidential, and "
            "delivered to the Receiving Party within fifteen (15) days of the oral disclosure. "
            "{{ci_categories_clause}}"
        ),
        guidance="Written-and-marked requirement; narrowest definition.",
        key_terms={"marking_required": True},
    ),
)

_mutual_ci_exclusions = _clause(
    clause_type="ci_exclusions",
    heading="Exclusions from Confidential Information",
    category="confidentiality",
    position=3,
    drafting_notes="Standard carve-outs. Preferred tier adds burden-of-proof language.",
    required_defined_terms=["Confidential Information"],
    cross_references=["confidential_info_definition"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "The obligations of confidentiality under this Agreement shall not apply to any "
            "information that the Receiving Party can demonstrate by competent written evidence: "
            "(a) was already known to the Receiving Party at the time of disclosure, without "
            "restriction, as evidenced by written records predating such disclosure; "
            "(b) is or becomes publicly available through no fault or breach of this Agreement "
            "by the Receiving Party; (c) is rightfully received by the Receiving Party from a "
            "third party without restriction on disclosure and without breach of a "
            "non-disclosure obligation; or (d) is independently developed by the Receiving "
            "Party without use of or reference to the Disclosing Party's Confidential "
            "Information, as evidenced by written records."
        ),
        guidance="Burden of proof on receiving party; requires written evidence.",
        key_terms={"burden_of_proof": "receiving_party"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "Confidential Information does not include information that: (a) was publicly "
            "known at the time of disclosure or becomes publicly known through no wrongful "
            "act of the Receiving Party; (b) was known to the Receiving Party prior to "
            "disclosure by the Disclosing Party, as shown by the Receiving Party's files "
            "and records; (c) becomes known to the Receiving Party through disclosure by "
            "sources other than the Disclosing Party having the legal right to disclose "
            "such information; or (d) is independently developed by the Receiving Party "
            "without reference to or use of the Disclosing Party's Confidential Information."
        ),
        guidance="Standard four-part exclusion without explicit burden language.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "The term \"Confidential Information\" shall not include information that: "
            "(a) is or becomes generally available to the public other than as a result of "
            "unauthorized disclosure by the Receiving Party; (b) was available to the "
            "Receiving Party on a non-confidential basis prior to disclosure; (c) becomes "
            "available to the Receiving Party on a non-confidential basis from a source "
            "other than the Disclosing Party; or (d) was independently developed by the "
            "Receiving Party."
        ),
        guidance="Lean exclusion language without evidentiary requirements.",
    ),
)

_mutual_obligations = _clause(
    clause_type="receiving_party_obligations",
    heading="Obligations of the Receiving Party",
    category="confidentiality",
    position=4,
    drafting_notes="Core protection clause. Preferred imposes highest-standard-of-care + need-to-know.",
    required_defined_terms=["Confidential Information", "Receiving Party", "Disclosing Party"],
    cross_references=["confidential_info_definition", "permitted_disclosures"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "The Receiving Party shall: (a) hold the Disclosing Party's Confidential "
            "Information in strict confidence and protect it with at least the same degree "
            "of care that it uses to protect its own most highly confidential information, "
            "but in no event less than a reasonable degree of care; (b) not disclose the "
            "Confidential Information to any third party except as expressly permitted under "
            "this Agreement; (c) restrict access to the Confidential Information to those of "
            "its employees, officers, directors, agents, advisors, and contractors "
            "(collectively, \"Representatives\") who have a bona fide need to know such "
            "information for the Purpose and who are bound by written confidentiality "
            "obligations no less restrictive than those contained herein; (d) not use the "
            "Confidential Information for any purpose other than the Purpose; and "
            "(e) be responsible for any breach of this Agreement by any of its Representatives. "
            "The Receiving Party shall promptly notify the Disclosing Party in writing upon "
            "discovery of any unauthorized use or disclosure of Confidential Information."
        ),
        guidance=(
            "Highest standard of care; written NDA required for representatives; "
            "vicarious liability for representatives."
        ),
        key_terms={
            "standard_of_care": "highest_own_plus_reasonable",
            "representative_nda": True,
            "vicarious_liability": True,
        },
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "The Receiving Party agrees to: (a) use the Confidential Information solely "
            "for the Purpose; (b) protect the Confidential Information using the same "
            "degree of care that it uses to protect its own confidential information of a "
            "similar nature, but not less than reasonable care; (c) limit disclosure of "
            "Confidential Information to its employees and contractors who need to know "
            "such information for the Purpose and who are bound by confidentiality "
            "obligations substantially similar to those in this Agreement; and (d) promptly "
            "notify the Disclosing Party of any unauthorized disclosure or use of "
            "Confidential Information of which the Receiving Party becomes aware."
        ),
        guidance="Same-degree-of-care standard; substantially similar NDA for reps.",
        key_terms={
            "standard_of_care": "same_degree_reasonable_floor",
            "representative_nda": "substantially_similar",
        },
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "The Receiving Party shall use commercially reasonable efforts to protect the "
            "Disclosing Party's Confidential Information from unauthorized disclosure and "
            "shall not use such information except in connection with the Purpose. The "
            "Receiving Party may disclose Confidential Information to its employees and "
            "advisors who need to know such information, provided such persons are informed "
            "of the confidential nature of the information."
        ),
        guidance="Commercially reasonable efforts; oral notice to reps acceptable.",
        key_terms={"standard_of_care": "commercially_reasonable"},
    ),
)

_mutual_permitted_disclosures = _clause(
    clause_type="permitted_disclosures",
    heading="Permitted Disclosures",
    category="confidentiality",
    position=5,
    drafting_notes="Scope of allowed sharing. Preferred is narrow; fallback is broad.",
    cross_references=["receiving_party_obligations"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "The Receiving Party may disclose Confidential Information only to its "
            "Representatives who (a) have a demonstrable need to know such information "
            "solely for the Purpose, (b) have been informed of the confidential nature of "
            "the information, and (c) are bound by written agreements containing "
            "confidentiality obligations at least as restrictive as those set forth in this "
            "Agreement. Any disclosure to affiliates requires the prior written consent of "
            "the Disclosing Party. The Receiving Party shall maintain a written record of "
            "all persons to whom Confidential Information has been disclosed."
        ),
        guidance="Affiliate consent required; written log of disclosures.",
        key_terms={"affiliate_consent": "required", "disclosure_log": True},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "The Receiving Party may disclose Confidential Information to its employees, "
            "officers, directors, and professional advisors (including attorneys and "
            "accountants) who need access for the Purpose and who are bound by "
            "confidentiality obligations no less protective than this Agreement. The "
            "Receiving Party may also disclose Confidential Information to its affiliates, "
            "provided such affiliates agree in writing to be bound by the terms of this "
            "Agreement. The Receiving Party shall be responsible for any breach by the "
            "foregoing persons."
        ),
        guidance="Affiliate disclosure allowed with written agreement.",
        key_terms={"affiliate_consent": "written_agreement"},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "The Receiving Party may share Confidential Information with its employees, "
            "contractors, and affiliates who have a need to know for the Purpose, provided "
            "that such persons are made aware of the confidential nature of the information "
            "and agree to treat it in accordance with the terms of this Agreement."
        ),
        guidance="Broad sharing with awareness requirement only.",
    ),
)

_mutual_compelled_disclosure = _clause(
    clause_type="compelled_disclosure",
    heading="Compelled Disclosure",
    category="confidentiality",
    position=6,
    drafting_notes="Legal/regulatory carve-out with prior-notice obligations.",
    cross_references=["receiving_party_obligations"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "If the Receiving Party is compelled by applicable law, regulation, or legal "
            "process to disclose any Confidential Information, the Receiving Party shall, "
            "to the extent legally permitted, provide the Disclosing Party with prompt "
            "written notice of such requirement prior to disclosure so that the Disclosing "
            "Party may seek a protective order or other appropriate remedy. The Receiving "
            "Party shall cooperate with the Disclosing Party, at the Disclosing Party's "
            "expense, in seeking such protective order. If such protective order or other "
            "remedy is not obtained, the Receiving Party shall disclose only that portion "
            "of the Confidential Information that its legal counsel advises is legally "
            "required to be disclosed and shall use commercially reasonable efforts to "
            "obtain assurance that confidential treatment will be afforded to the disclosed "
            "information."
        ),
        guidance="Prior notice + cooperation + minimal disclosure + seek protective order.",
        key_terms={"prior_notice": True, "cooperation": True, "protective_order": True},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "If the Receiving Party becomes legally obligated to disclose Confidential "
            "Information, it shall give the Disclosing Party prompt notice, where legally "
            "permissible, so that the Disclosing Party may seek a protective order or other "
            "remedy. If no protective order is obtained, the Receiving Party may disclose "
            "only that portion of the Confidential Information that is legally required and "
            "shall exercise reasonable efforts to ensure confidential treatment of the "
            "disclosed information."
        ),
        guidance="Standard compelled disclosure with notice and minimal disclosure.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "Nothing in this Agreement shall prevent the Receiving Party from disclosing "
            "Confidential Information to the extent required by law, regulation, or court "
            "order, provided that the Receiving Party gives reasonable prior notice to the "
            "Disclosing Party where practicable."
        ),
        guidance="Simple legal-process carve-out with best-efforts notice.",
    ),
)

_mutual_term = _clause(
    clause_type="term_and_duration",
    heading="Term and Duration",
    category="termination",
    position=7,
    drafting_notes="Covers both the disclosure window and the survival period.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "This Agreement shall commence on the Effective Date and shall remain in full "
            "force and effect for a period of {{term_months}} months (the \"Term\"), unless "
            "earlier terminated by either Party upon thirty (30) days' prior written notice "
            "to the other Party. Notwithstanding any expiration or termination of this "
            "Agreement, the obligations of confidentiality set forth herein shall survive "
            "for a period of {{confidentiality_survival_years}} years from the date of "
            "disclosure of the applicable Confidential Information. With respect to any "
            "Confidential Information that constitutes a trade secret under applicable law, "
            "the obligations of confidentiality shall continue for so long as such "
            "information remains a trade secret."
        ),
        guidance="Fixed survival + perpetual trade-secret protection.",
        key_terms={
            "termination_notice_days": 30,
            "trade_secret_perpetual": True,
        },
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "This Agreement shall be effective as of the Effective Date and continue for "
            "{{term_months}} months unless terminated earlier by either Party with thirty "
            "(30) days' written notice. The confidentiality obligations under this Agreement "
            "shall survive expiration or termination for a period of "
            "{{confidentiality_survival_years}} years following the date of disclosure of "
            "the relevant Confidential Information."
        ),
        guidance="Fixed term with fixed survival; no perpetual trade-secret tail.",
        key_terms={"termination_notice_days": 30},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "This Agreement is effective from {{effective_date}} and continues for "
            "{{term_months}} months. Either Party may terminate this Agreement at any time "
            "upon written notice. Confidentiality obligations shall survive termination for "
            "{{confidentiality_survival_years}} years from the date of termination."
        ),
        guidance="Survival measured from termination rather than disclosure.",
    ),
)

_mutual_return_destruction = _clause(
    clause_type="return_destruction",
    heading="Return and Destruction of Confidential Information",
    category="termination",
    position=8,
    drafting_notes="Post-termination handling of CI.",
    cross_references=["term_and_duration"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "Upon the expiration or termination of this Agreement, or upon the written "
            "request of the Disclosing Party at any time, the Receiving Party shall "
            "promptly: (a) return to the Disclosing Party all originals and copies of "
            "Confidential Information in any form or medium; or (b) destroy all such "
            "Confidential Information and certify such destruction in writing to the "
            "Disclosing Party within fifteen (15) days. Notwithstanding the foregoing, the "
            "Receiving Party may retain one (1) archival copy of the Confidential "
            "Information solely for purposes of compliance with applicable legal or "
            "regulatory record-retention requirements, provided that such copy remains "
            "subject to the confidentiality obligations of this Agreement. The Receiving "
            "Party shall also use commercially reasonable efforts to permanently erase or "
            "destroy all Confidential Information stored in electronic backup or archival "
            "systems within sixty (60) days of the request."
        ),
        guidance="Return or destroy + certification + electronic purge + archival exception.",
        key_terms={
            "certification_required": True,
            "archival_copy_allowed": True,
            "electronic_purge_days": 60,
        },
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "Upon termination or expiration of this Agreement, or upon the Disclosing "
            "Party's written request, the Receiving Party shall promptly return or destroy "
            "all Confidential Information and any copies thereof. The Receiving Party shall "
            "confirm such return or destruction in writing upon request. The Receiving Party "
            "may retain copies of Confidential Information to the extent required by law or "
            "regulation, subject to the continuing confidentiality obligations herein."
        ),
        guidance="Return or destroy with confirmation on request.",
        key_terms={"certification_required": "on_request"},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "Upon termination of this Agreement, the Receiving Party shall, at the "
            "Disclosing Party's election, return or destroy all Confidential Information "
            "received. Copies retained in routine electronic backups need not be actively "
            "purged but remain subject to the confidentiality obligations of this Agreement."
        ),
        guidance="Disclosing party elects return or destroy; no active electronic purge.",
    ),
)

_mutual_remedies = _clause(
    clause_type="remedies",
    heading="Remedies",
    category="remedies",
    position=9,
    drafting_notes="Equitable relief and damages provisions.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "Each Party acknowledges that a breach or threatened breach of this Agreement "
            "may cause the non-breaching Party irreparable harm for which monetary damages "
            "would be an inadequate remedy. Accordingly, in addition to any other remedies "
            "available at law or in equity, the non-breaching Party shall be entitled to "
            "seek injunctive relief, specific performance, or other equitable remedies "
            "without the necessity of proving actual damages or posting any bond or other "
            "security. In any action to enforce this Agreement, the prevailing Party shall "
            "be entitled to recover its reasonable attorneys' fees, costs, and expenses "
            "incurred in connection with such action."
        ),
        guidance="Injunctive relief without bond + fee shifting to prevailing party.",
        key_terms={
            "injunctive_relief": True,
            "bond_waiver": True,
            "fee_shifting": "prevailing_party",
        },
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "Each Party agrees that any breach of this Agreement may result in irreparable "
            "harm to the Disclosing Party and that monetary damages alone would be "
            "insufficient. The Disclosing Party shall therefore be entitled to seek "
            "injunctive or other equitable relief in addition to all other remedies "
            "available at law or in equity. Such remedies shall not be deemed to be the "
            "exclusive remedies for a breach of this Agreement but shall be in addition to "
            "all other remedies available at law or in equity."
        ),
        guidance="Injunctive relief available; no fee shifting or bond waiver.",
        key_terms={"injunctive_relief": True},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "Each Party acknowledges that a breach of this Agreement may cause irreparable "
            "harm and that the injured Party may seek equitable relief, including "
            "injunction, in addition to any other available legal remedies."
        ),
        guidance="Minimal equitable relief acknowledgment.",
    ),
)

_mutual_no_license = _clause(
    clause_type="no_license",
    heading="No License or Implied Rights",
    category="ip_ownership",
    position=10,
    drafting_notes="Preserves IP ownership of disclosing party.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "Nothing in this Agreement shall be construed as granting any right, license, "
            "or interest in or to any Confidential Information, patent, copyright, trade "
            "secret, trademark, or other intellectual property right of the Disclosing "
            "Party, whether by implication, estoppel, or otherwise. All Confidential "
            "Information remains the sole and exclusive property of the Disclosing Party, "
            "and no right or license is granted to the Receiving Party except as expressly "
            "set forth herein. The Receiving Party shall not reverse-engineer, disassemble, "
            "or decompile any Confidential Information or any prototypes, software, or "
            "other tangible objects embodying the Confidential Information."
        ),
        guidance="Explicit IP reservation with reverse-engineering prohibition.",
        key_terms={"reverse_engineering_prohibited": True},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "Nothing in this Agreement grants the Receiving Party any license or right in "
            "or to any Confidential Information, intellectual property, or other proprietary "
            "rights of the Disclosing Party, except the limited right to use such "
            "information solely for the Purpose. All Confidential Information remains the "
            "property of the Disclosing Party."
        ),
        guidance="Standard no-license provision with limited use acknowledgment.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "No license, right, or interest in any trademark, patent, copyright, or other "
            "intellectual property of the Disclosing Party is granted under this Agreement. "
            "Title to the Confidential Information shall remain with the Disclosing Party."
        ),
        guidance="Concise no-license statement.",
    ),
)

_mutual_governing_law = _clause(
    clause_type="governing_law",
    heading="Governing Law and Dispute Resolution",
    category="dispute_resolution",
    position=11,
    drafting_notes="Governs choice of law, venue, and dispute mechanism.",
    jurisdiction_variants={
        "US-DE": "laws of the State of Delaware",
        "US-NY": "laws of the State of New York",
        "GB": "laws of England and Wales",
        "IN": "laws of India",
        "SG": "laws of the Republic of Singapore",
    },
    preferred=_tier(
        tone="protective",
        template_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "{{governing_law}}, without regard to its conflict-of-laws principles. Any "
            "dispute, controversy, or claim arising out of or relating to this Agreement, "
            "including the breach, termination, or validity thereof, shall be exclusively "
            "resolved by {{dispute_resolution}} in {{venue}}. Each Party hereby irrevocably "
            "submits to the exclusive jurisdiction of such forum and waives any objection to "
            "venue or inconvenient forum. To the extent permitted by applicable law, each "
            "Party irrevocably waives any right to a jury trial in any action or proceeding "
            "arising out of or relating to this Agreement."
        ),
        guidance="Exclusive jurisdiction + jury waiver.",
        key_terms={"exclusive_jurisdiction": True, "jury_waiver": True},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "{{governing_law}}. Any dispute arising under this Agreement shall be resolved "
            "by {{dispute_resolution}} in {{venue}}. Each Party consents to the personal "
            "jurisdiction of the courts located in {{venue}} for purposes of adjudicating "
            "any dispute under this Agreement."
        ),
        guidance="Standard governing law and consent to jurisdiction.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "This Agreement is governed by the {{governing_law}}. Disputes shall be "
            "resolved by {{dispute_resolution}} in {{venue}}."
        ),
        guidance="Minimal governing law clause.",
    ),
)

_mutual_non_solicitation = _clause(
    clause_type="non_solicitation",
    heading="Non-Solicitation",
    category="restrictive_covenants",
    position=12,
    is_required=False,
    conditional_on="nda_details.non_solicitation == true",
    drafting_notes="Optional clause; include only when non-solicitation is requested.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "During the Term and for a period of {{non_solicitation_months}} months "
            "following the expiration or termination of this Agreement, neither Party shall, "
            "directly or indirectly, solicit, recruit, hire, or attempt to solicit, recruit, "
            "or hire any employee, officer, or contractor of the other Party with whom it "
            "has had contact or about whom it has received Confidential Information in "
            "connection with this Agreement. This restriction shall not apply to general "
            "solicitations of employment not specifically directed toward the other Party's "
            "personnel, such as public job postings."
        ),
        guidance="Broad non-solicitation with general-advertising carve-out.",
        key_terms={"scope": "employees_officers_contractors"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "During the Term and for {{non_solicitation_months}} months thereafter, "
            "neither Party shall directly solicit for employment any employee of the other "
            "Party who was involved in the Purpose, without the prior written consent of "
            "that Party. General advertisements and unsolicited applications shall not "
            "constitute solicitation under this section."
        ),
        guidance="Narrower scope limited to employees involved in the Purpose.",
        key_terms={"scope": "involved_employees_only"},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "For {{non_solicitation_months}} months after termination, neither Party shall "
            "directly solicit for hire any key employee of the other Party who participated "
            "in the Purpose. This restriction does not apply to unsolicited applications or "
            "general employment advertising."
        ),
        guidance="Minimal non-solicitation limited to key employees.",
        key_terms={"scope": "key_employees_only"},
    ),
)

_mutual_boilerplate = _clause(
    clause_type="boilerplate",
    heading="General Provisions",
    category="boilerplate",
    position=13,
    drafting_notes="Standard boilerplate: entire agreement, amendment, waiver, severability, assignment, notices, counterparts.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "Entire Agreement. This Agreement constitutes the entire agreement between the "
            "Parties with respect to the subject matter hereof and supersedes all prior and "
            "contemporaneous understandings, agreements, representations, and warranties, "
            "whether written or oral, with respect to such subject matter.\n\n"
            "Amendment. No amendment, modification, or waiver of any provision of this "
            "Agreement shall be effective unless in writing and signed by both Parties.\n\n"
            "Waiver. No failure or delay by either Party in exercising any right, power, or "
            "privilege under this Agreement shall operate as a waiver thereof, nor shall any "
            "single or partial exercise thereof preclude any other or further exercise "
            "thereof or the exercise of any other right, power, or privilege.\n\n"
            "Severability. If any provision of this Agreement is held to be invalid, "
            "illegal, or unenforceable, the remaining provisions shall continue in full "
            "force and effect. The invalid provision shall be modified to the minimum extent "
            "necessary to make it valid and enforceable while preserving the Parties' "
            "original intent.\n\n"
            "Assignment. Neither Party may assign or transfer this Agreement, or any rights "
            "or obligations hereunder, without the prior written consent of the other Party, "
            "except that either Party may assign this Agreement to an affiliate or in "
            "connection with a merger, acquisition, or sale of all or substantially all of "
            "its assets, provided that the assignee agrees in writing to be bound by the "
            "terms hereof.\n\n"
            "Notices. All notices under this Agreement shall be in writing and shall be "
            "deemed duly given when delivered personally, sent by nationally recognized "
            "overnight courier, or sent by certified mail, return receipt requested, to the "
            "addresses set forth in the preamble.\n\n"
            "Counterparts. This Agreement may be executed in counterparts, each of which "
            "shall be deemed an original and all of which together shall constitute one and "
            "the same instrument. Electronic signatures shall have the same force and "
            "effect as original signatures."
        ),
        guidance="Full boilerplate suite with modification-for-enforceability severability.",
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "Entire Agreement. This Agreement is the complete and exclusive statement of "
            "the agreement between the Parties regarding its subject matter and supersedes "
            "all prior agreements and understandings.\n\n"
            "Amendment. This Agreement may be amended only by a written instrument signed "
            "by both Parties.\n\n"
            "Waiver. The failure of either Party to enforce any provision shall not "
            "constitute a waiver of that Party's right to enforce that provision or any "
            "other provision.\n\n"
            "Severability. If any provision of this Agreement is found unenforceable, the "
            "remaining provisions shall remain in effect.\n\n"
            "Assignment. Neither Party may assign this Agreement without the other Party's "
            "prior written consent.\n\n"
            "Counterparts. This Agreement may be executed in counterparts, including by "
            "electronic signature."
        ),
        guidance="Standard boilerplate without assignment carve-outs.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "This Agreement is the entire agreement between the Parties on this subject "
            "and supersedes all prior agreements. Amendments must be in writing and signed "
            "by both Parties. If any provision is unenforceable, the remaining provisions "
            "remain in effect. Neither Party may assign this Agreement without the other "
            "Party's consent. This Agreement may be signed in counterparts."
        ),
        guidance="Compact boilerplate for simple transactions.",
    ),
)

_mutual_signature_blocks = _clause(
    clause_type="signature_blocks",
    heading="Signatures",
    category="boilerplate",
    position=14,
    drafting_notes="Execution block for both parties.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "IN WITNESS WHEREOF, the Parties have executed this Mutual Non-Disclosure "
            "Agreement as of the Effective Date.\n\n"
            "{{party_1_name}}\n\n"
            "By: ____________________________\n"
            "Name: __________________________\n"
            "Title: _________________________\n"
            "Date: __________________________\n\n"
            "{{party_2_name}}\n\n"
            "By: ____________________________\n"
            "Name: __________________________\n"
            "Title: _________________________\n"
            "Date: __________________________"
        ),
        guidance="Formal execution block with witness language.",
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "The Parties have executed this Agreement as of the Effective Date.\n\n"
            "{{party_1_name}}\n\n"
            "Signature: _____________________\n"
            "Name: __________________________\n"
            "Title: _________________________\n"
            "Date: __________________________\n\n"
            "{{party_2_name}}\n\n"
            "Signature: _____________________\n"
            "Name: __________________________\n"
            "Title: _________________________\n"
            "Date: __________________________"
        ),
        guidance="Standard execution block.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "Agreed and accepted:\n\n"
            "{{party_1_name}}\n"
            "Signature: _____________________\n"
            "Name / Title: __________________\n"
            "Date: __________________________\n\n"
            "{{party_2_name}}\n"
            "Signature: _____________________\n"
            "Name / Title: __________________\n"
            "Date: __________________________"
        ),
        guidance="Simplified execution block.",
    ),
)

# ===================================================================
#  MUTUAL NDA PLAYBOOK  (assembled)
# ===================================================================

NDA_MUTUAL_PLAYBOOK: Dict[str, Any] = {
    "contract_type": "nda_mutual",
    "name": "Mutual Non-Disclosure Agreement",
    "jurisdiction": "{{governing_law}}",
    "section_order": list(_SECTION_ORDER),
    "clauses": [
        _mutual_preamble,
        _mutual_recitals,
        _mutual_ci_definition,
        _mutual_ci_exclusions,
        _mutual_obligations,
        _mutual_permitted_disclosures,
        _mutual_compelled_disclosure,
        _mutual_term,
        _mutual_return_destruction,
        _mutual_remedies,
        _mutual_no_license,
        _mutual_governing_law,
        _mutual_non_solicitation,
        _mutual_boilerplate,
        _mutual_signature_blocks,
    ],
}

# ===================================================================
#  UNILATERAL NDA  —  unique sections + reuse from mutual
# ===================================================================

_uni_preamble = _clause(
    clause_type="preamble",
    heading="Preamble",
    category="boilerplate",
    position=0,
    drafting_notes="One-directional: identifies Disclosing Party and Receiving Party.",
    required_defined_terms=["Disclosing Party", "Receiving Party"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement (this \"Agreement\") is entered into as of "
            "{{effective_date}} (the \"Effective Date\"), by and between "
            "{{disclosing_party_name}}, a {{party_1_entity_type}} organized and existing "
            "under the laws of {{party_1_jurisdiction}}, with its principal place of "
            "business at {{party_1_address}} (the \"Disclosing Party\" or "
            "\"{{disclosing_party_short_name}}\"), and {{receiving_party_name}}, "
            "a {{party_2_entity_type}} organized and existing under the laws of "
            "{{party_2_jurisdiction}}, with its principal place of business at "
            "{{party_2_address}} (the \"Receiving Party\" or "
            "\"{{receiving_party_short_name}}\"). The Disclosing Party and the Receiving "
            "Party are each referred to herein individually as a \"Party\" and collectively "
            "as the \"Parties.\""
        ),
        guidance="Full entity identification with one-directional roles.",
        key_terms={"direction": "unilateral"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement (\"Agreement\") is made as of {{effective_date}} "
            "by and between {{disclosing_party_name}} "
            "(\"{{disclosing_party_short_name}}\"), the \"Disclosing Party,\" having its "
            "principal office at {{party_1_address}}, and {{receiving_party_name}} "
            "(\"{{receiving_party_short_name}}\"), the \"Receiving Party,\" having its "
            "principal office at {{party_2_address}}."
        ),
        guidance="Standard identification with designated roles.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Agreement is entered into as of {{effective_date}} between "
            "{{disclosing_party_name}} (\"Disclosing Party\") and "
            "{{receiving_party_name}} (\"Receiving Party\")."
        ),
        guidance="Minimal preamble for one-way NDA.",
    ),
)

_uni_recitals = _clause(
    clause_type="recitals",
    heading="Recitals",
    category="boilerplate",
    position=1,
    drafting_notes="One-directional recitals: only Disclosing Party discloses.",
    preferred=_tier(
        tone="protective",
        template_text=(
            "WHEREAS, the Disclosing Party possesses certain confidential and proprietary "
            "information relating to {{purpose}} (the \"Purpose\"); and\n\n"
            "WHEREAS, the Disclosing Party desires to disclose certain of such confidential "
            "information to the Receiving Party for the sole purpose of enabling the "
            "Receiving Party to evaluate the Purpose; and\n\n"
            "WHEREAS, the Disclosing Party wishes to ensure that such information is "
            "protected against unauthorized use and disclosure;\n\n"
            "NOW, THEREFORE, in consideration of the mutual covenants and agreements set "
            "forth herein, and for other good and valuable consideration, the receipt and "
            "sufficiency of which are hereby acknowledged, the Parties agree as follows:"
        ),
        guidance="Three-part recitals emphasizing one-directional flow.",
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "WHEREAS, the Disclosing Party intends to disclose certain confidential "
            "information to the Receiving Party in connection with {{purpose}} "
            "(the \"Purpose\"), and the Receiving Party agrees to protect such information;\n\n"
            "NOW, THEREFORE, in consideration of the mutual promises herein, the Parties "
            "agree as follows:"
        ),
        guidance="Consolidated one-directional recitals.",
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "The Disclosing Party wishes to share confidential information with the "
            "Receiving Party in connection with {{purpose}} (the \"Purpose\"), and the "
            "Receiving Party agrees to protect such information as set forth below."
        ),
        guidance="Single-sentence one-directional lead-in.",
    ),
)

_uni_ci_definition = _clause(
    clause_type="confidential_info_definition",
    heading="Definition of Confidential Information",
    category="confidentiality",
    position=2,
    drafting_notes="One-directional: only Disclosing Party's information is covered.",
    required_defined_terms=["Confidential Information", "Disclosing Party", "Receiving Party"],
    preferred=_tier(
        tone="protective",
        template_text=(
            "\"Confidential Information\" means any and all non-public, confidential, or "
            "proprietary information disclosed by or on behalf of the Disclosing Party to "
            "the Receiving Party, whether disclosed orally, in writing, electronically, or "
            "by any other means, and whether or not marked or designated as \"confidential,\" "
            "including but not limited to: (a) trade secrets, inventions, ideas, processes, "
            "formulae, source and object code, data, programs, software, know-how, and "
            "improvements thereto; (b) information regarding plans for research, development, "
            "new products, marketing and selling, business plans, budgets and unpublished "
            "financial statements, licenses, prices and costs, margins, discounts, credit "
            "terms, pricing and billing policies, quoting procedures, methods of obtaining "
            "business, forecasts, future plans and potential strategies, and financial "
            "projections; (c) information regarding the skills and compensation of employees, "
            "contractors, and agents of the Disclosing Party; (d) information regarding "
            "suppliers and customers of the Disclosing Party; (e) confidential or proprietary "
            "concepts, documentation, reports, data, specifications, computer software, source "
            "code, object code, flow charts, databases, and inventions; and (f) all other "
            "information that a reasonable person would understand to be confidential given "
            "the nature of the information and the circumstances of disclosure. "
            "{{ci_categories_clause}} Confidential Information also includes any notes, "
            "analyses, compilations, studies, summaries, and other material prepared by the "
            "Receiving Party that contain or are based upon, in whole or in part, any "
            "information included in the foregoing."
        ),
        guidance="Broad one-directional definition; no marking required.",
        key_terms={"marking_required": False, "direction": "unilateral"},
    ),
    acceptable=_tier(
        tone="balanced",
        template_text=(
            "\"Confidential Information\" means information disclosed by the Disclosing "
            "Party to the Receiving Party that is designated as confidential or that, given "
            "the nature of the information or the circumstances surrounding its disclosure, "
            "reasonably should be considered as confidential. Confidential Information "
            "includes, without limitation, technical data, trade secrets, business plans, "
            "product plans, customer lists, financial information, software, and any other "
            "information of a similar nature, whether or not reduced to a tangible form. "
            "Information disclosed orally shall be considered Confidential Information if "
            "it is identified as confidential at the time of disclosure and confirmed in "
            "writing within thirty (30) days thereafter. {{ci_categories_clause}}"
        ),
        guidance="Balanced one-directional definition with oral-confirmation window.",
        key_terms={"marking_required": "oral_confirmation_30_days"},
    ),
    fallback=_tier(
        tone="commercial",
        template_text=(
            "\"Confidential Information\" means information that is disclosed by the "
            "Disclosing Party to the Receiving Party in written or tangible form and is "
            "clearly marked as \"Confidential\" or \"Proprietary\" at the time of disclosure. "
            "Information disclosed orally shall constitute Confidential Information only if "
            "(a) identified as confidential at the time of disclosure and (b) reduced to "
            "writing, marked as confidential, and delivered to the Receiving Party within "
            "fifteen (15) days of the oral disclosure. {{ci_categories_clause}}"
        ),
        guidance="Written-and-marked requirement; one-directional.",
        key_terms={"marking_required": True},
    ),
)

# For unilateral NDA, reuse mutual clauses for sections that are substantively identical
# (the template text already uses "Disclosing Party" / "Receiving Party" language).

NDA_UNILATERAL_PLAYBOOK: Dict[str, Any] = {
    "contract_type": "nda_unilateral",
    "name": "Unilateral Non-Disclosure Agreement",
    "jurisdiction": "{{governing_law}}",
    "section_order": list(_SECTION_ORDER),
    "clauses": [
        _uni_preamble,
        _uni_recitals,
        _uni_ci_definition,
        _mutual_ci_exclusions,
        _mutual_obligations,
        _mutual_permitted_disclosures,
        _mutual_compelled_disclosure,
        _mutual_term,
        _mutual_return_destruction,
        _mutual_remedies,
        _mutual_no_license,
        _mutual_governing_law,
        _mutual_non_solicitation,
        _mutual_boilerplate,
        _mutual_signature_blocks,
    ],
}
