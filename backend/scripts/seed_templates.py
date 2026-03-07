"""
Seed Contract Templates — paired with default playbooks.

Creates 6 pre-built Indian contract templates:
1. NDA — Mutual (free)
2. NDA — Unilateral (free)
3. Master Service Agreement (premium)
4. SaaS Subscription Agreement (premium)
5. Employment Agreement (premium)
6. Consulting Agreement (premium)

Usage:
    cd backend && python scripts/seed_templates.py
"""

import asyncio
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.template import ContractTemplate
from app.models.playbook import Playbook


TEMPLATES = [
    {
        "name": "NDA — Mutual",
        "description": "Standard mutual NDA for two Indian parties exchanging confidential information. Covers definitions, obligations, term (3 years), remedies, and governing law under Indian Contract Act, 1872.",
        "category": "nda",
        "paired_playbook_name": "NDA — Mutual",
        "is_premium": False,
        "template_content": """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of [DATE] ("Effective Date")

BETWEEN:

[PARTY A NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] (hereinafter referred to as "Party A")

AND

[PARTY B NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] (hereinafter referred to as "Party B")

(Party A and Party B are individually referred to as a "Party" and collectively as the "Parties")

WHEREAS the Parties wish to explore a potential business relationship and in connection therewith, each Party may disclose certain confidential and proprietary information to the other Party.

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the Parties agree as follows:

1. DEFINITION OF CONFIDENTIAL INFORMATION

1.1 "Confidential Information" means any and all information disclosed by either Party to the other Party, whether orally, in writing, electronically, or by inspection, including but not limited to: trade secrets, business plans, financial information, customer lists, technical data, software, designs, processes, and know-how.

1.2 Confidential Information shall not include information that: (a) is or becomes publicly available through no fault of the Receiving Party; (b) was known to the Receiving Party prior to disclosure; (c) is independently developed by the Receiving Party; or (d) is rightfully received from a third party without restriction.

2. OBLIGATIONS OF RECEIVING PARTY

2.1 Each Party agrees to: (a) hold the other Party's Confidential Information in strict confidence; (b) not disclose such information to any third party without prior written consent; (c) use such information solely for the Purpose; and (d) protect such information with the same degree of care used for its own confidential information, but no less than reasonable care.

3. PERMITTED DISCLOSURES

3.1 A Party may disclose Confidential Information to its employees, directors, advisors, and contractors who have a need to know, provided they are bound by confidentiality obligations no less restrictive than this Agreement.

3.2 A Party may disclose Confidential Information if required by law, regulation, or court order, provided the disclosing party gives prompt written notice to the other Party (to the extent legally permitted) and cooperates in seeking protective measures.

4. TERM AND DURATION

4.1 This Agreement shall be effective from the Effective Date and shall continue for a period of three (3) years unless earlier terminated by either Party with thirty (30) days' written notice.

4.2 The obligations of confidentiality shall survive the termination of this Agreement for a period of three (3) years from the date of disclosure.

5. RETURN OR DESTRUCTION OF INFORMATION

5.1 Upon termination of this Agreement or upon written request by the Disclosing Party, the Receiving Party shall promptly return or destroy all Confidential Information in its possession, including all copies, summaries, and extracts thereof, and certify such destruction in writing.

6. REMEDIES

6.1 Each Party acknowledges that any breach of this Agreement may cause irreparable harm to the other Party, and the non-breaching Party shall be entitled to seek injunctive relief in addition to any other remedies available at law or in equity.

7. NO LICENSE OR WARRANTY

7.1 Nothing in this Agreement grants either Party any license or rights in the other Party's intellectual property or Confidential Information beyond the limited right to use such information for the Purpose.

7.2 All Confidential Information is provided "AS IS" without warranty of any kind.

8. GOVERNING LAW AND JURISDICTION

8.1 This Agreement shall be governed by and construed in accordance with the laws of India, including the Indian Contract Act, 1872.

8.2 Any disputes arising out of or in connection with this Agreement shall be subject to the exclusive jurisdiction of the courts at [CITY], India.

9. ENTIRE AGREEMENT

9.1 This Agreement constitutes the entire agreement between the Parties with respect to the subject matter hereof and supersedes all prior agreements, understandings, and negotiations.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

PARTY A                                PARTY B
Authorized Signatory                    Authorized Signatory
Name:                                   Name:
Title:                                  Title:
Date:                                   Date:
""",
    },
    {
        "name": "NDA — Unilateral",
        "description": "One-way NDA where only one party discloses confidential information. Suitable for vendor evaluations, hiring processes, and contractor engagements under Indian law.",
        "category": "nda",
        "paired_playbook_name": "NDA — Unilateral",
        "is_premium": False,
        "template_content": """UNILATERAL NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of [DATE] ("Effective Date")

BETWEEN:

[DISCLOSING PARTY NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] (hereinafter referred to as the "Disclosing Party")

AND

[RECEIVING PARTY NAME], a company/individual having its address at [ADDRESS] (hereinafter referred to as the "Receiving Party")

WHEREAS the Disclosing Party possesses certain confidential and proprietary information and wishes to disclose such information to the Receiving Party for the purpose of [PURPOSE] ("Purpose").

NOW, THEREFORE, the Parties agree as follows:

1. DEFINITION OF CONFIDENTIAL INFORMATION

1.1 "Confidential Information" means any and all information disclosed by the Disclosing Party to the Receiving Party, whether orally, in writing, or by inspection, including but not limited to: trade secrets, business plans, financial data, customer information, technical specifications, software, designs, and know-how.

1.2 Confidential Information shall not include information that: (a) is publicly available through no fault of the Receiving Party; (b) was known to the Receiving Party prior to disclosure; (c) is independently developed by the Receiving Party without reference to the Confidential Information; or (d) is rightfully obtained from a third party without restriction.

2. OBLIGATIONS OF THE RECEIVING PARTY

2.1 The Receiving Party shall: (a) hold all Confidential Information in strict confidence; (b) not disclose any Confidential Information to third parties without prior written consent of the Disclosing Party; (c) use the Confidential Information solely for the Purpose; (d) take all reasonable precautions to prevent unauthorized disclosure; and (e) restrict access to Confidential Information to its employees and agents who have a need to know and are bound by confidentiality obligations.

3. PERMITTED DISCLOSURES

3.1 The Receiving Party may disclose Confidential Information to the extent required by applicable law, regulation, or court order, provided the Receiving Party gives the Disclosing Party prompt written notice (to the extent legally permitted) and cooperates in obtaining a protective order.

4. NO REVERSE ENGINEERING

4.1 The Receiving Party shall not reverse engineer, decompile, or disassemble any Confidential Information, including any software or physical objects provided under this Agreement, except to the extent permitted by applicable law for interoperability purposes.

5. TERM AND SURVIVAL

5.1 This Agreement shall remain in effect for a period of two (2) years from the Effective Date.

5.2 The confidentiality obligations shall survive termination for a period of three (3) years.

6. RETURN OF INFORMATION

6.1 Upon termination or written request, the Receiving Party shall return or destroy all Confidential Information and certify such destruction in writing within fifteen (15) business days.

7. NO LICENSE

7.1 No license or rights under any patent, copyright, trademark, or trade secret are granted by implication or otherwise under this Agreement.

8. REMEDIES

8.1 The Receiving Party acknowledges that breach may cause irreparable harm and the Disclosing Party shall be entitled to injunctive relief in addition to all other remedies.

9. GOVERNING LAW

9.1 This Agreement shall be governed by the laws of India, including the Indian Contract Act, 1872.

9.2 Disputes shall be subject to the exclusive jurisdiction of courts at [CITY], India.

IN WITNESS WHEREOF, the Parties have executed this Agreement.

DISCLOSING PARTY                        RECEIVING PARTY
Name:                                   Name:
Title:                                  Title:
Date:                                   Date:
""",
    },
    {
        "name": "Master Service Agreement (MSA)",
        "description": "Comprehensive MSA template for ongoing IT, consulting, or outsourcing relationships. Covers scope, SLAs, payment, IP, liability caps, termination, and Indian law compliance.",
        "category": "msa",
        "paired_playbook_name": "Master Service Agreement (MSA)",
        "is_premium": True,
        "template_content": """MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into as of [DATE] ("Effective Date")

BETWEEN:

[CLIENT NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] ("Client")

AND

[SERVICE PROVIDER NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] ("Service Provider")

1. SCOPE OF SERVICES

1.1 The Service Provider shall provide the services described in one or more Statements of Work ("SOW") executed by both Parties and attached as annexures to this Agreement.

1.2 Each SOW shall specify: (a) detailed description of services; (b) deliverables and milestones; (c) timelines; (d) acceptance criteria; and (e) fees and payment schedule.

2. TERM

2.1 This Agreement shall commence on the Effective Date and continue for an initial term of one (1) year ("Initial Term"), unless earlier terminated in accordance with Section 12.

2.2 This Agreement shall automatically renew for successive one (1) year periods unless either Party provides thirty (30) days' written notice of non-renewal prior to the expiry of the then-current term.

3. PAYMENT TERMS

3.1 The Client shall pay the Service Provider the fees set forth in each SOW.

3.2 Invoices shall be payable within thirty (30) days of receipt ("Net 30").

3.3 Late payments shall accrue interest at the rate of 1.5% per month or the maximum rate permitted by law, whichever is lower.

3.4 All fees are exclusive of applicable taxes (GST/IGST), which shall be borne by the Client.

4. INTELLECTUAL PROPERTY

4.1 Pre-Existing IP: Each Party retains all rights to its pre-existing intellectual property.

4.2 Work Product: All deliverables created specifically for the Client under this Agreement ("Work Product") shall be the exclusive property of the Client upon full payment. The Service Provider hereby assigns all rights, title, and interest in the Work Product to the Client.

4.3 Tools and Frameworks: The Service Provider retains ownership of its pre-existing tools, frameworks, and methodologies used in performing the Services. The Client is granted a non-exclusive, perpetual license to use such tools as embedded in the Work Product.

5. CONFIDENTIALITY

5.1 Each Party shall maintain the confidentiality of the other Party's proprietary information for the term of this Agreement and for three (3) years following termination.

6. WARRANTIES

6.1 The Service Provider warrants that: (a) the Services shall be performed in a professional and workmanlike manner; (b) the deliverables shall conform to the specifications in the applicable SOW; and (c) the Services shall not infringe any third-party intellectual property rights.

6.2 The Client warrants that it has the authority to enter into this Agreement and will provide reasonable cooperation and access necessary for the Service Provider to perform the Services.

7. LIMITATION OF LIABILITY

7.1 Neither Party's aggregate liability under this Agreement shall exceed the total fees paid or payable by the Client in the twelve (12) months preceding the claim.

7.2 Neither Party shall be liable for any indirect, incidental, consequential, special, or punitive damages, including loss of profits, data, or business opportunity.

7.3 The limitations in this Section shall not apply to: (a) breaches of confidentiality; (b) IP infringement; (c) willful misconduct or gross negligence; or (d) indemnification obligations.

8. INDEMNIFICATION

8.1 Each Party shall indemnify, defend, and hold harmless the other Party from and against any third-party claims arising from: (a) breach of this Agreement; (b) negligence or willful misconduct; or (c) violation of applicable law.

8.2 Indemnification is subject to: prompt notice, cooperation, and sole control of defense by the indemnifying Party.

9. DATA PROTECTION

9.1 Both Parties shall comply with applicable data protection laws, including the Information Technology Act, 2000 and the Digital Personal Data Protection Act, 2023.

9.2 If the Service Provider processes personal data on behalf of the Client, the Parties shall execute a Data Processing Agreement.

10. FORCE MAJEURE

10.1 Neither Party shall be liable for failure to perform due to events beyond its reasonable control, including natural disasters, war, pandemic, government action, or interruption of telecommunications.

10.2 The affected Party shall notify the other Party within five (5) business days and use reasonable efforts to mitigate the impact.

11. ASSIGNMENT

11.1 Neither Party may assign this Agreement without the prior written consent of the other Party, except that either Party may assign to an affiliate or in connection with a merger, acquisition, or sale of substantially all assets.

12. TERMINATION

12.1 Termination for Convenience: Either Party may terminate this Agreement with thirty (30) days' written notice.

12.2 Termination for Cause: Either Party may terminate if the other Party materially breaches this Agreement and fails to cure within thirty (30) days of written notice.

12.3 Effect of Termination: Upon termination, the Service Provider shall deliver all Work Product completed to date, and the Client shall pay for Services rendered through the termination date.

13. DISPUTE RESOLUTION

13.1 The Parties shall first attempt to resolve disputes through good-faith negotiation for thirty (30) days.

13.2 If negotiation fails, disputes shall be resolved by binding arbitration under the Arbitration and Conciliation Act, 1996, seated at [CITY], India, with a sole arbitrator appointed by mutual consent.

14. GOVERNING LAW

14.1 This Agreement shall be governed by the laws of India.

IN WITNESS WHEREOF, the Parties have executed this Agreement.

CLIENT                                  SERVICE PROVIDER
Name:                                   Name:
Title:                                  Title:
Date:                                   Date:
""",
    },
    {
        "name": "SaaS Subscription Agreement",
        "description": "Cloud software subscription template covering SLAs, data ownership, security standards, price caps, and DPDP Act 2023 compliance for Indian customers.",
        "category": "saas",
        "paired_playbook_name": "SaaS Subscription Agreement",
        "is_premium": True,
        "template_content": """SAAS SUBSCRIPTION AGREEMENT

This SaaS Subscription Agreement ("Agreement") is entered into as of [DATE]

BETWEEN:

[CUSTOMER NAME], having its principal office at [ADDRESS] ("Customer")

AND

[PROVIDER NAME], having its principal office at [ADDRESS] ("Provider")

1. DEFINITIONS

1.1 "Service" means the cloud-based software application described in the applicable Order Form.
1.2 "Customer Data" means all data uploaded, stored, or processed by Customer through the Service.
1.3 "Subscription Term" means the period specified in the Order Form.

2. GRANT OF LICENSE

2.1 Provider grants Customer a non-exclusive, non-transferable right to access and use the Service during the Subscription Term for Customer's internal business purposes.

3. SERVICE LEVELS

3.1 Provider shall maintain a monthly uptime of at least 99.9% ("Uptime SLA"), measured as: ((Total Minutes - Downtime Minutes) / Total Minutes) x 100.

3.2 Scheduled maintenance windows (notified 48 hours in advance) are excluded from Uptime calculations.

3.3 Service Credits: If monthly uptime falls below the SLA, Customer shall receive service credits as follows: 99.0-99.9%: 10% credit; 95.0-99.0%: 25% credit; below 95.0%: 50% credit.

4. DATA OWNERSHIP AND SECURITY

4.1 Customer Data: Customer retains all rights, title, and interest in Customer Data. Provider acquires no rights in Customer Data except as necessary to provide the Service.

4.2 Security: Provider shall implement and maintain industry-standard security measures, including encryption at rest and in transit, access controls, and regular security audits. Provider shall maintain SOC 2 Type II or ISO 27001 certification.

4.3 Data Processing: Provider shall process Customer Data only as necessary to provide the Service and in accordance with applicable data protection laws, including the Digital Personal Data Protection Act, 2023.

5. FEES AND PAYMENT

5.1 Customer shall pay the subscription fees specified in the Order Form.

5.2 Payment terms: Net 30 from invoice date.

5.3 Price Escalation: Annual fee increases shall not exceed the Consumer Price Index (CPI) plus 2%, with a maximum cap of 8% per year.

6. INTELLECTUAL PROPERTY

6.1 Provider IP: Provider retains all rights in the Service, including all technology, software, and documentation.

6.2 Customer Data: Customer retains all rights in Customer Data. Provider shall not use Customer Data for any purpose other than providing the Service.

6.3 Feedback: Customer grants Provider a perpetual, royalty-free license to use any feedback or suggestions provided regarding the Service.

7. LIMITATION OF LIABILITY

7.1 Provider's aggregate liability shall not exceed the total fees paid by Customer in the twelve (12) months preceding the claim.

7.2 Neither Party shall be liable for indirect, consequential, or punitive damages.

8. INDEMNIFICATION

8.1 Provider shall indemnify Customer against third-party claims alleging that the Service infringes intellectual property rights.

8.2 Customer shall indemnify Provider against claims arising from Customer's use of the Service in violation of applicable law.

9. TERM AND TERMINATION

9.1 The initial Subscription Term is specified in the Order Form.

9.2 Auto-Renewal: The Agreement shall automatically renew for successive one (1) year periods. Either Party may opt out by providing thirty (30) days' written notice before the renewal date.

9.3 Data Portability: Upon termination, Provider shall make Customer Data available for export in a machine-readable format for thirty (30) days, after which Customer Data shall be deleted.

10. FORCE MAJEURE

10.1 Neither Party shall be liable for failure to perform due to events beyond reasonable control.

11. GOVERNING LAW

11.1 This Agreement shall be governed by the laws of India. Disputes shall be resolved by arbitration under the Arbitration and Conciliation Act, 1996.

IN WITNESS WHEREOF, the Parties have executed this Agreement.
""",
    },
    {
        "name": "Employment Agreement (India)",
        "description": "Standard employment agreement for Indian employees covering probation, notice periods, IP assignment, non-compete (Section 27 considerations), and state-specific compliance.",
        "category": "employment",
        "paired_playbook_name": "Employment Agreement (India)",
        "is_premium": True,
        "template_content": """EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of [DATE]

BETWEEN:

[EMPLOYER NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] ("Employer" or "Company")

AND

[EMPLOYEE NAME], residing at [ADDRESS], holding [PAN/AADHAAR] ("Employee")

1. POSITION AND DUTIES

1.1 The Employee is appointed to the position of [JOB TITLE] in the [DEPARTMENT] department, reporting to [REPORTING MANAGER].

1.2 The Employee shall perform the duties as described in Schedule A and such other duties as may be reasonably assigned.

2. COMMENCEMENT AND PROBATION

2.1 The employment shall commence on [START DATE].

2.2 The Employee shall serve a probation period of six (6) months from the commencement date. During probation, either Party may terminate with fifteen (15) days' written notice.

2.3 Upon successful completion of probation, the Employee shall be confirmed in writing.

3. COMPENSATION

3.1 The Employee shall receive an annual CTC of INR [AMOUNT] ("Compensation"), payable monthly, subject to applicable deductions (TDS, PF, ESI as applicable).

3.2 The compensation structure is detailed in Schedule B.

3.3 Annual performance reviews shall be conducted, and any revisions to compensation shall be at the Company's discretion based on performance and market benchmarks.

4. WORKING HOURS AND LEAVE

4.1 Standard working hours shall be [9:00 AM to 6:00 PM], Monday through Friday.

4.2 The Employee shall be entitled to leaves as per the Company's leave policy and applicable state Shops and Establishments Act provisions.

5. NOTICE PERIOD

5.1 After confirmation, either Party may terminate employment with two (2) months' written notice or payment in lieu thereof.

5.2 During the notice period, the Employee shall continue to perform duties diligently and assist in knowledge transfer.

6. INTELLECTUAL PROPERTY

6.1 All work product, inventions, designs, code, and materials created by the Employee in the course of employment or using Company resources ("Work Product") shall be the exclusive property of the Company.

6.2 The Employee assigns all rights, title, and interest in Work Product to the Company.

6.3 This clause does not apply to personal projects created entirely outside working hours, without use of Company resources, and unrelated to the Company's business.

7. CONFIDENTIALITY

7.1 The Employee shall maintain strict confidentiality of all Company information during and after employment.

7.2 Confidentiality obligations shall survive termination for a period of two (2) years.

8. NON-SOLICITATION

8.1 For a period of twelve (12) months following termination, the Employee shall not directly or indirectly solicit any employee, consultant, or client of the Company.

9. RESTRICTIVE COVENANTS

9.1 The Employee acknowledges that the restrictions in Sections 7 and 8 are reasonable and necessary to protect the Company's legitimate business interests.

9.2 Any non-compete restriction shall be limited to the duration of employment only, in accordance with Section 27 of the Indian Contract Act, 1872.

10. TERMINATION

10.1 Termination by Company for Cause: The Company may terminate the Employee immediately for cause, including: (a) material breach of this Agreement; (b) gross misconduct; (c) fraud or dishonesty; (d) conviction of a criminal offense; (e) habitual neglect of duties.

10.2 Termination by Employee: The Employee may resign by providing the notice period specified in Section 5.

10.3 Upon termination, the Employee shall return all Company property, documents, and access credentials.

11. GOVERNING LAW

11.1 This Agreement shall be governed by the laws of India, including applicable state labor laws and the Shops and Establishments Act of [STATE].

11.2 Disputes shall be subject to the jurisdiction of courts at [CITY], India.

IN WITNESS WHEREOF:

EMPLOYER                                EMPLOYEE
Name:                                   Name:
Title:                                  Signature:
Date:                                   Date:
""",
    },
    {
        "name": "Consulting Agreement",
        "description": "Professional services/freelancer agreement for Indian market. Covers scope, milestones, IP ownership, independent contractor status, and liability caps.",
        "category": "custom",
        "paired_playbook_name": "Consulting / Professional Services Agreement",
        "is_premium": True,
        "template_content": """CONSULTING / PROFESSIONAL SERVICES AGREEMENT

This Agreement is entered into as of [DATE]

BETWEEN:

[CLIENT NAME], a company incorporated under the Companies Act, 2013, having its registered office at [ADDRESS] ("Client")

AND

[CONSULTANT NAME], [individual/firm] having its address at [ADDRESS] ("Consultant")

1. ENGAGEMENT AND SCOPE

1.1 The Client engages the Consultant to provide the professional services described in Schedule A ("Services").

1.2 The Consultant shall perform the Services in accordance with the specifications, milestones, and timelines set forth in Schedule A.

2. INDEPENDENT CONTRACTOR STATUS

2.1 The Consultant is an independent contractor and not an employee, agent, or partner of the Client. The Consultant shall have no authority to bind the Client.

2.2 The Consultant is responsible for its own taxes (including GST registration if applicable), insurance, and compliance with applicable laws.

3. FEES AND PAYMENT

3.1 The Client shall pay the Consultant the fees specified in Schedule B, based on milestones or time-and-material basis as agreed.

3.2 Invoices shall be payable within thirty (30) days of receipt.

3.3 The Consultant shall submit invoices with supporting documentation (timesheets, deliverable acceptance, etc.).

4. INTELLECTUAL PROPERTY

4.1 Work Product: All deliverables, reports, code, designs, and materials created under this Agreement ("Work Product") shall be the exclusive property of the Client upon full payment.

4.2 Pre-Existing IP: The Consultant retains ownership of its pre-existing tools, methodologies, and frameworks. The Client is granted a non-exclusive, perpetual license to use any pre-existing IP incorporated into the Work Product.

4.3 The Consultant warrants that the Work Product does not infringe any third-party intellectual property rights.

5. CONFIDENTIALITY

5.1 The Consultant shall maintain strict confidentiality of all Client information for the term of this Agreement and for three (3) years following termination.

5.2 Confidential Information shall not include publicly available information or information independently developed by the Consultant.

6. LIMITATION OF LIABILITY

6.1 The Consultant's aggregate liability shall not exceed the total fees paid under this Agreement in the twelve (12) months preceding the claim.

6.2 Neither Party shall be liable for indirect, consequential, or punitive damages.

7. INDEMNIFICATION

7.1 The Consultant shall indemnify the Client against third-party claims arising from: (a) breach of this Agreement; (b) negligence or willful misconduct; or (c) IP infringement in the Work Product.

7.2 The Client shall indemnify the Consultant against claims arising from the Client's use of the Work Product beyond the agreed scope.

8. TERM AND TERMINATION

8.1 This Agreement shall commence on [START DATE] and continue until completion of the Services or [END DATE], whichever is earlier.

8.2 Either Party may terminate with fifteen (15) days' written notice.

8.3 The Client may terminate immediately for Consultant's material breach.

8.4 Upon termination, the Consultant shall deliver all completed Work Product, and the Client shall pay for Services rendered to date.

9. GOVERNING LAW

9.1 This Agreement shall be governed by the laws of India.

9.2 Disputes shall be resolved by arbitration under the Arbitration and Conciliation Act, 1996, at [CITY], India.

IN WITNESS WHEREOF:

CLIENT                                  CONSULTANT
Name:                                   Name:
Title:                                  Signature:
Date:                                   Date:
""",
    },
]


