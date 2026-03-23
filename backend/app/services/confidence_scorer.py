"""
Confidence Scorer - Multi-factor confidence scoring for every redline.

Computes a weighted confidence score from 5 factors:
  - Text verification (30%) : Did the quote match the contract? (from HallucinationGuard)
  - Rule corroboration (25%): Did both regex AND AI flag the same issue?
  - Playbook alignment (20%): How specific was the playbook rule that triggered this?
  - Model confidence (15%) : AI's self-reported certainty
  - Cross-references (10%) : Do other redlines corroborate this one?

Returns: score (0-1), level (HIGH/MEDIUM/LOW), breakdown dict.
  HIGH   = >= 0.75  (auto-show in UI)
  MEDIUM = 0.50-0.74 (show with verification badge)
  LOW    = < 0.50   (collapsed by default)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level thresholds."""
    HIGH = "HIGH"       # >= 0.75
    MEDIUM = "MEDIUM"   # 0.50 - 0.74
    LOW = "LOW"         # < 0.50


# ---- Weight configuration ----
DEFAULT_WEIGHTS = {
    "text_verification": 0.30,
    "rule_corroboration": 0.25,
    "playbook_alignment": 0.20,
    "model_confidence": 0.15,
    "cross_references": 0.10,
}


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of how the confidence score was computed."""
    text_verification: float = 0.0      # 0-1 from hallucination guard
    rule_corroboration: float = 0.0     # 0-1 regex+AI agreement
    playbook_alignment: float = 0.0     # 0-1 playbook rule specificity
    model_confidence: float = 0.0       # 0-1 AI self-reported
    cross_references: float = 0.0       # 0-1 corroboration from other redlines

    def to_dict(self) -> Dict[str, float]:
        return {
            "text_verification": round(self.text_verification, 3),
            "rule_corroboration": round(self.rule_corroboration, 3),
            "playbook_alignment": round(self.playbook_alignment, 3),
            "model_confidence": round(self.model_confidence, 3),
            "cross_references": round(self.cross_references, 3),
        }


@dataclass
class ConfidenceScore:
    """Final confidence score for a single redline."""
    score: float                         # Weighted 0-1
    level: ConfidenceLevel               # HIGH / MEDIUM / LOW
    breakdown: ConfidenceBreakdown        # Per-factor scores

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "level": self.level.value,
            "breakdown": self.breakdown.to_dict(),
        }


def _level_from_score(score: float) -> ConfidenceLevel:
    if score >= 0.75:
        return ConfidenceLevel.HIGH
    if score >= 0.50:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


class ConfidenceScorer:
    """
    Compute multi-factor confidence scores for AI-generated redlines.

    Usage::

        scorer = ConfidenceScorer()
        score = scorer.score_redline(
            text_verification_confidence=0.99,
            regex_matched=True,
            ai_flagged=True,
            playbook_rule=some_rule_dict,
            model_confidence=0.85,
            related_rule_names=["Unlimited Liability"],
            all_flagged_rules=["Unlimited Liability", "Broad Indemnification"],
        )
        print(score.level)  # HIGH
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        # Sanity: weights must sum to ~1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning("Confidence weights sum to %.3f (expected 1.0), normalizing.", total)
            self.weights = {k: v / total for k, v in self.weights.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_redline(
        self,
        text_verification_confidence: float = 0.0,
        regex_matched: bool = False,
        ai_flagged: bool = True,
        playbook_rule: Optional[Dict[str, Any]] = None,
        model_confidence: Optional[float] = None,
        related_rule_names: Optional[List[str]] = None,
        all_flagged_rules: Optional[List[str]] = None,
    ) -> ConfidenceScore:
        """
        Score a single redline across all 5 factors.

        Args:
            text_verification_confidence: 0-1 from HallucinationGuard.
            regex_matched: Whether the rule engine also flagged this text.
            ai_flagged: Whether AI flagged this (True for all AI redlines).
            playbook_rule: The playbook rule dict that triggered this.
            model_confidence: AI's self-reported confidence (0-1), if available.
            related_rule_names: Rule names that this redline is related to.
            all_flagged_rules: All rule names flagged in the document.

        Returns:
            ConfidenceScore with weighted score, level, and breakdown.
        """
        breakdown = ConfidenceBreakdown()

        # Factor 1: Text Verification (30%)
        breakdown.text_verification = self._score_text_verification(
            text_verification_confidence
        )

        # Factor 2: Rule Corroboration (25%)
        breakdown.rule_corroboration = self._score_rule_corroboration(
            regex_matched, ai_flagged
        )

        # Factor 3: Playbook Alignment (20%)
        breakdown.playbook_alignment = self._score_playbook_alignment(playbook_rule)

        # Factor 4: Model Confidence (15%)
        breakdown.model_confidence = self._score_model_confidence(model_confidence)

        # Factor 5: Cross-References (10%)
        breakdown.cross_references = self._score_cross_references(
            related_rule_names or [], all_flagged_rules or []
        )

        # Weighted sum
        weighted_score = (
            self.weights["text_verification"] * breakdown.text_verification
            + self.weights["rule_corroboration"] * breakdown.rule_corroboration
            + self.weights["playbook_alignment"] * breakdown.playbook_alignment
            + self.weights["model_confidence"] * breakdown.model_confidence
            + self.weights["cross_references"] * breakdown.cross_references
        )

        # Clamp to [0, 1]
        weighted_score = max(0.0, min(1.0, weighted_score))
        level = _level_from_score(weighted_score)

        return ConfidenceScore(
            score=weighted_score,
            level=level,
            breakdown=breakdown,
        )

    def score_batch(
        self,
        redlines: List[Dict[str, Any]],
        all_flagged_rules: Optional[List[str]] = None,
    ) -> List[ConfidenceScore]:
        """
        Score a batch of redlines.

        Each dict in `redlines` should have keys matching score_redline() args:
          - text_verification_confidence (float)
          - regex_matched (bool)
          - ai_flagged (bool)
          - playbook_rule (dict or None)
          - model_confidence (float or None)
          - related_rule_names (list of str)

        Args:
            redlines: List of dicts with scoring inputs.
            all_flagged_rules: Collected rule names from all redlines.

        Returns:
            List of ConfidenceScore in same order.
        """
        if all_flagged_rules is None:
            all_flagged_rules = []
            for r in redlines:
                names = r.get("related_rule_names") or []
                all_flagged_rules.extend(names)

        return [
            self.score_redline(
                text_verification_confidence=r.get("text_verification_confidence", 0.0),
                regex_matched=r.get("regex_matched", False),
                ai_flagged=r.get("ai_flagged", True),
                playbook_rule=r.get("playbook_rule"),
                model_confidence=r.get("model_confidence"),
                related_rule_names=r.get("related_rule_names"),
                all_flagged_rules=all_flagged_rules,
            )
            for r in redlines
        ]

    # ------------------------------------------------------------------
    # Factor scorers (each returns 0.0 - 1.0)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_text_verification(verification_confidence: float) -> float:
        """
        Factor 1: Text Verification (30%).

        Direct pass-through of HallucinationGuard confidence.
        1.0 = exact match, 0.99 = normalized, 0.7-0.95 = fuzzy, 0.0 = rejected.
        """
        return max(0.0, min(1.0, verification_confidence))

    @staticmethod
    def _score_rule_corroboration(regex_matched: bool, ai_flagged: bool) -> float:
        """
        Factor 2: Rule Corroboration (25%).

        Both regex AND AI agree -> 1.0
        Only AI flagged -> 0.7 (AI-only findings should not be penalized heavily)
        Only regex matched -> 0.5 (pattern exists, AI didn't flag = maybe benign)
        Neither -> 0.0
        """
        if regex_matched and ai_flagged:
            return 1.0
        if ai_flagged and not regex_matched:
            return 0.7  # AI-only findings should not be penalized heavily
        if regex_matched and not ai_flagged:
            return 0.5  # regex without AI confirmation should be suspicious
        return 0.0

    @staticmethod
    def _score_playbook_alignment(playbook_rule: Optional[Dict[str, Any]]) -> float:
        """
        Factor 3: Playbook Alignment (20%).

        Score based on how specific and complete the playbook rule is:
        - Has primary_position + is_deal_breaker + verification_prompt -> 1.0
        - Has primary_position + fallback_position -> 0.8
        - Has primary_position only -> 0.6
        - Generic / no rule -> 0.3
        """
        if playbook_rule is None:
            return 0.3  # No playbook rule -> generic AI finding

        score = 0.3  # Baseline for having any rule

        primary = playbook_rule.get("primary_position") or playbook_rule.get("description")
        if primary and len(str(primary)) > 10:
            score += 0.3  # Specific primary position

        fallback = playbook_rule.get("fallback_position")
        if fallback and len(str(fallback)) > 10:
            score += 0.15

        if playbook_rule.get("is_deal_breaker"):
            score += 0.1

        verification = playbook_rule.get("verification_prompt")
        if verification and len(str(verification)) > 10:
            score += 0.15

        return min(1.0, score)

    @staticmethod
    def _score_model_confidence(model_confidence: Optional[float]) -> float:
        """
        Factor 4: Model Confidence (15%).

        AI's self-reported certainty. If not provided, assume moderate confidence.
        """
        if model_confidence is None:
            return 0.4  # Conservative default when AI doesn't report confidence
        return max(0.0, min(1.0, model_confidence))

    @staticmethod
    def _score_cross_references(
        related_rule_names: List[str],
        all_flagged_rules: List[str],
    ) -> float:
        """
        Factor 5: Cross-References (10%).

        Score based on whether other flagged rules corroborate this one.
        E.g., "Unlimited Liability" + "Broad Indemnification" together
        is more credible than either alone.

        Corroboration pairs (related clause types):
        """
        if not related_rule_names or not all_flagged_rules:
            return 0.3  # Baseline

        CORROBORATION_MAP = {
            "Unlimited Liability": ["Broad Indemnification", "Unilateral Termination"],
            "Broad Indemnification": ["Unlimited Liability", "Broad IP Assignment"],
            "Unilateral Termination": ["Unlimited Liability", "Auto-Renewal"],
            "Broad IP Assignment": ["Broad Indemnification", "Non-Compete Clause"],
            "Auto-Renewal": ["Unilateral Termination", "Assignment Restriction"],
            "Non-Compete Clause": ["Non-Solicitation Clause", "Exclusive Dealing"],
            "Non-Solicitation Clause": ["Non-Compete Clause"],
            "Exclusive Dealing": ["Non-Compete Clause", "Assignment Restriction"],
            "Perpetual Confidentiality": ["Non-Solicitation Clause"],
        }

        score = 0.3  # Baseline

        for rule_name in related_rule_names:
            corroborators = CORROBORATION_MAP.get(rule_name, [])
            for corroborator in corroborators:
                if corroborator in all_flagged_rules:
                    score += 0.25
                    break  # One corroboration per rule is enough

        return min(1.0, score)
