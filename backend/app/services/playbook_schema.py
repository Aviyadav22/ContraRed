"""
Playbook Schema Validation - Pydantic models for playbook rule validation.

Used at startup (optional) and during playbook CRUD operations to validate
that playbook rules conform to the expected schema.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class PlaybookRuleSchema(BaseModel):
    """Validation schema for a single playbook rule."""

    clause_type: str = Field(..., min_length=1, max_length=200)
    primary_position: str = Field(..., min_length=1)
    fallback_position: Optional[str] = None
    risk_level: str = Field(default="YELLOW")
    is_deal_breaker: bool = False
    detection_patterns: Optional[dict] = None
    suggested_language: Optional[dict] = None
    requires_ai_verification: bool = True
    verification_prompt: Optional[str] = None
    risk_description: Optional[str] = None
    acceptable_position: Optional[str] = None

    @field_validator("clause_type")
    @classmethod
    def normalize_clause_type(cls, v: str) -> str:
        return v.strip()

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        allowed = {"RED", "YELLOW", "GREEN", "red", "yellow", "green"}
        if v not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}, got '{v}'")
        return v.upper()


def check_playbook_completeness(rules: List[dict]) -> List[str]:
    """Check playbook rules for missing optional fields and return warnings."""
    warnings = []
    for i, rule in enumerate(rules):
        name = rule.get("name") or rule.get("clause_type") or f"rule[{i}]"
        if not rule.get("fallback_position"):
            warnings.append(f"{name}: missing fallback_position")
        if not rule.get("risk_description"):
            warnings.append(f"{name}: missing risk_description")
    return warnings


def validate_risk_score(score: float) -> float:
    """Clamp risk_score to 0-100 range."""
    return max(0.0, min(100.0, float(score)))
