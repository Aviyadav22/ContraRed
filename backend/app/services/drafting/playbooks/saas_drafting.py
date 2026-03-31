"""
SaaS Agreement Drafting Playbook — MSA + SLA + DPA + Order Form
================================================================
Comprehensive Software-as-a-Service agreement playbook with 22 sections
at three negotiation tiers (preferred / acceptable / fallback).

Perspective: Vendor (Provider) side.
  - preferred  = vendor-protective
  - acceptable = balanced
  - fallback   = customer-protective

Placeholders ({{mustache}} syntax):
  {{provider_name}}, {{customer_name}}, {{provider_entity_type}},
  {{customer_entity_type}}, {{provider_jurisdiction}}, {{customer_jurisdiction}},
  {{provider_address}}, {{customer_address}}, {{provider_short_name}},
  {{customer_short_name}}, {{effective_date}}, {{term_months}},
  {{governing_law}}, {{dispute_resolution}}, {{venue}},
  {{service_description}}, {{pricing_model}}, {{price_amount}},
  {{billing_frequency}}, {{uptime_commitment}}, {{authorized_users}},
  {{auto_renewal_text}}, {{annual_value}}, {{confidentiality_survival_years}}
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
    "scope_of_services",
    "grant_of_license",
    "customer_obligations",
    "fees_and_payment",
    "intellectual_property",
    "data_ownership",
    "confidentiality",
    "representations_warranties",
    "disclaimers",
    "indemnification",
    "limitation_of_liability",
    "data_security",
    "term_and_termination",
    "effects_of_termination",
    "dispute_resolution",
    "boilerplate",
    "signature_blocks",
    "sla",
    "dpa",
    "order_form",
]

# ---------------------------------------------------------------------------
# Clauses
# ---------------------------------------------------------------------------

_CLAUSES: List[Dict[str, Any]] = [
    # ── 1. PREAMBLE ──────────────────────────────────────────────────────
    _clause(
        "preamble",
        "Preamble",
        preferred=_tier(
            "vendor-protective",
            (
                "This Software-as-a-Service Agreement (this \"Agreement\") is entered into "
                "as of {{effective_date}} (the \"Effective Date\") by and between "
                "{{provider_name}}, a {{provider_entity_type}} organized under the laws of "
                "{{provider_jurisdiction}}, with its principal place of business at "
                "{{provider_address}} (\"Provider\"), and {{customer_name}}, a "
                "{{customer_entity_type}} organized under the laws of "
                "{{customer_jurisdiction}}, with its principal place of business at "
                "{{customer_address}} (\"Customer\"). Provider has developed and operates "
                "a proprietary cloud-based software platform described herein, and Customer "
                "desires to subscribe to and access such platform subject to the terms and "
                "conditions set forth in this Agreement."
            ),
            guidance="Standard preamble identifying both parties and the nature of the SaaS relationship.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Software-as-a-Service Agreement (this \"Agreement\") is made and "
                "entered into as of {{effective_date}} (the \"Effective Date\") by and "
                "between {{provider_name}}, a {{provider_entity_type}} organized under the "
                "laws of {{provider_jurisdiction}} (\"Provider\"), and {{customer_name}}, a "
                "{{customer_entity_type}} organized under the laws of "
                "{{customer_jurisdiction}} (\"Customer\"). Provider offers a cloud-based "
                "software platform, and Customer wishes to subscribe to such platform "
                "under mutually agreed terms. Provider and Customer are each referred to "
                "individually as a \"Party\" and collectively as the \"Parties.\""
            ),
            guidance="Balanced preamble with mutual Party definitions.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "This Software-as-a-Service Agreement (this \"Agreement\") is entered into "
                "as of {{effective_date}} (the \"Effective Date\") by and between "
                "{{provider_name}}, a {{provider_entity_type}} with offices at "
                "{{provider_address}} (\"Provider\" or \"Vendor\"), and {{customer_name}}, "
                "a {{customer_entity_type}} with offices at {{customer_address}} "
                "(\"Customer\" or \"Subscriber\"). WHEREAS, Customer requires access to "
                "certain cloud-based software services for its business operations; and "
                "WHEREAS, Provider represents that it is capable of providing such services "
                "in accordance with industry best practices and the service levels specified "
                "herein; NOW, THEREFORE, in consideration of the mutual covenants and "
                "agreements set forth below, the Parties agree as follows."
            ),
            guidance="Customer-protective preamble with recitals and best-practices representation.",
        ),
        position=1,
    ),

    # ── 2. DEFINITIONS ───────────────────────────────────────────────────
    _clause(
        "definitions",
        "Definitions",
        preferred=_tier(
            "vendor-protective",
            (
                "1. DEFINITIONS. As used in this Agreement, the following terms shall have "
                "the meanings set forth below:\n\n"
                "(a) \"Authorized Users\" means the employees, contractors, or agents of "
                "Customer who are authorized by Customer to access and use the Service, "
                "not to exceed {{authorized_users}} individuals unless otherwise agreed in "
                "an Order Form.\n\n"
                "(b) \"Customer Data\" means any data, information, or material submitted "
                "by Customer or its Authorized Users to the Service in the course of using "
                "the Service.\n\n"
                "(c) \"Documentation\" means Provider's then-current user guides, online "
                "help files, and technical documentation for the Service as made generally "
                "available by Provider.\n\n"
                "(d) \"Service\" means the cloud-based software application described in "
                "the applicable Order Form and as further described at "
                "{{service_description}}, including all Updates made available by Provider.\n\n"
                "(e) \"Service Level Agreement\" or \"SLA\" means the service level "
                "commitments set forth in Exhibit A attached hereto.\n\n"
                "(f) \"Subscription Term\" means the initial period of {{term_months}} "
                "months commencing on the Effective Date, and any renewal terms thereafter.\n\n"
                "(g) \"Updates\" means bug fixes, patches, and minor feature enhancements "
                "that Provider makes generally available to its subscribers at no additional "
                "charge. Updates do not include new products or major feature releases that "
                "Provider markets as separate offerings."
            ),
            guidance="Vendor-oriented definitions; narrow scope of Service and Updates.",
            key_terms={"authorized_users": "{{authorized_users}}", "term_months": "{{term_months}}"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "1. DEFINITIONS. For the purposes of this Agreement:\n\n"
                "(a) \"Authorized Users\" means the individuals designated by Customer to "
                "access and use the Service, up to the number specified in the applicable "
                "Order Form (initially {{authorized_users}}).\n\n"
                "(b) \"Customer Data\" means all electronic data, information, content, and "
                "materials submitted by or on behalf of Customer through the Service, "
                "including personal data as defined under applicable data protection laws.\n\n"
                "(c) \"Documentation\" means all user manuals, operating procedures, "
                "technical specifications, and online help materials provided by Provider "
                "in connection with the Service.\n\n"
                "(d) \"Intellectual Property Rights\" means all patents, copyrights, trade "
                "secrets, trademarks, and other proprietary rights recognized under "
                "applicable law.\n\n"
                "(e) \"Service\" means the software-as-a-service offering described in the "
                "applicable Order Form, including {{service_description}}, together with "
                "all Updates and Upgrades made generally available.\n\n"
                "(f) \"SLA\" means the Service Level Agreement attached as Exhibit A.\n\n"
                "(g) \"Subscription Term\" has the meaning set forth in Section 14.\n\n"
                "(h) \"Updates\" means modifications, bug fixes, patches, and enhancements "
                "to the Service. \"Upgrades\" means major new versions or modules of the "
                "Service that Provider makes generally available."
            ),
            guidance="Balanced definitions including Upgrades and broader Customer Data scope.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "1. DEFINITIONS. The following capitalized terms shall have the meanings "
                "ascribed to them below. Any capitalized terms not defined in this Section "
                "shall have the meanings given to them elsewhere in this Agreement.\n\n"
                "(a) \"Authorized Users\" means Customer's employees, contractors, agents, "
                "and third-party service providers who require access to the Service in "
                "connection with Customer's business operations, not subject to any "
                "numerical limit except as set forth in the Order Form.\n\n"
                "(b) \"Customer Data\" means all data, content, materials, and information "
                "of any kind that Customer or its Authorized Users upload, store, transmit, "
                "or process through the Service, including all personal data, metadata, "
                "usage analytics derived from Customer Data, and any derivatives thereof.\n\n"
                "(c) \"Documentation\" means all user guides, API documentation, technical "
                "specifications, training materials, and integration guides provided or "
                "made available by Provider.\n\n"
                "(d) \"Service\" means the complete software-as-a-service platform described "
                "in the Order Form, including {{service_description}}, together with all "
                "Updates, Upgrades, new features, modules, integrations, and enhancements "
                "made available during the Subscription Term at no additional charge.\n\n"
                "(e) \"SLA\" means the Service Level Agreement attached as Exhibit A, "
                "which forms an integral and enforceable part of this Agreement.\n\n"
                "(f) \"Subscription Term\" has the meaning set forth in Section 14.\n\n"
                "(g) \"Professional Services\" means any implementation, customization, "
                "training, or consulting services provided by Provider under a Statement "
                "of Work."
            ),
            guidance="Customer-protective: broad Service definition, analytics included in Customer Data.",
        ),
        position=2,
        required_defined_terms=["Service", "Customer Data", "Authorized Users", "SLA"],
    ),

    # ── 3. SCOPE OF SERVICES ─────────────────────────────────────────────
    _clause(
        "scope_of_services",
        "Scope of Services",
        preferred=_tier(
            "vendor-protective",
            (
                "2. SCOPE OF SERVICES. Subject to the terms and conditions of this "
                "Agreement and payment of all applicable Fees, Provider shall make the "
                "Service available to Customer during the Subscription Term as described "
                "in the applicable Order Form. The Service shall be provided on a "
                "subscription basis and accessed via the internet through a standard web "
                "browser or Provider's designated application. Provider reserves the right "
                "to modify the features and functionality of the Service from time to time, "
                "provided that such modifications do not materially diminish the core "
                "functionality of the Service during the then-current Subscription Term. "
                "Provider may offer additional services, modules, or integrations for "
                "separate fees as set forth in supplemental Order Forms."
            ),
            guidance="Provider retains broad right to modify Service features.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "2. SCOPE OF SERVICES. During the Subscription Term, Provider shall "
                "provide Customer with access to the Service as described in the applicable "
                "Order Form and in accordance with the SLA. The Service includes access to "
                "the platform described at {{service_description}}, the Documentation, and "
                "standard customer support as specified in the SLA. Provider may update or "
                "modify the Service from time to time, provided that: (a) such changes do "
                "not materially reduce the functionality available to Customer; and (b) "
                "Provider gives Customer at least thirty (30) days' prior written notice of "
                "any material changes. Any new features or modules added to the Service "
                "during the Subscription Term shall be made available to Customer at no "
                "additional charge unless designated as premium features."
            ),
            guidance="Balanced: notice requirement for material changes; new features included unless premium.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "2. SCOPE OF SERVICES. Provider shall make the Service available to "
                "Customer during the Subscription Term in accordance with this Agreement, "
                "the SLA, and the applicable Order Form. The Service shall include, without "
                "limitation: (a) the full platform functionality described at "
                "{{service_description}}; (b) all Documentation and training materials; "
                "(c) all Updates, Upgrades, and new features released during the "
                "Subscription Term; (d) standard and priority customer support as set forth "
                "in the SLA; and (e) data migration assistance upon onboarding and "
                "offboarding. Provider shall not materially reduce, degrade, or remove any "
                "features or functionality of the Service during the Subscription Term "
                "without Customer's prior written consent. Provider shall maintain the "
                "Service in compliance with all applicable laws, regulations, and industry "
                "standards, including SOC 2 Type II and ISO 27001 certifications."
            ),
            guidance="Customer-protective: no reduction without consent; compliance certifications required.",
        ),
        position=3,
        cross_references=["sla", "order_form"],
    ),

    # ── 4. GRANT OF LICENSE ──────────────────────────────────────────────
    _clause(
        "grant_of_license",
        "Grant of License",
        preferred=_tier(
            "vendor-protective",
            (
                "3. GRANT OF LICENSE. Subject to Customer's compliance with all terms of "
                "this Agreement, Provider hereby grants to Customer a limited, "
                "non-exclusive, non-transferable, non-sublicensable right to access and "
                "use the Service during the Subscription Term solely for Customer's "
                "internal business purposes and in accordance with the Documentation. "
                "This license does not convey any ownership interest in the Service or any "
                "right to use the Service beyond the scope expressly authorized herein. "
                "Customer shall not permit access to the Service by any party other than "
                "its Authorized Users. Any use of the Service in excess of the authorized "
                "scope shall constitute a material breach of this Agreement."
            ),
            guidance="Narrow license with strict scope; excess use is material breach.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "3. GRANT OF LICENSE. Provider grants to Customer a non-exclusive, "
                "non-transferable right to access and use the Service during the "
                "Subscription Term for Customer's internal business purposes, subject to "
                "the terms of this Agreement. Customer may permit its Authorized Users "
                "and its affiliates' employees to access the Service, provided that "
                "Customer remains responsible for such users' compliance with this "
                "Agreement. Customer may use the Service through APIs and third-party "
                "integrations in accordance with the Documentation and any published API "
                "usage policies."
            ),
            guidance="Moderate license scope; affiliate access and API use permitted.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "3. GRANT OF LICENSE. Provider grants to Customer a non-exclusive, "
                "worldwide right to access and use the Service during the Subscription "
                "Term for Customer's internal business purposes and for the benefit of "
                "Customer's affiliates, subsidiaries, clients, and end users as reasonably "
                "necessary in the ordinary course of Customer's business. Customer may "
                "sublicense access to the Service to its affiliates and subsidiaries "
                "without additional fees, provided the total number of Authorized Users "
                "does not exceed the applicable Order Form limits. Customer may access "
                "the Service through APIs, integrations, automated scripts, and any other "
                "programmatic means consistent with the Documentation."
            ),
            guidance="Broad license with sublicensing to affiliates and wide usage rights.",
        ),
        position=4,
    ),

    # ── 5. CUSTOMER OBLIGATIONS ──────────────────────────────────────────
    _clause(
        "customer_obligations",
        "Customer Obligations",
        preferred=_tier(
            "vendor-protective",
            (
                "4. CUSTOMER OBLIGATIONS. Customer shall: (a) be responsible for all "
                "activity occurring under its user accounts and for maintaining the "
                "confidentiality of all login credentials; (b) use the Service only in "
                "compliance with all applicable laws, regulations, and this Agreement; "
                "(c) not reverse engineer, decompile, disassemble, or otherwise attempt "
                "to derive the source code of the Service; (d) not use the Service to "
                "develop a competing product or service; (e) not share, transfer, or "
                "resell access to the Service to any third party; (f) ensure that "
                "Customer Data does not infringe any third-party rights; and (g) promptly "
                "notify Provider of any unauthorized use of the Service or breach of "
                "security of which Customer becomes aware."
            ),
            guidance="Comprehensive restrictions including non-compete and anti-reverse-engineering.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "4. CUSTOMER OBLIGATIONS. Customer agrees to: (a) maintain the security "
                "of its account credentials and promptly notify Provider of any "
                "unauthorized access; (b) use the Service in compliance with applicable "
                "laws and the Documentation; (c) refrain from reverse engineering, "
                "decompiling, or disassembling the Service except to the extent expressly "
                "permitted by applicable law; (d) not use the Service to store or transmit "
                "any malicious code; (e) ensure that Customer Data does not violate any "
                "applicable law or third-party rights; and (f) cooperate with Provider in "
                "investigating any security incidents."
            ),
            guidance="Reasonable restrictions with statutory override for reverse engineering.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "4. CUSTOMER OBLIGATIONS. Customer shall: (a) use commercially reasonable "
                "efforts to maintain the security of its account credentials; (b) use the "
                "Service in compliance with applicable laws; (c) not knowingly introduce "
                "malicious code into the Service; and (d) cooperate with Provider in good "
                "faith to resolve any security incidents. For the avoidance of doubt, "
                "Customer shall not be liable for any breach of this Section that results "
                "from a vulnerability or defect in the Service or Provider's systems."
            ),
            guidance="Minimal obligations; Provider bears responsibility for own vulnerabilities.",
        ),
        position=5,
    ),

    # ── 6. FEES AND PAYMENT ──────────────────────────────────────────────
    _clause(
        "fees_and_payment",
        "Fees and Payment",
        preferred=_tier(
            "vendor-protective",
            (
                "5. FEES AND PAYMENT.\n\n"
                "5.1 Fees. Customer shall pay the fees set forth in the applicable Order "
                "Form (the \"Fees\") in accordance with the {{pricing_model}} pricing "
                "model. The initial Fee is {{price_amount}} payable {{billing_frequency}}. "
                "All Fees are non-refundable and non-cancellable.\n\n"
                "5.2 Price Increases. Provider may increase Fees upon thirty (30) days' "
                "written notice prior to any renewal term. If Customer does not object in "
                "writing within fifteen (15) days, the new Fees shall apply.\n\n"
                "5.3 Late Payments. Any amounts not paid when due shall accrue interest at "
                "the rate of one and one-half percent (1.5%) per month or the maximum rate "
                "permitted by law, whichever is less. Customer shall reimburse Provider for "
                "all costs of collection, including reasonable attorneys' fees.\n\n"
                "5.4 Taxes. All Fees are exclusive of taxes. Customer is responsible for "
                "all applicable sales, use, VAT, and withholding taxes."
            ),
            guidance="Non-refundable fees; Provider-friendly price increase mechanism; aggressive late payment.",
            key_terms={"pricing_model": "{{pricing_model}}", "price_amount": "{{price_amount}}"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "5. FEES AND PAYMENT.\n\n"
                "5.1 Fees. Customer shall pay the Fees specified in the applicable Order "
                "Form based on the {{pricing_model}} pricing model. The initial Fee is "
                "{{price_amount}}, payable {{billing_frequency}}.\n\n"
                "5.2 Price Adjustments. Provider may adjust Fees at the start of each "
                "renewal term by providing at least sixty (60) days' prior written notice. "
                "Any increase shall not exceed five percent (5%) of the Fees for the "
                "immediately preceding term unless mutually agreed.\n\n"
                "5.3 Late Payments. Amounts not paid within thirty (30) days of the due "
                "date shall accrue interest at one percent (1%) per month or the maximum "
                "rate permitted by law, whichever is less.\n\n"
                "5.4 Taxes. All Fees are exclusive of applicable taxes. Each Party shall "
                "be responsible for taxes imposed on it by law.\n\n"
                "5.5 Refunds. If Provider materially fails to meet the SLA for three (3) "
                "consecutive months, Customer may request a pro-rata refund for the "
                "affected period."
            ),
            guidance="Balanced: capped price increases, SLA-linked refund right.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "5. FEES AND PAYMENT.\n\n"
                "5.1 Fees. Customer shall pay the Fees specified in the applicable Order "
                "Form. The initial Fee is {{price_amount}}, payable {{billing_frequency}} "
                "under the {{pricing_model}} model. Fees for the initial Subscription Term "
                "are fixed and shall not be increased.\n\n"
                "5.2 Renewal Pricing. For any renewal term, Provider shall provide at "
                "least ninety (90) days' prior written notice of any proposed Fee increase. "
                "Customer may terminate this Agreement upon written notice if it does not "
                "accept the proposed increase, without early termination penalties.\n\n"
                "5.3 Late Payments. Amounts not paid within forty-five (45) days of the "
                "due date shall accrue interest at the lesser of one-half percent (0.5%) "
                "per month or the maximum rate permitted by law. Provider shall provide "
                "written notice of non-payment and a thirty (30) day cure period before "
                "suspending the Service.\n\n"
                "5.4 Refunds. Customer is entitled to a pro-rata refund of prepaid Fees "
                "upon termination for cause or if the SLA is not met for any two (2) "
                "consecutive months.\n\n"
                "5.5 Taxes. All Fees are exclusive of applicable taxes. Provider shall "
                "provide valid tax invoices as required by law."
            ),
            guidance="Customer-protective: locked pricing, generous cure periods, pro-rata refunds.",
        ),
        position=6,
        cross_references=["order_form", "sla"],
    ),

    # ── 7. INTELLECTUAL PROPERTY ─────────────────────────────────────────
    _clause(
        "intellectual_property",
        "Intellectual Property",
        preferred=_tier(
            "vendor-protective",
            (
                "6. INTELLECTUAL PROPERTY.\n\n"
                "6.1 Provider IP. As between the Parties, Provider exclusively owns all "
                "right, title, and interest in and to the Service, Documentation, and all "
                "improvements, modifications, derivatives, and enhancements thereof, "
                "including any modifications made at Customer's request or based on "
                "Customer's feedback. All rights not expressly granted herein are reserved "
                "to Provider.\n\n"
                "6.2 Feedback. Customer hereby assigns to Provider all right, title, and "
                "interest in any suggestions, ideas, enhancement requests, feedback, or "
                "other information provided by Customer relating to the Service "
                "(\"Feedback\"). Provider may use Feedback for any purpose without "
                "obligation to Customer.\n\n"
                "6.3 Aggregated Data. Provider may collect, use, and disclose aggregated, "
                "anonymized data derived from Customer's use of the Service for any lawful "
                "business purpose, including product improvement and benchmarking."
            ),
            guidance="Provider owns all IP including feedback and aggregated data.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "6. INTELLECTUAL PROPERTY.\n\n"
                "6.1 Provider IP. Provider retains all right, title, and interest in and "
                "to the Service, the Documentation, and all related intellectual property "
                "rights. Nothing in this Agreement transfers ownership of any Provider IP "
                "to Customer.\n\n"
                "6.2 Customer IP. Customer retains all right, title, and interest in and "
                "to the Customer Data and any materials provided by Customer.\n\n"
                "6.3 Feedback. If Customer provides Feedback regarding the Service, "
                "Provider may use such Feedback to improve the Service without restriction "
                "or obligation to Customer, provided that Provider shall not identify "
                "Customer as the source of any Feedback.\n\n"
                "6.4 Aggregated Data. Provider may use aggregated and de-identified data "
                "derived from the Service for product improvement and analytics, provided "
                "such data cannot reasonably be used to identify Customer or any individual."
            ),
            guidance="Balanced: clear IP separation; feedback license without attribution.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "6. INTELLECTUAL PROPERTY.\n\n"
                "6.1 Provider IP. Provider retains all right, title, and interest in and "
                "to the Service and Documentation. Customer acknowledges that the Service "
                "contains Provider's trade secrets and proprietary information.\n\n"
                "6.2 Customer IP. Customer retains all right, title, and interest in and "
                "to the Customer Data, Customer's confidential information, and any "
                "customizations, configurations, or integrations developed by or for "
                "Customer.\n\n"
                "6.3 Feedback. Any Feedback provided by Customer is voluntary. Provider "
                "may incorporate Feedback into the Service, but Customer retains a "
                "perpetual, royalty-free, non-exclusive license to use any concepts "
                "embodied in such Feedback.\n\n"
                "6.4 Aggregated Data. Provider shall not collect, use, or disclose any "
                "aggregated or anonymized data derived from Customer Data without "
                "Customer's prior written consent."
            ),
            guidance="Customer-protective: no aggregated data without consent; feedback license retained.",
        ),
        position=7,
    ),

    # ── 8. DATA OWNERSHIP ────────────────────────────────────────────────
    _clause(
        "data_ownership",
        "Data Ownership",
        preferred=_tier(
            "vendor-protective",
            (
                "7. DATA OWNERSHIP. As between the Parties, Customer retains ownership of "
                "Customer Data. Customer grants to Provider a non-exclusive, worldwide, "
                "royalty-free license to use, copy, store, transmit, modify, and display "
                "Customer Data solely to the extent necessary to provide the Service and "
                "as otherwise permitted under this Agreement. Provider shall have no "
                "obligation to retain Customer Data for more than thirty (30) days "
                "following the termination or expiration of this Agreement."
            ),
            guidance="Customer owns data but short retention post-termination.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "7. DATA OWNERSHIP. Customer exclusively owns all Customer Data. Provider "
                "shall not acquire any rights in Customer Data except the limited license "
                "to process Customer Data as necessary to perform the Service and comply "
                "with applicable law. Provider shall retain Customer Data for sixty (60) "
                "days following termination or expiration of this Agreement, during which "
                "time Customer may export its data. After such period, Provider shall "
                "securely delete all Customer Data in accordance with the DPA."
            ),
            guidance="Clear ownership; 60-day post-termination export window.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "7. DATA OWNERSHIP. Customer exclusively owns all right, title, and "
                "interest in and to the Customer Data, including all intellectual property "
                "rights therein. Provider acquires no rights in Customer Data and shall "
                "process Customer Data solely as instructed by Customer and as necessary "
                "to provide the Service. Provider shall retain Customer Data for ninety "
                "(90) days following termination or expiration of this Agreement in a "
                "format that is readily exportable. Customer may request export of its "
                "data at any time during the Subscription Term and such post-termination "
                "period. Provider shall cooperate with Customer's reasonable data "
                "portability requests at no additional charge."
            ),
            guidance="Customer-protective: 90-day retention, free data portability.",
        ),
        position=8,
        cross_references=["dpa", "effects_of_termination"],
    ),

    # ── 9. CONFIDENTIALITY ───────────────────────────────────────────────
    _clause(
        "confidentiality",
        "Confidentiality",
        preferred=_tier(
            "vendor-protective",
            (
                "8. CONFIDENTIALITY.\n\n"
                "8.1 Definition. \"Confidential Information\" means any non-public "
                "information disclosed by either Party to the other, whether in writing, "
                "orally, or by inspection, that is designated as confidential or that a "
                "reasonable person would understand to be confidential given the nature of "
                "the information and the circumstances of disclosure.\n\n"
                "8.2 Obligations. The receiving Party shall: (a) hold Confidential "
                "Information in strict confidence; (b) not disclose Confidential "
                "Information to any third party except as expressly permitted herein; and "
                "(c) use Confidential Information solely for the purposes of this "
                "Agreement. The receiving Party may disclose Confidential Information to "
                "its employees and contractors who have a need to know and who are bound "
                "by confidentiality obligations no less restrictive than those herein.\n\n"
                "8.3 Exclusions. Confidential Information does not include information that: "
                "(a) is or becomes publicly available through no fault of the receiving "
                "Party; (b) was known to the receiving Party prior to disclosure; (c) is "
                "independently developed without use of Confidential Information; or (d) is "
                "rightfully received from a third party without restriction.\n\n"
                "8.4 Survival. Confidentiality obligations shall survive for "
                "{{confidentiality_survival_years}} years after expiration or termination "
                "of this Agreement."
            ),
            guidance="Standard mutual confidentiality with clear exclusions.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "8. CONFIDENTIALITY.\n\n"
                "8.1 Each Party acknowledges that it may receive Confidential Information "
                "of the other Party. \"Confidential Information\" means all non-public "
                "information disclosed by a Party in connection with this Agreement, "
                "including but not limited to: business plans, technical data, product "
                "roadmaps, customer lists, pricing, and Customer Data.\n\n"
                "8.2 The receiving Party shall protect the disclosing Party's Confidential "
                "Information using the same degree of care it uses for its own confidential "
                "information, but no less than a reasonable standard of care. The receiving "
                "Party may disclose Confidential Information to its employees, contractors, "
                "and professional advisors with a need to know.\n\n"
                "8.3 The standard exclusions apply: public availability, prior knowledge, "
                "independent development, and lawful third-party receipt.\n\n"
                "8.4 Compelled Disclosure. If the receiving Party is compelled by law to "
                "disclose Confidential Information, it shall provide reasonable prior "
                "notice to the disclosing Party and cooperate in seeking a protective "
                "order.\n\n"
                "8.5 These obligations survive for {{confidentiality_survival_years}} years "
                "following termination, except that obligations with respect to trade "
                "secrets survive for as long as such information remains a trade secret."
            ),
            guidance="Balanced: includes compelled disclosure carve-out and trade secret perpetuity.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "8. CONFIDENTIALITY.\n\n"
                "8.1 \"Confidential Information\" means all information disclosed by either "
                "Party, in any form, that is designated as confidential or that would "
                "reasonably be considered confidential. Customer Data shall be deemed "
                "Customer's Confidential Information regardless of designation.\n\n"
                "8.2 The receiving Party shall protect Confidential Information with no "
                "less than a reasonable standard of care. Provider shall implement "
                "industry-standard technical and organizational measures to safeguard "
                "Customer's Confidential Information.\n\n"
                "8.3 Standard exclusions apply. Compelled disclosure requires prompt "
                "notice and cooperation to minimize scope.\n\n"
                "8.4 Return or Destruction. Upon termination or at the disclosing Party's "
                "request, the receiving Party shall return or securely destroy all "
                "Confidential Information and certify such destruction in writing within "
                "thirty (30) days.\n\n"
                "8.5 These obligations survive for {{confidentiality_survival_years}} years "
                "following termination. Provider's obligations regarding Customer Data "
                "survive indefinitely."
            ),
            guidance="Customer-protective: Customer Data auto-classified as CI; perpetual protection.",
        ),
        position=9,
    ),

    # ── 10. REPRESENTATIONS & WARRANTIES ─────────────────────────────────
    _clause(
        "representations_warranties",
        "Representations and Warranties",
        preferred=_tier(
            "vendor-protective",
            (
                "9. REPRESENTATIONS AND WARRANTIES.\n\n"
                "9.1 Mutual Representations. Each Party represents and warrants that: "
                "(a) it has the legal power and authority to enter into this Agreement; "
                "(b) this Agreement constitutes a valid and binding obligation; and (c) its "
                "performance will not violate any other agreement to which it is a party.\n\n"
                "9.2 Provider Warranty. Provider warrants that during the Subscription "
                "Term, the Service will perform substantially in accordance with the "
                "Documentation. Customer's sole and exclusive remedy for a breach of this "
                "warranty shall be, at Provider's option, either correction of the "
                "non-conforming Service or termination of this Agreement with a pro-rata "
                "refund of prepaid Fees for the remaining Subscription Term."
            ),
            guidance="Minimal warranties; sole remedy is fix or refund.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "9. REPRESENTATIONS AND WARRANTIES.\n\n"
                "9.1 Mutual Representations. Each Party represents and warrants that: "
                "(a) it is duly organized and validly existing under applicable law; "
                "(b) it has all necessary power and authority to enter into and perform its "
                "obligations under this Agreement; and (c) this Agreement is enforceable "
                "against it in accordance with its terms.\n\n"
                "9.2 Provider Warranties. Provider represents and warrants that: (a) the "
                "Service will perform materially in accordance with the Documentation and "
                "SLA during the Subscription Term; (b) Provider will provide the Service "
                "in a professional and workmanlike manner; (c) the Service will not "
                "knowingly introduce any viruses, malware, or harmful code into Customer's "
                "systems; and (d) Provider has implemented commercially reasonable security "
                "measures consistent with industry standards.\n\n"
                "9.3 Customer Warranties. Customer represents that it has the right to "
                "provide Customer Data and that such data does not infringe any third-party "
                "rights."
            ),
            guidance="Balanced: professional service standard, security warranty, no harmful code.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "9. REPRESENTATIONS AND WARRANTIES.\n\n"
                "9.1 Mutual Representations. Each Party represents and warrants that it is "
                "duly organized, validly existing, and in good standing, and has all "
                "necessary corporate authority to execute this Agreement.\n\n"
                "9.2 Provider Warranties. Provider represents and warrants that: (a) the "
                "Service will conform to the Documentation and meet or exceed the SLA at "
                "all times during the Subscription Term; (b) the Service will be provided "
                "in accordance with industry best practices and by qualified personnel; "
                "(c) the Service is and will remain free of viruses, trojans, backdoors, "
                "and other malicious code; (d) Provider maintains SOC 2 Type II "
                "certification (or equivalent) and will provide audit reports upon request; "
                "(e) the Service does not and will not infringe any third-party intellectual "
                "property rights; (f) Provider complies with all applicable data protection "
                "laws, including GDPR and CCPA; and (g) Provider carries adequate "
                "professional liability and cyber insurance."
            ),
            guidance="Extensive Provider warranties including SOC 2, non-infringement, and insurance.",
        ),
        position=10,
    ),

    # ── 11. DISCLAIMERS ──────────────────────────────────────────────────
    _clause(
        "disclaimers",
        "Disclaimers",
        preferred=_tier(
            "vendor-protective",
            (
                "10. DISCLAIMERS. EXCEPT AS EXPRESSLY SET FORTH IN SECTION 9, THE SERVICE "
                "IS PROVIDED \"AS IS\" AND \"AS AVAILABLE.\" PROVIDER DISCLAIMS ALL OTHER "
                "WARRANTIES, WHETHER EXPRESS, IMPLIED, OR STATUTORY, INCLUDING WITHOUT "
                "LIMITATION ANY WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR "
                "PURPOSE, TITLE, NON-INFRINGEMENT, AND ANY WARRANTIES ARISING FROM COURSE "
                "OF DEALING, USAGE, OR TRADE PRACTICE. PROVIDER DOES NOT WARRANT THAT THE "
                "SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR COMPLETELY SECURE. PROVIDER "
                "SHALL NOT BE LIABLE FOR ANY DELAY OR FAILURE IN PERFORMANCE RESULTING FROM "
                "CAUSES BEYOND ITS REASONABLE CONTROL."
            ),
            guidance="Broad AS-IS disclaimer with force majeure reference.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "10. DISCLAIMERS. EXCEPT FOR THE EXPRESS WARRANTIES SET FORTH IN SECTION 9, "
                "AND TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, PROVIDER DISCLAIMS "
                "ALL OTHER WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, "
                "INCLUDING ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A "
                "PARTICULAR PURPOSE, AND NON-INFRINGEMENT. THE FOREGOING DISCLAIMERS SHALL "
                "NOT LIMIT PROVIDER'S OBLIGATIONS UNDER THE SLA OR ANY INDEMNIFICATION "
                "OBLIGATIONS SET FORTH IN THIS AGREEMENT."
            ),
            guidance="Disclaimers preserved but SLA and indemnification obligations carved out.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "10. DISCLAIMERS. EXCEPT FOR THE EXPRESS WARRANTIES SET FORTH IN SECTION 9, "
                "EACH PARTY DISCLAIMS ALL IMPLIED WARRANTIES TO THE MAXIMUM EXTENT "
                "PERMITTED BY APPLICABLE LAW. NOTWITHSTANDING THE FOREGOING, NOTHING IN "
                "THIS SECTION SHALL BE DEEMED TO LIMIT OR EXCLUDE: (A) PROVIDER'S "
                "OBLIGATIONS UNDER THE SLA; (B) EITHER PARTY'S INDEMNIFICATION "
                "OBLIGATIONS; (C) PROVIDER'S DATA SECURITY OBLIGATIONS; OR (D) LIABILITY "
                "FOR FRAUD, GROSS NEGLIGENCE, OR WILLFUL MISCONDUCT."
            ),
            guidance="Narrow disclaimers with broad carve-outs for SLA, security, and intentional acts.",
        ),
        position=11,
    ),

    # ── 12. INDEMNIFICATION ──────────────────────────────────────────────
    _clause(
        "indemnification",
        "Indemnification",
        preferred=_tier(
            "vendor-protective",
            (
                "11. INDEMNIFICATION.\n\n"
                "11.1 Provider Indemnity. Provider shall defend, indemnify, and hold "
                "harmless Customer from any third-party claim that the Service, as provided "
                "by Provider and used by Customer in accordance with this Agreement, "
                "infringes a valid United States patent or copyright (an \"IP Claim\"). "
                "Provider's obligations are contingent on Customer: (a) promptly notifying "
                "Provider of the claim; (b) granting Provider sole control of the defense "
                "and settlement; and (c) providing reasonable cooperation at Provider's "
                "expense.\n\n"
                "11.2 IP Remedies. If the Service becomes the subject of an IP Claim, "
                "Provider may, at its sole option: (a) procure the right for Customer to "
                "continue using the Service; (b) modify the Service to be non-infringing; "
                "or (c) terminate this Agreement and refund any prepaid unused Fees.\n\n"
                "11.3 Customer Indemnity. Customer shall defend, indemnify, and hold "
                "harmless Provider from any claim arising from: (a) Customer Data; "
                "(b) Customer's use of the Service in violation of this Agreement; or "
                "(c) Customer's breach of applicable law."
            ),
            guidance="IP-only Provider indemnity; broad Customer indemnity.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "11. INDEMNIFICATION.\n\n"
                "11.1 Provider Indemnity. Provider shall defend, indemnify, and hold "
                "harmless Customer from: (a) any third-party IP Claim alleging that the "
                "Service infringes any intellectual property right; and (b) any claim "
                "arising from Provider's breach of its data security obligations under "
                "Section 13 or the DPA, including costs of breach notification and credit "
                "monitoring. Provider's indemnity is subject to Customer providing prompt "
                "notice and reasonable cooperation.\n\n"
                "11.2 Customer Indemnity. Customer shall defend, indemnify, and hold "
                "harmless Provider from: (a) any claim arising from Customer Data or "
                "Customer's use of the Service in violation of this Agreement; and (b) any "
                "claim arising from Customer's violation of applicable law.\n\n"
                "11.3 Procedure. The indemnified Party shall promptly notify the "
                "indemnifying Party of any claim and provide reasonable cooperation. The "
                "indemnifying Party shall have sole control of the defense, provided that "
                "it shall not settle any claim that imposes obligations on the indemnified "
                "Party without consent."
            ),
            guidance="Balanced: IP + data breach indemnity from Provider; mutual procedures.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "11. INDEMNIFICATION.\n\n"
                "11.1 Provider Indemnity. Provider shall defend, indemnify, and hold "
                "harmless Customer, its affiliates, and their respective officers, "
                "directors, and employees from and against any and all claims, damages, "
                "losses, liabilities, and expenses (including reasonable attorneys' fees) "
                "arising from or related to: (a) any claim that the Service infringes any "
                "third-party intellectual property right worldwide; (b) any data breach or "
                "security incident involving Customer Data, regardless of fault; (c) any "
                "claim arising from Provider's negligence, willful misconduct, or material "
                "breach of this Agreement; and (d) any violation by Provider of applicable "
                "data protection laws. Provider's indemnification obligations under this "
                "Section shall not be subject to the limitation of liability in Section "
                "12.\n\n"
                "11.2 Customer Indemnity. Customer shall indemnify Provider from claims "
                "directly arising from Customer Data that Customer knew or should have "
                "known was unlawful."
            ),
            guidance="Broad uncapped Provider indemnity; minimal Customer indemnity.",
        ),
        position=12,
        cross_references=["limitation_of_liability", "data_security", "dpa"],
    ),

    # ── 13. LIMITATION OF LIABILITY ──────────────────────────────────────
    _clause(
        "limitation_of_liability",
        "Limitation of Liability",
        preferred=_tier(
            "vendor-protective",
            (
                "12. LIMITATION OF LIABILITY.\n\n"
                "12.1 Consequential Damages Exclusion. TO THE MAXIMUM EXTENT PERMITTED BY "
                "APPLICABLE LAW, IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER "
                "PARTY FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE "
                "DAMAGES, OR ANY LOSS OF PROFITS, REVENUE, DATA, GOODWILL, OR BUSINESS "
                "OPPORTUNITY, REGARDLESS OF THE CAUSE OF ACTION OR THEORY OF LIABILITY, "
                "EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.\n\n"
                "12.2 Liability Cap. EXCEPT FOR CUSTOMER'S PAYMENT OBLIGATIONS, EACH "
                "PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS "
                "AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID OR PAYABLE BY CUSTOMER "
                "DURING THE THREE (3) MONTHS IMMEDIATELY PRECEDING THE EVENT GIVING RISE "
                "TO THE CLAIM."
            ),
            guidance="Low cap at 3 months fees; full consequential exclusion.",
            key_terms={"liability_cap": "3 months fees"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "12. LIMITATION OF LIABILITY.\n\n"
                "12.1 Consequential Damages Exclusion. NEITHER PARTY SHALL BE LIABLE FOR "
                "ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, "
                "INCLUDING LOSS OF PROFITS, REVENUE, OR DATA, ARISING OUT OF OR RELATED "
                "TO THIS AGREEMENT, REGARDLESS OF THE THEORY OF LIABILITY.\n\n"
                "12.2 Liability Cap. EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS "
                "AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID OR PAYABLE BY CUSTOMER "
                "DURING THE TWELVE (12) MONTHS IMMEDIATELY PRECEDING THE FIRST EVENT "
                "GIVING RISE TO LIABILITY.\n\n"
                "12.3 Carve-Outs. The limitations in Sections 12.1 and 12.2 shall not "
                "apply to: (a) either Party's indemnification obligations under Section "
                "11; (b) Provider's breach of its data security obligations; (c) either "
                "Party's breach of confidentiality obligations; or (d) liability arising "
                "from a Party's gross negligence or willful misconduct."
            ),
            guidance="12-month cap with carve-outs for indemnification, security, and bad faith.",
            key_terms={"liability_cap": "12 months fees"},
        ),
        fallback=_tier(
            "customer-protective",
            (
                "12. LIMITATION OF LIABILITY.\n\n"
                "12.1 Consequential Damages. NEITHER PARTY SHALL BE LIABLE FOR INDIRECT OR "
                "CONSEQUENTIAL DAMAGES EXCEPT TO THE EXTENT ARISING FROM: (A) PROVIDER'S "
                "BREACH OF DATA SECURITY OR CONFIDENTIALITY OBLIGATIONS; (B) PROVIDER'S "
                "INDEMNIFICATION OBLIGATIONS; (C) EITHER PARTY'S INFRINGEMENT OF THE "
                "OTHER PARTY'S INTELLECTUAL PROPERTY RIGHTS; OR (D) GROSS NEGLIGENCE OR "
                "WILLFUL MISCONDUCT.\n\n"
                "12.2 Liability Cap. EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER THIS "
                "AGREEMENT SHALL NOT EXCEED THE GREATER OF: (A) THE TOTAL FEES PAID OR "
                "PAYABLE BY CUSTOMER DURING THE TWENTY-FOUR (24) MONTHS IMMEDIATELY "
                "PRECEDING THE FIRST EVENT GIVING RISE TO LIABILITY; OR (B) ONE MILLION "
                "UNITED STATES DOLLARS (US$1,000,000).\n\n"
                "12.3 Super Cap. NOTWITHSTANDING SECTION 12.2, PROVIDER'S LIABILITY FOR "
                "DATA BREACHES, INDEMNIFICATION OBLIGATIONS, AND WILLFUL MISCONDUCT SHALL "
                "NOT EXCEED THREE (3) TIMES THE AMOUNT SET FORTH IN SECTION 12.2."
            ),
            guidance="24-month or $1M cap; super cap for breaches at 3x; broad consequential carve-outs.",
            key_terms={"liability_cap": "24 months or $1M"},
        ),
        position=13,
    ),

    # ── 14. DATA SECURITY ────────────────────────────────────────────────
    _clause(
        "data_security",
        "Data Security",
        preferred=_tier(
            "vendor-protective",
            (
                "13. DATA SECURITY. Provider shall implement and maintain commercially "
                "reasonable administrative, technical, and physical safeguards designed to "
                "protect Customer Data from unauthorized access, use, or disclosure. "
                "Provider shall promptly notify Customer upon becoming aware of any "
                "confirmed security breach affecting Customer Data. The specific security "
                "measures are described in Provider's security documentation, which "
                "Provider may update from time to time."
            ),
            guidance="Commercially reasonable standard; Provider controls security documentation.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "13. DATA SECURITY.\n\n"
                "13.1 Security Measures. Provider shall implement and maintain "
                "administrative, technical, and physical safeguards that are at least "
                "consistent with industry standards and applicable law to protect Customer "
                "Data. Such measures shall include encryption of data in transit and at "
                "rest, access controls, regular vulnerability assessments, and employee "
                "security training.\n\n"
                "13.2 Breach Notification. Provider shall notify Customer of any security "
                "breach affecting Customer Data within forty-eight (48) hours of becoming "
                "aware of such breach. The notification shall include the nature and scope "
                "of the breach, the data affected, and the remedial measures taken.\n\n"
                "13.3 Compliance. Provider shall maintain SOC 2 Type II certification or "
                "an equivalent standard and shall provide a summary audit report upon "
                "Customer's reasonable request."
            ),
            guidance="Industry standard with 48-hour breach notice and SOC 2 requirement.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "13. DATA SECURITY.\n\n"
                "13.1 Security Program. Provider shall establish, implement, and maintain "
                "a comprehensive information security program that includes administrative, "
                "technical, and physical safeguards designed to protect Customer Data in "
                "accordance with: (a) industry best practices, including NIST Cybersecurity "
                "Framework; (b) all applicable data protection laws; and (c) any security "
                "requirements specified in the Order Form.\n\n"
                "13.2 Specific Measures. Provider's security program shall include, at a "
                "minimum: AES-256 encryption at rest, TLS 1.2+ in transit, multi-factor "
                "authentication, role-based access controls, annual penetration testing by "
                "independent third parties, continuous vulnerability monitoring, and "
                "incident response procedures.\n\n"
                "13.3 Breach Notification. Provider shall notify Customer of any actual or "
                "suspected security breach within twenty-four (24) hours of discovery.\n\n"
                "13.4 Audit Rights. Customer or its designated third-party auditor may, "
                "upon thirty (30) days' prior written notice and no more than once per "
                "year, audit Provider's security practices and facilities. Provider shall "
                "cooperate and provide access to relevant records and personnel.\n\n"
                "13.5 Certifications. Provider shall maintain SOC 2 Type II and ISO 27001 "
                "certifications throughout the Subscription Term and provide audit reports "
                "to Customer upon request."
            ),
            guidance="Comprehensive: NIST framework, specific encryption, audit rights, 24-hour notice.",
        ),
        position=14,
        cross_references=["dpa", "confidentiality"],
    ),

    # ── 15. TERM AND TERMINATION ─────────────────────────────────────────
    _clause(
        "term_and_termination",
        "Term and Termination",
        preferred=_tier(
            "vendor-protective",
            (
                "14. TERM AND TERMINATION.\n\n"
                "14.1 Initial Term. This Agreement commences on the Effective Date and "
                "continues for an initial period of {{term_months}} months (the \"Initial "
                "Term\").\n\n"
                "14.2 Renewal. {{auto_renewal_text}}. The Initial Term and all renewal "
                "terms are collectively referred to as the \"Subscription Term.\"\n\n"
                "14.3 Termination for Cause. Either Party may terminate this Agreement "
                "upon written notice if the other Party materially breaches this Agreement "
                "and fails to cure such breach within thirty (30) days of receiving written "
                "notice thereof.\n\n"
                "14.4 Termination for Insolvency. Either Party may terminate this "
                "Agreement immediately upon written notice if the other Party becomes "
                "insolvent, makes an assignment for the benefit of creditors, or becomes "
                "the subject of bankruptcy proceedings.\n\n"
                "14.5 No Refund on Termination by Customer. If Customer terminates this "
                "Agreement other than for cause, no refund of prepaid Fees shall be due."
            ),
            guidance="Auto-renewal default; no refund on customer-initiated termination.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "14. TERM AND TERMINATION.\n\n"
                "14.1 Initial Term. This Agreement commences on the Effective Date and "
                "continues for {{term_months}} months.\n\n"
                "14.2 Renewal. {{auto_renewal_text}}. Either Party may elect not to renew "
                "by providing at least sixty (60) days' written notice before the end of "
                "the then-current term.\n\n"
                "14.3 Termination for Cause. Either Party may terminate upon thirty (30) "
                "days' written notice of a material breach that remains uncured.\n\n"
                "14.4 Termination for Convenience. Either Party may terminate this "
                "Agreement for convenience upon ninety (90) days' written notice, subject "
                "to payment of all accrued Fees.\n\n"
                "14.5 Refund. Upon termination by Customer for cause, Provider shall "
                "refund a pro-rata portion of any prepaid Fees for the remainder of the "
                "Subscription Term."
            ),
            guidance="Balanced: convenience termination with notice; pro-rata refund for cause termination.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "14. TERM AND TERMINATION.\n\n"
                "14.1 Initial Term. This Agreement commences on the Effective Date and "
                "continues for {{term_months}} months.\n\n"
                "14.2 Renewal. {{auto_renewal_text}}. Either Party may elect not to renew "
                "by providing at least ninety (90) days' prior written notice.\n\n"
                "14.3 Termination for Cause. Customer may terminate this Agreement "
                "immediately upon written notice if: (a) Provider materially breaches this "
                "Agreement and fails to cure within fifteen (15) days; (b) Provider fails "
                "to meet the SLA for two (2) consecutive months; or (c) a data breach "
                "occurs involving Customer Data.\n\n"
                "14.4 Termination for Convenience. Customer may terminate this Agreement "
                "for convenience upon thirty (30) days' written notice, subject to "
                "Provider refunding a pro-rata portion of prepaid Fees for the unused "
                "Subscription Term.\n\n"
                "14.5 Provider Termination. Provider may terminate only for material breach "
                "by Customer that remains uncured for thirty (30) days after written notice."
            ),
            guidance="Customer-protective: short cure periods, SLA-based termination, pro-rata refunds.",
        ),
        position=15,
    ),

    # ── 16. EFFECTS OF TERMINATION ───────────────────────────────────────
    _clause(
        "effects_of_termination",
        "Effects of Termination",
        preferred=_tier(
            "vendor-protective",
            (
                "15. EFFECTS OF TERMINATION. Upon termination or expiration of this "
                "Agreement: (a) Customer's access to the Service shall immediately cease; "
                "(b) Customer shall pay all outstanding Fees within thirty (30) days; "
                "(c) each Party shall return or destroy Confidential Information of the "
                "other Party; and (d) Provider shall make Customer Data available for "
                "export for thirty (30) days following termination, after which Provider "
                "may delete all Customer Data. Sections 6, 8, 10, 11, 12, and this "
                "Section 15 shall survive any termination or expiration of this Agreement."
            ),
            guidance="Short data export window; clear survival clause.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "15. EFFECTS OF TERMINATION. Upon termination or expiration: (a) Customer's "
                "right to access the Service shall cease, except as provided in this "
                "Section; (b) Provider shall make Customer Data available for export in a "
                "commonly used, machine-readable format for sixty (60) days following "
                "termination; (c) Provider shall securely delete all Customer Data after "
                "such sixty (60) day period and provide written certification of deletion; "
                "(d) each Party shall return or destroy the other Party's Confidential "
                "Information; and (e) all accrued payment obligations shall survive. "
                "Sections 6, 7, 8, 10, 11, 12, 16, and this Section shall survive."
            ),
            guidance="60-day export window with deletion certification.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "15. EFFECTS OF TERMINATION. Upon termination or expiration: (a) Provider "
                "shall continue to provide Customer with read-only access to the Service "
                "for ninety (90) days to facilitate data migration; (b) Provider shall "
                "export all Customer Data in Customer's choice of format (including JSON, "
                "CSV, SQL, and API access) at no additional charge; (c) Provider shall "
                "permanently and securely delete all Customer Data, including backups, "
                "within thirty (30) days after Customer confirms successful data migration, "
                "and shall certify such deletion in writing; (d) Provider shall provide "
                "reasonable transition assistance at Provider's then-current professional "
                "services rates; and (e) all prepaid Fees for the unused portion of the "
                "Subscription Term shall be refunded within thirty (30) days. Sections 6 "
                "through 12, 16, and this Section shall survive."
            ),
            guidance="Extended transition support, multiple export formats, refund of unused fees.",
        ),
        position=16,
    ),

    # ── 17. DISPUTE RESOLUTION ───────────────────────────────────────────
    _clause(
        "dispute_resolution",
        "Dispute Resolution",
        preferred=_tier(
            "vendor-protective",
            (
                "16. DISPUTE RESOLUTION.\n\n"
                "16.1 Governing Law. This Agreement shall be governed by and construed in "
                "accordance with the laws of {{governing_law}}, without regard to its "
                "conflict of laws principles.\n\n"
                "16.2 Arbitration. Any dispute arising out of or relating to this Agreement "
                "that the Parties cannot resolve through negotiation shall be finally "
                "settled by binding arbitration administered by the American Arbitration "
                "Association under its Commercial Arbitration Rules. The arbitration shall "
                "be conducted in {{venue}} by a single arbitrator. The arbitrator's "
                "decision shall be final and binding. Judgment upon the award may be "
                "entered in any court of competent jurisdiction.\n\n"
                "16.3 Injunctive Relief. Notwithstanding Section 16.2, either Party may "
                "seek injunctive or other equitable relief in any court of competent "
                "jurisdiction to protect its intellectual property rights or Confidential "
                "Information."
            ),
            guidance="Binding arbitration favoring Provider's preferred venue.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "16. DISPUTE RESOLUTION.\n\n"
                "16.1 Governing Law. This Agreement is governed by the laws of "
                "{{governing_law}}, without regard to conflict of laws provisions.\n\n"
                "16.2 Escalation. The Parties shall first attempt to resolve disputes "
                "through good faith negotiation between senior management for thirty (30) "
                "days. If unresolved, the Parties shall submit the dispute to mediation "
                "under the rules of {{dispute_resolution}} for a period not to exceed "
                "sixty (60) days.\n\n"
                "16.3 Litigation. If mediation is unsuccessful, either Party may initiate "
                "litigation in the courts of {{venue}}. Each Party consents to the "
                "exclusive jurisdiction and venue of such courts.\n\n"
                "16.4 Equitable Relief. Either Party may seek injunctive or equitable "
                "relief at any time, without first engaging in the escalation procedures."
            ),
            guidance="Multi-step escalation: negotiation, mediation, then litigation.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "16. DISPUTE RESOLUTION.\n\n"
                "16.1 Governing Law. This Agreement shall be governed by the laws of "
                "{{governing_law}} without regard to conflict of laws principles. If the "
                "Parties are in different jurisdictions, the governing law shall be that of "
                "Customer's principal place of business.\n\n"
                "16.2 Negotiation. The Parties shall attempt to resolve any dispute through "
                "good faith negotiation for a period of thirty (30) days.\n\n"
                "16.3 Litigation. Either Party may bring suit in the courts of {{venue}} or "
                "in any court of competent jurisdiction where Customer has its principal "
                "place of business. Customer may initiate litigation in its home "
                "jurisdiction.\n\n"
                "16.4 Jury Trial Waiver. EACH PARTY WAIVES ANY RIGHT TO A JURY TRIAL.\n\n"
                "16.5 Prevailing Party. The prevailing Party in any dispute shall be "
                "entitled to recover its reasonable attorneys' fees and costs."
            ),
            guidance="Customer-protective: Customer's choice of jurisdiction; fee-shifting.",
        ),
        position=17,
    ),

    # ── 18. BOILERPLATE ──────────────────────────────────────────────────
    _clause(
        "boilerplate",
        "General Provisions",
        preferred=_tier(
            "vendor-protective",
            (
                "17. GENERAL PROVISIONS.\n\n"
                "(a) Entire Agreement. This Agreement, together with all Order Forms, "
                "Exhibits, and Schedules, constitutes the entire agreement between the "
                "Parties and supersedes all prior or contemporaneous agreements, proposals, "
                "or representations relating to the subject matter hereof.\n\n"
                "(b) Amendment. This Agreement may be amended only by a written instrument "
                "signed by both Parties, except that Provider may update its standard "
                "terms, policies, and Documentation from time to time upon reasonable "
                "notice to Customer.\n\n"
                "(c) Assignment. Customer may not assign this Agreement without Provider's "
                "prior written consent. Provider may assign this Agreement freely in "
                "connection with a merger, acquisition, or sale of substantially all of "
                "its assets.\n\n"
                "(d) Force Majeure. Neither Party shall be liable for any failure to "
                "perform due to causes beyond its reasonable control.\n\n"
                "(e) Notices. All notices shall be in writing and sent to the addresses "
                "set forth in this Agreement.\n\n"
                "(f) Severability. If any provision is held invalid, the remaining "
                "provisions shall continue in full force and effect.\n\n"
                "(g) Waiver. Failure to enforce any provision shall not constitute a waiver."
            ),
            guidance="Provider can update terms unilaterally; asymmetric assignment.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "17. GENERAL PROVISIONS.\n\n"
                "(a) Entire Agreement. This Agreement, including all Exhibits and Order "
                "Forms, is the complete agreement between the Parties regarding the subject "
                "matter hereof.\n\n"
                "(b) Amendment. Amendments must be in writing and signed by authorized "
                "representatives of both Parties.\n\n"
                "(c) Assignment. Neither Party may assign this Agreement without the prior "
                "written consent of the other Party, except in connection with a merger, "
                "acquisition, or sale of all or substantially all of the assigning Party's "
                "assets.\n\n"
                "(d) Force Majeure. Neither Party shall be liable for failures due to "
                "events beyond reasonable control, provided the affected Party gives prompt "
                "notice and uses reasonable efforts to mitigate.\n\n"
                "(e) Notices. Notices shall be in writing and deemed given when delivered "
                "by hand, by nationally recognized courier, or by email with confirmation.\n\n"
                "(f) Severability. Invalid provisions shall be reformed to the minimum "
                "extent necessary.\n\n"
                "(g) Independent Contractors. The Parties are independent contractors.\n\n"
                "(h) Waiver. Waivers must be in writing."
            ),
            guidance="Balanced: mutual assignment restrictions with M&A carve-out.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "17. GENERAL PROVISIONS.\n\n"
                "(a) Entire Agreement. This Agreement constitutes the entire agreement. "
                "No terms in Provider's clickwrap, browsewrap, or online terms shall "
                "modify this Agreement unless expressly agreed in writing.\n\n"
                "(b) Amendment. Amendments require written agreement signed by both "
                "Parties. Provider may not modify the terms of this Agreement through "
                "updated online terms, policies, or Documentation.\n\n"
                "(c) Assignment. Neither Party may assign without prior written consent. "
                "In the event of a change of control of Provider, Customer may terminate "
                "this Agreement within sixty (60) days with a full refund of prepaid Fees.\n\n"
                "(d) Force Majeure. Neither Party is liable for force majeure events, "
                "provided that: (i) the affected Party gives immediate notice; and (ii) if "
                "the event continues for more than thirty (30) days, either Party may "
                "terminate with a pro-rata refund.\n\n"
                "(e) Notices. Notices shall be in writing via email with read receipt or "
                "nationally recognized courier.\n\n"
                "(f) Severability. Invalid provisions shall be interpreted to achieve the "
                "original intent to the maximum extent possible.\n\n"
                "(g) No Third-Party Beneficiaries except Customer's affiliates.\n\n"
                "(h) Counterparts. This Agreement may be executed in counterparts."
            ),
            guidance="Customer-protective: no clickwrap modification; change of control termination right.",
        ),
        position=18,
    ),

    # ── 19. SIGNATURE BLOCKS ─────────────────────────────────────────────
    _clause(
        "signature_blocks",
        "Signature Blocks",
        preferred=_tier(
            "vendor-protective",
            (
                "IN WITNESS WHEREOF, the Parties have executed this Software-as-a-Service "
                "Agreement as of the Effective Date.\n\n"
                "PROVIDER: {{provider_name}}\n"
                "By: ___________________________\n"
                "Name:\nTitle:\nDate:\n\n"
                "CUSTOMER: {{customer_name}}\n"
                "By: ___________________________\n"
                "Name:\nTitle:\nDate:"
            ),
            guidance="Standard dual signature block.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "IN WITNESS WHEREOF, the Parties have caused this Software-as-a-Service "
                "Agreement to be executed by their duly authorized representatives as of "
                "the Effective Date first written above.\n\n"
                "{{provider_name}} (\"Provider\")\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:\n\n"
                "{{customer_name}} (\"Customer\")\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:"
            ),
            guidance="Standard signature block with printed name fields.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "IN WITNESS WHEREOF, the Parties have caused this Software-as-a-Service "
                "Agreement to be duly executed by their authorized representatives.\n\n"
                "PROVIDER:\n"
                "{{provider_name}}, a {{provider_entity_type}}\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:\n"
                "Address: {{provider_address}}\n\n"
                "CUSTOMER:\n"
                "{{customer_name}}, a {{customer_entity_type}}\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:\n"
                "Address: {{customer_address}}"
            ),
            guidance="Detailed signature block with entity type and address.",
        ),
        position=19,
    ),

    # ── 20. SLA (EXHIBIT A) ──────────────────────────────────────────────
    _clause(
        "sla",
        "Service Level Agreement (Exhibit A)",
        preferred=_tier(
            "vendor-protective",
            (
                "EXHIBIT A — SERVICE LEVEL AGREEMENT\n\n"
                "1. UPTIME COMMITMENT. Provider shall use commercially reasonable efforts "
                "to maintain Service availability of {{uptime_commitment}} (the \"Uptime "
                "Commitment\") measured on a monthly basis, excluding scheduled maintenance "
                "windows and force majeure events.\n\n"
                "2. SCHEDULED MAINTENANCE. Provider may schedule maintenance windows with "
                "at least twenty-four (24) hours' prior notice. Maintenance windows shall "
                "not count against the Uptime Commitment.\n\n"
                "3. EXCLUSIONS. The Uptime Commitment does not cover: (a) downtime caused "
                "by Customer's systems, network, or software; (b) features designated as "
                "\"beta\" or \"preview\"; (c) third-party service outages; or (d) "
                "circumstances beyond Provider's reasonable control.\n\n"
                "4. SERVICE CREDITS. If the Service fails to meet the Uptime Commitment "
                "in any calendar month, Customer may request service credits as follows:\n"
                "  - 99.0% to <99.5%: credit of 10% of monthly Fees\n"
                "  - 95.0% to <99.0%: credit of 25% of monthly Fees\n"
                "  - Below 95.0%: credit of 50% of monthly Fees\n"
                "Service credits are Customer's sole and exclusive remedy for downtime and "
                "shall not exceed fifty percent (50%) of the monthly Fee. Credits must be "
                "requested within thirty (30) days of the end of the affected month.\n\n"
                "5. SUPPORT. Provider shall provide standard support during business hours "
                "(9:00 AM — 6:00 PM Provider's local time, Monday through Friday).\n"
                "  - P1 (Service Down): Response within 4 hours\n"
                "  - P2 (Major Impact): Response within 8 hours\n"
                "  - P3 (Minor Impact): Response within 2 business days\n"
                "  - P4 (General Inquiry): Response within 5 business days"
            ),
            guidance="99.5% target; credits as sole remedy; capped at 50% of monthly fee.",
            key_terms={"uptime": "99.5%", "max_credit": "50% monthly fee"},
        ),
        acceptable=_tier(
            "balanced",
            (
                "EXHIBIT A — SERVICE LEVEL AGREEMENT\n\n"
                "1. UPTIME COMMITMENT. Provider guarantees Service availability of "
                "{{uptime_commitment}} per month, measured as the percentage of total "
                "minutes in the month minus scheduled maintenance.\n\n"
                "2. SCHEDULED MAINTENANCE. Provider shall schedule maintenance during "
                "off-peak hours and provide at least forty-eight (48) hours' prior notice. "
                "Maintenance windows shall not exceed eight (8) hours per month.\n\n"
                "3. MEASUREMENT. Uptime shall be measured by Provider's monitoring tools, "
                "and Customer shall have access to a real-time status dashboard.\n\n"
                "4. SERVICE CREDITS.\n"
                "  - 99.5% to <99.9%: credit of 10% of monthly Fees\n"
                "  - 99.0% to <99.5%: credit of 25% of monthly Fees\n"
                "  - Below 99.0%: credit of 50% of monthly Fees\n"
                "Credits are applied automatically to the next billing cycle.\n\n"
                "5. TERMINATION RIGHT. If Service availability falls below 99.0% for three "
                "(3) consecutive months, Customer may terminate this Agreement with a "
                "pro-rata refund.\n\n"
                "6. SUPPORT.\n"
                "  - P1 (Service Down): Response within 1 hour, resolution target 4 hours\n"
                "  - P2 (Major Impact): Response within 4 hours, resolution target 1 business day\n"
                "  - P3 (Minor Impact): Response within 1 business day\n"
                "  - P4 (General Inquiry): Response within 2 business days"
            ),
            guidance="99.9% target; auto-credits; SLA-based termination right.",
            key_terms={"uptime": "99.9%", "max_credit": "50% monthly fee"},
        ),
        fallback=_tier(
            "customer-protective",
            (
                "EXHIBIT A — SERVICE LEVEL AGREEMENT\n\n"
                "1. UPTIME COMMITMENT. Provider guarantees Service availability of not "
                "less than {{uptime_commitment}} per calendar month, measured 24/7/365 "
                "including all maintenance windows.\n\n"
                "2. MAINTENANCE. All maintenance shall be performed during designated "
                "windows (Saturday 2:00 AM — 6:00 AM Provider's local time) with at least "
                "seventy-two (72) hours' prior notice. Emergency maintenance shall be "
                "communicated immediately and shall not exceed two (2) hours.\n\n"
                "3. MEASUREMENT. Uptime shall be independently verified using a mutually "
                "agreed third-party monitoring tool. Customer shall have full access to "
                "all monitoring data and historical uptime records.\n\n"
                "4. SERVICE CREDITS.\n"
                "  - 99.9% to <99.95%: credit of 10% of monthly Fees\n"
                "  - 99.5% to <99.9%: credit of 25% of monthly Fees\n"
                "  - Below 99.5%: credit of 50% of monthly Fees\n"
                "Credits are applied automatically. Unused credits may be carried forward "
                "or applied as a reduction to renewal Fees.\n\n"
                "5. TERMINATION AND REMEDIES. If Service availability falls below 99.5% "
                "for any two (2) consecutive months, Customer may: (a) terminate this "
                "Agreement immediately with a full refund of all prepaid Fees; or "
                "(b) require Provider to implement a remediation plan within fifteen (15) "
                "days. Service credits are in addition to, and not in lieu of, any other "
                "remedies available to Customer under this Agreement or at law.\n\n"
                "6. SUPPORT.\n"
                "  - P1 (Service Down): Response within 15 minutes, resolution target 2 hours\n"
                "  - P2 (Major Impact): Response within 1 hour, resolution target 4 hours\n"
                "  - P3 (Minor Impact): Response within 4 hours, resolution target 1 business day\n"
                "  - P4 (General Inquiry): Response within 1 business day\n\n"
                "7. REPORTING. Provider shall deliver monthly SLA performance reports to "
                "Customer within five (5) business days of the end of each calendar month."
            ),
            guidance="99.95% target; credits not sole remedy; audit rights; aggressive response times.",
            key_terms={"uptime": "99.95%", "max_credit": "50% monthly fee"},
        ),
        position=20,
        cross_references=["fees_and_payment", "term_and_termination"],
    ),

    # ── 21. DPA (EXHIBIT B) ──────────────────────────────────────────────
    _clause(
        "dpa",
        "Data Processing Agreement (Exhibit B)",
        preferred=_tier(
            "vendor-protective",
            (
                "EXHIBIT B — DATA PROCESSING AGREEMENT\n\n"
                "This Data Processing Agreement (\"DPA\") forms part of the Agreement "
                "between Provider and Customer.\n\n"
                "1. ROLES. For the purposes of applicable data protection laws, Customer "
                "is the data controller and Provider is the data processor with respect to "
                "personal data processed through the Service.\n\n"
                "2. PROCESSING SCOPE. Provider shall process personal data only as "
                "necessary to provide the Service and in accordance with Customer's "
                "documented instructions. The categories of data subjects, types of "
                "personal data, and purposes of processing are described in Annex 1.\n\n"
                "3. SUB-PROCESSORS. Customer grants Provider a general written "
                "authorization to engage sub-processors. Provider shall maintain a list of "
                "current sub-processors on its website and shall notify Customer at least "
                "thirty (30) days before engaging any new sub-processor. If Customer "
                "objects, the Parties shall discuss in good faith, but Provider may proceed "
                "with the engagement if commercially necessary.\n\n"
                "4. DATA SECURITY. Provider shall implement appropriate technical and "
                "organizational measures as described in Section 13 of the Agreement.\n\n"
                "5. BREACH NOTIFICATION. Provider shall notify Customer without undue "
                "delay, and in any event within seventy-two (72) hours, after becoming "
                "aware of a personal data breach.\n\n"
                "6. DATA SUBJECT REQUESTS. Provider shall promptly assist Customer in "
                "responding to data subject access, rectification, erasure, and portability "
                "requests.\n\n"
                "7. DATA DELETION. Upon termination of the Agreement, Provider shall delete "
                "all personal data within thirty (30) days unless retention is required by "
                "applicable law.\n\n"
                "8. INTERNATIONAL TRANSFERS. If personal data is transferred outside the "
                "European Economic Area, Provider shall ensure appropriate safeguards are "
                "in place, including the EU Standard Contractual Clauses (SCCs) as set "
                "forth in Annex 2.\n\n"
                "9. AUDIT. Upon reasonable request and at Customer's expense, Provider "
                "shall make available information necessary to demonstrate compliance with "
                "this DPA. Provider may satisfy audit requests by providing its most recent "
                "SOC 2 Type II report or equivalent certification."
            ),
            guidance="GDPR Article 28 structure; general sub-processor authorization; SOC 2 substitutes for audit.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "EXHIBIT B — DATA PROCESSING AGREEMENT\n\n"
                "This Data Processing Agreement (\"DPA\") supplements the Agreement between "
                "Provider (processor) and Customer (controller).\n\n"
                "1. DEFINITIONS. Terms used in this DPA shall have the meanings given in "
                "the GDPR (Regulation (EU) 2016/679) and other applicable data protection "
                "laws.\n\n"
                "2. SCOPE OF PROCESSING. Provider shall process personal data solely on "
                "behalf of Customer and in accordance with Customer's documented "
                "instructions. Provider shall not process personal data for its own "
                "purposes. The details of processing are set forth in Annex 1.\n\n"
                "3. PROVIDER OBLIGATIONS. Provider shall: (a) ensure that persons "
                "authorized to process personal data have committed to confidentiality; "
                "(b) implement appropriate security measures; (c) assist Customer with data "
                "protection impact assessments; and (d) make available all information "
                "necessary to demonstrate compliance.\n\n"
                "4. SUB-PROCESSORS. Provider shall maintain a list of sub-processors and "
                "notify Customer at least thirty (30) days before adding or replacing a "
                "sub-processor. Customer may reasonably object, and if the objection "
                "cannot be resolved, Customer may terminate the affected Service.\n\n"
                "5. BREACH NOTIFICATION. Provider shall notify Customer within seventy-two "
                "(72) hours of discovering a personal data breach, providing details of the "
                "nature, scope, likely consequences, and remedial measures.\n\n"
                "6. DATA SUBJECT RIGHTS. Provider shall assist Customer in fulfilling its "
                "obligations to respond to data subject requests within applicable "
                "timeframes.\n\n"
                "7. INTERNATIONAL TRANSFERS. Transfers outside the EEA shall be subject to "
                "the EU Standard Contractual Clauses (SCCs), which are incorporated by "
                "reference in Annex 2.\n\n"
                "8. DELETION AND RETURN. Upon termination, Provider shall return or delete "
                "all personal data within sixty (60) days at Customer's election, and "
                "certify deletion in writing.\n\n"
                "9. AUDIT. Customer may audit Provider's compliance with this DPA once per "
                "year upon thirty (30) days' notice. Provider shall cooperate and provide "
                "access to relevant records."
            ),
            guidance="Balanced GDPR structure; Customer termination right for sub-processor objection; annual audit.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "EXHIBIT B — DATA PROCESSING AGREEMENT\n\n"
                "This Data Processing Agreement (\"DPA\") is an integral and enforceable "
                "part of the Agreement.\n\n"
                "1. DEFINITIONS AND INTERPRETATION. Terms used herein have the meanings "
                "given in the GDPR, CCPA, UK GDPR, and all other applicable data "
                "protection legislation. In the event of conflict between this DPA and the "
                "Agreement, this DPA shall prevail with respect to data protection "
                "matters.\n\n"
                "2. ROLES AND RESPONSIBILITIES. Customer is the controller. Provider is "
                "the processor and shall process personal data only on Customer's "
                "documented instructions. Provider shall immediately inform Customer if it "
                "believes an instruction infringes applicable data protection law.\n\n"
                "3. PROCESSING LIMITATIONS. Provider shall: (a) process personal data "
                "solely for the purpose of providing the Service; (b) not sell, share, or "
                "disclose personal data except as instructed by Customer; (c) not combine "
                "personal data with data from other customers; and (d) not process personal "
                "data for profiling, advertising, or any purpose other than providing the "
                "Service.\n\n"
                "4. PERSONNEL. All Provider personnel with access to personal data shall be "
                "subject to binding confidentiality obligations and shall receive regular "
                "data protection training.\n\n"
                "5. SUB-PROCESSORS. Provider shall obtain Customer's specific prior written "
                "consent before engaging any sub-processor. Provider shall enter into "
                "written agreements with sub-processors imposing obligations equivalent to "
                "those in this DPA. Provider remains fully liable for acts and omissions of "
                "its sub-processors.\n\n"
                "6. SECURITY. Provider shall implement technical and organizational "
                "measures at least as protective as those described in Section 13, "
                "including encryption, pseudonymization, and regular security testing.\n\n"
                "7. BREACH NOTIFICATION. Provider shall notify Customer within twenty-four "
                "(24) hours of discovering any actual or suspected personal data breach, "
                "providing all information required by Article 33 of the GDPR and assisting "
                "Customer with regulatory notifications.\n\n"
                "8. DATA SUBJECT RIGHTS. Provider shall assist Customer in responding to "
                "data subject requests within ten (10) business days at no additional cost. "
                "Provider shall implement technical measures enabling automated fulfillment "
                "of access, portability, and erasure requests.\n\n"
                "9. DPIAs AND CONSULTATION. Provider shall assist Customer with data "
                "protection impact assessments and prior consultations with supervisory "
                "authorities as required by applicable law.\n\n"
                "10. INTERNATIONAL TRANSFERS. Transfers outside the EEA, UK, or Switzerland "
                "require: (a) EU Standard Contractual Clauses (SCCs) as set forth in "
                "Annex 2; (b) a transfer impact assessment; and (c) supplementary measures "
                "as necessary. Provider shall inform Customer of any government access "
                "requests.\n\n"
                "11. DELETION AND RETURN. Upon termination, Provider shall: (a) return all "
                "personal data in a structured, commonly used, machine-readable format; and "
                "(b) permanently delete all copies, including from backups, within thirty "
                "(30) days, with certified written confirmation.\n\n"
                "12. AUDIT. Customer or its authorized auditor may audit Provider's "
                "compliance with this DPA at any time upon fifteen (15) days' notice and "
                "no more than twice per year. Provider shall cooperate fully and bear its "
                "own costs. SOC 2 reports supplement but do not replace audit rights."
            ),
            guidance="Strict GDPR: specific sub-processor consent, 24-hour breach notice, full audit rights.",
        ),
        position=21,
        cross_references=["data_security", "confidentiality", "data_ownership"],
    ),

    # ── 22. ORDER FORM (EXHIBIT C) ───────────────────────────────────────
    _clause(
        "order_form",
        "Order Form (Exhibit C)",
        preferred=_tier(
            "vendor-protective",
            (
                "EXHIBIT C — ORDER FORM\n\n"
                "This Order Form is entered into pursuant to the Software-as-a-Service "
                "Agreement dated {{effective_date}} between {{provider_name}} (\"Provider\") "
                "and {{customer_name}} (\"Customer\").\n\n"
                "1. SERVICE: {{service_description}}\n"
                "2. SUBSCRIPTION TIER: As selected by Customer\n"
                "3. AUTHORIZED USERS: {{authorized_users}}\n"
                "4. SUBSCRIPTION TERM: {{term_months}} months commencing on "
                "{{effective_date}}\n"
                "5. FEES: {{price_amount}} per {{billing_frequency}} under the "
                "{{pricing_model}} model\n"
                "6. ANNUAL CONTRACT VALUE: {{annual_value}}\n"
                "7. AUTO-RENEWAL: {{auto_renewal_text}}\n"
                "8. PAYMENT TERMS: Net 30 days from invoice date\n"
                "9. SPECIAL TERMS: None, unless specified below.\n\n"
                "This Order Form is subject to and governed by the terms of the Agreement. "
                "In the event of a conflict between this Order Form and the Agreement, the "
                "Agreement shall prevail.\n\n"
                "PROVIDER: {{provider_name}}\n"
                "By: ___________________________\n"
                "Name:\nTitle:\nDate:\n\n"
                "CUSTOMER: {{customer_name}}\n"
                "By: ___________________________\n"
                "Name:\nTitle:\nDate:"
            ),
            guidance="Agreement prevails over Order Form in conflicts.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "EXHIBIT C — ORDER FORM\n\n"
                "Order Form under the Software-as-a-Service Agreement dated "
                "{{effective_date}} between {{provider_name}} and {{customer_name}}.\n\n"
                "1. SERVICE DESCRIPTION: {{service_description}}\n"
                "2. SUBSCRIPTION PLAN: As selected\n"
                "3. AUTHORIZED USERS: {{authorized_users}} (additional users may be added "
                "at the then-current per-user rate)\n"
                "4. INITIAL TERM: {{term_months}} months from {{effective_date}}\n"
                "5. FEES: {{price_amount}} {{billing_frequency}}, {{pricing_model}} model\n"
                "6. ANNUAL VALUE: {{annual_value}}\n"
                "7. RENEWAL: {{auto_renewal_text}}\n"
                "8. PAYMENT: Net 30 days. Late payment subject to interest per Section 5.\n"
                "9. SLA TIER: Standard (see Exhibit A)\n"
                "10. SPECIAL TERMS: [To be completed by the Parties]\n\n"
                "In the event of conflict between this Order Form and the Agreement, this "
                "Order Form shall prevail solely with respect to the specific commercial "
                "terms set forth herein.\n\n"
                "{{provider_name}}\n"
                "Signature: ___________________________\n"
                "Name:\nTitle:\nDate:\n\n"
                "{{customer_name}}\n"
                "Signature: ___________________________\n"
                "Name:\nTitle:\nDate:"
            ),
            guidance="Order Form prevails for commercial terms only.",
        ),
        fallback=_tier(
            "customer-protective",
            (
                "EXHIBIT C — ORDER FORM\n\n"
                "This Order Form (\"OF\") is incorporated into and forms part of the "
                "Software-as-a-Service Agreement dated {{effective_date}} between "
                "{{provider_name}} (\"Provider\") and {{customer_name}} (\"Customer\").\n\n"
                "1. SERVICE: {{service_description}}\n"
                "2. AUTHORIZED USERS: {{authorized_users}} (Customer may add users at any "
                "time at the per-user rate in effect at the time of the original Order "
                "Form)\n"
                "3. TERM: {{term_months}} months from {{effective_date}}\n"
                "4. FEES: {{price_amount}} {{billing_frequency}} ({{pricing_model}}). Fees "
                "are fixed for the Initial Term and shall not be increased without "
                "Customer's written consent.\n"
                "5. ANNUAL VALUE: {{annual_value}}\n"
                "6. RENEWAL: {{auto_renewal_text}}\n"
                "7. PAYMENT: Net 45 days from invoice date.\n"
                "8. SLA TIER: Premium (see Exhibit A)\n"
                "9. VOLUME DISCOUNT: To be negotiated for orders exceeding the initial "
                "commitment.\n"
                "10. SPECIAL TERMS: [Customer-specified]\n\n"
                "In the event of conflict between this Order Form and the Agreement, this "
                "Order Form shall prevail. In the event of conflict between this Order Form "
                "and any Exhibit, the provision more favorable to Customer shall prevail.\n\n"
                "PROVIDER: {{provider_name}}\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:\n\n"
                "CUSTOMER: {{customer_name}}\n"
                "Signature: ___________________________\n"
                "Printed Name:\nTitle:\nDate:"
            ),
            guidance="Customer-protective: locked pricing, Net 45, customer-favorable conflict resolution.",
        ),
        position=22,
        cross_references=["fees_and_payment", "sla"],
    ),
]

# ---------------------------------------------------------------------------
# Assemble the playbook
# ---------------------------------------------------------------------------

SAAS_PLAYBOOK: Dict[str, Any] = {
    "contract_type": "saas",
    "display_name": "SaaS Agreement (MSA + SLA + DPA + Order Form)",
    "description": (
        "Comprehensive Software-as-a-Service agreement covering the master "
        "subscription agreement, service level commitments, data processing "
        "addendum (GDPR Article 28), and order form. Three tiers represent "
        "vendor perspective: preferred (vendor-protective), acceptable "
        "(balanced), and fallback (customer-protective)."
    ),
    "perspective": "vendor",
    "section_order": _SECTION_ORDER,
    "clauses": _CLAUSES,
    "placeholders": [
        "provider_name", "customer_name", "provider_entity_type",
        "customer_entity_type", "provider_jurisdiction", "customer_jurisdiction",
        "provider_address", "customer_address", "provider_short_name",
        "customer_short_name", "effective_date", "term_months",
        "governing_law", "dispute_resolution", "venue",
        "service_description", "pricing_model", "price_amount",
        "billing_frequency", "uptime_commitment", "authorized_users",
        "auto_renewal_text", "annual_value", "confidentiality_survival_years",
    ],
    "exhibits": ["sla", "dpa", "order_form"],
}
