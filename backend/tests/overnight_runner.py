#!/usr/bin/env python3
"""
Overnight E2E Test Runner for ContraRed Unified Pipeline.

Generates 10 large (40-50 page) realistic contracts and runs them through
the unified AI pipeline. Analyzes results, measures performance, and
iterates on optimizations.

Usage:
    cd backend
    PYTHONIOENCODING=utf-8 python tests/overnight_runner.py
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

# Load .env before app imports
load_dotenv(override=True)

os.environ.setdefault("DEBUG", "true")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("overnight_results.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("overnight")

from app.services.analysis_pipeline import analysis_pipeline  # noqa: E402


# ─────────────────────────────────────────────────────────────
# CONTRACT GENERATORS — Each produces 15,000-25,000 words
# ─────────────────────────────────────────────────────────────

def _boilerplate_definitions(contract_type: str, parties: tuple) -> str:
    """Generate a comprehensive defined terms section."""
    p1, p2 = parties
    return f"""
ARTICLE 1: DEFINITIONS AND INTERPRETATION

1.1 Definitions. As used in this Agreement, the following terms shall have the meanings set forth below:

"Affiliate" means, with respect to any Person, any other Person that directly or indirectly controls, is controlled by, or is under common control with such Person. For purposes of this definition, "control" means the possession, directly or indirectly, of the power to direct or cause the direction of the management and policies of a Person, whether through ownership of voting securities, by contract, or otherwise. Without limiting the generality of the foregoing, a Person shall be deemed to control another Person if the first Person owns, directly or indirectly, more than fifty percent (50%) of the voting equity interests of the second Person.

"Agreement" means this {contract_type}, together with all exhibits, schedules, appendices, and amendments hereto, as the same may be amended, restated, supplemented, or otherwise modified from time to time in accordance with the terms hereof.

"Applicable Law" means all applicable federal, state, local, municipal, and foreign laws, statutes, regulations, ordinances, rules, orders, decrees, judgments, consent decrees, settlements, and governmental requirements enacted, promulgated, entered into, agreed upon, or imposed by any Governmental Authority, including the common law as applicable.

"Business Day" means any day that is not a Saturday, Sunday, or other day on which commercial banks in New York City are authorized or required by Applicable Law to remain closed. For the avoidance of doubt, commercial banks shall not be deemed to be authorized or required by law to remain closed due to "stay at home," "shelter-in-place," "non-essential employee," or any other similar orders or restrictions or the closure of any physical branch locations at the direction of any Governmental Authority so long as the electronic funds transfer systems of commercial banks in New York City are generally open for use by customers on such day.

"Confidential Information" means all information, whether written, oral, electronic, visual, or in any other form, that is disclosed by or on behalf of either party to the other party in connection with this Agreement, including but not limited to: (a) trade secrets, inventions, ideas, processes, formulas, source and object codes, data, programs, other works of authorship, know-how, improvements, discoveries, developments, designs, and techniques; (b) information regarding plans for research, development, new products, marketing, and selling, business plans, budgets and unpublished financial statements, licenses, prices and costs, margins, discounts, credit terms, pricing and billing policies, quoting procedures, methods of obtaining business, forecasts, future plans and potential strategies, financial projections and business strategies, operational plans, financing and capital-raising plans, activities and arrangements, internal services and operational manuals, methods of conducting business, suppliers and supplier information, and purchasing; (c) information regarding the skills and compensation of employees, contractors, and any other service providers of the disclosing party; (d) information regarding customers and potential customers of the disclosing party, including customer lists, customer referrals, and customer information; (e) third-party confidential information included with, or incorporated in, any information provided by the disclosing party to the receiving party; and (f) the terms and conditions of this Agreement. Confidential Information shall not include information that: (i) is or becomes generally available to the public other than as a result of a breach of this Agreement by the receiving party; (ii) was available to the receiving party on a non-confidential basis prior to its disclosure by the disclosing party; (iii) becomes available to the receiving party on a non-confidential basis from a source other than the disclosing party, provided that such source is not bound by a confidentiality agreement with the disclosing party; or (iv) was independently developed by the receiving party without use of or reference to the Confidential Information of the disclosing party.

"Damages" means any and all losses, damages, liabilities, deficiencies, claims, actions, judgments, settlements, interest, awards, penalties, fines, costs, or expenses of whatever kind, including reasonable attorneys' fees and the cost of enforcing any right to indemnification hereunder and the cost of pursuing any insurance providers.

"Effective Date" means the date first written above, being the date on which this Agreement is executed by the last party to sign hereof.

"Force Majeure Event" means any event beyond the reasonable control of a party, including but not limited to: acts of God, floods, fires, earthquakes, epidemics, pandemics, tsunamis, explosions, war (whether or not declared), terrorism, invasion, riot, other civil unrest, embargoes, blockades, sanctions, national or regional emergency, strikes, labor stoppages or slowdowns or other industrial disturbances, passage of laws or any action taken by a Governmental Authority, including imposing an embargo, export or import restriction, quota or other restriction or prohibition, or any complete or partial government shutdown, or national or regional shortage of adequate power or telecommunications or transportation.

"GAAP" means United States generally accepted accounting principles in effect from time to time, applied consistently throughout the periods involved.

"Governmental Authority" means any federal, state, provincial, local, municipal, foreign, or other government, any governmental, regulatory, or administrative authority, agency, department, bureau, board, commission, or official, or any quasi-governmental or private body exercising any regulatory, taxing, importing, or other governmental or quasi-governmental authority, including any court, tribunal, arbitral body, or self-regulatory organization.

"Intellectual Property" means all intellectual property and proprietary rights, including: (a) all inventions (whether patentable or unpatentable and whether or not reduced to practice), all improvements thereto, and all patents, patent applications, and patent disclosures, together with all reissues, continuations, continuations-in-part, revisions, extensions, and reexaminations thereof; (b) all trademarks, service marks, trade dress, logos, slogans, trade names, corporate names, Internet domain names, and rights in telephone numbers, together with all translations, adaptations, derivations, and combinations thereof and including all goodwill associated therewith, and all applications, registrations, and renewals in connection therewith; (c) all copyrightable works, all copyrights, and all applications, registrations, and renewals in connection therewith; (d) all mask works and all applications, registrations, and renewals in connection therewith; (e) all trade secrets and confidential business information; (f) all computer software; (g) all material and all databases and data collections and all rights therein; (h) all moral rights; and (i) all other intellectual property and proprietary rights.

"Material Adverse Effect" or "MAE" means any event, occurrence, fact, condition, or change that is, or would reasonably be expected to become, individually or in the aggregate, materially adverse to: (a) the business, results of operations, condition (financial or otherwise), or assets of {p1}; or (b) the ability of any party to consummate the transactions contemplated hereby on a timely basis; provided, however, that none of the following shall be deemed to constitute, and none of the following shall be taken into account in determining whether there has been, a Material Adverse Effect: (i) any adverse change, effect, event, occurrence, state of facts, or development attributable to conditions affecting the industries in which {p1} participates, the United States economy, or the financial or securities markets generally; (ii) any adverse change, effect, event, occurrence, state of facts, or development attributable to conditions resulting from an outbreak or escalation of hostilities, pandemics, the declaration by any Governmental Authority of a national emergency or war, or the occurrence of any natural disasters; and (iii) any adverse change in or effect on the business of {p1} that is cured before the earlier of the termination date and the closing date.

"Person" means any individual, partnership, firm, corporation, limited liability company, association, trust, unincorporated organization, or other entity, as well as any syndicate or group that would be deemed to be a person under Section 13(d)(3) of the Securities Exchange Act of 1934, as amended.

"Representatives" means, with respect to any Person, such Person's officers, directors, employees, managers, members, partners, agents, attorneys, accountants, advisors, and other representatives.

"Services" means the services to be provided by {p1} to {p2} pursuant to this Agreement and each Statement of Work, as more particularly described herein and therein.

"Statement of Work" or "SOW" means a statement of work, project order, task order, or similar document that references this Agreement and sets forth the specific Services to be performed, deliverables, milestones, fees, timeline, and other terms applicable to such Services.

"Territory" means the United States of America, including all fifty states, the District of Columbia, and all territories and possessions thereof, and, to the extent applicable, Canada, the United Kingdom, the European Union and its member states, and such other jurisdictions as may be specified in a Statement of Work.

1.2 Interpretation. In this Agreement, unless the context otherwise requires: (a) the singular includes the plural and vice versa; (b) reference to any gender includes all genders; (c) reference to any agreement, document, or instrument means such agreement, document, or instrument as amended or modified and in effect from time to time in accordance with the terms thereof; (d) reference to any Applicable Law means such Applicable Law as amended, modified, codified, replaced, or reenacted, in whole or in part, and in effect from time to time, including rules and regulations promulgated thereunder; (e) "hereunder," "hereof," "hereto," and words of similar import shall be deemed references to this Agreement as a whole and not to any particular Article, Section, or other provision thereof; (f) "including" means including without limiting the generality of any description preceding or succeeding such term and for purposes of this Agreement the word "including" shall mean "including but not limited to"; (g) references to Articles, Sections, Exhibits, and Schedules mean the Articles, Sections, Exhibits, and Schedules of this Agreement; and (h) references to "$" or "dollars" mean the lawful money of the United States.

1.3 Order of Precedence. In the event of any conflict or inconsistency among the terms and conditions of this Agreement and any exhibits, schedules, or Statements of Work attached hereto, the following order of precedence shall apply (with the first listed document having the highest priority): (a) any amendments to this Agreement; (b) this Agreement; (c) the Statements of Work (in reverse chronological order); and (d) any other exhibits or schedules.
"""


def _boilerplate_general_provisions(gov_law: str, gov_state: str, dispute_forum: str) -> str:
    """Generate standard general provisions (force majeure, notices, assignment, etc.)."""
    return f"""
ARTICLE [X]: GENERAL PROVISIONS

[X].1 Force Majeure. Neither party shall be liable for any failure or delay in performing its obligations under this Agreement (except for any payment obligations) to the extent that such failure or delay results from a Force Majeure Event, provided that the affected party: (a) promptly notifies the other party in writing of the nature and extent of the Force Majeure Event causing its failure or delay in performance; (b) uses commercially reasonable efforts to mitigate the effects of the Force Majeure Event; and (c) resumes the performance of its obligations as soon as reasonably practicable after the removal of the Force Majeure Event. Notwithstanding the foregoing, if a Force Majeure Event prevents a party from performing its material obligations under this Agreement for a period exceeding ninety (90) consecutive days, the other party may terminate this Agreement upon thirty (30) days written notice to the affected party.

[X].2 Notices. All notices, requests, consents, claims, demands, waivers, and other communications hereunder shall be in writing and shall be deemed to have been given: (a) when delivered by hand (with written confirmation of receipt); (b) when received by the addressee if sent by a nationally recognized overnight courier (receipt requested); (c) on the date sent by email (with confirmation of transmission) if sent during normal business hours of the recipient, and on the next Business Day if sent after normal business hours of the recipient; or (d) on the third day after the date mailed, by certified or registered mail, return receipt requested, postage prepaid. Such communications must be sent to the respective parties at the addresses set forth in the signature blocks below (or to such other address as may be designated by a party from time to time in accordance with this Section).

[X].3 Entire Agreement. This Agreement, including and together with any related exhibits, schedules, attachments, and appendices, constitutes the sole and entire agreement of the parties with respect to the subject matter contained herein, and supersedes all prior and contemporaneous understandings, agreements, representations, and warranties, both written and oral, regarding such subject matter. For the avoidance of doubt, nothing in this Section shall be deemed to terminate or modify any confidentiality agreement previously entered into by the parties (or their Affiliates) to the extent that such confidentiality agreement, by its terms, survives the execution of this Agreement.

[X].4 Amendment and Modification. No amendment to or modification of this Agreement is effective unless it is in writing and signed by an authorized representative of each party. No waiver by any party of any of the provisions hereof shall be effective unless explicitly set forth in writing and signed by the party so waiving. Except as otherwise set forth in this Agreement, no failure to exercise, or delay in exercising, any right, remedy, power, or privilege arising from this Agreement shall operate or be construed as a waiver thereof; nor shall any single or partial exercise of any right, remedy, power, or privilege hereunder preclude any other or further exercise thereof or the exercise of any other right, remedy, power, or privilege.

[X].5 Severability. If any term or provision of this Agreement is invalid, illegal, or unenforceable in any jurisdiction, such invalidity, illegality, or unenforceability shall not affect any other term or provision of this Agreement or invalidate or render unenforceable such term or provision in any other jurisdiction. Upon a determination that any term or provision is invalid, illegal, or unenforceable, the parties hereto shall negotiate in good faith to modify this Agreement to effect the original intent of the parties as closely as possible in a mutually acceptable manner in order that the transactions contemplated hereby are consummated as originally contemplated to the greatest extent possible.

[X].6 Governing Law. This Agreement shall be governed by and construed in accordance with the internal laws of the State of {gov_state} without giving effect to any choice or conflict of law provision or rule (whether of the State of {gov_state} or any other jurisdiction) that would cause the application of the laws of any jurisdiction other than those of the State of {gov_state}.

[X].7 Dispute Resolution. Any dispute, controversy, or claim arising out of or relating to this Agreement, including the breach, termination, or validity thereof, shall be {dispute_forum}. Each party irrevocably and unconditionally consents to the personal jurisdiction of such courts and agrees that process may be served in any manner permitted by Applicable Law.

[X].8 Assignment. Neither party may assign or transfer this Agreement or any of its rights or obligations hereunder, in whole or in part, without the prior written consent of the other party, which consent shall not be unreasonably withheld, conditioned, or delayed. Any purported assignment or transfer without such consent shall be null and void. Notwithstanding the foregoing, either party may assign this Agreement, in whole or in part, without the consent of the other party, to an Affiliate or in connection with a merger, acquisition, corporate reorganization, or sale of all or substantially all of the assigning party's assets. This Agreement is binding upon and shall inure to the benefit of the parties hereto and their respective permitted successors and assigns.

[X].9 No Third-Party Beneficiaries. This Agreement is for the sole benefit of the parties hereto and their respective successors and permitted assigns and nothing herein, express or implied, is intended to or shall confer upon any other Person any legal or equitable right, benefit, or remedy of any nature whatsoever under or by reason of this Agreement.

[X].10 Counterparts. This Agreement may be executed in counterparts, each of which shall be deemed an original, but all of which together shall be deemed to be one and the same agreement. A signed copy of this Agreement delivered by email or other means of electronic transmission shall be deemed to have the same legal effect as delivery of an original signed copy of this Agreement.

[X].11 Headings. The headings in this Agreement are for reference only and shall not affect the interpretation of this Agreement.

[X].12 Relationship of the Parties. The relationship between the parties is that of independent contractors. Nothing contained in this Agreement shall be construed as creating any agency, partnership, joint venture, or other form of joint enterprise, employment, or fiduciary relationship between the parties, and neither party shall have authority to contract for or bind the other party in any manner whatsoever.

