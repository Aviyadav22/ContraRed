"""NDA Unilateral — Default playbook for one-way non-disclosure agreements."""
import uuid

def _r(clause_type, primary, risk, patterns, fallback=None, deal_breaker=False,
       ai_verify=True, prompt=None, order=0,
       detection_mode="keywords_only", risk_description=None,
       acceptable_position=None, unacceptable_signals=None,
       acceptable_signals=None, clause_context=None):
    sl = {"preferred": primary}
    if fallback:
        sl["fallback"] = fallback
    d = {
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
    d["detection_mode"] = detection_mode
    d["risk_description"] = risk_description
    d["acceptable_position"] = acceptable_position
    d["unacceptable_signals"] = unacceptable_signals or []
    d["acceptable_signals"] = acceptable_signals or []
    d["clause_context"] = clause_context
    return d

NDA_UNILATERAL = {
    "name": "NDA — Unilateral",
    "description": "Default playbook for one-way NDAs where only one party discloses confidential information. Includes all mutual NDA rules plus checks for overreach (non-compete, IP assignment, reverse engineering).",
    "category": "NDA",
    "rules": [
        # Inherit core NDA rules
        _r(
            clause_type="definition_of_confidential_information",
            primary="Confidential Information should be clearly defined with specific categories and reasonable exclusions.",
            risk="yellow",
            patterns=[
                r"(?i)\b(confidential\s+information)\s+(shall\s+)?(mean|include|encompass)",
                r"(?i)\bany\s+and\s+all\s+information\b",
                r"(?i)\b(proprietary\s+(information|data|material))\b",
            ],
            fallback="Confidential Information means information clearly marked as confidential or that a reasonable person would understand to be confidential, excluding publicly available information, independently developed information, and information received from a third party without restriction.",
            prompt="Check if the definition is overly broad without standard exclusions.",
            order=0,
        ),
        _r(
            clause_type="confidentiality_term",
            primary="Confidentiality obligations should be limited to 3-5 years, not perpetual.",
            risk="yellow",
            patterns=[
                r"(?i)\b(perpetual|indefinite|unlimited)\s+(confidentiality|obligation)\b",
                r"(?i)\b(survive|surviving)\s+(indefinitely|in\s+perpetuity|forever)\b",
            ],
            fallback="Confidentiality obligations shall survive for three (3) years from the date of disclosure.",
            prompt="Check if term is perpetual or exceeds 5 years.",
            order=1,
        ),
        _r(
            clause_type="permitted_disclosures",
            primary="Must include exceptions for legally compelled disclosures.",
            risk="yellow",
            patterns=[
                r"(?i)\bshall\s+not\s+disclose\b(?!.{0,200}(except|unless|provided\s+that))",
                r"(?i)\b(absolute|unconditional)\s+(prohibition|restriction)\s+on\s+disclosure\b",
            ],
            fallback="The Receiving Party may disclose Confidential Information as required by law, regulation, or court order, provided it gives prompt written notice and cooperates in seeking a protective order.",
            prompt="Check if legally compelled disclosure exceptions exist.",
            order=2,
        ),
        _r(
            clause_type="return_of_information",
            primary="Receiving party must return or destroy all confidential information upon termination.",
            risk="yellow",
            patterns=[
                r"(?i)\b(return|destruction|destroy)\s+(of\s+)?(confidential|proprietary)\s+(information|material)",
                r"(?i)\bupon\s+(termination|expir|request).{0,80}(return|destroy|delete)\b",
            ],
            fallback="Upon termination or request, the Receiving Party shall return or destroy all Confidential Information and certify destruction in writing within fifteen (15) business days.",
            prompt="Check if return/destruction clause exists. Flag if missing.",
            order=3,
        ),
        # Unilateral-specific: overreach detection
        _r(
            clause_type="non_compete_in_nda",
            primary="Non-compete clauses should NOT be in a simple NDA. This is overreach. Non-competes are largely unenforceable in India under Section 27 of the Indian Contract Act, 1872.",
            risk="red",
            patterns=[
                r"(?i)\b(non[\s-]?compete)\b",
                r"(?i)\bshall\s+not\s+compete\b",
                r"(?i)\b(restriction\s+on\s+competition)\b",
                r"(?i)\b(refrain\s+from\s+compet(ing|ition))\b",
            ],
            deal_breaker=True,
            fallback="Remove non-compete clause entirely. Non-compete restrictions are inappropriate in an NDA and are largely unenforceable in India under Section 27 of the Indian Contract Act, 1872.",
            prompt="Check if a non-compete clause is embedded in this NDA. This is a deal-breaker — NDAs should not restrict competition.",
            order=4,
            detection_mode="ai_with_keywords",
            risk_description="Non-compete in a simple NDA is significant overreach",
            unacceptable_signals=["shall not compete", "non-compete"],
            acceptable_signals=["no non-compete clause present"],
            clause_context="Non-compete in an NDA is a red flag — suggests restricting competition not protecting information",
            acceptable_position="Remove non-compete entirely",
        ),
        _r(
            clause_type="ip_assignment_in_nda",
            primary="An NDA should NOT transfer or assign intellectual property rights. Any IP assignment language is overreach.",
            risk="red",
            patterns=[
                r"(?i)\b(assign(s|ment)?\s+(of\s+)?(all\s+)?(intellectual\s+property|IP))\b",
                r"(?i)\b(work(s)?\s+for\s+hire)\b",
                r"(?i)\b(all\s+(rights|IP|intellectual\s+property)\s+shall\s+(belong|vest)\s+(in|to|with))\b",
                r"(?i)\b(transfer\s+of\s+(all\s+)?IP\s+rights)\b",
            ],
            deal_breaker=True,
            fallback="Remove IP assignment clause entirely. An NDA should protect confidential information, not transfer intellectual property rights. Each party retains all IP rights in its own confidential information.",
            prompt="Check if IP assignment or transfer language exists in this NDA. This is a deal-breaker — NDAs should not transfer IP.",
            order=5,
            detection_mode="ai_with_keywords",
            risk_description="IP assignment in an NDA — should not transfer IP rights",
            unacceptable_signals=["assigns all intellectual property", "IP shall vest in", "transfer of IP rights"],
            acceptable_signals=["no IP assignment", "each party retains its own IP"],
            clause_context="IP assignment in an NDA is inappropriate",
            acceptable_position="Remove IP assignment; each party retains its own IP",
        ),
        _r(
            clause_type="reverse_engineering_prohibition",
            primary="Reverse engineering prohibition should be reasonable. Flag if overly broad or prevents interoperability.",
            risk="yellow",
            patterns=[
                r"(?i)\b(reverse\s+engineer(ing)?)\b",
                r"(?i)\b(decompil(e|ation)|disassembl(e|y))\b",
                r"(?i)\b(derive\s+source\s+code)\b",
            ],
            fallback="The Receiving Party shall not reverse engineer, decompile, or disassemble any software or technology disclosed as Confidential Information, except as permitted by applicable law for interoperability purposes.",
            prompt="Check if reverse engineering prohibition is present and whether it's overly broad or includes an interoperability exception.",
            order=6,
            detection_mode="ai_with_keywords",
            risk_description="Reverse engineering prohibition overly broad beyond disclosed information",
            unacceptable_signals=["shall not reverse engineer any product", "prohibition on all reverse engineering"],
            acceptable_signals=["limited to confidential information", "interoperability exception"],
            acceptable_position="Prohibition limited to disclosed materials; interoperability exception preserved",
        ),
        _r(
            clause_type="non_solicitation_in_nda",
            primary="Non-solicitation in NDA should be limited to 12 months maximum.",
            risk="yellow",
            patterns=[
                r"(?i)\b(non[\s-]?solicit(ation)?)\b",
                r"(?i)\bshall\s+not\s+(solicit|hire|recruit)\b",
            ],
            fallback="Neither Party shall solicit for employment any employee of the other Party involved in the exchange of Confidential Information for twelve (12) months following termination.",
            prompt="Check if non-solicitation duration exceeds 12 months.",
            order=7,
        ),
        _r(
            clause_type="governing_law_jurisdiction",
            primary="Governing law should be Indian law.",
            risk="green",
            patterns=[
                r"(?i)\b(govern(ed|ing)\s+(by|law))\b",
                r"(?i)\b(laws\s+of\s+(the\s+)?(state|country|republic)\s+of\s+india)\b",
                r"(?i)\b(jurisdiction\s+of\s+(the\s+)?(courts?\s+)(at|in|of))\b",
            ],
            fallback="This Agreement shall be governed by the laws of India. Courts at [City], India shall have exclusive jurisdiction.",
            prompt="Check if governing law is Indian law. Flag foreign jurisdiction.",
            order=8,
        ),
    ],
}
