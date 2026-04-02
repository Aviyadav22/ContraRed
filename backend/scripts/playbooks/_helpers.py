"""Shared helper for building playbook rule dicts."""
import uuid


def _r(clause_type, primary, risk, patterns, fallback=None, deal_breaker=False,
       ai_verify=True, prompt=None, order=0,
       detection_mode="ai_with_keywords", risk_description=None,
       acceptable_position=None, unacceptable_signals=None,
       acceptable_signals=None, clause_context=None):
    """Build a playbook rule dict for seeding."""
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
        "detection_mode": detection_mode,
        "risk_description": risk_description,
        "acceptable_position": acceptable_position,
        "unacceptable_signals": unacceptable_signals or [],
        "acceptable_signals": acceptable_signals or [],
        "clause_context": clause_context,
    }
