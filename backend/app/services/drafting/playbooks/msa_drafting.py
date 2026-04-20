"""
Master Service Agreement (MSA) Drafting Playbook
==================================================
15-section MSA playbook at three negotiation tiers
(preferred / acceptable / fallback).

Perspective: Service Provider side.
  - preferred  = provider-protective
  - acceptable = balanced
  - fallback   = client-protective

Placeholders ({{mustache}} syntax):
  {{party_1_name}}, {{party_1_entity_type}}, {{party_1_jurisdiction}},
  {{party_1_address}}, {{party_2_name}}, {{party_2_entity_type}},
  {{party_2_jurisdiction}}, {{party_2_address}}, {{effective_date}},
  {{term_months}}, {{governing_law}}, {{venue}}
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.drafting.playbooks.nda_drafting import _clause, _tier

# ---------------------------------------------------------------------------
# Section order
# ---------------------------------------------------------------------------

_SECTION_ORDER: List[str] = [
    "preamble",
    "definitions",
    "services_scope",
    "sow_structure",
    "fees_payment",
    "intellectual_property",
    "confidentiality",
    "reps_warranties",
    "indemnification",
    "limitation_of_liability",
    "insurance",
    "term_termination",
    "dispute_resolution",
    "boilerplate",
    "signature",
]

# ---------------------------------------------------------------------------
# Clauses
# ---------------------------------------------------------------------------

_CLAUSES: List[Dict[str, Any]] = [

    # ── 1. PREAMBLE ─────────────────────────────────────────────────────
    _clause(
        "preamble",
        "Master Service Agreement",
        preferred=_tier(
            "provider-protective",
            (
                "This Master Service Agreement (this \"Agreement\") is entered into as of "
                "{{effective_date}} (the \"Effective Date\") by and between {{party_1_name}}, "
                "a {{party_1_entity_type}} organized under the laws of {{party_1_jurisdiction}}, "
                "with its principal place of business at {{party_1_address}} (\"Service Provider\"), "
                "and {{party_2_name}}, a {{party_2_entity_type}} organized under the laws of "
                "{{party_2_jurisdiction}}, with its principal place of business at {{party_2_address}} "
                "(\"Client\"). Service Provider possesses specialized expertise and resources to "
                "provide certain professional services, and Client desires to engage Service Provider "
                "to perform such services on the terms and conditions set forth herein and in any "
                "Statements of Work executed hereunder. This Agreement establishes the general terms "
                "governing the relationship between the parties; specific project engagements shall "
                "be governed by individual Statements of Work incorporated by reference."
            ),
            guidance="Establishes Provider as the expert party with master/SOW structure.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Master Service Agreement (this \"Agreement\") is made and entered into as of "
                "{{effective_date}} (the \"Effective Date\") by and between {{party_1_name}}, "
                "a {{party_1_entity_type}} organized under the laws of {{party_1_jurisdiction}}, "
                "with offices at {{party_1_address}} (\"Service Provider\"), and {{party_2_name}}, "
                "a {{party_2_entity_type}} organized under the laws of {{party_2_jurisdiction}}, "
                "with offices at {{party_2_address}} (\"Client\"). The parties desire to establish "
                "terms under which Service Provider will provide, and Client will receive, certain "
                "professional services as described in one or more Statements of Work to be executed "
                "pursuant to this Agreement. Each Statement of Work shall be subject to the terms of "
                "this Agreement unless expressly modified therein."
            ),
            guidance="Neutral preamble with balanced party descriptions.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "This Master Service Agreement (this \"Agreement\") is entered into as of "
                "{{effective_date}} (the \"Effective Date\") by and between {{party_2_name}}, "
                "a {{party_2_entity_type}} organized under the laws of {{party_2_jurisdiction}}, "
                "with its principal place of business at {{party_2_address}} (\"Client\"), and "
                "{{party_1_name}}, a {{party_1_entity_type}} organized under the laws of "
                "{{party_1_jurisdiction}}, with its principal place of business at {{party_1_address}} "
                "(\"Service Provider\"). Client requires certain professional services and has "
                "selected Service Provider to perform such services subject to the terms herein. "
                "In the event of any conflict between this Agreement and any Statement of Work, "
                "the terms most favorable to Client shall control unless expressly stated otherwise "
                "in the applicable Statement of Work."
            ),
            guidance="Client-first ordering; conflict resolution favors Client.",
        ),
        category="boilerplate",
        required_defined_terms=["Service Provider", "Client"],
        position=1,
    ),

    # ── 2. DEFINITIONS ──────────────────────────────────────────────────
    _clause(
        "definitions",
        "Definitions",
        preferred=_tier(
            "provider-protective",
            (
                "As used in this Agreement, the following terms shall have the meanings set forth "
                "below: \"Confidential Information\" means any non-public information disclosed by "
                "either party, excluding information independently developed or publicly available. "
                "\"Deliverables\" means the tangible and intangible work product specifically "
                "identified as deliverables in a Statement of Work. \"Intellectual Property\" means "
                "all patents, copyrights, trade secrets, trademarks, and other proprietary rights. "
                "\"Pre-Existing IP\" means Intellectual Property owned by a party prior to the "
                "Effective Date or developed outside the scope of this Agreement. \"Services\" means "
                "the professional services described in each Statement of Work. \"Statement of Work\" "
                "or \"SOW\" means a written document executed by both parties that describes specific "
                "Services, Deliverables, timelines, and fees. \"Service Provider Materials\" means "
                "tools, methodologies, frameworks, and know-how developed by Service Provider "
                "independently of any engagement with Client."
            ),
            guidance="Broad definition of Provider Materials to protect reuse rights.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "As used in this Agreement: \"Confidential Information\" means any information "
                "disclosed by either party that is marked confidential or would reasonably be "
                "understood to be confidential given the nature of the information and the "
                "circumstances of disclosure. \"Deliverables\" means the specific work product "
                "identified as deliverables in an SOW. \"Intellectual Property\" or \"IP\" means "
                "all patents, copyrights, trade secrets, trademarks, and related rights. "
                "\"Pre-Existing IP\" means IP owned or controlled by a party before the Effective "
                "Date or developed independently of this Agreement. \"Services\" means the "
                "professional services described in an SOW. \"Statement of Work\" or \"SOW\" means "
                "a document signed by both parties specifying Services, Deliverables, schedules, "
                "fees, and acceptance criteria."
            ),
            guidance="Balanced definitions with standard scope.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "As used in this Agreement: \"Confidential Information\" means all information "
                "disclosed by either party in connection with this Agreement, whether oral, written, "
                "or electronic, regardless of whether marked as confidential. \"Deliverables\" means "
                "all work product, documentation, code, designs, and materials created by Service "
                "Provider in connection with the Services, whether or not identified in an SOW. "
                "\"Intellectual Property\" means all patents, copyrights, trade secrets, trademarks, "
                "moral rights, and other proprietary rights worldwide. \"Pre-Existing IP\" means IP "
                "owned by a party before the Effective Date, provided such ownership is documented "
                "in writing prior to commencement of Services. \"Services\" means all professional "
                "services performed by Service Provider for Client. \"Statement of Work\" means a "
                "document specifying Services, Deliverables, schedules, fees, acceptance criteria, "
                "and performance standards, signed by authorized representatives of both parties."
            ),
            guidance="Broad Deliverables definition; narrow Pre-Existing IP carve-out.",
        ),
        category="boilerplate",
        required_defined_terms=[
            "Confidential Information", "Deliverables", "Intellectual Property",
            "Pre-Existing IP", "Services", "Statement of Work",
            "Service Provider Materials",
        ],
        position=2,
    ),

    # ── 3. SERVICES SCOPE ───────────────────────────────────────────────
    _clause(
        "services_scope",
        "Scope of Services",
        preferred=_tier(
            "provider-protective",
            (
                "Service Provider shall perform the Services described in each Statement of Work "
                "executed under this Agreement. The scope of Services shall be limited to those "
                "expressly set forth in the applicable SOW. Any work requested by Client that falls "
                "outside the scope of an existing SOW shall require a new or amended SOW agreed to "
                "in writing by both parties, and Service Provider shall have no obligation to perform "
                "such out-of-scope work. Service Provider shall perform all Services in a professional "
                "and workmanlike manner consistent with generally accepted industry standards. Service "
                "Provider shall have sole discretion over the methods, means, and manner of performing "
                "the Services, provided the Deliverables meet the specifications in the applicable SOW."
            ),
            guidance="Strict scope limitation; Provider controls methods.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Service Provider shall perform the Services described in each Statement of Work "
                "executed under this Agreement. The parties acknowledge that each SOW defines the "
                "specific scope, timeline, and deliverables for a particular engagement. Changes "
                "to the scope of any SOW shall be documented in a written change order signed by "
                "both parties. Service Provider shall perform all Services in a professional and "
                "workmanlike manner consistent with industry standards applicable to the type of "
                "services being provided. Service Provider shall allocate qualified personnel to "
                "each engagement and shall consult with Client regarding the assignment of key "
                "personnel when reasonably requested."
            ),
            guidance="Mutual change order process; consultation on staffing.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Service Provider shall perform the Services described in each Statement of Work "
                "and any additional services reasonably necessary to achieve the objectives set "
                "forth therein. Service Provider shall perform all Services in a professional, "
                "timely, and workmanlike manner consistent with the highest industry standards "
                "applicable to the type of services provided. Service Provider shall assign "
                "appropriately skilled and experienced personnel to each engagement and shall "
                "not reassign or replace key personnel identified in an SOW without Client's "
                "prior written consent. Service Provider shall comply with all Client policies, "
                "procedures, and reasonable instructions communicated in writing, to the extent "
                "they relate to the performance of Services on Client premises or systems."
            ),
            guidance="Includes incidental services; Client approval for personnel changes.",
        ),
        category="commercial_terms",
        position=3,
    ),

    # ── 4. SOW STRUCTURE ────────────────────────────────────────────────
    _clause(
        "sow_structure",
        "Statement of Work Process",
        preferred=_tier(
            "provider-protective",
            (
                "Each engagement shall be governed by a Statement of Work executed by authorized "
                "representatives of both parties. Each SOW shall specify: (a) a description of "
                "the Services to be performed; (b) the Deliverables, if any; (c) the project "
                "timeline and milestones; (d) the fees and payment schedule; and (e) any special "
                "terms applicable to the engagement. No SOW shall be binding until signed by both "
                "parties. Service Provider may propose changes to an SOW if the scope, assumptions, "
                "or requirements change materially, and any change shall be documented in a written "
                "change order. Delay caused by Client's failure to provide timely information, "
                "feedback, or approvals shall extend all affected deadlines by a commensurate period."
            ),
            guidance="Change order mechanism; Client-delay extension clause.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Each engagement shall be governed by a Statement of Work signed by both parties. "
                "Each SOW shall include: (a) a description of Services; (b) Deliverables and "
                "acceptance criteria; (c) project timeline and milestones; (d) fees and payment "
                "terms; (e) assigned key personnel; and (f) any assumptions or dependencies. "
                "Changes to an SOW shall be documented in a written change order signed by both "
                "parties, describing the change, its impact on timeline and fees, and any revised "
                "Deliverables. Both parties shall cooperate in good faith to resolve disputes "
                "regarding the scope of work."
            ),
            guidance="Balanced SOW structure with acceptance criteria included.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Each engagement shall be governed by a detailed Statement of Work signed by both "
                "parties. Each SOW shall include at minimum: (a) a comprehensive description of "
                "Services; (b) Deliverables with detailed specifications and acceptance criteria; "
                "(c) a project plan with milestones, dependencies, and completion dates; (d) fixed "
                "fees or rate schedules with a not-to-exceed cap; (e) named key personnel and "
                "required qualifications; (f) assumptions and Client dependencies; and (g) "
                "performance metrics and service levels. Client may request reasonable changes "
                "to any SOW, and Service Provider shall promptly provide a written estimate of "
                "the impact on timeline and cost for Client's review and approval before "
                "proceeding with any changed work."
            ),
            guidance="Detailed SOW requirements; Client controls change approval.",
        ),
        category="commercial_terms",
        position=4,
    ),

    # ── 5. FEES AND PAYMENT ─────────────────────────────────────────────
    _clause(
        "fees_payment",
        "Fees and Payment",
        preferred=_tier(
            "provider-protective",
            (
                "Client shall pay Service Provider the fees set forth in each SOW in accordance "
                "with the payment schedule specified therein. Unless otherwise stated in the SOW, "
                "Service Provider shall invoice Client monthly in arrears for time-and-materials "
                "engagements or upon achievement of milestones for fixed-fee engagements. All "
                "invoices are due and payable within thirty (30) days of the invoice date. Late "
                "payments shall accrue interest at the lesser of one and one-half percent (1.5%) "
                "per month or the maximum rate permitted by law. All fees are exclusive of taxes, "
                "and Client shall be responsible for all applicable taxes, duties, and levies. "
                "Service Provider reserves the right to suspend Services if any invoice remains "
                "unpaid for more than fifteen (15) days past due after written notice."
            ),
            guidance="Net-30 terms; 1.5% monthly late fee; suspension right.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Client shall pay Service Provider the fees set forth in each SOW. Service Provider "
                "shall submit invoices in accordance with the schedule specified in the applicable "
                "SOW. All undisputed invoices are due and payable within forty-five (45) days of "
                "receipt. Client shall notify Service Provider in writing of any disputed charges "
                "within fifteen (15) days of receipt of the invoice, specifying the nature of the "
                "dispute in reasonable detail. Late payments on undisputed amounts shall accrue "
                "interest at one percent (1%) per month. All fees are exclusive of applicable taxes. "
                "Service Provider may adjust rates annually upon sixty (60) days' prior written "
                "notice, provided such adjustment does not exceed five percent (5%)."
            ),
            guidance="Net-45; dispute mechanism; capped annual rate increase.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Client shall pay Service Provider the fees set forth in each SOW, subject to "
                "Client's acceptance of Deliverables and satisfaction of applicable milestones. "
                "Invoices shall be submitted with reasonable supporting documentation. All invoices "
                "are due and payable within sixty (60) days of receipt. Client may withhold payment "
                "on any disputed amounts in good faith pending resolution, and such withholding "
                "shall not constitute a breach. Late payment interest, if any, shall not exceed "
                "the lesser of one-half percent (0.5%) per month or the maximum legal rate. Fees "
                "stated in an SOW are firm for the SOW term and shall not be increased without "
                "Client's written consent. Service Provider shall not suspend Services due to "
                "a payment dispute provided Client pays all undisputed amounts when due."
            ),
            guidance="Net-60; withholding on disputes; no unilateral rate increases.",
        ),
        category="commercial_terms",
        position=5,
    ),

    # ── 6. INTELLECTUAL PROPERTY ────────────────────────────────────────
    _clause(
        "intellectual_property",
        "Intellectual Property",
        preferred=_tier(
            "provider-protective",
            (
                "Pre-Existing IP. Each party shall retain all right, title, and interest in its "
                "Pre-Existing IP. Service Provider hereby grants Client a non-exclusive, perpetual, "
                "royalty-free license to use any Service Provider Pre-Existing IP incorporated into "
                "the Deliverables solely as necessary to use the Deliverables for Client's internal "
                "business purposes. Work Product. Subject to Service Provider's Pre-Existing IP and "
                "Service Provider Materials, Service Provider hereby assigns to Client all right, "
                "title, and interest in Deliverables created specifically for Client under an SOW. "
                "Service Provider Materials. Service Provider shall retain all rights in its tools, "
                "methodologies, frameworks, libraries, know-how, and general skills, including any "
                "improvements developed during the engagement, regardless of whether they are "
                "incorporated into Deliverables."
            ),
            guidance="Provider retains tools/methodologies; narrow assignment of custom work only.",
            key_terms={"ip_ownership": "custom_deliverables_only"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "Pre-Existing IP. Each party retains ownership of its Pre-Existing IP. Service "
                "Provider grants Client a non-exclusive, perpetual, irrevocable, royalty-free "
                "license to use, modify, and create derivative works of any Pre-Existing IP "
                "embedded in Deliverables, solely for Client's business purposes. Work Product. "
                "Upon full payment, Service Provider assigns to Client all right, title, and "
                "interest in Deliverables created under this Agreement, excluding Pre-Existing IP. "
                "Service Provider retains the right to use general knowledge, skills, experience, "
                "and non-confidential concepts acquired during performance."
            ),
            guidance="Assignment upon payment; Provider retains general knowledge.",
            key_terms={"ip_ownership": "assignment_upon_payment"},
        ),
        fallback=_tier(
            "client-protective",
            (
                "Pre-Existing IP. Each party retains ownership of its Pre-Existing IP, which must "
                "be identified in writing prior to incorporation into Deliverables. Service Provider "
                "grants Client a non-exclusive, perpetual, irrevocable, worldwide, royalty-free "
                "license to use, modify, sublicense, and distribute Pre-Existing IP incorporated "
                "into Deliverables. Work Product. All Deliverables and work product created by "
                "Service Provider in connection with the Services shall be deemed works made for "
                "hire and shall be the sole and exclusive property of Client. To the extent any "
                "Deliverable does not qualify as a work made for hire, Service Provider hereby "
                "irrevocably assigns to Client all rights therein. Service Provider shall execute "
                "all documents necessary to perfect Client's ownership."
            ),
            guidance="Work-for-hire; full assignment; broad license to Pre-Existing IP.",
            key_terms={"ip_ownership": "work_for_hire"},
        ),
        category="ip_ownership",
        required_defined_terms=["Deliverables", "Pre-Existing IP", "Intellectual Property"],
        position=6,
    ),

    # ── 7. CONFIDENTIALITY ──────────────────────────────────────────────
    _clause(
        "confidentiality",
        "Confidentiality",
        preferred=_tier(
            "provider-protective",
            (
                "Each party (as \"Receiving Party\") agrees that it will not disclose the other "
                "party's (the \"Disclosing Party's\") Confidential Information to any third party "
                "and will protect such information using at least the same degree of care it uses "
                "to protect its own confidential information, but in no event less than reasonable "
                "care. The Receiving Party may disclose Confidential Information to its employees, "
                "contractors, and professional advisors who need to know such information and who "
                "are bound by obligations of confidentiality no less restrictive than those herein. "
                "These obligations shall survive termination for a period of three (3) years. "
                "Confidential Information shall not include information that: (a) is or becomes "
                "publicly available through no fault of the Receiving Party; (b) was known to the "
                "Receiving Party prior to disclosure; (c) is independently developed; or (d) is "
                "received from a third party without restriction."
            ),
            guidance="Standard mutual confidentiality with 3-year survival.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Each party shall maintain the confidentiality of the other party's Confidential "
                "Information and shall not disclose it to any third party except as permitted herein. "
                "Each party shall use at least the same degree of care to protect the other's "
                "Confidential Information as it uses for its own, but no less than reasonable care. "
                "Disclosure is permitted to employees, agents, and subcontractors with a legitimate "
                "need to know who are bound by written confidentiality obligations. These obligations "
                "survive for five (5) years after disclosure or, for trade secrets, for so long as "
                "such information remains a trade secret under applicable law. Standard exclusions "
                "apply for public information, prior knowledge, independent development, and "
                "third-party disclosure without restriction."
            ),
            guidance="5-year survival; trade secret exception.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Service Provider acknowledges that in performing Services it may access Client's "
                "proprietary and confidential information, including business plans, customer data, "
                "technical specifications, and financial information. Service Provider shall hold "
                "all such Confidential Information in strict confidence and shall not use it for "
                "any purpose other than performing the Services. Service Provider shall limit access "
                "to Confidential Information to those personnel who require access and who have "
                "executed individual confidentiality agreements. These obligations shall survive "
                "indefinitely with respect to trade secrets and for five (5) years after "
                "termination for all other Confidential Information. Upon termination, Service "
                "Provider shall promptly return or destroy all Confidential Information and certify "
                "destruction in writing."
            ),
            guidance="Heightened obligations on Provider; indefinite trade secret survival.",
        ),
        category="confidentiality",
        required_defined_terms=["Confidential Information"],
        position=7,
    ),

    # ── 8. REPRESENTATIONS AND WARRANTIES ───────────────────────────────
    _clause(
        "reps_warranties",
        "Representations and Warranties",
        preferred=_tier(
            "provider-protective",
            (
                "Service Provider represents and warrants that: (a) it has the authority to enter "
                "into this Agreement; (b) Services will be performed in a professional and "
                "workmanlike manner consistent with generally accepted industry standards; and "
                "(c) Deliverables will conform to the specifications in the applicable SOW for "
                "a period of thirty (30) days following delivery (the \"Warranty Period\"). "
                "Client's sole remedy for breach of the Deliverables warranty shall be re-performance "
                "or correction of the non-conforming Deliverable. EXCEPT AS EXPRESSLY SET FORTH "
                "HEREIN, SERVICE PROVIDER MAKES NO OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING "
                "WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT."
            ),
            guidance="30-day warranty; re-performance as sole remedy; broad disclaimer.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Service Provider represents and warrants that: (a) it has the authority and "
                "capacity to enter into this Agreement and perform the Services; (b) Services "
                "will be performed in a professional manner consistent with industry standards; "
                "(c) Deliverables will materially conform to the specifications in the applicable "
                "SOW for sixty (60) days following acceptance; (d) the Services and Deliverables "
                "will not infringe any third-party intellectual property rights; and (e) it will "
                "comply with all applicable laws in performing the Services. Client represents and "
                "warrants that it has the authority to enter into this Agreement and will cooperate "
                "in good faith with Service Provider as reasonably necessary for performance."
            ),
            guidance="60-day warranty; mutual reps; non-infringement included.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Service Provider represents and warrants that: (a) it has full authority and "
                "capacity to perform the Services; (b) Services will be performed with the degree "
                "of skill and care expected of leading professionals in the applicable field; "
                "(c) Deliverables will conform to all specifications, requirements, and acceptance "
                "criteria set forth in the applicable SOW for ninety (90) days following acceptance; "
                "(d) the Services, Deliverables, and any materials provided will not infringe, "
                "misappropriate, or violate any third-party rights; (e) all personnel performing "
                "Services are qualified and properly licensed; and (f) it will comply with all "
                "applicable laws, regulations, and industry standards. If Deliverables fail to "
                "conform, Service Provider shall promptly correct or re-perform at no additional "
                "cost, or Client may terminate the applicable SOW for a full refund of fees paid."
            ),
            guidance="90-day warranty; refund remedy; highest standard of care.",
        ),
        category="representations",
        position=8,
    ),

    # ── 9. INDEMNIFICATION ──────────────────────────────────────────────
    _clause(
        "indemnification",
        "Indemnification",
        preferred=_tier(
            "provider-protective",
            (
                "Service Provider shall indemnify, defend, and hold harmless Client from third-party "
                "claims arising from Service Provider's gross negligence, willful misconduct, or "
                "infringement of third-party intellectual property rights by the Deliverables, "
                "provided Client gives prompt written notice, grants sole control of the defense, "
                "and provides reasonable cooperation. Client shall indemnify, defend, and hold "
                "harmless Service Provider from third-party claims arising from Client's use of "
                "Deliverables in violation of this Agreement, Client's negligence or willful "
                "misconduct, or Client-provided materials. Each party's indemnification obligations "
                "are subject to the limitation of liability provisions herein."
            ),
            guidance="Mutual indemnity; Provider limited to gross negligence and IP claims.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Each party (the \"Indemnifying Party\") shall indemnify, defend, and hold harmless "
                "the other party and its affiliates, officers, directors, and employees (the "
                "\"Indemnified Party\") from and against all third-party claims, damages, losses, "
                "and reasonable expenses (including attorneys' fees) arising from: (a) the "
                "Indemnifying Party's breach of this Agreement; (b) the Indemnifying Party's "
                "negligence or willful misconduct; or (c) infringement of third-party intellectual "
                "property rights by materials provided by the Indemnifying Party. The Indemnified "
                "Party shall provide prompt notice, reasonable cooperation, and the right to "
                "participate in the defense at its own expense."
            ),
            guidance="Symmetric mutual indemnity including breach.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Service Provider shall indemnify, defend, and hold harmless Client and its "
                "affiliates, officers, directors, employees, and agents from and against all claims, "
                "damages, losses, liabilities, and expenses (including reasonable attorneys' fees) "
                "arising from or related to: (a) any breach of this Agreement by Service Provider; "
                "(b) negligent or wrongful acts or omissions of Service Provider or its personnel; "
                "(c) infringement or misappropriation of any third-party rights by the Services or "
                "Deliverables; or (d) Service Provider's failure to comply with applicable laws. "
                "Client shall indemnify Service Provider solely against claims arising from Client's "
                "gross negligence or willful misconduct. Service Provider's indemnification "
                "obligations shall not be subject to any limitation of liability."
            ),
            guidance="Broad Provider indemnity; narrow Client indemnity; uncapped.",
        ),
        category="indemnification",
        position=9,
    ),

    # ── 10. LIMITATION OF LIABILITY ─────────────────────────────────────
    _clause(
        "limitation_of_liability",
        "Limitation of Liability",
        preferred=_tier(
            "provider-protective",
            (
                "EXCEPT FOR BREACHES OF CONFIDENTIALITY OR A PARTY'S INDEMNIFICATION OBLIGATIONS, "
                "NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
                "CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOST PROFITS, LOST REVENUE, OR LOSS "
                "OF DATA, REGARDLESS OF THE THEORY OF LIABILITY. EXCEPT FOR BREACHES OF "
                "CONFIDENTIALITY, EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT "
                "SHALL NOT EXCEED THE FEES PAID OR PAYABLE BY CLIENT TO SERVICE PROVIDER UNDER "
                "THE APPLICABLE STATEMENT OF WORK GIVING RISE TO THE CLAIM DURING THE SIX (6) "
                "MONTHS PRECEDING THE EVENT GIVING RISE TO LIABILITY."
            ),
            guidance="Per-SOW cap at 6 months' fees; broad consequential damages waiver.",
            key_terms={"liability_cap": "6_months_per_sow"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "EXCEPT FOR (I) BREACHES OF CONFIDENTIALITY, (II) INDEMNIFICATION OBLIGATIONS, OR "
                "(III) A PARTY'S GROSS NEGLIGENCE OR WILLFUL MISCONDUCT, NEITHER PARTY SHALL BE "
                "LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. "
                "EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED "
                "THE TOTAL FEES PAID OR PAYABLE BY CLIENT UNDER THE APPLICABLE SOW DURING THE "
                "TWELVE (12) MONTHS PRECEDING THE FIRST EVENT GIVING RISE TO LIABILITY."
            ),
            guidance="Per-SOW cap at 12 months' fees; standard carve-outs.",
            key_terms={"liability_cap": "12_months_per_sow"},
        ),
        fallback=_tier(
            "client-protective",
            (
                "SERVICE PROVIDER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATING TO THIS "
                "AGREEMENT SHALL NOT EXCEED THE GREATER OF (A) THE TOTAL FEES PAID AND PAYABLE "
                "UNDER ALL STATEMENTS OF WORK DURING THE TWENTY-FOUR (24) MONTHS PRECEDING THE "
                "EVENT GIVING RISE TO LIABILITY, OR (B) ONE MILLION DOLLARS ($1,000,000). THIS "
                "LIMITATION SHALL NOT APPLY TO SERVICE PROVIDER'S INDEMNIFICATION OBLIGATIONS, "
                "BREACHES OF CONFIDENTIALITY, INTELLECTUAL PROPERTY INFRINGEMENT, OR GROSS "
                "NEGLIGENCE OR WILLFUL MISCONDUCT. CLIENT'S LIABILITY SHALL NOT EXCEED THE "
                "FEES PAYABLE UNDER THE APPLICABLE SOW. NEITHER PARTY SHALL BE LIABLE FOR "
                "INDIRECT OR CONSEQUENTIAL DAMAGES EXCEPT TO THE EXTENT ARISING FROM BREACHES "
                "OF CONFIDENTIALITY OR IP INFRINGEMENT."
            ),
            guidance="24-month aggregate cap with $1M floor; broad carve-outs for Provider.",
            key_terms={"liability_cap": "24_months_aggregate_or_1m"},
        ),
        category="limitation_of_liability",
        position=10,
    ),

    # ── 11. INSURANCE ───────────────────────────────────────────────────
    _clause(
        "insurance",
        "Insurance",
        preferred=_tier(
            "provider-protective",
            (
                "Service Provider shall maintain during the term of this Agreement: (a) commercial "
                "general liability insurance with limits of not less than one million dollars "
                "($1,000,000) per occurrence; (b) professional liability (errors and omissions) "
                "insurance with limits of not less than one million dollars ($1,000,000) per claim; "
                "and (c) workers' compensation insurance as required by applicable law. Service "
                "Provider shall provide certificates of insurance upon Client's reasonable request. "
                "The foregoing insurance requirements shall not be construed to limit Service "
                "Provider's liability under this Agreement."
            ),
            guidance="Standard minimums; certificates on request only.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Service Provider shall maintain during the term and for two (2) years thereafter: "
                "(a) commercial general liability insurance with limits of not less than two million "
                "dollars ($2,000,000) per occurrence and four million dollars ($4,000,000) aggregate; "
                "(b) professional liability insurance with limits of not less than two million dollars "
                "($2,000,000) per claim; (c) cyber liability insurance with limits of not less than "
                "one million dollars ($1,000,000); and (d) workers' compensation insurance as required "
                "by law. Service Provider shall name Client as an additional insured on the general "
                "liability policy and provide certificates annually and upon request."
            ),
            guidance="Higher limits; cyber liability; additional insured; 2-year tail.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Service Provider shall maintain during the term and for three (3) years thereafter: "
                "(a) commercial general liability insurance with limits of not less than five million "
                "dollars ($5,000,000) per occurrence; (b) professional liability insurance with limits "
                "of not less than five million dollars ($5,000,000) per claim and aggregate; "
                "(c) cyber liability insurance with limits of not less than five million dollars "
                "($5,000,000); (d) workers' compensation as required by law; and (e) employer's "
                "liability insurance of one million dollars ($1,000,000). Service Provider shall "
                "name Client as an additional insured, provide thirty (30) days' advance notice "
                "of cancellation or material change, and furnish certificates of insurance prior "
                "to commencing Services and annually thereafter."
            ),
            guidance="$5M limits; 3-year tail; cancellation notice; certificates proactively.",
        ),
        category="commercial_terms",
        position=11,
    ),

    # ── 12. TERM AND TERMINATION ────────────────────────────────────────
    _clause(
        "term_termination",
        "Term and Termination",
        preferred=_tier(
            "provider-protective",
            (
                "This Agreement shall commence on the Effective Date and continue for an initial "
                "term of {{term_months}} months (the \"Initial Term\"), after which it shall "
                "automatically renew for successive one-year periods unless either party provides "
                "at least sixty (60) days' written notice of non-renewal. Either party may terminate "
                "this Agreement for material breach if such breach remains uncured for thirty (30) "
                "days following written notice. Service Provider may terminate immediately upon "
                "written notice if Client fails to pay undisputed fees within sixty (60) days of "
                "their due date. Upon termination, Client shall pay all fees for Services performed "
                "through the effective date of termination, including work in progress."
            ),
            guidance="Auto-renewal; 30-day cure period; payment for WIP on termination.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Agreement shall commence on the Effective Date and continue for {{term_months}} "
                "months, automatically renewing for successive twelve-month terms unless either party "
                "provides ninety (90) days' written notice of non-renewal. Either party may terminate "
                "this Agreement for material breach if such breach remains uncured thirty (30) days "
                "after written notice specifying the breach. Either party may terminate immediately "
                "if the other party becomes insolvent, files for bankruptcy, or ceases operations. "
                "Upon termination, (a) each party shall return or destroy the other's Confidential "
                "Information, (b) Client shall pay for all Services performed through termination, "
                "and (c) Service Provider shall deliver all completed and in-progress Deliverables."
            ),
            guidance="Balanced termination; WIP deliverables returned; insolvency trigger.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "This Agreement shall commence on the Effective Date and continue for {{term_months}} "
                "months. Renewal shall require written agreement of both parties. Client may terminate "
                "this Agreement or any SOW for convenience upon thirty (30) days' written notice, in "
                "which case Client shall pay only for Services satisfactorily performed through the "
                "termination date. Either party may terminate for material breach if such breach "
                "remains uncured fifteen (15) days after written notice. Upon termination for any "
                "reason: (a) Service Provider shall immediately deliver all Deliverables, work in "
                "progress, and Client materials; (b) Service Provider shall cooperate in transitioning "
                "Services to Client or a successor provider; and (c) all licenses granted to Client "
                "hereunder shall survive. Service Provider shall refund any prepaid fees for Services "
                "not yet performed."
            ),
            guidance="Termination for convenience; 15-day cure; transition assistance; refunds.",
        ),
        category="termination",
        required_defined_terms=["Term", "Initial Term", "Renewal Term"],
        position=12,
    ),

    # ── 13. DISPUTE RESOLUTION ──────────────────────────────────────────
    _clause(
        "dispute_resolution",
        "Dispute Resolution",
        preferred=_tier(
            "provider-protective",
            (
                "This Agreement shall be governed by and construed in accordance with the laws of "
                "{{governing_law}}, without regard to its conflict of laws principles. Any dispute "
                "arising out of or relating to this Agreement shall first be submitted to good faith "
                "negotiation between senior executives for thirty (30) days. If unresolved, the "
                "dispute shall be resolved by binding arbitration administered by the American "
                "Arbitration Association under its Commercial Arbitration Rules, conducted in "
                "{{venue}} before a single arbitrator. The arbitrator's award shall be final and "
                "binding. Each party shall bear its own attorneys' fees and costs, and the parties "
                "shall share arbitration costs equally."
            ),
            guidance="Arbitration preferred; shared costs; single arbitrator.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Agreement shall be governed by the laws of {{governing_law}}, without regard "
                "to conflict of laws provisions. The parties shall attempt to resolve any dispute "
                "through good faith negotiation for thirty (30) days, followed by mediation for "
                "an additional thirty (30) days if negotiation fails. If the dispute remains "
                "unresolved, either party may submit it to binding arbitration under the rules "
                "of the American Arbitration Association, conducted in {{venue}} before a single "
                "arbitrator. The prevailing party shall be entitled to recover its reasonable "
                "attorneys' fees and costs. Nothing herein shall prevent either party from "
                "seeking injunctive or equitable relief in a court of competent jurisdiction."
            ),
            guidance="Escalation: negotiation, mediation, arbitration; fee-shifting.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "This Agreement shall be governed by and construed in accordance with the laws of "
                "{{governing_law}}, without regard to conflict of laws principles. Any dispute "
                "arising under this Agreement shall be resolved exclusively in the state or federal "
                "courts located in {{venue}}, and Service Provider hereby consents to the personal "
                "jurisdiction of such courts. Service Provider waives any objection to venue or "
                "inconvenient forum. The prevailing party shall be entitled to recover its reasonable "
                "attorneys' fees, costs, and expenses from the non-prevailing party. Client shall "
                "be entitled to seek injunctive relief without posting a bond."
            ),
            guidance="Litigation in Client's venue; fee-shifting; injunctive relief without bond.",
        ),
        category="dispute_resolution",
        position=13,
    ),

    # ── 14. BOILERPLATE ─────────────────────────────────────────────────
    _clause(
        "boilerplate",
        "General Provisions",
        preferred=_tier(
            "provider-protective",
            (
                "Assignment. Neither party may assign this Agreement without the other's prior "
                "written consent, except that Service Provider may assign this Agreement to an "
                "affiliate or in connection with a merger, acquisition, or sale of substantially "
                "all of its assets. Notices. All notices shall be in writing and sent to the "
                "addresses set forth above, and shall be deemed given upon personal delivery, one "
                "business day after overnight courier, or three business days after deposit in the "
                "mail. Force Majeure. Neither party shall be liable for delays or failures caused "
                "by events beyond its reasonable control, including acts of God, pandemics, "
                "government actions, or internet disruptions. Severability. If any provision is "
                "held invalid, the remaining provisions shall continue in full force. Entire "
                "Agreement. This Agreement, together with all SOWs and exhibits, constitutes the "
                "entire agreement between the parties and supersedes all prior agreements. "
                "Independent Contractor. Service Provider is an independent contractor and nothing "
                "herein creates an employment, partnership, or agency relationship."
            ),
            guidance="Provider can assign to affiliates/successors; standard boilerplate.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Assignment. Neither party may assign this Agreement without prior written consent, "
                "not to be unreasonably withheld. Either party may assign to an affiliate or "
                "successor in a merger or acquisition upon written notice. Notices. All notices "
                "shall be in writing, sent to the addresses above, and are effective upon confirmed "
                "delivery. Force Majeure. Neither party shall be liable for failure to perform due "
                "to events beyond reasonable control; the affected party shall use commercially "
                "reasonable efforts to mitigate the impact and resume performance promptly. "
                "Severability. Invalid provisions shall be reformed to the minimum extent necessary "
                "to make them valid while preserving intent. Entire Agreement. This Agreement and "
                "all SOWs constitute the entire agreement. Amendments require written agreement "
                "signed by both parties. Waiver. No waiver of any right shall be effective unless "
                "in writing signed by the waiving party."
            ),
            guidance="Mutual assignment to affiliates; reformation; waiver clause.",
        ),
        fallback=_tier(
            "client-protective",
            (
                "Assignment. Service Provider may not assign or subcontract this Agreement or any "
                "SOW without Client's prior written consent. Client may freely assign this Agreement "
                "to any affiliate or successor entity. Notices. All notices shall be in writing "
                "and deemed effective upon receipt via email with confirmation, personal delivery, "
                "or overnight courier. Force Majeure. If a force majeure event prevents performance "
                "for more than thirty (30) days, Client may terminate the affected SOW without "
                "liability. Severability. If any provision is held invalid, it shall be modified to "
                "the minimum extent necessary, and all other provisions shall remain in effect. "
                "Entire Agreement. This Agreement and all SOWs constitute the entire agreement. "
                "No modification is effective unless in writing signed by both parties. Order of "
                "Precedence. In the event of conflict: (1) this Agreement, (2) the applicable SOW, "
                "(3) any exhibits, unless the SOW expressly states otherwise."
            ),
            guidance="Client can freely assign; Provider needs consent; force majeure termination right.",
        ),
        category="boilerplate",
        position=14,
    ),

    # ── 15. SIGNATURE ───────────────────────────────────────────────────
    _clause(
        "signature",
        "Signature",
        preferred=_tier(
            "provider-protective",
            (
                "IN WITNESS WHEREOF, the parties have caused this Master Service Agreement to be "
                "executed by their duly authorized representatives as of the Effective Date.\n\n"
                "{{party_1_name}}\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "{{party_2_name}}\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________"
            ),
        ),
        acceptable=_tier(
            "balanced",
            (
                "IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective "
                "Date first written above.\n\n"
                "{{party_1_name}}\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "{{party_2_name}}\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________"
            ),
        ),
        fallback=_tier(
            "client-protective",
            (
                "IN WITNESS WHEREOF, the parties have executed this Master Service Agreement by "
                "their authorized representatives.\n\n"
                "{{party_2_name}} (Client)\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "{{party_1_name}} (Service Provider)\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________"
            ),
        ),
        category="boilerplate",
        position=15,
    ),
]

# ---------------------------------------------------------------------------
# Exported playbook
# ---------------------------------------------------------------------------

_MSA_FORBIDDEN_TERMS: List[str] = [
    # NDA vocabulary
    "Disclosing Party", "Receiving Party",
    # SaaS vocabulary — MSA uses Service Provider / Client, not Provider / Customer
    "Provider", "Customer", "Subscription", "Subscription Services",
    "SaaS", "Order Form",
    # Employment vocabulary
    "Employer", "Employee",
    # Legacy placeholder tokens
    "[Client Name]", "[Service Provider Name]",
]

_MSA_DIRECTIVES: List[str] = [
    "This is a Master Service Agreement. The ONLY defined role terms are "
    "'Service Provider' (the party performing the services) and 'Client' "
    "(the party receiving the services). NEVER use 'Provider' / "
    "'Customer' (SaaS), 'Disclosing Party' / 'Receiving Party' (NDA), "
    "or 'Employer' / 'Employee' — those role labels are not defined in "
    "this Agreement.",
    "This is a framework / umbrella agreement. Specific engagements, "
    "deliverables, timelines, and fees are set out in Statements of Work "
    "('SOWs') executed under this MSA. Do NOT treat this MSA as a "
    "subscription agreement. Reference the SOW structure where scope or "
    "deliverables come up.",
    "Deliverables and work product are owned by or licensed to the Client "
    "per the ownership clause — never introduce SaaS 'subscription' "
    "language or call the work output 'the Services' in a subscription "
    "sense.",
]

_MSA_CLAUSE_DIRECTIVES: Dict[str, List[str]] = {
    "preamble": [
        "Identify each Party's full legal name, entity type, jurisdiction "
        "of organisation, and principal place of business. Use 'Service "
        "Provider' for Party 1 and 'Client' for Party 2 as the short-"
        "names for the remainder of the Agreement."
    ],
    "confidentiality": [
        "Confidentiality obligations in an MSA flow between 'Service "
        "Provider' and 'Client' mutually. Do NOT introduce NDA "
        "'Disclosing Party' / 'Receiving Party' role labels. If the prose "
        "needs to distinguish direction of disclosure, use lower-case "
        "descriptive phrases like 'the disclosing party' or 'the "
        "receiving party' — they are not defined terms here."
    ],
}

_MSA_DETECTORS: List[Dict[str, Any]] = [
    {"type": "forbidden_terms"},
    {"type": "truncated_clause"},
    {"type": "nested_quote_duplication"},
    {"type": "entity_jurisdiction_mismatch"},
]


MSA_PLAYBOOK: Dict[str, Any] = {
    "name": "Master Service Agreement",
    "contract_type": "msa",
    "jurisdiction": "Any",
    "section_order": _SECTION_ORDER,
    # --- Modular metadata consumed by the Draft Agent ---
    "roles": {
        "service_provider": {"label": "Service Provider", "party": "party_1"},
        "client": {"label": "Client", "party": "party_2"},
    },
    "forbidden_terms": list(_MSA_FORBIDDEN_TERMS),
    "mandatory_directives": list(_MSA_DIRECTIVES),
    "clause_mandatory_directives": dict(_MSA_CLAUSE_DIRECTIVES),
    "detectors": list(_MSA_DETECTORS),
    # ----------------------------------------------------
    "clauses": _CLAUSES,
}