[X].13 Waiver of Jury Trial. EACH PARTY HEREBY IRREVOCABLY AND UNCONDITIONALLY WAIVES, TO THE FULLEST EXTENT PERMITTED BY APPLICABLE LAW, ANY RIGHT IT MAY HAVE TO A TRIAL BY JURY IN RESPECT OF ANY ACTION, SUIT, OR PROCEEDING ARISING OUT OF OR RELATING TO THIS AGREEMENT OR THE TRANSACTIONS CONTEMPLATED HEREBY.

[X].14 Cumulative Remedies. The rights and remedies under this Agreement are cumulative and are in addition to and not in substitution for any other rights and remedies available at law or in equity or otherwise.

[X].15 Survival. The provisions of this Agreement that by their nature should survive termination or expiration of this Agreement, including but not limited to provisions relating to confidentiality, intellectual property, indemnification, limitation of liability, and dispute resolution, shall survive any termination or expiration of this Agreement.

[X].16 Export Compliance. Each party shall comply with all applicable United States export control laws and regulations, including the Export Administration Regulations maintained by the United States Department of Commerce, trade and economic sanctions maintained by the Office of Foreign Assets Control of the United States Department of the Treasury, and the International Traffic in Arms Regulations maintained by the United States Department of State. Neither party shall, directly or indirectly, export, re-export, or release any technology, software, or software source code to any country, entity, or person to which such export, re-export, or release is prohibited by Applicable Law.

[X].17 Anti-Corruption. Each party represents and warrants that it has not, and covenants that it will not, in connection with the transactions contemplated by this Agreement, directly or indirectly, make, offer, agree to offer, or authorize any payment, gift, or transfer of anything of value for the purpose of influencing any act or decision of any government official, or inducing any government official to do or omit to do any act in violation of the official's lawful duty, in each case in violation of the U.S. Foreign Corrupt Practices Act or any other anti-corruption law applicable to the transactions contemplated by this Agreement.

[X].18 Insurance. Each party shall maintain, at its own expense, adequate insurance coverage with financially sound and reputable insurers to cover its obligations and liabilities under this Agreement, including commercial general liability insurance, professional liability (errors and omissions) insurance, workers' compensation insurance, and cyber liability insurance, each with coverage limits that are commercially reasonable for businesses of similar size and nature.
"""


def _generate_saas_agreement() -> str:
    """Generate a 40-50 page Enterprise SaaS Agreement."""
    defs = _boilerplate_definitions("Enterprise SaaS Subscription Agreement", ("Vendor", "Customer"))
    general = _boilerplate_general_provisions("Delaware", "Delaware", "resolved exclusively in the federal and state courts located in Wilmington, Delaware")

    core = """
ENTERPRISE SAAS SUBSCRIPTION AGREEMENT

This Enterprise SaaS Subscription Agreement (this "Agreement") is entered into as of [DATE] (the "Effective Date"), by and between CloudMatrix Technologies, Inc., a Delaware corporation, with its principal place of business at 200 Park Avenue South, Suite 1200, New York, NY 10003 ("Vendor"), and Apex Enterprise Solutions, Inc., a Delaware corporation, with its principal place of business at 500 Technology Drive, Suite 400, San Jose, CA 95110 ("Customer"). Vendor and Customer are sometimes referred to herein individually as a "Party" and collectively as the "Parties."

RECITALS

WHEREAS, Vendor has developed and operates a proprietary cloud-based enterprise resource planning and data analytics platform known as "CloudMatrix Enterprise Platform" (the "Platform"), which provides comprehensive business intelligence, data warehousing, automated reporting, machine learning-driven analytics, and enterprise workflow management capabilities;

WHEREAS, Customer desires to subscribe to and use the Platform for its internal business operations, and Vendor desires to provide Customer with access to the Platform, subject to the terms and conditions set forth herein;

WHEREAS, the Parties desire to set forth the terms and conditions under which Vendor will provide the Platform and related services to Customer, including service level commitments, data processing obligations, intellectual property ownership, and the respective rights and obligations of the Parties;

WHEREAS, Customer has conducted due diligence on the Platform and Vendor's business practices and has determined that the Platform meets Customer's requirements for enterprise resource planning and data analytics, subject to the specific customizations and configurations set forth in the applicable Statements of Work;

NOW, THEREFORE, in consideration of the mutual covenants, terms, and conditions set forth herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:

""" + defs + """

ARTICLE 2: SUBSCRIPTION AND ACCESS

2.1 Subscription Grant. Subject to the terms and conditions of this Agreement, Vendor hereby grants to Customer, during the Subscription Term, a non-exclusive, non-transferable (except as expressly permitted herein), non-sublicensable right to access and use the Platform solely for Customer's internal business purposes and in accordance with the terms and conditions of this Agreement, the applicable Subscription Plan, and the Documentation. The subscription granted hereunder includes access for up to the number of Authorized Users specified in the applicable Order Form.

2.2 Authorized Users. Customer may permit its employees, contractors, and agents ("Authorized Users") to access and use the Platform, provided that: (a) the number of Authorized Users does not exceed the number specified in the applicable Order Form; (b) each Authorized User has a unique user account and login credentials; (c) Customer does not permit any Authorized User to share login credentials with any other person; (d) Customer is responsible for all activities that occur under its Authorized Users' accounts; and (e) Customer shall ensure that all Authorized Users comply with the terms and conditions of this Agreement and the Acceptable Use Policy. Customer shall promptly notify Vendor of any unauthorized use of any Authorized User's account or any other breach of security of which Customer becomes aware.

2.3 Restrictions. Customer shall not, and shall not permit any Authorized User or third party to: (a) copy, modify, or create derivative works of the Platform or any component thereof; (b) rent, lease, lend, sell, sublicense, assign, distribute, publish, transfer, or otherwise make the Platform available to any third party; (c) reverse engineer, disassemble, decompile, decode, adapt, or otherwise attempt to derive or gain access to the source code of the Platform, in whole or in part; (d) bypass or breach any security device or protection used by the Platform or access or use the Platform other than by an Authorized User through the use of valid access credentials; (e) input, upload, transmit, or otherwise provide to or through the Platform any information or materials that are unlawful or injurious, or that contain, transmit, or activate any harmful code; (f) damage, destroy, disrupt, disable, impair, interfere with, or otherwise impede or harm in any manner the Platform or Vendor's provision of services to any third party, in whole or in part; (g) remove, delete, alter, or obscure any trademarks, Documentation, warranties, or disclaimers, or any copyright, trademark, patent, or other intellectual property or proprietary rights notices from any Platform or any copy thereof; (h) access or use the Platform in any manner or for any purpose that infringes, misappropriates, or otherwise violates any Intellectual Property or other right of any third party, or that violates any Applicable Law; (i) access or use the Platform for purposes of competitive analysis, the development, provision, or use of a competing software service or product, or any other purpose that is to Vendor's detriment or commercial disadvantage; or (j) otherwise access or use the Platform beyond the scope of the authorization granted under this Agreement.

2.4 Suspension. Vendor may suspend Customer's or any Authorized User's access to the Platform, in whole or in part, without liability, if Vendor reasonably determines that: (a) there is a threat or attack on the Platform; (b) Customer's or any Authorized User's use of the Platform disrupts or poses a security risk to the Platform or to any other customer or vendor of Vendor; (c) Customer or any Authorized User is using the Platform for fraudulent or illegal activities; (d) Customer has ceased to continue its business in the ordinary course, made an assignment for the benefit of creditors or similar disposition of its assets, or become the subject of any bankruptcy, reorganization, liquidation, dissolution, or similar proceeding; (e) Vendor's provision of the Platform to Customer or any Authorized User is prohibited by Applicable Law; or (f) Customer is in material breach of this Agreement, including any failure to make payment when due. Vendor shall use commercially reasonable efforts to provide written notice of any such suspension to Customer and to provide updates regarding resumption of access to the Platform following any such suspension.

2.5 Platform Modifications. Vendor may, in its sole discretion, make any changes to the Platform that it deems necessary or useful to: (a) maintain or enhance the quality or delivery of the Platform; (b) comply with Applicable Law; or (c) reflect changes in technology or the market. Vendor shall not materially reduce the overall functionality of the Platform during the Subscription Term. Notwithstanding the foregoing, Vendor reserves the right to discontinue any feature or functionality of the Platform at any time upon ninety (90) days prior written notice to Customer. IN THE EVENT THAT VENDOR DISCONTINUES A MATERIAL FEATURE THAT WAS A PRIMARY BASIS FOR CUSTOMER'S SUBSCRIPTION, CUSTOMER'S SOLE REMEDY SHALL BE TO TERMINATE THIS AGREEMENT WITH A PRO-RATA REFUND OF PREPAID FEES.

ARTICLE 3: FEES AND PAYMENT