async def seed_templates():
    """Create all template records with paired playbook references."""
    async with AsyncSessionLocal() as db:
        # Get existing playbook map
        result = await db.execute(
            select(Playbook).where(Playbook.is_default == True)
        )
        playbooks = {p.name: p for p in result.scalars().all()}
        print(f"Found {len(playbooks)} default playbooks")

        # Delete the test template created earlier
        result = await db.execute(
            select(ContractTemplate).where(ContractTemplate.name == "NDA - Mutual")
        )
        test_template = result.scalar_one_or_none()
        if test_template:
            await db.delete(test_template)
            await db.commit()
            print("Deleted test template 'NDA - Mutual'")

        created = 0
        for tmpl_data in TEMPLATES:
            # Check if template already exists
            result = await db.execute(
                select(ContractTemplate).where(ContractTemplate.name == tmpl_data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"  SKIP: '{tmpl_data['name']}' already exists")
                continue

            # Find paired playbook
            paired_playbook = playbooks.get(tmpl_data["paired_playbook_name"])
            if paired_playbook:
                print(f"  Paired: '{tmpl_data['name']}' -> playbook '{paired_playbook.name}'")
            else:
                print(f"  WARNING: No playbook found for '{tmpl_data['paired_playbook_name']}'")

            template = ContractTemplate(
                name=tmpl_data["name"],
                description=tmpl_data["description"],
                category=tmpl_data["category"],
                template_content=tmpl_data["template_content"],
                paired_playbook_id=paired_playbook.id if paired_playbook else None,
                is_premium=tmpl_data["is_premium"],
            )
            db.add(template)
            created += 1

        await db.commit()
        print(f"\nCreated {created} templates")

        # Verify
        result = await db.execute(select(ContractTemplate))
        all_templates = result.scalars().all()
        print(f"Total templates in DB: {len(all_templates)}")
        for t in all_templates:
            print(f"  - {t.name} ({t.category}) {'[PREMIUM]' if t.is_premium else '[FREE]'} paired={t.paired_playbook_id}")


if __name__ == "__main__":
    asyncio.run(seed_templates())
