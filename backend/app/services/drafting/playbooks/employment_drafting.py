"""
Employment Agreement Drafting Playbook
========================================
12-section employment agreement playbook at three negotiation tiers
(preferred / acceptable / fallback).

Perspective: Employer side.
  - preferred  = employer-protective
  - acceptable = balanced
  - fallback   = employee-protective

Placeholders ({{mustache}} syntax):
  {{party_1_name}}, {{party_1_entity_type}}, {{party_1_jurisdiction}},
  {{party_1_address}}, {{party_2_name}}, {{effective_date}},
  {{governing_law}}, {{venue}}
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.drafting.playbooks.nda_drafting import _clause, _tier

# ---------------------------------------------------------------------------
# Section order
# ---------------------------------------------------------------------------

_SECTION_ORDER: List[str] = [
    "preamble",
    "position_duties",
    "compensation",
    "benefits",
    "work_hours",
    "confidentiality",
    "ip_assignment",
    "non_compete",
    "non_solicitation",
    "termination",
    "governing_law",
    "signature",
]

# ---------------------------------------------------------------------------
# Clauses
# ---------------------------------------------------------------------------

_CLAUSES: List[Dict[str, Any]] = [

    # ── 1. PREAMBLE ─────────────────────────────────────────────────────
    _clause(
        "preamble",
        "Employment Agreement",
        preferred=_tier(
            "employer-protective",
            (
                "This Employment Agreement (this \"Agreement\") is entered into as of "
                "{{effective_date}} (the \"Effective Date\") by and between {{party_1_name}}, "
                "a {{party_1_entity_type}} organized under the laws of {{party_1_jurisdiction}}, "
                "with its principal place of business at {{party_1_address}} (the \"Company\"), "
                "and {{party_2_name}} (the \"Employee\"). The Company desires to employ Employee "
                "and Employee desires to accept such employment, subject to the terms and conditions "
                "set forth herein. Employee acknowledges that this Agreement supersedes any prior "
                "agreements, representations, or understandings, whether written or oral, relating "
                "to Employee's employment with the Company."
            ),
            guidance="Company-first; supersedes all prior agreements.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Employment Agreement (this \"Agreement\") is made as of {{effective_date}} "
                "(the \"Effective Date\") between {{party_1_name}}, a {{party_1_entity_type}} "
                "organized under the laws of {{party_1_jurisdiction}}, with offices at "
                "{{party_1_address}} (the \"Company\"), and {{party_2_name}} (the \"Employee\"). "
                "The Company and Employee mutually desire to establish the terms under which "
                "Employee will be employed by the Company. This Agreement sets forth the complete "
                "understanding of the parties regarding Employee's employment and supersedes all "
                "prior negotiations and agreements on this subject."
            ),
            guidance="Balanced; mutual desire language.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "This Employment Agreement (this \"Agreement\") is entered into as of "
                "{{effective_date}} (the \"Effective Date\") between {{party_2_name}} "
                "(the \"Employee\") and {{party_1_name}}, a {{party_1_entity_type}} organized "
                "under the laws of {{party_1_jurisdiction}}, with its principal place of business "
                "at {{party_1_address}} (the \"Company\"). Employee has agreed to accept "
                "employment with the Company in reliance upon the representations, commitments, "
                "and compensation described herein. This Agreement constitutes a binding obligation "
                "of the Company to provide the compensation, benefits, and protections described "
                "herein for the full term of employment."
            ),
            guidance="Employee-first; binding obligation on Company.",
        ),
        category="boilerplate",
        position=1,
    ),

    # ── 2. POSITION AND DUTIES ──────────────────────────────────────────
    _clause(
        "position_duties",
        "Position and Duties",
        preferred=_tier(
            "employer-protective",
            (
                "Employee shall serve in the position of [Title] and shall perform such duties "
                "and responsibilities as may be assigned from time to time by the Company, "
                "including duties reasonably related to Employee's position and experience. "
                "Employee shall report to [Reporting Manager/Title] or such other person as the "
                "Company may designate. Employee shall devote substantially all of Employee's "
                "business time, attention, skill, and effort to the performance of duties under "
                "this Agreement and shall not engage in any other business activity, whether or "
                "not for compensation, without the Company's prior written consent. Employee "
                "shall comply with all Company policies, procedures, and codes of conduct as "
                "may be adopted or amended from time to time."
            ),
            guidance="Broad duty assignment; exclusivity of service; policy compliance.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Employee shall serve as [Title] and shall perform duties and responsibilities "
                "consistent with such position as reasonably assigned by the Company. Employee "
                "shall report to [Reporting Manager/Title]. Employee shall devote Employee's full "
                "business time and best professional efforts to the Company during business hours. "
                "Employee may engage in civic, charitable, and personal investment activities "
                "provided they do not interfere with Employee's duties or create a conflict of "
                "interest. The Company shall provide Employee with the resources, support, and "
                "authority reasonably necessary to perform the assigned duties."
            ),
            guidance="Allows personal activities; Company provides resources.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Employee shall serve as [Title] with duties and responsibilities materially "
                "consistent with such position as described in Exhibit A attached hereto. The "
                "Company shall not materially diminish Employee's title, duties, authority, or "
                "reporting relationships without Employee's written consent. Employee shall report "
                "to [Reporting Manager/Title]. Employee shall devote reasonable business time and "
                "effort to the Company but may engage in outside business activities, board service, "
                "teaching, and personal investments provided they do not materially interfere with "
                "Employee's duties or create a direct competitive conflict. Any material change to "
                "Employee's duties or reporting structure shall constitute Good Reason for "
                "termination purposes under Section 10."
            ),
            guidance="Duties defined in exhibit; material change triggers Good Reason.",
        ),
        category="commercial_terms",
        position=2,
    ),

    # ── 3. COMPENSATION ─────────────────────────────────────────────────
    _clause(
        "compensation",
        "Compensation",
        preferred=_tier(
            "employer-protective",
            (
                "Base Salary. The Company shall pay Employee an annual base salary of $[Amount] "
                "(the \"Base Salary\"), payable in accordance with the Company's standard payroll "
                "practices, less applicable withholdings. The Company may review the Base Salary "
                "annually but is under no obligation to increase it. Bonus. Employee may be "
                "eligible for a discretionary annual bonus as determined by the Company in its "
                "sole discretion based on individual performance and Company results. No bonus "
                "shall be deemed earned until actually paid, and Employee must be actively employed "
                "on the payment date to receive any bonus. Equity. Employee may be eligible for "
                "equity awards under the Company's equity incentive plan, subject to the terms "
                "of the plan and applicable award agreements."
            ),
            guidance="Discretionary bonus; no obligation to increase salary; equity subject to plan.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Base Salary. The Company shall pay Employee an annual base salary of $[Amount] "
                "(the \"Base Salary\"), payable in accordance with standard payroll practices. "
                "The Base Salary shall be reviewed annually and may be increased (but not decreased "
                "without Employee's consent) based on performance and market conditions. Bonus. "
                "Employee shall be eligible for a target annual bonus of [X]% of Base Salary, "
                "based on achievement of mutually agreed performance objectives. Bonus payments "
                "shall be made within ninety (90) days after the end of the applicable performance "
                "period. Equity. Employee shall receive an initial equity grant of [shares/options] "
                "under the Company's equity incentive plan, vesting over four (4) years with a "
                "one-year cliff, subject to the terms of the plan and award agreement."
            ),
            guidance="No salary decrease; target bonus with objectives; defined equity grant.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Base Salary. The Company shall pay Employee an annual base salary of not less than "
                "$[Amount] (the \"Base Salary\"), payable in accordance with the Company's standard "
                "payroll practices. The Base Salary shall be reviewed annually and shall be increased "
                "by no less than the greater of three percent (3%) or the consumer price index "
                "adjustment. The Company shall not reduce the Base Salary without Employee's written "
                "consent. Bonus. Employee shall receive a guaranteed minimum annual bonus of [X]% "
                "of Base Salary, with a target bonus of [Y]% based on mutually agreed objectives. "
                "Pro-rata bonus shall be paid upon termination without cause or resignation for "
                "Good Reason. Equity. Employee shall receive an initial equity grant as specified "
                "in the offer letter, with acceleration provisions as set forth in Section 10."
            ),
            guidance="Guaranteed minimum bonus; CPI salary floor; pro-rata on termination; acceleration.",
        ),
        category="commercial_terms",
        position=3,
    ),

    # ── 4. BENEFITS ──────────────────────────────────────────────────────
    _clause(
        "benefits",
        "Benefits",
        preferred=_tier(
            "employer-protective",
            (
                "Employee shall be eligible to participate in benefit plans and programs generally "
                "available to similarly situated employees, subject to the terms and conditions of "
                "such plans. The Company reserves the right to modify, amend, or terminate any "
                "benefit plan at any time in its discretion. Employee shall be entitled to paid "
                "time off in accordance with the Company's PTO policy as in effect from time to "
                "time. The Company shall not be required to maintain any particular benefit plan "
                "or level of benefits during the term of this Agreement."
            ),
            guidance="Company discretion over benefits; standard PTO policy.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Employee shall be eligible to participate in all benefit plans generally available "
                "to employees at Employee's level, including health insurance (medical, dental, and "
                "vision), life insurance, disability insurance, and retirement plans (401(k) or "
                "equivalent with Company matching). Employee shall receive not less than [X] days "
                "of paid time off per year, accruing on a pro-rata basis. The Company shall provide "
                "reasonable notice of material changes to benefit plans. Employee shall also be "
                "eligible for the Company's professional development and education reimbursement "
                "programs."
            ),
            guidance="Specific benefits enumerated; minimum PTO commitment; development benefits.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Employee shall participate in all benefit plans available to senior employees, "
                "including comprehensive health insurance (medical, dental, vision, and mental "
                "health) for Employee and dependents, life insurance of not less than two times "
                "Base Salary, short-term and long-term disability insurance, and the Company's "
                "retirement plan with maximum employer matching. Employee shall receive not less "
                "than [X] days of paid time off per year, with unused PTO carrying over to the "
                "following year. The Company shall not reduce the level of benefits provided to "
                "Employee below the level in effect on the Effective Date without Employee's "
                "written consent. The Company shall reimburse Employee for all reasonable "
                "professional development expenses up to $[Amount] per year."
            ),
            guidance="Comprehensive enumerated benefits; PTO carryover; no reduction without consent.",
        ),
        category="commercial_terms",
        position=4,
    ),

    # ── 5. WORK HOURS ───────────────────────────────────────────────────
    _clause(
        "work_hours",
        "Work Hours and Location",
        preferred=_tier(
            "employer-protective",
            (
                "Employee's normal work schedule shall be determined by the Company and may include "
                "hours beyond the standard business day as reasonably necessary to fulfill Employee's "
                "duties. If Employee is classified as exempt under the Fair Labor Standards Act, "
                "Employee shall not be entitled to overtime compensation. The Company shall "
                "determine Employee's primary work location, which may be modified at the Company's "
                "discretion upon reasonable notice. Employee shall be available to travel as "
                "reasonably required for the performance of duties."
            ),
            guidance="Company sets schedule and location; exempt status; travel requirement.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Employee's regular work schedule shall be Monday through Friday during standard "
                "business hours, with flexibility as mutually agreed. Employee's primary work "
                "location shall be [Office Location / Remote / Hybrid]. Any material change to "
                "Employee's work location shall require thirty (30) days' advance notice and "
                "Employee's reasonable consent. The Company shall reimburse Employee for reasonable "
                "and pre-approved business travel expenses in accordance with Company policy. "
                "If Employee is classified as non-exempt, overtime shall be compensated in "
                "accordance with applicable law."
            ),
            guidance="Defined schedule; location change requires consent; travel reimbursement.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Employee's regular work schedule shall not exceed forty (40) hours per week "
                "absent mutual agreement. Employee's primary work location shall be [Office "
                "Location / Remote / Hybrid] and shall not be changed without Employee's written "
                "consent. If remote work is permitted, the Company shall provide or reimburse "
                "Employee for necessary equipment, internet, and home office expenses. Business "
                "travel shall be limited to [X] days per month unless Employee agrees otherwise. "
                "All travel shall be in business class for flights over four hours. The Company "
                "shall comply with all applicable wage and hour laws and shall compensate overtime "
                "as required by law regardless of exempt classification."
            ),
            guidance="40-hour cap; location locked; home office reimbursement; travel limits.",
        ),
        category="commercial_terms",
        position=5,
    ),

    # ── 6. CONFIDENTIALITY ──────────────────────────────────────────────
    _clause(
        "confidentiality",
        "Confidentiality",
        preferred=_tier(
            "employer-protective",
            (
                "Employee acknowledges that during employment, Employee will have access to and "
                "become acquainted with Confidential Information of the Company. \"Confidential "
                "Information\" means all non-public information relating to the Company's business, "
                "including trade secrets, customer lists, financial data, business plans, product "
                "roadmaps, source code, algorithms, marketing strategies, vendor terms, and employee "
                "information, whether disclosed orally, in writing, or electronically. Employee "
                "shall hold all Confidential Information in strict confidence, shall not disclose "
                "it to any third party, and shall not use it for any purpose other than performing "
                "Employee's duties. These obligations shall survive termination of employment "
                "indefinitely with respect to trade secrets and for five (5) years for all other "
                "Confidential Information."
            ),
            guidance="Broad definition; indefinite for trade secrets; 5-year survival.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "During and after employment, Employee shall maintain the confidentiality of the "
                "Company's Confidential Information. \"Confidential Information\" means non-public "
                "information relating to the Company's business that is marked as confidential or "
                "that a reasonable person would understand to be confidential. Confidential "
                "Information does not include information that: (a) is or becomes publicly available "
                "through no fault of Employee; (b) was known to Employee before employment; or "
                "(c) is independently developed by Employee outside of employment without use of "
                "Confidential Information. Employee may disclose Confidential Information as "
                "required by law or court order, provided Employee gives the Company prompt notice "
                "and cooperates with efforts to obtain a protective order. These obligations "
                "survive for three (3) years after termination."
            ),
            guidance="Standard exclusions; whistleblower-friendly; 3-year survival.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Employee agrees to maintain the confidentiality of the Company's Confidential "
                "Information during employment and for two (2) years following termination. "
                "\"Confidential Information\" means information that is both (i) specifically "
                "identified as confidential by the Company in writing at the time of disclosure "
                "and (ii) not generally known in the industry. Confidential Information expressly "
                "excludes: Employee's general knowledge, skills, and experience; information in "
                "the public domain; information independently developed; and Employee's personal "
                "contacts and relationships. Nothing in this Agreement restricts Employee's right "
                "to discuss wages, working conditions, or workplace concerns, or to report "
                "potential violations of law to government agencies without prior Company notice "
                "or authorization."
            ),
            guidance="Narrow definition; 2-year survival; protects whistleblower and NLRA rights.",
        ),
        category="confidentiality",
        position=6,
    ),

    # ── 7. IP ASSIGNMENT ────────────────────────────────────────────────
    _clause(
        "ip_assignment",
        "Intellectual Property Assignment",
        preferred=_tier(
            "employer-protective",
            (
                "Work Product. All inventions, works of authorship, designs, discoveries, "
                "improvements, trade secrets, and other intellectual property (collectively, "
                "\"Work Product\") conceived, created, or reduced to practice by Employee, alone "
                "or with others, during Employee's employment and related to the Company's business "
                "or created using Company resources, shall be the sole and exclusive property of "
                "the Company. All Work Product shall be considered works made for hire to the "
                "maximum extent permitted by law. To the extent any Work Product does not qualify "
                "as a work made for hire, Employee hereby irrevocably assigns to the Company all "
                "right, title, and interest therein. Employee shall promptly disclose all Work "
                "Product to the Company and shall execute all documents necessary to perfect the "
                "Company's rights. Prior Inventions. Employee has listed on Exhibit B all prior "
                "inventions that Employee wishes to exclude from this assignment."
            ),
            guidance="Broad assignment; work-for-hire; disclosure obligation; prior inventions exhibit.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "Work Product. All inventions, works, and intellectual property created by Employee "
                "within the scope of employment and related to the Company's current or planned "
                "business shall be the property of the Company as works made for hire. To the "
                "extent any such work does not qualify as work made for hire, Employee assigns all "
                "rights to the Company. Employee shall disclose inventions related to the Company's "
                "business promptly. This assignment does not apply to inventions developed entirely "
                "on Employee's own time without use of Company resources, unless they relate to "
                "the Company's business or result from work performed for the Company. Prior "
                "Inventions excluded from this Agreement are listed on Exhibit B."
            ),
            guidance="Scope limited to Company business; own-time exception.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Work Product. Inventions and works of authorship created by Employee within the "
                "scope of Employee's assigned duties and using Company resources shall be assigned "
                "to the Company. This assignment applies only to work directly related to Employee's "
                "specific job responsibilities as described in Section 2. Employee retains all "
                "rights in inventions developed entirely on Employee's own time, using Employee's "
                "own resources, that do not relate to the Company's current business or demonstrably "
                "anticipated research. To the extent required by applicable state law (including "
                "California Labor Code Section 2870, Delaware Code Title 19 Section 805, and "
                "similar statutes), this Section shall not apply to inventions that qualify for "
                "statutory protection. Prior Inventions are listed on Exhibit B, and the Company "
                "acknowledges Employee's ownership thereof."
            ),
            guidance="Narrow scope; statutory carve-outs; own-time/resources exception explicit.",
        ),
        category="ip_ownership",
        position=7,
    ),

    # ── 8. NON-COMPETE ──────────────────────────────────────────────────
    _clause(
        "non_compete",
        "Non-Competition",
        preferred=_tier(
            "employer-protective",
            (
                "During employment and for twenty-four (24) months following termination for any "
                "reason (the \"Restricted Period\"), Employee shall not, directly or indirectly, "
                "engage in, own, manage, operate, consult for, or be employed by any business that "
                "competes with the Company's business as conducted at the time of termination, "
                "within any geographic area in which the Company conducts business or has concrete "
                "plans to conduct business. Employee acknowledges that the Company's business is "
                "conducted nationally and internationally, and that a broad geographic restriction "
                "is reasonable given Employee's access to Confidential Information and customer "
                "relationships. Employee further agrees not to assist any person or entity in "
                "competing with the Company during the Restricted Period."
            ),
            guidance="24-month; broad geographic and activity scope.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "During employment and for twelve (12) months following termination (the "
                "\"Restricted Period\"), Employee shall not, directly or indirectly, provide "
                "services to a Competing Business in a role substantially similar to Employee's "
                "role at the Company within the geographic territories where Employee had material "
                "responsibilities. \"Competing Business\" means any entity whose primary business "
                "directly competes with the Company's principal products or services as of the "
                "termination date. This restriction shall not prevent Employee from: (a) owning "
                "less than five percent (5%) of publicly traded securities; (b) working in a "
                "division or role of a diversified company that does not compete with the Company; "
                "or (c) engaging in activities approved in writing by the Company."
            ),
            guidance="12-month; similar role limitation; carve-outs for passive investment and non-competing divisions.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "During employment and for six (6) months following termination without cause or "
                "resignation for Good Reason (the \"Restricted Period\"), Employee shall not "
                "directly provide services in a substantially identical role to a direct competitor "
                "of the Company within the metropolitan area of Employee's primary work location. "
                "This restriction shall not apply if Employee is terminated for cause, resigns "
                "without Good Reason, or if the Company fails to pay the non-compete consideration "
                "described below. As consideration for this non-compete, the Company shall pay "
                "Employee fifty percent (50%) of Employee's Base Salary during the Restricted "
                "Period (the \"Garden Leave Payment\"). If the Company elects not to make the "
                "Garden Leave Payment, this non-compete shall be void. This Section shall be "
                "unenforceable to the extent prohibited by applicable state law."
            ),
            guidance="6-month; narrow scope; garden leave payment required; state law savings clause.",
        ),
        category="restrictive_covenants",
        position=8,
    ),

    # ── 9. NON-SOLICITATION ─────────────────────────────────────────────
    _clause(
        "non_solicitation",
        "Non-Solicitation",
        preferred=_tier(
            "employer-protective",
            (
                "During employment and for twenty-four (24) months following termination for any "
                "reason, Employee shall not, directly or indirectly: (a) solicit, recruit, or hire "
                "any employee or contractor of the Company, or encourage any such person to leave "
                "the Company's service; or (b) solicit, divert, or attempt to divert any customer, "
                "client, vendor, or business partner of the Company for the purpose of providing "
                "products or services competitive with those offered by the Company. This "
                "restriction applies to any person who was an employee, contractor, customer, "
                "or business partner at any time during the twelve (12) months preceding "
                "Employee's termination."
            ),
            guidance="24-month; covers employees, contractors, customers, and vendors.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "During employment and for twelve (12) months following termination, Employee "
                "shall not, directly or indirectly: (a) solicit or recruit any employee or "
                "contractor of the Company with whom Employee had material working contact "
                "during the twelve (12) months preceding termination; or (b) solicit any customer "
                "or client of the Company with whom Employee had a material business relationship "
                "during such period, for the purpose of diverting business to a competing entity. "
                "This restriction shall not prohibit general advertising or recruitment not "
                "specifically targeted at Company personnel, or prevent Employee from hiring any "
                "person who independently responds to a general job posting."
            ),
            guidance="12-month; limited to material contacts; general advertising carve-out.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "During employment and for six (6) months following termination, Employee shall "
                "not directly and personally solicit any employee of the Company who reported "
                "directly to Employee within the six (6) months preceding termination, for the "
                "purpose of inducing such employee to leave the Company. This restriction does "
                "not apply to: (a) general advertising or job postings; (b) recruitment by third "
                "parties acting independently; (c) individuals who contact Employee on their own "
                "initiative; or (d) former employees who left the Company before Employee's "
                "termination. Employee shall have no restrictions on solicitation of customers "
                "or clients, as such relationships belong to Employee as well as the Company."
            ),
            guidance="6-month; direct reports only; no customer non-solicit; broad exceptions.",
        ),
        category="restrictive_covenants",
        position=9,
    ),

    # ── 10. TERMINATION ─────────────────────────────────────────────────
    _clause(
        "termination",
        "Termination",
        preferred=_tier(
            "employer-protective",
            (
                "At-Will Employment. Employee's employment is at-will and may be terminated by "
                "either party at any time, with or without cause or notice. Termination Without "
                "Cause. If the Company terminates Employee's employment without Cause, Employee "
                "shall receive: (a) accrued but unpaid salary through the termination date; "
                "(b) accrued but unused PTO; and (c) subject to execution of a release of claims, "
                "severance equal to three (3) months of Base Salary paid in installments. "
                "Termination for Cause. \"Cause\" means: material breach of this Agreement; fraud "
                "or dishonesty; conviction of a felony; gross misconduct; willful failure to "
                "perform duties after written notice and thirty (30) days to cure; or violation "
                "of Company policy. No severance is payable upon termination for Cause."
            ),
            guidance="At-will; 3-month severance; broad Cause definition.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "At-Will Employment. Employment is at-will and may be terminated by either party. "
                "Termination Without Cause. If the Company terminates Employee without Cause, "
                "Employee shall receive, subject to a mutual release of claims: (a) accrued "
                "compensation; (b) severance equal to six (6) months of Base Salary; (c) pro-rata "
                "bonus for the year of termination; and (d) continuation of health benefits at "
                "Company expense for six (6) months. Termination for Cause. \"Cause\" means: "
                "material breach after written notice and thirty (30) days to cure; conviction of "
                "a felony involving dishonesty; fraud or embezzlement; or willful and sustained "
                "failure to perform duties. Resignation for Good Reason. Employee may resign for "
                "Good Reason (material reduction in duties, compensation, or relocation beyond "
                "50 miles) and receive severance as if terminated without Cause."
            ),
            guidance="6-month severance; Good Reason defined; COBRA continuation.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "Termination Without Cause. If the Company terminates Employee without Cause, "
                "Employee shall receive: (a) twelve (12) months of Base Salary as severance; "
                "(b) the full target bonus for the year of termination; (c) immediate vesting of "
                "all unvested equity awards; (d) eighteen (18) months of Company-paid COBRA "
                "continuation; and (e) outplacement services for up to six (6) months. Severance "
                "shall be paid in a lump sum within thirty (30) days. Termination for Cause. "
                "\"Cause\" is strictly limited to: conviction of a felony directly related to "
                "employment; willful fraud causing material financial harm to the Company; or "
                "material breach of this Agreement after written notice specifying the breach and "
                "forty-five (45) days to cure. Good Reason. Employee may resign for Good Reason "
                "upon: material diminution of duties, title, or authority; reduction in Base Salary "
                "or target bonus; relocation beyond twenty-five (25) miles; or material breach by "
                "the Company. Resignation for Good Reason triggers the same severance as "
                "termination without Cause. Change of Control. In the event of a Change of "
                "Control, all equity shall immediately vest, and if Employee is terminated within "
                "twelve (12) months of such event, severance shall be doubled."
            ),
            guidance="12-month severance; lump sum; equity acceleration; double-trigger CoC.",
        ),
        category="termination",
        position=10,
    ),

    # ── 11. GOVERNING LAW ───────────────────────────────────────────────
    _clause(
        "governing_law",
        "Governing Law and Dispute Resolution",
        preferred=_tier(
            "employer-protective",
            (
                "This Agreement shall be governed by and construed in accordance with the laws of "
                "{{governing_law}}, without regard to its conflict of laws principles. Any dispute "
                "arising out of or relating to this Agreement or Employee's employment shall be "
                "resolved exclusively by binding arbitration administered by the American "
                "Arbitration Association under its Employment Arbitration Rules, conducted in "
                "{{venue}} before a single arbitrator. The arbitrator's award shall be final and "
                "binding and may be entered as a judgment in any court of competent jurisdiction. "
                "Each party shall bear its own attorneys' fees and costs. Employee waives any right "
                "to participate in a class, collective, or representative action."
            ),
            guidance="Mandatory arbitration; class action waiver; each party bears own costs.",
        ),
        acceptable=_tier(
            "balanced",
            (
                "This Agreement shall be governed by the laws of {{governing_law}}. The parties "
                "shall attempt to resolve any dispute through good faith negotiation for thirty "
                "(30) days. If unresolved, either party may initiate mediation before a mutually "
                "agreed mediator. If mediation fails within sixty (60) days, either party may "
                "pursue binding arbitration under the AAA Employment Arbitration Rules in {{venue}} "
                "or file suit in a court of competent jurisdiction. The prevailing party in any "
                "arbitration or litigation shall be entitled to recover reasonable attorneys' fees. "
                "Nothing herein prevents either party from seeking temporary injunctive or equitable "
                "relief in court."
            ),
            guidance="Escalation process; choice of arbitration or court; fee-shifting.",
        ),
        fallback=_tier(
            "employee-protective",
            (
                "This Agreement shall be governed by the laws of {{governing_law}}. Employee shall "
                "have the right to pursue any dispute arising under this Agreement in the state or "
                "federal courts located in {{venue}}, and the Company consents to the exclusive "
                "jurisdiction of such courts. Employee retains all rights to pursue claims under "
                "applicable employment statutes, including the right to file charges with government "
                "agencies and participate in class or collective actions. If the Company initiates "
                "legal proceedings against Employee, the Company shall advance Employee's reasonable "
                "attorneys' fees, subject to repayment only if Employee is found to have acted in "
                "bad faith. Employee shall not be required to arbitrate any claim unless Employee "
                "voluntarily elects to do so."
            ),
            guidance="Court access preserved; no mandatory arbitration; fee advancement; class action rights.",
        ),
        category="dispute_resolution",
        position=11,
    ),

    # ── 12. SIGNATURE ───────────────────────────────────────────────────
    _clause(
        "signature",
        "Signature",
        preferred=_tier(
            "employer-protective",
            (
                "IN WITNESS WHEREOF, the parties have executed this Employment Agreement as of "
                "the Effective Date.\n\n"
                "{{party_1_name}} (the Company)\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "{{party_2_name}} (Employee)\n"
                "Signature: ____________________\n"
                "Date: _________________________"
            ),
        ),
        acceptable=_tier(
            "balanced",
            (
                "IN WITNESS WHEREOF, the parties have executed this Employment Agreement as of "
                "the Effective Date first written above.\n\n"
                "{{party_1_name}}\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "{{party_2_name}}\n"
                "Signature: ____________________\n"
                "Date: _________________________"
            ),
        ),
        fallback=_tier(
            "employee-protective",
            (
                "IN WITNESS WHEREOF, the parties have executed this Employment Agreement.\n\n"
                "{{party_2_name}} (Employee)\n"
                "Signature: ____________________\n"
                "Date: _________________________\n\n"
                "{{party_1_name}} (the Company)\n"
                "By: ___________________________\n"
                "Name: _________________________\n"
                "Title: ________________________\n"
                "Date: _________________________\n\n"
                "Employee acknowledges having had the opportunity to review this Agreement with "
                "independent legal counsel before signing."
            ),
        ),
        category="boilerplate",
        position=12,
    ),
]

# ---------------------------------------------------------------------------
# Exported playbook
# ---------------------------------------------------------------------------

EMPLOYMENT_PLAYBOOK: Dict[str, Any] = {
    "name": "Employment Agreement",
    "contract_type": "employment",
    "jurisdiction": "Any",
    "section_order": _SECTION_ORDER,
    "clauses": _CLAUSES,
}