3.1 Subscription Fees. Customer shall pay the subscription fees ("Subscription Fees") as set forth in the applicable Order Form. Unless otherwise specified in an Order Form, all Subscription Fees are stated in United States dollars and are non-refundable and non-cancellable. Subscription Fees are exclusive of all taxes, levies, or duties imposed by taxing authorities, and Customer shall be responsible for payment of all such taxes, levies, or duties (excluding taxes based solely on Vendor's income).

3.2 Payment Terms. Unless otherwise specified in an Order Form, Vendor shall invoice Customer annually in advance for the Subscription Fees, and Customer shall pay each invoice within thirty (30) days after the date of such invoice. If Customer fails to make any payment when due, without limiting Vendor's other rights and remedies: (a) Vendor may charge interest on the past due amount at the rate of one and one-half percent (1.5%) per month (or the highest rate permitted by Applicable Law, whichever is lower), calculated daily and compounded monthly; (b) Customer shall reimburse Vendor for all reasonable costs incurred by Vendor in collecting any late payments or interest, including attorneys' fees, court costs, and collection agency fees; and (c) if such failure continues for ten (10) days following written notice thereof, Vendor may suspend Customer's and its Authorized Users' access to the Platform until such amounts are paid in full.

3.3 Price Increases. VENDOR RESERVES THE RIGHT TO INCREASE SUBSCRIPTION FEES AT ANY TIME UPON SIXTY (60) DAYS WRITTEN NOTICE TO CUSTOMER. FOR AUTO-RENEWAL PERIODS, SUBSCRIPTION FEES SHALL AUTOMATICALLY INCREASE BY THE GREATER OF: (A) FIFTEEN PERCENT (15%) OF THE THEN-CURRENT SUBSCRIPTION FEES; OR (B) THE PERCENTAGE INCREASE IN THE CONSUMER PRICE INDEX FOR ALL URBAN CONSUMERS (CPI-U) AS PUBLISHED BY THE U.S. BUREAU OF LABOR STATISTICS FOR THE TWELVE-MONTH PERIOD ENDING PRIOR TO THE RENEWAL DATE. CUSTOMER'S CONTINUED USE OF THE PLATFORM FOLLOWING ANY SUCH INCREASE SHALL CONSTITUTE ACCEPTANCE OF THE INCREASED FEES.

3.4 Usage-Based Fees. In addition to the Subscription Fees, Customer shall pay usage-based fees ("Usage Fees") for any usage of the Platform that exceeds the usage limits specified in the applicable Order Form. Vendor shall calculate Usage Fees on a monthly basis and shall invoice Customer for such fees in arrears. Customer shall pay each Usage Fee invoice within fifteen (15) days after the date of such invoice. Vendor's measurement of Customer's use of the Platform shall be binding unless Customer demonstrates manifest error in writing within thirty (30) days of receiving an invoice.

3.5 True-Up. Vendor may conduct quarterly true-up assessments to determine whether Customer's actual usage exceeds the subscribed usage limits. If Customer's usage exceeds the subscribed limits during any quarter, Vendor shall invoice Customer for the excess usage at the then-current list price (without any discounts previously applied) for the applicable usage metric, retroactive to the beginning of the quarter in which the excess usage first occurred.

ARTICLE 4: DATA RIGHTS AND PROCESSING

4.1 Customer Data Ownership. As between Customer and Vendor, Customer retains all right, title, and interest in and to any data, information, or materials submitted, uploaded, or transmitted by or on behalf of Customer through the Platform ("Customer Data"), including all Intellectual Property therein. Customer is solely responsible for the accuracy, quality, and legality of Customer Data and the means by which Customer acquired Customer Data.

4.2 License to Customer Data. CUSTOMER HEREBY GRANTS VENDOR A PERPETUAL, IRREVOCABLE, WORLDWIDE, ROYALTY-FREE, FULLY PAID-UP, NON-EXCLUSIVE LICENSE TO USE, COPY, MODIFY, CREATE DERIVATIVE WORKS FROM, DISTRIBUTE, PUBLICLY DISPLAY, PUBLICLY PERFORM, AND SUBLICENSE CUSTOMER DATA IN AGGREGATED, ANONYMIZED, OR DE-IDENTIFIED FORM FOR ANY PURPOSE, INCLUDING BUT NOT LIMITED TO: (A) PRODUCT IMPROVEMENT AND DEVELOPMENT; (B) BENCHMARKING AND ANALYTICS; (C) MARKETING, ADVERTISING, AND PROMOTIONAL MATERIALS; (D) TRAINING OF MACHINE LEARNING MODELS AND ARTIFICIAL INTELLIGENCE SYSTEMS; AND (E) SALE OR LICENSING TO THIRD PARTIES AS PART OF AGGREGATED DATA PRODUCTS. VENDOR SHALL USE COMMERCIALLY REASONABLE EFFORTS TO ENSURE THAT SUCH AGGREGATED, ANONYMIZED, OR DE-IDENTIFIED DATA DOES NOT IDENTIFY CUSTOMER OR ANY INDIVIDUAL. NOTWITHSTANDING THE FOREGOING, VENDOR ACKNOWLEDGES THAT THE RISK OF RE-IDENTIFICATION CANNOT BE ENTIRELY ELIMINATED AND SHALL NOT BE LIABLE FOR ANY RE-IDENTIFICATION THAT OCCURS DESPITE THE USE OF COMMERCIALLY REASONABLE DE-IDENTIFICATION TECHNIQUES.

4.3 Data Processing. Vendor shall process Customer Data solely for the purposes of providing the Platform and related services to Customer, except as otherwise expressly permitted under Section 4.2 above. Vendor shall implement and maintain appropriate technical and organizational measures to protect Customer Data against unauthorized or unlawful processing and against accidental loss, destruction, damage, theft, or disclosure. Vendor's data processing obligations are further set forth in the Data Processing Addendum attached hereto as Exhibit B.

4.4 Data Location. VENDOR MAY PROCESS AND STORE CUSTOMER DATA IN ANY JURISDICTION WHERE VENDOR OR ITS SUB-PROCESSORS MAINTAIN DATA PROCESSING FACILITIES, INCLUDING BUT NOT LIMITED TO THE UNITED STATES, THE EUROPEAN UNION, INDIA, SINGAPORE, AND SUCH OTHER JURISDICTIONS AS VENDOR MAY DETERMINE FROM TIME TO TIME IN ITS SOLE DISCRETION. VENDOR SHALL NOTIFY CUSTOMER OF ANY MATERIAL CHANGE IN THE JURISDICTIONS IN WHICH CUSTOMER DATA IS PROCESSED OR STORED WITHIN SIXTY (60) DAYS OF SUCH CHANGE. CUSTOMER ACKNOWLEDGES AND AGREES THAT DIFFERENT JURISDICTIONS MAY HAVE DIFFERENT DATA PROTECTION LAWS AND THAT VENDOR MAKES NO REPRESENTATIONS OR WARRANTIES REGARDING THE ADEQUACY OF DATA PROTECTION LAWS IN ANY JURISDICTION.

4.5 Data Deletion. Upon expiration or termination of this Agreement for any reason, Vendor shall, within sixty (60) days following the effective date of such expiration or termination, delete all Customer Data in Vendor's possession or control, except to the extent that: (a) Vendor is required by Applicable Law to retain any Customer Data; (b) Customer Data is contained in backup or archival copies that are maintained in accordance with Vendor's standard data retention policies (provided that Vendor shall continue to protect such Customer Data in accordance with this Agreement until such backup or archival copies are deleted in the ordinary course); or (c) Customer Data has been aggregated, anonymized, or de-identified in accordance with Section 4.2 above, in which case Vendor shall have no obligation to delete such data.

ARTICLE 5: SERVICE LEVEL AGREEMENT

5.1 Uptime Commitment. Vendor shall use commercially reasonable efforts to make the Platform available to Customer with a monthly uptime percentage of at least ninety-nine and one-half percent (99.5%) during each calendar month during the Subscription Term ("Uptime Commitment"). Monthly uptime percentage is calculated as: ((Total Minutes in Month - Downtime Minutes) / Total Minutes in Month) x 100.

5.2 Exclusions. The Uptime Commitment shall not apply to any unavailability, suspension, or termination of the Platform that is due to: (a) scheduled maintenance (which Vendor shall endeavor to perform during off-peak hours and shall notify Customer of at least twenty-four (24) hours in advance); (b) Force Majeure Events; (c) failures or malfunctions of Customer's or its Authorized Users' equipment, software, network connections, or other infrastructure; (d) Customer's or its Authorized Users' breach of this Agreement or misuse of the Platform; (e) actions taken by Vendor at Customer's request; (f) internet service provider failures or delays; (g) denial of service attacks or other cyberattacks; or (h) any other cause beyond Vendor's reasonable control.

5.3 Service Credits. IF VENDOR FAILS TO MEET THE UPTIME COMMITMENT IN ANY GIVEN CALENDAR MONTH, CUSTOMER'S SOLE AND EXCLUSIVE REMEDY SHALL BE TO RECEIVE A SERVICE CREDIT EQUAL TO THE APPLICABLE PERCENTAGE OF THE MONTHLY SUBSCRIPTION FEE SET FORTH BELOW, APPLIED TO THE NEXT INVOICE: (A) 99.0% TO 99.4% UPTIME: 5% SERVICE CREDIT; (B) 95.0% TO 98.9% UPTIME: 10% SERVICE CREDIT; (C) BELOW 95.0% UPTIME: 15% SERVICE CREDIT. IN NO EVENT SHALL THE TOTAL SERVICE CREDITS ISSUED TO CUSTOMER IN ANY CALENDAR MONTH EXCEED FIFTEEN PERCENT (15%) OF THE MONTHLY SUBSCRIPTION FEE FOR SUCH MONTH. SERVICE CREDITS ARE CUSTOMER'S SOLE AND EXCLUSIVE REMEDY FOR ANY FAILURE BY VENDOR TO MEET THE UPTIME COMMITMENT.

5.4 Support. Vendor shall provide Customer with technical support in accordance with the Support Plan specified in the applicable Order Form. Standard support includes email support during Vendor's business hours (9:00 AM to 5:00 PM Eastern Time, Monday through Friday, excluding holidays). Premium support (available for an additional fee) includes 24x7 phone and email support with guaranteed response times.

ARTICLE 6: INTELLECTUAL PROPERTY

6.1 Vendor IP. Customer acknowledges and agrees that, as between Customer and Vendor, Vendor owns all right, title, and interest in and to the Platform, the Documentation, and all improvements, enhancements, modifications, derivative works, and other changes thereto (collectively, "Vendor IP"), including all Intellectual Property therein, regardless of whether such improvements, enhancements, modifications, derivative works, or changes were: (a) developed by Vendor independently; (b) developed at Customer's request or based on Customer's feedback, suggestions, enhancement requests, or recommendations; or (c) developed jointly by Vendor and Customer. CUSTOMER HEREBY IRREVOCABLY ASSIGNS TO VENDOR ALL RIGHT, TITLE, AND INTEREST IN AND TO ANY INTELLECTUAL PROPERTY THAT CUSTOMER MAY HAVE OR ACQUIRE IN ANY IMPROVEMENTS, ENHANCEMENTS, MODIFICATIONS, DERIVATIVE WORKS, OR CHANGES TO THE PLATFORM OR VENDOR IP, WHETHER CONCEIVED, CREATED, OR DEVELOPED BY CUSTOMER ALONE OR JOINTLY WITH VENDOR.

6.2 Feedback. If Customer or any Authorized User provides Vendor with any suggestions, enhancement requests, recommendations, corrections, or other feedback regarding the Platform or any Vendor IP ("Feedback"), Customer hereby grants to Vendor a perpetual, irrevocable, worldwide, royalty-free, fully paid-up, non-exclusive license to use, copy, modify, create derivative works from, distribute, publicly display, publicly perform, and sublicense such Feedback for any purpose without any obligation, compensation, or attribution to Customer. Vendor shall be free to use Feedback for any purpose, including to improve the Platform and to develop new products and services.

6.3 Customer Configurations. VENDOR SHALL OWN ALL RIGHT, TITLE, AND INTEREST IN AND TO ANY CONFIGURATIONS, CUSTOMIZATIONS, WORKFLOWS, TEMPLATES, DASHBOARDS, REPORTS, QUERIES, INTEGRATIONS, OR OTHER ITEMS CREATED BY CUSTOMER OR ITS AUTHORIZED USERS WITHIN OR USING THE PLATFORM ("CUSTOMER CONFIGURATIONS"). CUSTOMER RECEIVES A NON-EXCLUSIVE, NON-TRANSFERABLE LICENSE TO USE CUSTOMER CONFIGURATIONS SOLELY IN CONNECTION WITH ITS AUTHORIZED USE OF THE PLATFORM DURING THE SUBSCRIPTION TERM. UPON TERMINATION OR EXPIRATION OF THIS AGREEMENT, ALL LICENSES TO USE CUSTOMER CONFIGURATIONS SHALL TERMINATE AND CUSTOMER SHALL HAVE NO FURTHER RIGHT TO ACCESS OR USE ANY CUSTOMER CONFIGURATIONS.

ARTICLE 7: WARRANTIES AND DISCLAIMERS

7.1 Mutual Representations and Warranties. Each Party represents and warrants to the other Party that: (a) it is duly organized, validly existing, and in good standing under the laws of the jurisdiction of its incorporation or organization; (b) it has the full right, power, and authority to enter into this Agreement and to perform its obligations hereunder; (c) the execution of this Agreement by its representative whose signature is set forth at the end of this Agreement has been duly authorized by all necessary corporate or organizational action of such Party; and (d) when executed and delivered by both Parties, this Agreement will constitute the legal, valid, and binding obligation of such Party, enforceable against such Party in accordance with its terms.

7.2 Vendor Performance Warranty. Vendor warrants that during the Subscription Term, the Platform will perform materially in accordance with the Documentation. If the Platform fails to perform materially in accordance with the Documentation, Customer's sole and exclusive remedy shall be for Vendor to use commercially reasonable efforts to correct such non-conformance within a reasonable time after receiving written notice from Customer describing the non-conformance in reasonable detail. If Vendor is unable to correct such non-conformance within sixty (60) days after receiving such notice, either Party may terminate this Agreement, and Vendor shall refund to Customer any prepaid Subscription Fees for the remainder of the then-current Subscription Term.

7.3 DISCLAIMER. EXCEPT FOR THE EXPRESS WARRANTIES SET FORTH IN SECTIONS 7.1 AND 7.2, THE PLATFORM AND ALL RELATED SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE." VENDOR HEREBY DISCLAIMS ALL WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT, AND ALL WARRANTIES ARISING FROM COURSE OF DEALING, USAGE, OR TRADE PRACTICE. VENDOR MAKES NO WARRANTY OF ANY KIND THAT THE PLATFORM, OR ANY PRODUCTS OR RESULTS OF THE USE THEREOF, WILL MEET CUSTOMER'S OR ANY OTHER PERSON'S REQUIREMENTS, OPERATE WITHOUT INTERRUPTION, ACHIEVE ANY INTENDED RESULT, BE COMPATIBLE OR WORK WITH ANY SOFTWARE, SYSTEM, OR OTHER SERVICES, OR BE SECURE, ACCURATE, COMPLETE, FREE OF HARMFUL CODE, OR ERROR FREE. WITHOUT LIMITING THE FOREGOING, VENDOR MAKES NO REPRESENTATION OR WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, REGARDING THE ACCURACY, RELIABILITY, OR COMPLETENESS OF ANY DATA, INFORMATION, OR CONTENT GENERATED BY OR THROUGH THE PLATFORM, INCLUDING ANY CONTENT GENERATED BY ARTIFICIAL INTELLIGENCE OR MACHINE LEARNING FEATURES OF THE PLATFORM.

ARTICLE 8: INDEMNIFICATION

8.1 Vendor Indemnification. Vendor shall indemnify, defend, and hold harmless Customer and its officers, directors, employees, agents, successors, and assigns from and against any and all Damages arising out of or relating to any third-party claim that Customer's use of the Platform in accordance with this Agreement infringes or misappropriates any United States patent, copyright, trade secret, or other Intellectual Property right of such third party. The foregoing obligation shall not apply to any claim arising out of or relating to: (a) Customer's use of the Platform in combination with any software, hardware, data, or technology not provided or authorized by Vendor; (b) modifications to the Platform not made by or on behalf of Vendor; (c) Customer's use of the Platform other than in accordance with this Agreement and the Documentation; or (d) Customer's use of any release of the Platform other than the most current release made available by Vendor.

8.2 Customer Indemnification. Customer shall indemnify, defend, and hold harmless Vendor and its officers, directors, employees, agents, successors, and assigns from and against any and all Damages arising out of or relating to any third-party claim based on: (a) Customer Data or Customer's use of the Platform, including any claim that Customer Data or Customer's use of the Platform infringes or misappropriates any third-party Intellectual Property or other right; (b) Customer's breach of this Agreement; or (c) Customer's violation of Applicable Law.

8.3 Indemnification Procedure. The indemnified party shall: (a) promptly notify the indemnifying party in writing of any claim for which it seeks indemnification; (b) give the indemnifying party sole control of the defense and settlement of such claim (provided that the indemnifying party shall not settle any claim without the indemnified party's prior written consent, which consent shall not be unreasonably withheld); and (c) provide the indemnifying party, at the indemnifying party's expense, with all reasonable assistance in connection with the defense and settlement of such claim. The indemnified party's failure to promptly notify the indemnifying party shall not relieve the indemnifying party of its obligations under this Section, except to the extent that the indemnifying party is materially prejudiced by such failure.

ARTICLE 9: LIMITATION OF LIABILITY

9.1 EXCLUSION OF DAMAGES. EXCEPT FOR A PARTY'S OBLIGATIONS UNDER ARTICLE 8 (INDEMNIFICATION) OR A PARTY'S BREACH OF ARTICLE 10 (CONFIDENTIALITY), IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER PARTY OR TO ANY THIRD PARTY FOR ANY LOSS OF USE, REVENUE, OR PROFIT, OR FOR ANY CONSEQUENTIAL, INCIDENTAL, INDIRECT, EXEMPLARY, SPECIAL, OR PUNITIVE DAMAGES WHETHER ARISING OUT OF BREACH OF CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, REGARDLESS OF WHETHER SUCH DAMAGE WAS FORESEEABLE AND WHETHER OR NOT SUCH PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

9.2 CAP ON LIABILITY. EXCEPT FOR A PARTY'S OBLIGATIONS UNDER ARTICLE 8 (INDEMNIFICATION) OR A PARTY'S BREACH OF ARTICLE 10 (CONFIDENTIALITY), IN NO EVENT SHALL EITHER PARTY'S AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT, WHETHER ARISING OUT OF OR RELATED TO BREACH OF CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, EXCEED THE TOTAL AMOUNTS PAID OR PAYABLE BY CUSTOMER TO VENDOR UNDER THIS AGREEMENT IN THE THREE (3) MONTH PERIOD IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO THE CLAIM. NOTWITHSTANDING THE FOREGOING, VENDOR'S LIABILITY FOR DATA BREACHES SHALL BE LIMITED TO ONE HUNDRED THOUSAND DOLLARS ($100,000) REGARDLESS OF THE NATURE OR SCOPE OF SUCH DATA BREACH.

9.3 ESSENTIAL BASIS. THE PARTIES ACKNOWLEDGE AND AGREE THAT THE LIMITATIONS SET FORTH IN THIS ARTICLE 9 ARE AN ESSENTIAL BASIS OF THE BARGAIN AND THAT THE PARTIES WOULD NOT HAVE ENTERED INTO THIS AGREEMENT WITHOUT SUCH LIMITATIONS.

ARTICLE 10: CONFIDENTIALITY

10.1 Obligations. Each Party agrees that it shall: (a) protect the other Party's Confidential Information using the same degree of care that it uses to protect its own Confidential Information of like nature, but in no event less than a reasonable degree of care; (b) not use the other Party's Confidential Information for any purpose outside the scope of this Agreement; (c) not disclose the other Party's Confidential Information to any third party except to its Representatives who have a need to know such information for purposes consistent with this Agreement, provided that such Representatives are bound by written confidentiality obligations at least as protective as those set forth herein; and (d) be responsible for any breach of this Section 10 by its Representatives.

10.2 Compelled Disclosure. If either Party is compelled by Applicable Law to disclose any Confidential Information of the other Party, such Party shall: (a) provide the other Party with prior written notice of such compelled disclosure (to the extent legally permitted); (b) provide reasonable assistance to the other Party in opposing or limiting such disclosure; and (c) limit the disclosure to the minimum extent necessary to comply with Applicable Law.

10.3 Survival. The obligations of confidentiality set forth in this Article 10 shall survive the expiration or termination of this Agreement for a period of five (5) years from the date of disclosure of the applicable Confidential Information, except with respect to trade secrets, which shall be protected for so long as they remain trade secrets under Applicable Law.

ARTICLE 11: TERM AND TERMINATION

11.1 Initial Term. This Agreement shall commence on the Effective Date and shall continue for an initial term of thirty-six (36) months (the "Initial Term"), unless earlier terminated in accordance with this Article 11.

11.2 Renewal. UPON EXPIRATION OF THE INITIAL TERM, THIS AGREEMENT SHALL AUTOMATICALLY RENEW FOR SUCCESSIVE TWELVE (12) MONTH PERIODS (EACH, A "RENEWAL TERM") UNLESS EITHER PARTY PROVIDES THE OTHER PARTY WITH WRITTEN NOTICE OF NON-RENEWAL AT LEAST ONE HUNDRED TWENTY (120) DAYS PRIOR TO THE EXPIRATION OF THE THEN-CURRENT TERM. CUSTOMER ACKNOWLEDGES THAT FAILURE TO PROVIDE TIMELY NOTICE OF NON-RENEWAL SHALL RESULT IN AUTOMATIC RENEWAL AT THE THEN-CURRENT SUBSCRIPTION FEES, AS ADJUSTED PURSUANT TO SECTION 3.3 ABOVE. THE INITIAL TERM AND ALL RENEWAL TERMS ARE COLLECTIVELY REFERRED TO AS THE "SUBSCRIPTION TERM."

11.3 Termination for Cause. Either Party may terminate this Agreement upon written notice to the other Party if: (a) the other Party materially breaches this Agreement and fails to cure such breach within thirty (30) days after receiving written notice thereof; or (b) the other Party becomes insolvent, files a petition for bankruptcy, or commences or has commenced against it proceedings relating to bankruptcy, receivership, reorganization, or assignment for the benefit of creditors.

11.4 Termination for Convenience by Vendor. VENDOR MAY TERMINATE THIS AGREEMENT AT ANY TIME FOR ANY REASON UPON NINETY (90) DAYS PRIOR WRITTEN NOTICE TO CUSTOMER. IN THE EVENT OF SUCH TERMINATION, VENDOR SHALL REFUND TO CUSTOMER A PRO-RATA PORTION OF ANY PREPAID SUBSCRIPTION FEES FOR THE REMAINDER OF THE THEN-CURRENT TERM.

11.5 Effect of Termination. Upon expiration or termination of this Agreement: (a) all rights and licenses granted to Customer hereunder shall immediately terminate; (b) Customer shall immediately cease all use of the Platform and return or destroy all copies of the Documentation and any other Vendor Confidential Information in Customer's possession or control; (c) Vendor shall make Customer Data available for export for a period of thirty (30) days following the effective date of termination, subject to payment of Vendor's then-current data export fees; and (d) after such thirty (30) day period, Vendor shall delete all Customer Data in accordance with Section 4.5 above.

11.6 Survival. Expiration or termination of this Agreement shall not affect any rights, obligations, or liabilities of either Party that accrued prior to such expiration or termination or that, by their nature, should survive such expiration or termination, including Sections 1, 3 (with respect to any outstanding payment obligations), 4.2, 4.5, 6, 7.3, 8, 9, 10, and 11.5.

ARTICLE 12: CHANGES TO TERMS

12.1 VENDOR RESERVES THE RIGHT TO MODIFY THESE TERMS AND CONDITIONS, INCLUDING THE ACCEPTABLE USE POLICY, PRIVACY POLICY, AND DATA PROCESSING ADDENDUM, AT ANY TIME BY POSTING UPDATED TERMS ON ITS WEBSITE OR BY PROVIDING NOTICE TO CUSTOMER VIA EMAIL OR THROUGH THE PLATFORM. CUSTOMER'S CONTINUED USE OF THE PLATFORM FOLLOWING THE POSTING OR NOTIFICATION OF ANY SUCH CHANGES SHALL CONSTITUTE CUSTOMER'S BINDING ACCEPTANCE OF SUCH CHANGES. IF CUSTOMER DOES NOT AGREE TO ANY SUCH CHANGES, CUSTOMER'S SOLE REMEDY IS TO TERMINATE THIS AGREEMENT IN ACCORDANCE WITH SECTION 11.3, PROVIDED THAT CUSTOMER PROVIDES WRITTEN NOTICE OF TERMINATION WITHIN THIRTY (30) DAYS AFTER THE DATE OF SUCH CHANGES.

""" + general + """

EXHIBIT A: ORDER FORM

[To be completed at time of execution]

Platform: CloudMatrix Enterprise Platform
Subscription Plan: Enterprise
Number of Authorized Users: 500
Initial Term: 36 months
Annual Subscription Fee: $450,000
Usage Limits: 10TB storage, 50M API calls/month
Support Plan: Premium (24x7)

EXHIBIT B: DATA PROCESSING ADDENDUM

1. Scope. This Data Processing Addendum ("DPA") supplements the Agreement and sets forth additional terms and conditions applicable to Vendor's processing of Customer Personal Data (as defined below) in connection with the Platform.

2. Definitions. "Customer Personal Data" means any personal data (as defined under Applicable Data Protection Laws) that is processed by Vendor on behalf of Customer in connection with the Platform. "Applicable Data Protection Laws" means all applicable laws relating to the processing of personal data, including the California Consumer Privacy Act (CCPA), the General Data Protection Regulation (GDPR), and any other applicable federal, state, or foreign data protection or privacy laws.

3. Processing. Vendor shall process Customer Personal Data only: (a) in accordance with Customer's documented instructions (which are deemed to include the terms of this Agreement); (b) to the extent necessary to provide the Platform and related services to Customer; and (c) in compliance with Applicable Data Protection Laws. Vendor shall not sell Customer Personal Data or use Customer Personal Data for any purpose other than as set forth in this DPA, except as expressly permitted under Section 4.2 of the Agreement with respect to aggregated, anonymized, or de-identified data.

4. Sub-Processors. VENDOR MAY ENGAGE SUB-PROCESSORS TO PROCESS CUSTOMER PERSONAL DATA WITHOUT CUSTOMER'S PRIOR CONSENT, PROVIDED THAT VENDOR: (A) MAINTAINS A LIST OF SUB-PROCESSORS ON ITS WEBSITE; AND (B) UPDATES SUCH LIST AT LEAST THIRTY (30) DAYS PRIOR TO ENGAGING ANY NEW SUB-PROCESSOR. CUSTOMER MAY OBJECT TO A NEW SUB-PROCESSOR BY PROVIDING WRITTEN NOTICE TO VENDOR WITHIN FIFTEEN (15) DAYS AFTER VENDOR UPDATES THE SUB-PROCESSOR LIST. IF VENDOR AND CUSTOMER CANNOT RESOLVE CUSTOMER'S OBJECTION WITHIN THIRTY (30) DAYS, CUSTOMER'S SOLE REMEDY SHALL BE TO TERMINATE THE APPLICABLE STATEMENT OF WORK WITH RESPECT TO THE SERVICES THAT REQUIRE THE USE OF THE OBJECTED-TO SUB-PROCESSOR.

5. Data Breach Notification. IN THE EVENT OF A SECURITY INCIDENT THAT RESULTS IN THE UNAUTHORIZED ACCESS, DISCLOSURE, OR LOSS OF CUSTOMER PERSONAL DATA ("DATA BREACH"), VENDOR SHALL NOTIFY CUSTOMER OF SUCH DATA BREACH WITHOUT UNDUE DELAY AND IN ANY EVENT WITHIN SEVENTY-TWO (72) HOURS AFTER BECOMING AWARE OF THE DATA BREACH. SUCH NOTIFICATION SHALL INCLUDE: (A) A DESCRIPTION OF THE NATURE OF THE DATA BREACH; (B) THE CATEGORIES AND APPROXIMATE NUMBER OF INDIVIDUALS AFFECTED; (C) THE LIKELY CONSEQUENCES OF THE DATA BREACH; AND (D) THE MEASURES TAKEN OR PROPOSED TO BE TAKEN TO ADDRESS THE DATA BREACH AND MITIGATE ITS EFFECTS.

6. Data Subject Rights. Vendor shall, taking into account the nature of the processing, assist Customer by appropriate technical and organizational measures, insofar as this is possible, in fulfilling Customer's obligation to respond to requests from individuals exercising their rights under Applicable Data Protection Laws.

7. International Data Transfers. Where Customer Personal Data is transferred outside of the European Economic Area, the United Kingdom, or Switzerland to a jurisdiction that has not been deemed to provide an adequate level of data protection, such transfer shall be subject to appropriate safeguards in accordance with Applicable Data Protection Laws, including the execution of Standard Contractual Clauses as approved by the European Commission.

EXHIBIT C: ACCEPTABLE USE POLICY

1. Customer shall not use the Platform to: (a) transmit or store any content that is unlawful, harmful, threatening, abusive, harassing, defamatory, vulgar, obscene, or otherwise objectionable; (b) impersonate any person or entity; (c) transmit any viruses, worms, defects, Trojan horses, or other items of a destructive nature; (d) interfere with or disrupt the integrity or performance of the Platform or the data contained therein; (e) attempt to gain unauthorized access to the Platform or its related systems or networks; (f) engage in any activity that would violate Applicable Law; or (g) use the Platform in any manner that could damage, disable, overburden, or impair the Platform.

2. Customer acknowledges that Vendor may establish general practices and limits concerning use of the Platform, including the maximum period of time that data will be retained by the Platform and the maximum storage space that will be allotted on Vendor's servers on Customer's behalf.

3. Vendor reserves the right to remove any content that it determines, in its sole discretion, violates this Acceptable Use Policy or is otherwise objectionable, with or without notice to Customer.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

CLOUDMATRIX TECHNOLOGIES, INC.          APEX ENTERPRISE SOLUTIONS, INC.
By: _________________________           By: _________________________
Name:                                    Name:
Title:                                   Title:
Date:                                    Date:

SCHEDULE 1: FEES AND PAYMENT SCHEDULE

Year 1: $450,000 (due annually in advance)
Year 2: $517,500 (15% increase per Section 3.3)
Year 3: $595,125 (15% increase per Section 3.3)

Implementation Fee: $75,000 (one-time, due at execution)
Data Migration Fee: $25,000 (one-time, due at execution)
Training Fee: $15,000 (up to 40 hours of on-site training)
Premium Support: $50,000/year (included in Year 1 Subscription Fee)

Data Export Fee (upon termination): $500/hour, minimum 10 hours
Custom Integration Fee: Time and materials at $350/hour
Additional Authorized Users (above 500): $100/user/month

SCHEDULE 2: SERVICE LEVEL METRICS

Metric 1: Platform Availability — Target: 99.5% monthly uptime
Metric 2: API Response Time — Target: <500ms for 95th percentile
Metric 3: Data Processing — Target: <5 minutes for standard reports
Metric 4: Support Response — Critical: 1 hour, High: 4 hours, Medium: 8 hours, Low: 24 hours
Metric 5: Backup Recovery — Target: RPO 1 hour, RTO 4 hours
"""
    return core


def _generate_msa() -> str:
    """Generate a 40-50 page Master Services Agreement."""
    defs = _boilerplate_definitions("Master Services Agreement", ("Provider", "Client"))
    general = _boilerplate_general_provisions("New York", "New York", "resolved exclusively in the federal and state courts located in the Borough of Manhattan, New York City, New York")

    core = """
MASTER SERVICES AGREEMENT

This Master Services Agreement (this "Agreement") is entered into as of [DATE] (the "Effective Date"), by and between Nexus Technology Partners LLC, a New York limited liability company, with its principal place of business at 350 Fifth Avenue, Suite 5100, New York, NY 10118 ("Provider"), and GlobalBank Financial Corporation, a Delaware corporation, with its principal place of business at 383 Madison Avenue, New York, NY 10179 ("Client"). Provider and Client are sometimes referred to herein individually as a "Party" and collectively as the "Parties."

RECITALS

WHEREAS, Provider is in the business of providing information technology consulting, software development, systems integration, and related professional services;

WHEREAS, Client desires to engage Provider to perform certain services on the terms and conditions set forth herein, and Provider desires to perform such services for Client;

WHEREAS, the specific services to be performed by Provider shall be described in one or more Statements of Work to be executed by the Parties from time to time in accordance with this Agreement;

NOW, THEREFORE, in consideration of the mutual covenants, terms, and conditions set forth herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:

""" + defs + """

ARTICLE 2: SERVICES

2.1 Engagement. Client hereby engages Provider to perform the services described in each Statement of Work executed by the Parties (the "Services"), and Provider hereby accepts such engagement, subject to the terms and conditions of this Agreement.

2.2 Statements of Work. Each Statement of Work shall be in writing and signed by authorized representatives of both Parties and shall include: (a) a description of the Services to be performed; (b) the deliverables to be provided (the "Deliverables"); (c) the timeline and milestones for the performance of the Services; (d) the fees and payment terms; (e) the staffing requirements, including any key personnel; (f) any Client-provided materials, facilities, or cooperation required; and (g) any acceptance criteria for the Deliverables.

2.3 Performance Standards. Provider shall perform the Services in a professional and workmanlike manner, consistent with generally accepted industry standards and practices. Provider shall assign qualified personnel with appropriate skills, training, and experience to perform the Services.

2.4 Key Personnel. If a Statement of Work identifies any key personnel, Provider shall not remove or replace such key personnel without Client's prior written consent, which shall not be unreasonably withheld. If any key personnel becomes unavailable due to resignation, disability, death, or other circumstances beyond Provider's reasonable control, Provider shall promptly notify Client and propose a suitable replacement of equivalent or superior qualifications for Client's approval.

2.5 Subcontractors. Provider may engage subcontractors to perform any portion of the Services, provided that: (a) Provider shall remain primarily responsible for the performance of the Services; (b) each subcontractor shall be bound by obligations of confidentiality at least as protective as those set forth in this Agreement; and (c) Provider shall be liable for all acts and omissions of its subcontractors as if such acts and omissions were those of Provider.

ARTICLE 3: FEES AND PAYMENT

3.1 Fees. Client shall pay Provider the fees set forth in each Statement of Work ("Fees"). Unless otherwise specified in a Statement of Work, Fees shall be calculated on a time-and-materials basis at the rates set forth in Schedule A attached hereto.

3.2 Invoicing and Payment. Provider shall invoice Client monthly in arrears for Services performed during the preceding month. Each invoice shall include a reasonably detailed description of the Services performed, the personnel involved, the hours worked, and the expenses incurred. Client shall pay each invoice within thirty (30) days after receipt.

3.3 Late Payments. IF CLIENT FAILS TO PAY ANY INVOICE WHEN DUE, PROVIDER MAY CHARGE INTEREST ON THE OVERDUE AMOUNT AT THE RATE OF EIGHTEEN PERCENT (18%) PER ANNUM OR THE MAXIMUM RATE PERMITTED BY APPLICABLE LAW, WHICHEVER IS LOWER, CALCULATED FROM THE DATE PAYMENT WAS DUE UNTIL THE DATE OF ACTUAL PAYMENT. IN ADDITION, CLIENT SHALL REIMBURSE PROVIDER FOR ALL COSTS OF COLLECTION, INCLUDING REASONABLE ATTORNEYS' FEES.

3.4 Expenses. Client shall reimburse Provider for all reasonable and pre-approved out-of-pocket expenses incurred in connection with the performance of the Services, including travel, lodging, meals, and materials. Provider shall submit expense reports with supporting documentation, and Client shall reimburse such expenses within thirty (30) days after receipt.

ARTICLE 4: INTELLECTUAL PROPERTY

4.1 Pre-existing IP. Each Party shall retain all right, title, and interest in and to its pre-existing Intellectual Property. Neither Party grants the other Party any rights in its pre-existing Intellectual Property, except as expressly set forth in this Agreement.

4.2 Work Product Ownership. ALL WORK PRODUCT, DELIVERABLES, INVENTIONS, DEVELOPMENTS, IMPROVEMENTS, DISCOVERIES, DESIGNS, DOCUMENTATION, SOURCE CODE, OBJECT CODE, AND OTHER MATERIALS CREATED, CONCEIVED, OR DEVELOPED BY PROVIDER OR ITS PERSONNEL IN THE COURSE OF PERFORMING THE SERVICES (COLLECTIVELY, "WORK PRODUCT") SHALL BE THE SOLE AND EXCLUSIVE PROPERTY OF PROVIDER. CLIENT ACKNOWLEDGES AND AGREES THAT ALL WORK PRODUCT, INCLUDING ANY CUSTOM SOFTWARE, INTEGRATIONS, OR CONFIGURATIONS DEVELOPED SPECIFICALLY FOR CLIENT, SHALL BE OWNED EXCLUSIVELY BY PROVIDER, REGARDLESS OF WHETHER CLIENT FUNDED SUCH DEVELOPMENT.

4.3 License to Client. Provider hereby grants to Client a non-exclusive, non-transferable, non-sublicensable license to use the Work Product solely for Client's internal business purposes during the term of this Agreement. Such license shall survive termination of this Agreement with respect to Work Product delivered to Client prior to termination.

4.4 Residuals. Notwithstanding anything to the contrary in this Agreement, Provider shall be free to use and employ its general skills, knowledge, and experience, and any ideas, concepts, know-how, methodologies, and techniques that are acquired or used in the course of performing the Services. Provider shall be free to use residual knowledge retained in the unaided memory of its personnel.

ARTICLE 5: WARRANTIES

5.1 Provider Warranties. Provider warrants that: (a) it has the right and authority to enter into this Agreement and to perform its obligations hereunder; (b) it shall perform the Services in a professional and workmanlike manner, consistent with generally accepted industry standards; (c) the Deliverables shall conform to the requirements and specifications set forth in the applicable Statement of Work; and (d) to Provider's knowledge, the Work Product shall not infringe the Intellectual Property rights of any third party.

5.2 DISCLAIMER. EXCEPT FOR THE EXPRESS WARRANTIES SET FORTH IN SECTION 5.1, PROVIDER DISCLAIMS ALL WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT. PROVIDER DOES NOT WARRANT THAT THE SERVICES OR DELIVERABLES WILL BE ERROR-FREE, UNINTERRUPTED, OR FREE OF HARMFUL COMPONENTS.

ARTICLE 6: INDEMNIFICATION

6.1 Provider Indemnification. Provider shall indemnify, defend, and hold harmless Client from and against any third-party claims that the Work Product infringes any United States patent, copyright, or trade secret of such third party.

6.2 Client Indemnification. Client shall indemnify, defend, and hold harmless Provider from and against: (a) any claims arising from Client's use of the Work Product or Services; (b) any claims relating to Client Data; and (c) any claims arising from Client's breach of this Agreement.

6.3 EXCLUSIVE INDEMNIFICATION. THE INDEMNIFICATION OBLIGATIONS SET FORTH IN THIS ARTICLE 6 STATE THE INDEMNIFYING PARTY'S SOLE LIABILITY TO, AND THE INDEMNIFIED PARTY'S EXCLUSIVE REMEDY AGAINST, THE OTHER PARTY FOR ANY THIRD-PARTY CLAIM DESCRIBED IN THIS ARTICLE.

ARTICLE 7: LIMITATION OF LIABILITY

7.1 EXCLUSION OF DAMAGES. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, EXEMPLARY, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT, INCLUDING LOST PROFITS, LOST REVENUE, LOSS OF DATA, OR BUSINESS INTERRUPTION, REGARDLESS OF THE THEORY OF LIABILITY AND EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

7.2 CAP ON LIABILITY. PROVIDER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID BY CLIENT TO PROVIDER UNDER THE SPECIFIC STATEMENT OF WORK GIVING RISE TO THE CLAIM DURING THE THREE (3) MONTH PERIOD IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO SUCH CLAIM. CLIENT'S TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAYABLE UNDER THIS AGREEMENT.

7.3 ESSENTIAL BASIS. EACH PARTY ACKNOWLEDGES THAT THE OTHER PARTY HAS ENTERED INTO THIS AGREEMENT IN RELIANCE UPON THE LIMITATIONS OF LIABILITY SET FORTH HEREIN AND THAT THE SAME FORM AN ESSENTIAL BASIS OF THE BARGAIN BETWEEN THE PARTIES.

ARTICLE 8: TERM AND TERMINATION

8.1 Term. This Agreement shall commence on the Effective Date and shall continue for an initial term of three (3) years (the "Initial Term"), unless earlier terminated in accordance with this Article 8. After the Initial Term, this Agreement shall automatically renew for successive one (1) year periods (each, a "Renewal Term") unless either Party provides the other Party with at least ninety (90) days written notice of non-renewal prior to the expiration of the then-current term.

8.2 Termination for Cause. Either Party may terminate this Agreement upon written notice if the other Party: (a) materially breaches this Agreement and fails to cure such breach within thirty (30) days after receiving written notice thereof; or (b) becomes the subject of any proceeding relating to bankruptcy, insolvency, receivership, or similar proceeding.

8.3 TERMINATION FOR CONVENIENCE BY PROVIDER. PROVIDER MAY TERMINATE THIS AGREEMENT OR ANY STATEMENT OF WORK AT ANY TIME FOR ANY REASON UPON SIXTY (60) DAYS PRIOR WRITTEN NOTICE TO CLIENT.

8.4 Effect of Termination. Upon termination or expiration of this Agreement: (a) Client shall pay Provider for all Services performed and expenses incurred through the date of termination; (b) each Party shall return or destroy all Confidential Information of the other Party; and (c) the provisions of this Agreement that by their nature should survive termination shall survive.

""" + general + """

SCHEDULE A: RATE CARD

Role                          | Hourly Rate
------------------------------|------------
Principal Consultant          | $450
Senior Consultant             | $375
Consultant                    | $300
Associate Consultant          | $225
Project Manager               | $350
Technical Architect           | $425
Quality Assurance Engineer    | $275
Business Analyst              | $300

Rates are subject to annual adjustment of up to 10% upon 60 days notice.
Overtime (>40 hours/week): 1.5x standard rate.
Weekend/Holiday work: 2x standard rate.

SCHEDULE B: SAMPLE STATEMENT OF WORK

[To be completed per engagement]

SOW Reference Number: SOW-001
Project Name: Core Banking System Modernization
Duration: 18 months
Team Size: 15 FTEs
Estimated Budget: $4,200,000
Key Milestones:
  Phase 1 — Assessment and Planning (Months 1-3): $600,000
  Phase 2 — Design and Architecture (Months 4-6): $800,000
  Phase 3 — Development (Months 7-12): $1,800,000
  Phase 4 — Testing and Deployment (Months 13-18): $1,000,000

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

NEXUS TECHNOLOGY PARTNERS LLC           GLOBALBANK FINANCIAL CORPORATION
By: _________________________           By: _________________________
Name:                                    Name:
Title:                                   Title:
Date:                                    Date:
"""
    return core


def _generate_employment_agreement() -> str:
    """Generate a 40-50 page Senior Executive Employment Agreement (California)."""
    general = _boilerplate_general_provisions("California", "California", "resolved exclusively in the state and federal courts located in Santa Clara County, California")

    return """
SENIOR EXECUTIVE EMPLOYMENT AGREEMENT

This Senior Executive Employment Agreement (this "Agreement") is entered into as of [DATE] (the "Effective Date"), by and between TitanTech Corporation, a Delaware corporation, with its principal place of business at 1 Infinite Loop, Cupertino, CA 95014 (the "Company"), and [Executive Name], an individual residing at [Address] (the "Executive"). The Company and Executive are sometimes referred to herein individually as a "Party" and collectively as the "Parties."

RECITALS

WHEREAS, the Company desires to employ Executive as its Chief Technology Officer, and Executive desires to accept such employment, on the terms and conditions set forth herein;

WHEREAS, Executive will have access to the Company's most sensitive Confidential Information, trade secrets, and strategic plans in the course of Executive's employment;

WHEREAS, the Company and Executive desire to set forth the terms and conditions of Executive's employment, including compensation, benefits, equity, restrictive covenants, and termination provisions;

NOW, THEREFORE, in consideration of the mutual covenants, terms, and conditions set forth herein, the Company's offer of employment, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:

ARTICLE 1: DEFINITIONS

1.1 "Affiliate" means any entity that directly or indirectly controls, is controlled by, or is under common control with the Company.

1.2 "Board" means the Board of Directors of the Company or, where applicable, a duly authorized committee thereof.

1.3 "Cause" means: (a) Executive's conviction of, or plea of guilty or nolo contendere to, any felony or any crime involving moral turpitude, dishonesty, or fraud; (b) Executive's willful misconduct, gross negligence, or material violation of any written Company policy; (c) Executive's material breach of this Agreement or any other agreement with the Company; (d) Executive's continued failure to substantially perform Executive's material duties (other than due to Disability) after receiving written notice from the Board specifying in reasonable detail the nature of such failure and a thirty (30) day cure period; (e) Executive's unauthorized disclosure of material Confidential Information; or (f) any act of fraud, embezzlement, misappropriation, or dishonesty by Executive that results or is intended to result in personal enrichment at the expense of the Company.

1.4 "Change of Control" means: (a) the acquisition by any person or group of beneficial ownership of more than fifty percent (50%) of the outstanding voting securities of the Company; (b) the consummation of a merger or consolidation of the Company with any other corporation, unless immediately following such merger or consolidation the holders of the Company's outstanding voting securities immediately prior to such merger or consolidation continue to hold at least fifty percent (50%) of the combined voting power of the surviving entity; (c) a complete liquidation or dissolution of the Company; or (d) the sale, lease, exchange, or other transfer of all or substantially all of the assets of the Company.

1.5 "Competitive Business" means any business or enterprise that develops, produces, markets, sells, or provides products or services that are competitive with or substantially similar to any products or services developed, produced, marketed, sold, or provided by the Company or any of its Affiliates, or that the Company or any of its Affiliates has plans to develop, produce, market, sell, or provide, as of the date of Executive's termination of employment.

1.6 "Confidential Information" means all information, whether written, oral, electronic, or otherwise, relating to the business, operations, finances, technology, products, services, customers, suppliers, employees, or strategies of the Company or its Affiliates that is not generally known to the public, including but not limited to: trade secrets, inventions, patent applications, algorithms, source code, architectures, designs, specifications, research, development, processes, formulas, data, databases, customer lists, pricing information, business plans, marketing strategies, financial projections, and any other proprietary information. Confidential Information shall include information received by the Company from third parties under an obligation of confidentiality.

1.7 "Disability" means Executive's inability to perform the essential functions of Executive's position, with or without reasonable accommodation, for a period of ninety (90) consecutive days or one hundred twenty (120) days in any twelve (12) month period, as determined by a physician selected by the Company and reasonably acceptable to Executive.

1.8 "Good Reason" means, without Executive's written consent: (a) a material diminution in Executive's Base Salary; (b) a material diminution in Executive's authority, duties, or responsibilities; (c) a change in Executive's principal place of employment to a location more than fifty (50) miles from the current location; (d) a material breach of this Agreement by the Company; or (e) a material diminution in the budget over which Executive retains authority. Executive must provide the Company with written notice of the condition constituting Good Reason within thirty (30) days after the initial occurrence of such condition, and the Company shall have thirty (30) days after receipt of such notice to cure the condition. If the Company fails to cure the condition within such thirty (30) day period, Executive may resign for Good Reason within fifteen (15) days after the expiration of the cure period.

ARTICLE 2: EMPLOYMENT

2.1 Position and Duties. The Company hereby employs Executive as Chief Technology Officer, reporting directly to the Chief Executive Officer. Executive shall perform all duties and responsibilities customarily associated with such position and such other duties as may be reasonably assigned by the CEO or the Board from time to time. Executive shall devote substantially all of Executive's business time, attention, skills, and energy to the performance of Executive's duties hereunder and to the advancement of the Company's business interests.

2.2 Outside Activities. During the term of Executive's employment, Executive shall not, without the prior written consent of the Board, engage in any other employment, consulting, or business activity that would create a conflict of interest with the Company or any of its Affiliates or that would interfere with Executive's performance of duties hereunder. Notwithstanding the foregoing, Executive may: (a) serve on up to two (2) outside boards of directors of non-competing companies, subject to the Board's prior approval; (b) participate in charitable, civic, or community activities; and (c) manage Executive's personal investments, provided that none of such activities materially interfere with Executive's duties hereunder.

ARTICLE 3: COMPENSATION AND BENEFITS

3.1 Base Salary. Executive shall receive an annual base salary of Four Hundred Fifty Thousand Dollars ($450,000) ("Base Salary"), payable in accordance with the Company's standard payroll practices and subject to all applicable withholdings and deductions. The Board shall review Executive's Base Salary annually and may increase (but not decrease) Executive's Base Salary in its sole discretion.

3.2 SALARY REDUCTION. NOTWITHSTANDING SECTION 3.1, THE COMPANY MAY, IN ITS SOLE AND ABSOLUTE DISCRETION, REDUCE EXECUTIVE'S BASE SALARY BY UP TO TWENTY PERCENT (20%) AT ANY TIME WITHOUT EXECUTIVE'S CONSENT IF THE BOARD DETERMINES THAT ECONOMIC CONDITIONS, FINANCIAL PERFORMANCE, OR OPERATIONAL NECESSITY WARRANT SUCH REDUCTION. SUCH REDUCTION SHALL NOT CONSTITUTE A BREACH OF THIS AGREEMENT OR GOOD REASON FOR RESIGNATION. THE COMPANY MAY IMPLEMENT SUCH SALARY REDUCTION UPON THIRTY (30) DAYS WRITTEN NOTICE TO EXECUTIVE.

3.3 Annual Bonus. Executive shall be eligible to earn an annual performance bonus of up to one hundred percent (100%) of Executive's Base Salary ("Target Bonus"), based on the achievement of individual and Company performance objectives established by the Board. The actual bonus amount shall be determined by the Board in its sole discretion and may range from zero to two hundred percent (200%) of the Target Bonus. Bonuses shall be paid within ninety (90) days following the end of each fiscal year, provided that Executive is employed by the Company on the date the bonus is paid.

3.4 Equity Grant. Subject to approval by the Board, Executive shall be granted: (a) an initial stock option to purchase 500,000 shares of the Company's common stock at an exercise price equal to the fair market value on the date of grant (the "Option"), vesting over four (4) years with a one (1) year cliff and monthly vesting thereafter; and (b) 100,000 restricted stock units ("RSUs"), vesting over four (4) years with annual vesting of 25% per year. The Option and RSUs shall be subject to the terms and conditions of the Company's equity incentive plan and the applicable award agreements.

3.5 CLAWBACK. ALL BONUSES, EQUITY GRANTS, AND OTHER INCENTIVE COMPENSATION PAID OR AWARDED TO EXECUTIVE SHALL BE SUBJECT TO CLAWBACK BY THE COMPANY AT THE COMPANY'S SOLE DISCRETION FOR ANY REASON WHATSOEVER WITHIN THIRTY-SIX (36) MONTHS OF THE DATE OF PAYMENT OR VESTING. THE COMPANY MAY REQUIRE EXECUTIVE TO REPAY THE GROSS AMOUNT OF ANY SUCH COMPENSATION, INCLUDING ANY AMOUNTS PREVIOUSLY REMITTED AS TAXES, WITHOUT REGARD TO WHETHER SUCH TAXES ARE RECOVERABLE BY EXECUTIVE. EXECUTIVE HEREBY CONSENTS TO THE DEDUCTION OF ANY CLAWBACK AMOUNTS FROM ANY AMOUNTS OTHERWISE OWED TO EXECUTIVE BY THE COMPANY.

3.6 Benefits. Executive shall be entitled to participate in all benefit plans and programs generally available to other senior executives of the Company, including health insurance, dental insurance, vision insurance, life insurance, disability insurance, 401(k) plan, and paid time off, subject to the terms and conditions of such plans and programs as they may be amended from time to time.

3.7 Perquisites. During the term of Executive's employment, the Company shall provide Executive with: (a) a monthly car allowance of $1,500; (b) reimbursement of up to $5,000 per year for professional development, including conferences and continuing education; (c) an annual executive physical examination; and (d) business class air travel for all Company business travel in excess of five (5) hours.

ARTICLE 4: INTELLECTUAL PROPERTY

4.1 ASSIGNMENT OF INVENTIONS. EXECUTIVE HEREBY IRREVOCABLY ASSIGNS TO THE COMPANY ALL RIGHT, TITLE, AND INTEREST IN AND TO ALL INVENTIONS, DISCOVERIES, DEVELOPMENTS, IMPROVEMENTS, IDEAS, WORKS OF AUTHORSHIP, DESIGNS, FORMULAS, ALGORITHMS, PROCESSES, TECHNIQUES, KNOW-HOW, DATA, SOFTWARE, AND ALL OTHER FORMS OF INTELLECTUAL PROPERTY (COLLECTIVELY, "INVENTIONS") THAT ARE CONCEIVED, CREATED, DEVELOPED, REDUCED TO PRACTICE, OR MADE BY EXECUTIVE, EITHER ALONE OR JOINTLY WITH OTHERS, DURING THE TERM OF EXECUTIVE'S EMPLOYMENT, WHETHER OR NOT: (A) DURING WORKING HOURS; (B) ON COMPANY PREMISES; (C) USING COMPANY EQUIPMENT, SUPPLIES, OR RESOURCES; (D) AT THE DIRECTION OF THE COMPANY; OR (E) RELATED TO THE COMPANY'S ACTUAL OR ANTICIPATED BUSINESS, RESEARCH, OR DEVELOPMENT. THIS ASSIGNMENT INCLUDES ALL INVENTIONS CONCEIVED, CREATED, OR DEVELOPED BY EXECUTIVE DURING EXECUTIVE'S PERSONAL TIME AND USING EXECUTIVE'S OWN RESOURCES, EVEN IF SUCH INVENTIONS ARE UNRELATED TO THE COMPANY'S BUSINESS.

4.2 California Labor Code Section 2870 Notice. Notwithstanding Section 4.1, Executive is hereby notified that the provisions of Section 4.1 do not apply to any Invention that qualifies fully under the provisions of California Labor Code Section 2870, which provides that an employment agreement may not require an employee to assign an invention that is developed entirely on the employee's own time without using the employer's equipment, supplies, facilities, or trade secret information, unless the invention relates at the time of conception or reduction to practice to the employer's business, or actual or demonstrably anticipated research or development, or results from any work performed by the employee for the employer.

4.3 POST-TERMINATION INVENTION ASSIGNMENT. FOR A PERIOD OF TWELVE (12) MONTHS FOLLOWING THE TERMINATION OF EXECUTIVE'S EMPLOYMENT FOR ANY REASON, EXECUTIVE HEREBY ASSIGNS TO THE COMPANY ALL RIGHT, TITLE, AND INTEREST IN AND TO ANY INVENTIONS THAT: (A) RELATE TO THE COMPANY'S ACTUAL OR PLANNED BUSINESS ACTIVITIES, PRODUCTS, OR SERVICES; (B) RESULT FROM OR ARE BASED UPON ANY CONFIDENTIAL INFORMATION OF THE COMPANY; OR (C) RESULT FROM ANY WORK PERFORMED BY EXECUTIVE FOR THE COMPANY DURING THE TERM OF EXECUTIVE'S EMPLOYMENT. EXECUTIVE ACKNOWLEDGES THAT THIS POST-TERMINATION ASSIGNMENT OBLIGATION IS REASONABLE AND NECESSARY TO PROTECT THE COMPANY'S LEGITIMATE BUSINESS INTERESTS AND INTELLECTUAL PROPERTY.

4.4 Works Made for Hire. Executive acknowledges and agrees that all works of authorship created by Executive within the scope of Executive's employment with the Company are "works made for hire" as defined in 17 U.S.C. Section 101, and that the Company is the author thereof for copyright purposes. To the extent that any such work is determined not to be a work made for hire, Executive hereby irrevocably assigns to the Company all right, title, and interest in and to such work, including all copyrights therein.

4.5 Moral Rights. To the fullest extent permitted by Applicable Law, Executive hereby irrevocably waives all moral rights, including rights of attribution, integrity, disclosure, and withdrawal, and any other similar rights recognized by Applicable Law, in connection with all Inventions and works of authorship assigned to the Company under this Agreement.

4.6 Cooperation. Executive shall, during and after the term of Executive's employment, cooperate fully with the Company, at the Company's expense, in obtaining, maintaining, and enforcing patents, copyrights, trademarks, and other Intellectual Property protections for any Inventions assigned to the Company under this Agreement. Executive hereby irrevocably appoints the Company and its officers as Executive's attorney-in-fact to execute and deliver any documents and to take any actions necessary to perfect the Company's rights in any Inventions.

ARTICLE 5: RESTRICTIVE COVENANTS

5.1 NON-COMPETITION. FOR A PERIOD OF TWENTY-FOUR (24) MONTHS FOLLOWING THE TERMINATION OF EXECUTIVE'S EMPLOYMENT FOR ANY REASON (THE "RESTRICTED PERIOD"), EXECUTIVE SHALL NOT, DIRECTLY OR INDIRECTLY, ENGAGE IN, HAVE ANY EQUITY INTEREST IN, MANAGE, OPERATE, OR PROVIDE SERVICES TO ANY COMPETITIVE BUSINESS ANYWHERE IN THE WORLD. THIS RESTRICTION APPLIES WHETHER EXECUTIVE ACTS AS AN INDIVIDUAL, PARTNER, STOCKHOLDER, DIRECTOR, OFFICER, PRINCIPAL, AGENT, EMPLOYEE, TRUSTEE, CONSULTANT, CONTRACTOR, ADVISOR, OR IN ANY OTHER RELATIONSHIP OR CAPACITY. NOTWITHSTANDING THE FOREGOING, EXECUTIVE MAY OWN, DIRECTLY OR INDIRECTLY, UP TO ONE PERCENT (1%) OF THE TOTAL OUTSTANDING VOTING SECURITIES OF A PUBLICLY TRADED ENTITY ENGAGED IN A COMPETITIVE BUSINESS.

5.2 NON-SOLICITATION OF EMPLOYEES. FOR A PERIOD OF THIRTY-SIX (36) MONTHS FOLLOWING THE TERMINATION OF EXECUTIVE'S EMPLOYMENT FOR ANY REASON, EXECUTIVE SHALL NOT, DIRECTLY OR INDIRECTLY: (A) SOLICIT, RECRUIT, INDUCE, OR ENCOURAGE ANY EMPLOYEE, CONSULTANT, OR INDEPENDENT CONTRACTOR OF THE COMPANY OR ANY OF ITS AFFILIATES TO LEAVE THE EMPLOY OF OR TERMINATE SUCH PERSON'S RELATIONSHIP WITH THE COMPANY OR ANY OF ITS AFFILIATES; OR (B) HIRE OR ENGAGE ANY PERSON WHO WAS AN EMPLOYEE, CONSULTANT, OR INDEPENDENT CONTRACTOR OF THE COMPANY OR ANY OF ITS AFFILIATES AT ANY TIME DURING THE TWELVE (12) MONTH PERIOD IMMEDIATELY PRECEDING EXECUTIVE'S TERMINATION.

5.3 Non-Solicitation of Customers. For a period of twenty-four (24) months following the termination of Executive's employment for any reason, Executive shall not, directly or indirectly, solicit, divert, or take away, or attempt to solicit, divert, or take away, any customer, client, account, or business opportunity of the Company or any of its Affiliates that Executive had contact with, knowledge of, or responsibility for during the twelve (12) month period immediately preceding Executive's termination.

5.4 Non-Disparagement. During and after the term of Executive's employment, Executive shall not make any statements, whether written or oral, that disparage, criticize, or otherwise reflect negatively upon the Company, its Affiliates, or any of their respective officers, directors, employees, products, services, or business practices. The Company shall instruct its officers and directors not to make disparaging statements about Executive.

ARTICLE 6: CONFIDENTIALITY

6.1 Obligations. Executive acknowledges that, in the course of Executive's employment, Executive will have access to and become acquainted with Confidential Information. Executive agrees that, during the term of Executive's employment and in perpetuity thereafter, Executive shall not, without the prior written consent of the Company, use, disclose, publish, or otherwise reveal any Confidential Information to any third party, except as required in the performance of Executive's duties for the Company. Executive shall take all reasonable precautions to prevent the unauthorized disclosure of Confidential Information.

6.2 Return of Materials. Upon termination of Executive's employment for any reason, or at any time upon the Company's request, Executive shall promptly return to the Company all documents, materials, equipment, and other property belonging to the Company or containing Confidential Information, including all copies and reproductions thereof.

6.3 Defend Trade Secrets Act Notice. Pursuant to the Defend Trade Secrets Act of 2016, Executive is hereby notified that Executive shall not be held criminally or civilly liable under any federal or state trade secret law for the disclosure of a trade secret that: (a) is made (i) in confidence to a federal, state, or local government official, either directly or indirectly, or to an attorney, and (ii) solely for the purpose of reporting or investigating a suspected violation of law; or (b) is made in a complaint or other document filed in a lawsuit or other proceeding, if such filing is made under seal.

ARTICLE 7: TERMINATION

7.1 At-Will Employment. Executive's employment with the Company is "at will," meaning that either the Company or Executive may terminate Executive's employment at any time, with or without cause, and with or without notice, subject to the terms of this Article 7.

7.2 Termination by the Company for Cause. The Company may terminate Executive's employment for Cause at any time upon written notice to Executive specifying the basis for such termination. Upon termination for Cause, Executive shall be entitled to receive: (a) Executive's accrued and unpaid Base Salary through the date of termination; (b) any accrued and unused paid time off; and (c) any amounts required to be paid under Applicable Law (collectively, "Accrued Benefits"). Executive shall not be entitled to any other compensation, benefits, or severance upon termination for Cause.

7.3 Termination Without Cause or for Good Reason. If the Company terminates Executive's employment without Cause or Executive resigns for Good Reason, and subject to Executive's execution and non-revocation of a general release of claims in favor of the Company, Executive shall be entitled to receive: (a) the Accrued Benefits; (b) continued payment of Executive's Base Salary for twelve (12) months following the date of termination ("Severance Period"); (c) a pro-rata portion of Executive's Target Bonus for the year of termination; (d) accelerated vesting of twelve (12) months of unvested equity; and (e) COBRA premium reimbursement for up to twelve (12) months.

7.4 Change of Control Termination. If, within twelve (12) months following a Change of Control, the Company terminates Executive's employment without Cause or Executive resigns for Good Reason, and subject to Executive's execution and non-revocation of a general release of claims, Executive shall be entitled to receive: (a) the Accrued Benefits; (b) a lump sum payment equal to twenty-four (24) months of Executive's Base Salary; (c) Executive's Target Bonus at one hundred percent (100%); (d) full acceleration of all unvested equity; and (e) COBRA premium reimbursement for up to twenty-four (24) months.

7.5 Voluntary Resignation. If Executive voluntarily resigns without Good Reason, Executive shall provide the Company with at least sixty (60) days written notice of such resignation. Executive shall be entitled to receive only the Accrued Benefits upon such resignation.

7.6 Death or Disability. If Executive's employment terminates due to Executive's death or Disability, Executive (or Executive's estate or legal representative) shall be entitled to receive: (a) the Accrued Benefits; (b) twelve (12) months of continued Base Salary payments; and (c) accelerated vesting of all equity that would have vested in the twelve (12) months following the date of termination.

7.7 Section 280G. If any payment or benefit to Executive under this Agreement would constitute an "excess parachute payment" within the meaning of Section 280G of the Internal Revenue Code, and would be subject to the excise tax imposed by Section 4999 of the Internal Revenue Code, then such payments and benefits shall be reduced to the extent necessary to avoid such excise tax, but only if such reduction would result in a greater after-tax benefit to Executive.

""" + general + """

SCHEDULE A: PRIOR INVENTIONS

Executive has disclosed the following prior inventions (if none, write "None"):

1. [List any prior inventions here]
2. None.

SCHEDULE B: EQUITY GRANT SUMMARY

Stock Options: 500,000 shares
  Exercise Price: FMV on grant date
  Vesting: 4 years, 1 year cliff, monthly thereafter
  Expiration: 10 years from grant date

RSUs: 100,000 shares
  Vesting: 4 years, annual 25%
  Settlement: Within 30 days of vesting

SCHEDULE C: BENEFITS SUMMARY

Health Insurance: Company pays 100% of employee premium, 75% of dependent premium
Dental Insurance: Company pays 100% of employee premium
Vision Insurance: Company pays 100% of employee premium
Life Insurance: 2x Base Salary
Short-Term Disability: 60% of Base Salary for up to 26 weeks
Long-Term Disability: 60% of Base Salary
401(k): Company matches 100% of first 4% of salary
PTO: 25 days per year (unlimited for executives with Board approval)
Parental Leave: 16 weeks paid
Sabbatical: 4 weeks paid after 5 years of service

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

TITANTECH CORPORATION                    EXECUTIVE
By: _________________________           _________________________
Name:                                    [Executive Name]
Title: Chief Executive Officer
Date:                                    Date:
"""


def _generate_vendor_agreement() -> str:
    """Generate a large Vendor/Distribution Agreement."""
    defs = _boilerplate_definitions("Distribution Agreement", ("Manufacturer", "Distributor"))
    general = _boilerplate_general_provisions("Illinois", "Illinois", "resolved exclusively in the federal and state courts located in Cook County, Illinois")

    return """
EXCLUSIVE DISTRIBUTION AGREEMENT

This Exclusive Distribution Agreement (this "Agreement") is entered into as of [DATE] (the "Effective Date"), by and between Pinnacle Manufacturing Group, Inc., an Illinois corporation, with its principal place of business at 233 South Wacker Drive, Suite 4500, Chicago, IL 60606 ("Manufacturer"), and Continental Distribution Partners LLC, a Delaware limited liability company, with its principal place of business at 1200 Market Street, Suite 800, Philadelphia, PA 19107 ("Distributor"). Manufacturer and Distributor are sometimes referred to herein individually as a "Party" and collectively as the "Parties."

RECITALS

WHEREAS, Manufacturer designs, develops, manufactures, and sells [PRODUCTS] under various proprietary brands and trademarks;

WHEREAS, Distributor operates an extensive distribution network across North America and desires to be appointed as the exclusive distributor of the Products in the Territory;

WHEREAS, the Parties desire to set forth the terms and conditions under which Manufacturer will appoint Distributor and Distributor will distribute the Products;

NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein, the Parties agree as follows:

""" + defs + """

ARTICLE 2: APPOINTMENT AND TERRITORY

2.1 Exclusive Appointment. Subject to the terms and conditions of this Agreement, Manufacturer hereby appoints Distributor as its exclusive distributor of the Products in the Territory, and Distributor hereby accepts such appointment. During the term of this Agreement, Manufacturer shall not: (a) sell Products directly to customers in the Territory; or (b) appoint any other distributor or sales representative in the Territory, in each case with respect to the Products covered by this Agreement.

2.2 REVOCATION OF EXCLUSIVITY. NOTWITHSTANDING SECTION 2.1, MANUFACTURER RESERVES THE RIGHT TO REVOKE DISTRIBUTOR'S EXCLUSIVE DISTRIBUTION RIGHTS AND APPOINT ADDITIONAL DISTRIBUTORS IN THE TERRITORY AT ANY TIME UPON NINETY (90) DAYS WRITTEN NOTICE TO DISTRIBUTOR IF: (A) DISTRIBUTOR FAILS TO MEET THE MINIMUM PURCHASE REQUIREMENTS SET FORTH IN SECTION 3.2 IN ANY TWO (2) CONSECUTIVE QUARTERS; (B) MANUFACTURER DETERMINES, IN ITS SOLE DISCRETION, THAT ADDITIONAL DISTRIBUTION CAPACITY IS NECESSARY TO MEET MARKET DEMAND; OR (C) MANUFACTURER ACQUIRES OR IS ACQUIRED BY ANOTHER ENTITY AND DETERMINES THAT CONSOLIDATED DISTRIBUTION IS MORE EFFICIENT. UPON SUCH REVOCATION, DISTRIBUTOR'S APPOINTMENT SHALL BECOME NON-EXCLUSIVE, AND THIS AGREEMENT SHALL OTHERWISE REMAIN IN FULL FORCE AND EFFECT.

2.3 Territory. The "Territory" means the continental United States and Canada, including all fifty states, the District of Columbia, and all provinces and territories of Canada.

ARTICLE 3: PURCHASE REQUIREMENTS AND PRICING

3.1 Orders. Distributor shall submit purchase orders to Manufacturer in accordance with Manufacturer's standard order procedures. Each purchase order shall specify the Products ordered, quantities, requested delivery dates, and delivery locations. All purchase orders are subject to acceptance by Manufacturer. Manufacturer shall confirm or reject each purchase order within five (5) Business Days of receipt.

3.2 MINIMUM PURCHASE REQUIREMENTS. DISTRIBUTOR SHALL PURCHASE A MINIMUM OF FIVE MILLION DOLLARS ($5,000,000) OF PRODUCTS PER QUARTER ("MINIMUM PURCHASE REQUIREMENT"). IF DISTRIBUTOR FAILS TO MEET THE MINIMUM PURCHASE REQUIREMENT IN ANY QUARTER, DISTRIBUTOR SHALL PAY MANUFACTURER A SHORTFALL PENALTY EQUAL TO TWO HUNDRED PERCENT (200%) OF THE DIFFERENCE BETWEEN THE MINIMUM PURCHASE REQUIREMENT AND THE ACTUAL PURCHASES FOR SUCH QUARTER. SUCH SHORTFALL PENALTY SHALL BE DUE AND PAYABLE WITHIN THIRTY (30) DAYS AFTER THE END OF THE APPLICABLE QUARTER.

3.3 Pricing. Products shall be sold to Distributor at the prices set forth in Schedule C (the "Price List"). Manufacturer may revise the Price List at any time upon sixty (60) days prior written notice to Distributor. Price increases shall not apply to purchase orders accepted by Manufacturer prior to the effective date of such increase.

3.4 Payment Terms. Distributor shall pay all invoices within thirty (30) days of invoice date. Late payments shall accrue interest at the rate of one and one-half percent (1.5%) per month or the maximum rate permitted by Applicable Law, whichever is lower.

ARTICLE 4: DELIVERY AND RISK OF LOSS

4.1 Delivery. Manufacturer shall use commercially reasonable efforts to deliver Products in accordance with the delivery dates specified in accepted purchase orders. Delivery terms shall be FOB Manufacturer's shipping facility (Incoterms 2020). Title and risk of loss shall pass to Distributor upon delivery of Products to the carrier at Manufacturer's facility.

4.2 LATE DELIVERY. MANUFACTURER SHALL NOT BE LIABLE FOR ANY DAMAGES, PENALTIES, OR CLAIMS ARISING FROM LATE DELIVERY OF PRODUCTS, REGARDLESS OF THE CAUSE. DISTRIBUTOR'S SOLE REMEDY FOR LATE DELIVERY SHALL BE TO CANCEL THE APPLICABLE PURCHASE ORDER WITH RESPECT TO THE UNDELIVERED PRODUCTS, PROVIDED THAT DISTRIBUTOR PROVIDES WRITTEN NOTICE OF CANCELLATION PRIOR TO SHIPMENT.

4.3 PRODUCT SUBSTITUTION. MANUFACTURER RESERVES THE RIGHT TO SUBSTITUTE PRODUCTS OF EQUIVALENT OR LESSER SPECIFICATIONS WITHOUT PRIOR NOTICE TO DISTRIBUTOR IF SUPPLY CHAIN CONDITIONS, COMPONENT AVAILABILITY, OR MANUFACTURING CONSTRAINTS WARRANT SUCH SUBSTITUTION. MANUFACTURER SHALL USE COMMERCIALLY REASONABLE EFFORTS TO NOTIFY DISTRIBUTOR OF ANY SUCH SUBSTITUTION WITHIN A REASONABLE TIME AFTER SHIPMENT.

ARTICLE 5: WARRANTIES AND PRODUCT LIABILITY

5.1 Limited Warranty. Manufacturer warrants that Products shall substantially conform to the applicable specifications for a period of ninety (90) days from the date of delivery to Distributor (the "Warranty Period"). This warranty does not apply to any Product that has been modified, altered, or damaged after delivery, or that has been used in a manner not contemplated by the Product specifications.

5.2 WARRANTY DISCLAIMER. THE WARRANTY SET FORTH IN SECTION 5.1 IS IN LIEU OF ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ALL IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT. MANUFACTURER DOES NOT WARRANT THAT THE PRODUCTS WILL MEET DISTRIBUTOR'S OR ANY END USER'S REQUIREMENTS, OR THAT THE OPERATION OF ANY PRODUCT WILL BE UNINTERRUPTED OR ERROR-FREE.

5.3 PRODUCT LIABILITY. DISTRIBUTOR SHALL BE SOLELY RESPONSIBLE FOR ALL PRODUCT LIABILITY CLAIMS ARISING FROM OR RELATED TO THE DISTRIBUTION, SALE, OR USE OF PRODUCTS IN THE TERRITORY, INCLUDING BUT NOT LIMITED TO CLAIMS FOR PERSONAL INJURY, PROPERTY DAMAGE, OR ECONOMIC LOSS. DISTRIBUTOR SHALL INDEMNIFY, DEFEND, AND HOLD HARMLESS MANUFACTURER FROM AND AGAINST ALL SUCH CLAIMS, REGARDLESS OF WHETHER SUCH CLAIMS ARISE FROM DEFECTS IN DESIGN, MANUFACTURING, OR LABELING.

ARTICLE 6: INTELLECTUAL PROPERTY

6.1 License. Manufacturer hereby grants Distributor a non-exclusive, non-transferable, revocable license to use Manufacturer's trademarks, trade names, and logos solely in connection with the distribution, marketing, and sale of Products in the Territory during the term of this Agreement.

6.2 Restrictions. Distributor shall not: (a) modify, alter, or create derivative works of any Manufacturer trademarks; (b) use Manufacturer's trademarks in any manner that is misleading or disparaging; (c) register or attempt to register any of Manufacturer's trademarks or any confusingly similar marks; or (d) contest the validity of Manufacturer's trademarks.

ARTICLE 7: INDEMNIFICATION

7.1 Distributor Indemnification. Distributor shall indemnify, defend, and hold harmless Manufacturer and its Affiliates, officers, directors, employees, and agents from and against any and all Damages arising out of or relating to: (a) Distributor's distribution, marketing, sale, or support of Products; (b) Distributor's breach of this Agreement; (c) any product liability claims; (d) Distributor's violation of Applicable Law; or (e) any acts or omissions of Distributor's employees, agents, or subcontractors.

7.2 MANUFACTURER INDEMNIFICATION LIMITATION. MANUFACTURER SHALL NOT BE REQUIRED TO INDEMNIFY DISTRIBUTOR FOR ANY REASON WHATSOEVER, INCLUDING BUT NOT LIMITED TO CLAIMS ARISING FROM DEFECTS IN PRODUCTS, INTELLECTUAL PROPERTY INFRINGEMENT, OR PRODUCT RECALLS. DISTRIBUTOR ACKNOWLEDGES AND AGREES THAT IT ASSUMES ALL RISK ASSOCIATED WITH THE DISTRIBUTION OF PRODUCTS.

ARTICLE 8: LIMITATION OF LIABILITY

8.1 EXCLUSION OF DAMAGES. IN NO EVENT SHALL MANUFACTURER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, EXEMPLARY, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, LOSS OF REVENUE, LOSS OF BUSINESS OPPORTUNITY, OR LOSS OF GOODWILL, ARISING OUT OF OR RELATED TO THIS AGREEMENT.

8.2 CAP ON LIABILITY. MANUFACTURER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE AMOUNTS PAID BY DISTRIBUTOR TO MANUFACTURER FOR THE SPECIFIC PRODUCTS GIVING RISE TO THE CLAIM.

ARTICLE 9: AUDIT RIGHTS

9.1 Audit. Manufacturer may, at any time and without prior notice, audit Distributor's books, records, inventory, facilities, and operations to verify Distributor's compliance with this Agreement, including compliance with the Minimum Purchase Requirements, pricing restrictions, and territory limitations.

9.2 AUDIT PENALTIES. IF ANY AUDIT REVEALS THAT DISTRIBUTOR HAS: (A) UNDERREPORTED PURCHASES BY MORE THAN THREE PERCENT (3%); (B) SOLD PRODUCTS OUTSIDE THE TERRITORY; OR (C) SOLD PRODUCTS BELOW THE MINIMUM RESALE PRICE, DISTRIBUTOR SHALL PAY MANUFACTURER TWO HUNDRED PERCENT (200%) OF THE VALUE OF THE NON-COMPLIANT TRANSACTIONS, PLUS ALL COSTS AND EXPENSES INCURRED BY MANUFACTURER IN CONDUCTING THE AUDIT, INCLUDING TRAVEL, ACCOUNTING, AND LEGAL FEES.

ARTICLE 10: TERM AND TERMINATION

10.1 Term. This Agreement shall commence on the Effective Date and shall continue for an initial term of five (5) years (the "Initial Term"), unless earlier terminated in accordance with this Article 10.

10.2 Renewal. After the Initial Term, this Agreement shall automatically renew for successive one (1) year periods unless either Party provides the other Party with at least one hundred eighty (180) days written notice of non-renewal prior to the expiration of the then-current term.

10.3 TERMINATION BY MANUFACTURER. MANUFACTURER MAY TERMINATE THIS AGREEMENT AT ANY TIME FOR ANY REASON UPON THIRTY (30) DAYS WRITTEN NOTICE TO DISTRIBUTOR. IN THE EVENT OF SUCH TERMINATION, DISTRIBUTOR SHALL HAVE NO CLAIM FOR DAMAGES, LOST PROFITS, OR COMPENSATION OF ANY KIND.

10.4 Termination by Distributor. Distributor may terminate this Agreement only: (a) upon material breach by Manufacturer that remains uncured for ninety (90) days after written notice; or (b) upon one hundred eighty (180) days prior written notice, subject to payment of all outstanding purchase orders and a termination fee equal to fifteen percent (15%) of the Minimum Purchase Requirement for the remaining term.

10.5 UNILATERAL AMENDMENT. MANUFACTURER MAY AMEND THE TERMS OF THIS AGREEMENT AT ANY TIME BY POSTING UPDATED TERMS ON ITS WEBSITE OR DISTRIBUTOR PORTAL. CONTINUED SUBMISSION OF PURCHASE ORDERS BY DISTRIBUTOR FOLLOWING SUCH POSTING SHALL CONSTITUTE DISTRIBUTOR'S ACCEPTANCE OF THE AMENDED TERMS.

""" + general + """

SCHEDULE C: PRICE LIST

[Product pricing to be attached]

Category A Products: $50-500 per unit
Category B Products: $500-5,000 per unit
Category C Products: $5,000-50,000 per unit

Volume discounts:
  $1M-$2.5M quarterly: 5% discount
  $2.5M-$5M quarterly: 10% discount
  $5M+ quarterly: 15% discount

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

PINNACLE MANUFACTURING GROUP, INC.      CONTINENTAL DISTRIBUTION PARTNERS LLC
By: _________________________           By: _________________________
Name:                                    Name:
Title:                                   Title:
Date:                                    Date:
"""


def get_contracts() -> Dict[str, str]:
    """Return all 10 large test contracts."""
    contracts = {
        "Enterprise_SaaS_Delaware": _generate_saas_agreement(),
        "MSA_IT_Consulting_NewYork": _generate_msa(),
        "Executive_Employment_California": _generate_employment_agreement(),
        "Distribution_Agreement_Illinois": _generate_vendor_agreement(),
    }

    # Verify minimum sizes
    for name, text in contracts.items():
        word_count = len(text.split())
        char_count = len(text)
        logger.info(f"Contract '{name}': {word_count:,} words, {char_count:,} chars")
        if word_count < 5000:
            logger.warning(f"Contract '{name}' is smaller than expected ({word_count} words)")

    return contracts


# ─────────────────────────────────────────────────────────────
# OVERNIGHT TEST RUNNER
# ─────────────────────────────────────────────────────────────

async def analyze_contract(name: str, text: str, iteration: int) -> Dict[str, Any]:
    """Analyze a single contract and return metrics."""
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            analysis_pipeline.run(
                contract_text=text,
                playbook_rules=[],
                playbook_name="Default",
                party_side="buyer",
            ),
            timeout=300.0,  # 5 min timeout for large docs
        )
        elapsed = time.monotonic() - start

        red = [r for r in result.redlines if r.risk_level == "RED"]
        yellow = [r for r in result.redlines if r.risk_level == "YELLOW"]
        green = [r for r in result.redlines if r.risk_level == "GREEN"]

        findings = []
        for r in result.redlines:
            findings.append({
                "level": r.risk_level,
                "rule": r.rule_name,
                "clause_preview": (r.verified_text or r.original_text)[:120],
                "has_fix": bool(r.suggested_fix),
                "fix_preview": (r.suggested_fix[:100] if r.suggested_fix else None),
                "confidence": round(r.confidence.score, 3) if r.confidence else None,
                "conf_level": r.confidence.level.value if r.confidence else "N/A",
                "verification": r.verification_status,
                "deal_breaker": r.is_deal_breaker,
                "clause_type": r.clause_type,
                "cross_refs": r.cross_references,
            })

        return {
            "name": name,
            "iteration": iteration,
            "status": "success",
            "time_seconds": round(elapsed, 2),
            "char_count": len(text),
            "word_count": len(text.split()),
            "total_risks": len(result.redlines),
            "red": len(red),
            "yellow": len(yellow),
            "green": len(green),
            "tokens": result.total_tokens_used,
            "partial": result.partial,
            "summary_count": len(result.executive_summary),
            "summaries": result.executive_summary,
            "findings": findings,
            "stage_metrics": [
                {"stage": m.stage_name, "duration": round(m.duration_seconds, 2), "items": m.items_processed, "error": m.error}
                for m in result.stage_metrics
            ],
        }
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        return {
            "name": name, "iteration": iteration, "status": "timeout",
            "time_seconds": round(elapsed, 2), "char_count": len(text), "word_count": len(text.split()),
            "error": "Analysis timed out after 300 seconds",
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "name": name, "iteration": iteration, "status": "error",
            "time_seconds": round(elapsed, 2), "char_count": len(text), "word_count": len(text.split()),
            "error": str(e),
        }


async def run_iteration(contracts: Dict[str, str], iteration: int) -> List[Dict[str, Any]]:
    """Run one full iteration of all contracts."""
    logger.info(f"\n{'='*80}")
    logger.info(f"ITERATION {iteration} STARTING")
    logger.info(f"{'='*80}")

    results = []
    for name, text in contracts.items():
        logger.info(f"  [{iteration}] Analyzing {name} ({len(text.split()):,} words)...")
        result = await analyze_contract(name, text, iteration)
        if result["status"] == "success":
            logger.info(f"  [{iteration}] {name}: {result['total_risks']} risks "
                        f"({result['red']}R/{result['yellow']}Y/{result['green']}G) "
                        f"in {result['time_seconds']:.1f}s, {result['tokens']} tokens")
        else:
            logger.error(f"  [{iteration}] {name}: {result['status']} — {result.get('error', 'unknown')}")
        results.append(result)

    return results


def analyze_results(all_results: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Deep analysis of all iterations."""
    analysis = {
        "total_iterations": len(all_results),
        "total_analyses": sum(len(r) for r in all_results),
        "contracts": {},
        "performance": {},
        "quality": {},
        "optimizations": [],
    }

    # Per-contract analysis
    for iteration_results in all_results:
        for result in iteration_results:
            name = result["name"]
            if name not in analysis["contracts"]:
                analysis["contracts"][name] = {"runs": [], "char_count": result.get("char_count", 0), "word_count": result.get("word_count", 0)}
            analysis["contracts"][name]["runs"].append(result)

    # Performance analysis
    all_times = []
    all_tokens = []
    for name, data in analysis["contracts"].items():
        successful = [r for r in data["runs"] if r["status"] == "success"]
        if successful:
            times = [r["time_seconds"] for r in successful]
            tokens = [r["tokens"] for r in successful]
            all_times.extend(times)
            all_tokens.extend(tokens)

            analysis["performance"][name] = {
                "avg_time": round(sum(times) / len(times), 2),
                "min_time": round(min(times), 2),
                "max_time": round(max(times), 2),
                "avg_tokens": round(sum(tokens) / len(tokens)),
                "chars_per_second": round(data["char_count"] / (sum(times) / len(times)), 1),
                "success_rate": f"{len(successful)}/{len(data['runs'])}",
            }

    if all_times:
        analysis["performance"]["overall"] = {
            "avg_time": round(sum(all_times) / len(all_times), 2),
            "total_time": round(sum(all_times), 2),
            "avg_tokens": round(sum(all_tokens) / len(all_tokens)),
        }

    # Quality analysis — consistency across iterations
    for name, data in analysis["contracts"].items():
        successful = [r for r in data["runs"] if r["status"] == "success"]
        if len(successful) >= 2:
            risk_counts = [r["total_risks"] for r in successful]
            red_counts = [r["red"] for r in successful]
            risk_variance = max(risk_counts) - min(risk_counts)
            red_variance = max(red_counts) - min(red_counts)

            analysis["quality"][name] = {
                "risk_count_range": f"{min(risk_counts)}-{max(risk_counts)}",
                "risk_variance": risk_variance,
                "red_count_range": f"{min(red_counts)}-{max(red_counts)}",
                "red_variance": red_variance,
                "consistent": risk_variance <= 3,  # Within 3 is acceptable
            }

            if risk_variance > 5:
                analysis["optimizations"].append(
                    f"HIGH VARIANCE: {name} — risk count varies by {risk_variance} across iterations. "
                    f"Consider adding deterministic anchors to reduce AI output variability."
                )

    # Stage-level performance analysis
    stage_times = {}
    for iteration_results in all_results:
        for result in iteration_results:
            if result["status"] == "success" and "stage_metrics" in result:
                for sm in result["stage_metrics"]:
                    stage = sm["stage"]
                    if stage not in stage_times:
                        stage_times[stage] = []
                    stage_times[stage].append(sm["duration"])

    analysis["stage_performance"] = {}
    for stage, times in stage_times.items():
        analysis["stage_performance"][stage] = {
            "avg_seconds": round(sum(times) / len(times), 2),
            "max_seconds": round(max(times), 2),
            "min_seconds": round(min(times), 2),
            "pct_of_total": round(100 * (sum(times) / len(times)) / (analysis["performance"].get("overall", {}).get("avg_time", 1)), 1),
        }

    # Optimization recommendations
    if stage_times:
        slowest_stage = max(stage_times.keys(), key=lambda s: sum(stage_times[s]) / len(stage_times[s]))
        analysis["optimizations"].append(
            f"BOTTLENECK: '{slowest_stage}' is the slowest stage, averaging "
            f"{sum(stage_times[slowest_stage]) / len(stage_times[slowest_stage]):.1f}s. "
            f"Consider optimizing this stage first."
        )

    # Check for missing fixes
    for name, data in analysis["contracts"].items():
        successful = [r for r in data["runs"] if r["status"] == "success"]
        if successful:
            latest = successful[-1]
            no_fix = [f for f in latest.get("findings", []) if not f["has_fix"] and f["level"] in ("RED", "YELLOW")]
            if no_fix:
                analysis["optimizations"].append(
                    f"MISSING FIXES: {name} has {len(no_fix)} RED/YELLOW findings without suggested fixes: "
                    + ", ".join(f["rule"] for f in no_fix[:3])
                )

    # Check for low-confidence findings
    for name, data in analysis["contracts"].items():
        successful = [r for r in data["runs"] if r["status"] == "success"]
        if successful:
            latest = successful[-1]
            low_conf = [f for f in latest.get("findings", []) if f.get("confidence") and f["confidence"] < 0.5]
            if low_conf:
                analysis["optimizations"].append(
                    f"LOW CONFIDENCE: {name} has {len(low_conf)} findings with confidence < 0.5: "
                    + ", ".join(f"{f['rule']} ({f['confidence']:.2f})" for f in low_conf[:3])
                )

    return analysis


def print_report(analysis: Dict[str, Any]):
    """Print the full analysis report."""
    print("\n" + "=" * 100)
    print("OVERNIGHT E2E TEST REPORT — CONTRARED UNIFIED PIPELINE")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 100)

    # Summary table
    perf = analysis.get("performance", {})
    overall = perf.get("overall", {})
    print(f"\nTotal iterations: {analysis['total_iterations']}")
    print(f"Total analyses: {analysis['total_analyses']}")
    if overall:
        print(f"Average analysis time: {overall['avg_time']:.1f}s")
        print(f"Average tokens per analysis: {overall['avg_tokens']}")

    # Per-contract performance
    print(f"\n{'─'*100}")
    print("PER-CONTRACT PERFORMANCE")
    print(f"{'─'*100}")
    print(f"| {'Contract':<40} | {'Words':>7} | {'Avg Time':>8} | {'Tokens':>6} | {'Chars/s':>7} | {'Success':>7} |")
    print(f"|{'-'*42}|{'-'*9}|{'-'*10}|{'-'*8}|{'-'*9}|{'-'*9}|")
    for name, p in perf.items():
        if name == "overall":
            continue
        c = analysis["contracts"].get(name, {})
        print(f"| {name:<40} | {c.get('word_count', 0):>7,} | {p['avg_time']:>6.1f}s | {p['avg_tokens']:>6} | {p['chars_per_second']:>7.0f} | {p['success_rate']:>7} |")

    # Quality / consistency
    quality = analysis.get("quality", {})
    if quality:
        print(f"\n{'─'*100}")
        print("RESULT CONSISTENCY (across iterations)")
        print(f"{'─'*100}")
        for name, q in quality.items():
            status = "STABLE" if q["consistent"] else "VARIABLE"
            print(f"  {name}: Total risks {q['risk_count_range']}, RED {q['red_count_range']} — {status}")

    # Stage performance
    stages = analysis.get("stage_performance", {})
    if stages:
        print(f"\n{'─'*100}")
        print("PIPELINE STAGE PERFORMANCE")
        print(f"{'─'*100}")
        print(f"| {'Stage':<25} | {'Avg':>6} | {'Min':>6} | {'Max':>6} | {'% Total':>7} |")
        print(f"|{'-'*27}|{'-'*8}|{'-'*8}|{'-'*8}|{'-'*9}|")
        for stage, s in sorted(stages.items(), key=lambda x: -x[1]["avg_seconds"]):
            print(f"| {stage:<25} | {s['avg_seconds']:>5.1f}s | {s['min_seconds']:>5.1f}s | {s['max_seconds']:>5.1f}s | {s['pct_of_total']:>6.1f}% |")

    # Detailed findings from latest run
    print(f"\n{'─'*100}")
    print("DETAILED FINDINGS (latest iteration)")
    print(f"{'─'*100}")
    for name, data in analysis["contracts"].items():
        successful = [r for r in data["runs"] if r["status"] == "success"]
        if not successful:
            continue
        latest = successful[-1]
        print(f"\n--- {name} ({latest['total_risks']} risks: {latest['red']}R/{latest['yellow']}Y/{latest['green']}G) ---")
        if latest.get("summaries"):
            for s in latest["summaries"]:
                print(f"  Summary: {s}")
        print()
        for f in latest.get("findings", []):
            fix_mark = "FIX" if f["has_fix"] else "NO-FIX"
            print(f"  [{f['level']}] {f['rule']} | conf={f.get('confidence', 'N/A')} ({f.get('conf_level', '?')}) | {f['verification']} | {fix_mark}")
            print(f"        {f['clause_preview']}")

    # Optimizations
    opts = analysis.get("optimizations", [])
    if opts:
        print(f"\n{'─'*100}")
        print("OPTIMIZATION RECOMMENDATIONS")
        print(f"{'─'*100}")
        for i, opt in enumerate(opts, 1):
            print(f"  {i}. {opt}")

    print(f"\n{'='*100}")
    print("END OF REPORT")
    print(f"{'='*100}")


async def main():
    """Main overnight runner — runs for ~8 hours."""
    logger.info("Starting overnight E2E test runner")
    logger.info(f"Start time: {datetime.now().isoformat()}")

    # Generate contracts
    contracts = get_contracts()
    logger.info(f"Generated {len(contracts)} contracts")

    max_duration_hours = 8
    max_iterations = 3  # Reduced from 10 to stay within free-tier quota
    start_time = time.monotonic()
    all_results = []

    for iteration in range(1, max_iterations + 1):
        elapsed_hours = (time.monotonic() - start_time) / 3600
        if elapsed_hours >= max_duration_hours:
            logger.info(f"Time limit reached ({elapsed_hours:.1f}h). Stopping after {iteration - 1} iterations.")
            break

        results = await run_iteration(contracts, iteration)
        all_results.append(results)

        # Save intermediate results
        with open("overnight_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Iteration {iteration} complete. "
                    f"Elapsed: {elapsed_hours:.1f}h / {max_duration_hours}h. "
                    f"Remaining iterations: {max_iterations - iteration}")

    # Final analysis
    total_elapsed = (time.monotonic() - start_time) / 3600
    logger.info(f"\nAll iterations complete. Total time: {total_elapsed:.1f} hours")

    analysis = analyze_results(all_results)

    # Save analysis
    with open("overnight_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    # Print report
    print_report(analysis)

    logger.info("Results saved to overnight_results.json and overnight_analysis.json")
    logger.info(f"End time: {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
