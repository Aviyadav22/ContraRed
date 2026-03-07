"""NDA Mutual — Default playbook for mutual non-disclosure agreements."""
import uuid

def _r(clause_type, primary, risk, patterns, fallback=None, deal_breaker=False, ai_verify=True, prompt=None, order=0):
    sl = {"preferred": primary}
    if fallback:
        sl["fallback"] = fallback
    return {
        "id": str(uuid.uuid4()),
        "clause_type": clause_type,
        "primary_position": primary,
        "fallback_position": fallback,
        "risk_level": risk,
        "is_deal_breaker": deal_breaker,
        "detection_patterns": {"match_type": "regex", "patterns": patterns},
        "suggested_language": sl,
        "requires_ai_verification": ai_verify,
        "verification_prompt": prompt,
        "order_index": order,
    }

NDA_MUTUAL = {
    "name": "NDA — Mutual",
    "description": "Default playbook for mutual non-disclosure agreements. Covers confidentiality scope, term, permitted disclosures, return of information, remedies, and jurisdiction under Indian law.",
    "category": "NDA",
    "rules": [
        _r(
            clause_type="definition_of_confidential_information",
            primary="Confidential Information should be clearly defined with specific categories and reasonable exclusions (publicly available info, independently developed, received from third party without restriction).",
            risk="yellow",
            patterns=[
                r"(?i)\b(confidential\s+information)\s+(shall\s+)?(mean|include|encompass)",
                r"(?i)\bany\s+and\s+all\s+information\b",
                r"(?i)\b(all\s+information\s+(disclosed|shared|provided))\b",
                r"(?i)\b(proprietary\s+(information|data|material))\b",
            ],
            fallback="Confidential Information means information clearly marked as confidential or that a reasonable person would understand to be confidential, excluding: (a) publicly available information; (b) information already known to the Receiving Party; (c) independently developed information; (d) information received from a third party without restriction.",
            ai_verify=True,
            prompt="Check if the definition of Confidential Information is overly broad (e.g., 'any and all information') without reasonable exclusions. Flag if standard carve-outs are missing.",
            order=0,
        ),
        _r(
            clause_type="confidentiality_term",
            primary="Confidentiality obligations should be limited to 3-5 years from the date of disclosure, not perpetual.",
            risk="yellow",
            patterns=[
                r"(?i)\b(perpetual|indefinite|unlimited)\s+(confidentiality|obligation|period)\b",
                r"(?i)\b(survive|surviving)\s+(indefinitely|in\s+perpetuity|forever)\b",
                r"(?i)\b(confidential(ity)?\s+(in\s+)?perpetuity)\b",
                r"(?i)\bno\s+(time|temporal)\s+limit\b",
            ],
            fallback="The confidentiality obligations under this Agreement shall survive for a period of three (3) years from the date of disclosure of the relevant Confidential Information.",
            ai_verify=True,
            prompt="Check if the confidentiality term is perpetual or unreasonably long (>5 years). Acceptable range is 2-5 years.",
            order=1,
        ),
        _r(
            clause_type="permitted_disclosures",
            primary="NDA must include exceptions for legally compelled disclosures (court orders, regulatory requirements, tax authorities).",
            risk="yellow",
            patterns=[
                r"(?i)\bshall\s+not\s+disclose\b(?!.{0,200}(except|unless|provided\s+that|save\s+and\s+except))",
                r"(?i)\bno\s+(exception|carve.?out|exclusion)\b",
                r"(?i)\b(absolute|unconditional)\s+(prohibition|restriction)\s+on\s+disclosure\b",
            ],
            fallback="The Receiving Party may disclose Confidential Information: (a) to its employees, advisors, and affiliates on a need-to-know basis; (b) as required by applicable law, regulation, or court order, provided the Receiving Party gives prompt written notice to the Disclosing Party and cooperates in seeking a protective order.",
            ai_verify=True,
            prompt="Check if the NDA allows disclosure when legally required (court order, regulatory mandate). Flag if no permitted disclosure exceptions exist.",
            order=2,
        ),
        _r(
            clause_type="return_of_information",
            primary="Upon termination or request, receiving party must return or destroy all confidential information and certify destruction in writing.",
            risk="yellow",
            patterns=[
                r"(?i)\b(return|destruction|destroy)\s+(of\s+)?(confidential|proprietary)\s+(information|material|document)",
                r"(?i)\bupon\s+(termination|expir|request).{0,80}(return|destroy|delete)\b",
                r"(?i)\b(certif(y|ication)\s+of\s+(destruction|deletion))\b",
            ],
            fallback="Upon termination of this Agreement or upon written request, the Receiving Party shall promptly return or destroy all Confidential Information and provide written certification of destruction within fifteen (15) business days.",
            ai_verify=True,
            prompt="Check if there is a return/destruction clause. Flag if missing entirely. Note: it is acceptable to allow retention of archival copies required by law.",
            order=3,
        ),
        _r(
            clause_type="non_solicitation_in_nda",
            primary="Non-solicitation clauses should be limited to 12 months if included in an NDA. Prefer no non-solicitation in a simple NDA.",
            risk="yellow",
            patterns=[
                r"(?i)\b(non[\s-]?solicit(ation)?)\b",
                r"(?i)\bshall\s+not\s+(solicit|hire|recruit)\b",
                r"(?i)\b(solicit|entice|induce).{0,60}(employee|personnel|staff|contractor)\b",
            ],
            fallback="Neither Party shall, during the term of this Agreement and for a period of twelve (12) months thereafter, directly solicit for employment any employee of the other Party who was involved in the exchange of Confidential Information.",
            ai_verify=True,
            prompt="Check if non-solicitation is included in this NDA. Flag if duration exceeds 12 months or scope is unreasonable.",
            order=4,
        ),
        _r(
            clause_type="remedies_injunctive_relief",
            primary="Remedies clause should be mutual — both parties entitled to injunctive relief for breach.",
            risk="green",
            patterns=[
                r"(?i)\b(injunctive\s+relief)\b",
                r"(?i)\b(specific\s+performance)\b",
                r"(?i)\b(irreparable\s+(harm|damage|injury))\b",
                r"(?i)\b(equitable\s+remed(y|ies))\b",
            ],
            fallback="Each Party acknowledges that any breach of this Agreement may cause irreparable harm for which monetary damages would be inadequate, and agrees that the non-breaching Party shall be entitled to seek injunctive relief in addition to any other remedies available at law or in equity.",
            ai_verify=True,
            prompt="Check if remedies/injunctive relief is available to both parties (mutual) or only one party (one-sided). Flag if one-sided.",
            order=5,
        ),
        _r(
            clause_type="governing_law_jurisdiction",
            primary="Governing law should be Indian law with jurisdiction in a convenient Indian city (Delhi, Mumbai, Bangalore).",
            risk="green",
            patterns=[
                r"(?i)\b(govern(ed|ing)\s+(by|law))\b",
                r"(?i)\b(laws\s+of\s+(the\s+)?(state|country|republic)\s+of\s+india)\b",
                r"(?i)\b(jurisdiction\s+of\s+(the\s+)?(courts?\s+)(at|in|of))\b",
                r"(?i)\b(applicable\s+law)\b",
            ],
            fallback="This Agreement shall be governed by and construed in accordance with the laws of India. The courts at [City], India shall have exclusive jurisdiction over any disputes arising under this Agreement.",
            ai_verify=True,
            prompt="Check if governing law is Indian law. Flag if a foreign jurisdiction is specified. Note the jurisdiction city.",
            order=6,
        ),
    ],
}
