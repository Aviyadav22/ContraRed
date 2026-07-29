"""
Multi-Stage Analysis Pipeline - 5-stage orchestrator for AI contract analysis.

Replaces the single-shot Gemini call with a structured pipeline:

  Stage 1: EXTRACTION     -> ContractMap + DefinedTerms + JurisdictionDetectionResult  (deterministic, no AI)
  Stage 2: CLASSIFICATION -> ClauseInventory via rule engine + Gemini Flash-Lite  (cheap + fast)
  Phase 6 wiring: tier swap + condition overrides + dependency effects applied between Stage 2 and 3
  Stage 3: RISK ASSESSMENT-> RawRedlines with confidence scores (Gemini Pro, high quality)
  Stage 4: VERIFICATION   -> VerifiedRedlines (hallucinations killed)  (deterministic, no AI)
  Stage 5: ENRICHMENT     -> FinalRedlines with cross-references (Gemini Flash-Lite per-redline)
  (Stage 6 removed in Phase B5: fix generation is now on-demand via /documents/generate-fix.)

Each stage is a separate async method.  The pipeline tracks timing and costs per stage.
Graceful degradation: if a stage fails, return partial results from completed stages.

This is a NEW orchestrator — it does NOT modify gemini_analyzer.py. It USES
GeminiAnalyzer internally for AI calls.
"""

import asyncio
import copy
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.gemini_analyzer import (
    AIAnalysisResult,
    AIServiceUnavailable,
    GeminiAnalyzer,
    gemini_analyzer,
    _sanitize_for_prompt,
)
from app.services.hallucination_guard import (
    HallucinationGuard,
    HallucinationStats,
)
from app.services.confidence_scorer import (
    ConfidenceBreakdown,
    ConfidenceLevel,
    ConfidenceScore,
    ConfidenceScorer,
)
from app.services.rule_engine import RuleEngine, RuleMatch
from app.services.structure_extractor import ContractMap, StructureExtractor
from app.services.scope_analyzer import scope_analyzer
from app.services.jurisdiction_detector import (
    apply_jurisdiction_overrides,
    jurisdiction_detector,
    JurisdictionDetectionResult,
)
from app.services.smriti_mcp_client import smriti_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for pipeline stages
# ---------------------------------------------------------------------------


@dataclass
class DefinedTerm:
    """A defined term extracted from the contract."""
    term: str
    definition: str
    section_index: int = 0


@dataclass
class ExtractionResult:
    """Stage 1 output."""
    contract_map: ContractMap
    defined_terms: List[DefinedTerm]
    jurisdiction_result: JurisdictionDetectionResult
    full_text: str


@dataclass
class ClauseInventoryItem:
    """A classified clause from stage 2."""
    clause_type: str
    text: str
    section_index: int
    risk_hint: str  # "RED", "YELLOW", "GREEN", "UNKNOWN"
    rule_match: Optional[RuleMatch] = None  # Set if regex also matched


@dataclass
class PipelineClassificationResult:
    """Stage 2 output."""
    clause_inventory: List[ClauseInventoryItem]
    rule_matches: List[RuleMatch]


@dataclass
class RawRedline:
    """Stage 3 output — a single redline before verification."""
    rule_name: str
    risk_level: str
    original_text: str
    explanation: str
    recommendation: str
    redline_type: str  # "violation" or "missing"
    is_deal_breaker: bool = False
    model_confidence: Optional[float] = None
    regex_matched: bool = False
    playbook_rule: Optional[Dict[str, Any]] = None
    clause_type: str = ""
    suggested_fix: Optional[str] = None
    rule_id: str = ""
    statutory_references: List[str] = field(default_factory=list)


@dataclass
class VerifiedRedline:
    """Stage 4 output — a redline after hallucination verification."""
    rule_name: str
    risk_level: str
    original_text: str
    verified_text: str  # May differ from original_text after correction
    explanation: str
    recommendation: str
    redline_type: str
    is_deal_breaker: bool
    verification_status: str  # "exact", "normalized", "fuzzy_corrected", "rejected"
    verification_confidence: float
    regex_matched: bool
    playbook_rule: Optional[Dict[str, Any]] = None
    model_confidence: Optional[float] = None
    clause_type: str = ""
    suggested_fix: Optional[str] = None
    rule_id: str = ""
    statutory_references: List[str] = field(default_factory=list)


@dataclass
class FinalRedline:
    """Stage 5 output — fully enriched redline."""
    rule_name: str
    risk_level: str
    original_text: str
    verified_text: str
    explanation: str
    recommendation: str
    redline_type: str
    is_deal_breaker: bool
    confidence: ConfidenceScore
    verification_status: str
    cross_references: List[str] = field(default_factory=list)
    clause_type: str = ""
    suggested_fix: Optional[str] = None
    fix_edits: List[Dict[str, str]] = field(default_factory=list)  # [{find, replace}]
    fix_reasoning: str = ""
    # Smriti MCP enrichment (optional — empty when Smriti unavailable)
    statutory_basis: Optional[Dict[str, Any]] = None
    case_law_context: List[Dict[str, Any]] = field(default_factory=list)
    rule_id: str = ""
    statutory_references: List[str] = field(default_factory=list)


@dataclass
class StageMetrics:
    """Timing and cost metrics for a single pipeline stage."""
    stage_name: str
    duration_seconds: float = 0.0
    tokens_used: int = 0
    items_processed: int = 0
    items_passed: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "stage": self.stage_name,
            "duration_seconds": round(self.duration_seconds, 3),
            "tokens_used": self.tokens_used,
            "items_processed": self.items_processed,
            "items_passed": self.items_passed,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class PipelineResult:
    """Complete pipeline output."""
    executive_summary: List[str]
    redlines: List[FinalRedline]
    hallucination_stats: Dict[str, Any]
    stage_metrics: List[StageMetrics]
    total_duration_seconds: float = 0.0
    total_tokens_used: int = 0
    partial: bool = False  # True if pipeline degraded gracefully
    # True only when the AI stages (risk assessment, enrichment) actually executed.
    # False means the pipeline fell back to rule-engine-only output — the user
    # needs to see a banner about it. Defaults to True; the pipeline flips this
    # to False when AIServiceUnavailable or a stage-3 exception forces fallback.
    ai_used: bool = True
    # Phase 5: Scope analysis and coverage report
    scope_analysis: Optional[Dict[str, Any]] = None
    coverage_report: Optional[Dict[str, Any]] = None
    jurisdiction_code: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    contract_type: Optional[str] = None  # Detected contract type (nda, saas, employment, msa, ma, general)
    review_perspective: Optional[str] = None
    playbook_coverage: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "executive_summary": self.executive_summary,
            "redlines": [
                {
                    "rule_name": r.rule_name,
                    "rule_id": r.rule_id,
                    "risk_level": r.risk_level,
                    "original_text": r.original_text,
                    "verified_text": r.verified_text,
                    "explanation": r.explanation,
                    "recommendation": r.recommendation,
                    "redline_type": r.redline_type,
                    "is_deal_breaker": r.is_deal_breaker,
                    "confidence": r.confidence.to_dict(),
                    "verification_status": r.verification_status,
                    "cross_references": r.cross_references,
                    "clause_type": r.clause_type,
                    "suggested_fix": r.suggested_fix,
                    "fix_edits": r.fix_edits,
                    "fix_reasoning": r.fix_reasoning,
                    "statutory_basis": r.statutory_basis,
                    "case_law_context": r.case_law_context,
                    "statutory_references": r.statutory_references,
                }
                for r in self.redlines
            ],
            "hallucination_stats": self.hallucination_stats,
            "stage_metrics": [m.to_dict() for m in self.stage_metrics],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "total_tokens_used": self.total_tokens_used,
            "partial": self.partial,
            "ai_used": self.ai_used,
        }
        if self.scope_analysis:
            d["scope_analysis"] = self.scope_analysis
        if self.coverage_report:
            d["coverage_report"] = self.coverage_report
        if self.jurisdiction_code:
            d["jurisdiction_code"] = self.jurisdiction_code
        if self.jurisdiction_name:
            d["jurisdiction_name"] = self.jurisdiction_name
        if self.contract_type:
            d["contract_type"] = self.contract_type
        if self.review_perspective:
            d["review_perspective"] = self.review_perspective
        if self.playbook_coverage:
            d["playbook_coverage"] = self.playbook_coverage
        return d


# ---------------------------------------------------------------------------
# Regex helpers for Stage 1 (deterministic extraction)
# ---------------------------------------------------------------------------

_DEFINED_TERM_PATTERNS = [
    # "Term" means ...
    re.compile(
        r'"([A-Z][A-Za-z\s]{2,40})"\s+(?:means?|shall\s+mean|refers?\s+to|includes?)\s+(.+?)(?:\.|;)',
        re.IGNORECASE,
    ),
    # 'Term' shall mean ...
    re.compile(
        r"'([A-Z][A-Za-z\s]{2,40})'\s+(?:means?|shall\s+mean)\s+(.+?)(?:\.|;)",
        re.IGNORECASE,
    ),
]

# Jurisdiction detection delegated to jurisdiction_detector.detect() (Phase B2);
# the prior _JURISDICTION_PATTERNS regexes were a parallel implementation.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_clause_type(rule_name: str) -> str:
    """Phase C1 — taxonomy-aware mapping. Wraps snap_to_clause_type so
    callers always get a value from the canonical ClauseType enum."""
    from app.services.clause_taxonomy import snap_to_clause_type
    raw = (rule_name or "").strip()
    snapped = snap_to_clause_type(raw).value
    if snapped != "unknown" or raw.lower() == "unknown":
        return snapped
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return (slug or "custom_rule")[:100]


# ---------------------------------------------------------------------------
# The Pipeline
# ---------------------------------------------------------------------------


class AnalysisPipeline:
    """
    5-stage analysis pipeline orchestrator.

    Usage::

        pipeline = AnalysisPipeline()
        result = await pipeline.run(
            contract_text="...",
            playbook_rules=[...],
            playbook_name="NDA Standard",
        )
        # result is a PipelineResult with verified, scored redlines
    """

    def __init__(
        self,
        analyzer: Optional[GeminiAnalyzer] = None,
        rule_engine: Optional[RuleEngine] = None,
    ):
        self._analyzer = analyzer or gemini_analyzer
        self._rule_engine = rule_engine or RuleEngine()
        self._scorer = ConfidenceScorer()
        self._scope_analyzer = scope_analyzer

    # ======================================================================
    # Main entry point
    # ======================================================================

    async def run(
        self,
        contract_text: str,
        playbook_rules: Optional[List[Dict[str, Any]]] = None,
        playbook_name: str = "Default",
        party_side: str = "neutral",
        org_context: str = "",
        jurisdiction_override: Optional[str] = None,
        deal_context: Optional[Any] = None,           # Phase C3 — DealContext (kept Any to avoid hard import)
        playbook_conditions: Optional[List[Any]] = None,  # Pre-loaded PlaybookCondition rows w/ rule_overrides
        playbook_dependencies: Optional[List[Any]] = None,  # Pre-loaded PlaybookRuleDependency rows
        rule_tiers_by_rule: Optional[Dict[str, Any]] = None,  # rule_id -> PlaybookRuleTier (selected tier)
        tier_preference: str = "ideal",
    ) -> PipelineResult:
        """
        Run the full 5-stage pipeline.

        Phase C3: ``deal_context`` and the pre-loaded Phase-6 rows let the
        pipeline apply conditional overrides, cross-rule dependencies, and
        negotiation-tier position swaps without owning a DB session. The
        endpoint is responsible for loading and passing them in.

        Graceful degradation: if any stage fails, returns partial results
        from completed stages with `partial=True`.
        """
        pipeline_start = time.monotonic()
        stage_metrics: List[StageMetrics] = []
        total_tokens = 0
        partial = False
        ai_used = True  # Flipped to False if Stage 3 (AI risk assessment) falls back
        executive_summary: List[str] = []
        final_redlines: List[FinalRedline] = []
        hallucination_stats: Dict[str, Any] = {}
        playbook_coverage: Optional[Dict[str, Any]] = None
        warnings: List[str] = []

        # ---- Pre-Stage: Input validation ----
        if not contract_text or len(contract_text.strip()) < 100:
            return PipelineResult(
                executive_summary=["Document is too short for meaningful analysis."],
                redlines=[],
                hallucination_stats={},
                stage_metrics=[],
                total_duration_seconds=time.monotonic() - pipeline_start,
                partial=True,
                ai_used=False,
            )

        # Check for non-English text
        if self._detect_non_english(contract_text):
            warnings.append("⚠️ This document appears to contain non-English text. Analysis accuracy may be reduced. ContraRed is optimized for English-language contracts.")

        # Check if document looks like a contract
        if not self._is_likely_contract(contract_text):
            warnings.append("⚠️ This document may not be a legal agreement. Analysis results should be reviewed with this in mind.")

        # Check if document looks like a partial/fragment
        if self._is_likely_fragment(contract_text):
            warnings.append("⚠️ This document appears to be a fragment or partial section. 'Missing clause' warnings may be inaccurate — clauses could exist in the full document.")

        # ---- Stage 1: EXTRACTION (deterministic, CPU-bound → thread pool) ----
        try:
            s1_start = time.monotonic()
            loop = asyncio.get_running_loop()
            extraction = await loop.run_in_executor(
                None, self._stage1_extraction, contract_text, jurisdiction_override
            )
            s1_metrics = StageMetrics(
                stage_name="extraction",
                duration_seconds=time.monotonic() - s1_start,
                items_processed=len(extraction.contract_map.nodes),
                items_passed=len(extraction.contract_map.nodes),
            )
            stage_metrics.append(s1_metrics)
        except Exception as e:
            logger.error("Pipeline Stage 1 (extraction) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="extraction", error=str(e)))
            return PipelineResult(
                executive_summary=["Analysis failed during document extraction."],
                redlines=[],
                hallucination_stats={},
                stage_metrics=stage_metrics,
                total_duration_seconds=time.monotonic() - pipeline_start,
                partial=True,
                ai_used=False,
            )

        # ---- Stage 2: CLASSIFICATION (rule engine, CPU-bound → thread pool) ----
        try:
            s2_start = time.monotonic()
            classification = await loop.run_in_executor(
                None, self._stage2_classification, extraction, playbook_rules
            )
            s2_metrics = StageMetrics(
                stage_name="classification",
                duration_seconds=time.monotonic() - s2_start,
                items_processed=len(classification.clause_inventory),
                items_passed=len(classification.rule_matches),
            )
            stage_metrics.append(s2_metrics)
        except Exception as e:
            logger.error("Pipeline Stage 2 (classification) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="classification", error=str(e)))
            partial = True
            classification = PipelineClassificationResult(clause_inventory=[], rule_matches=[])

        # ---- Phase 5: SCOPE ANALYSIS (deterministic, between Stage 2 and 3) ----
        scope_data: Optional[Dict[str, Any]] = None
        coverage_data: Optional[Dict[str, Any]] = None
        # Jurisdiction detection is a document-level fact and must not depend
        # on whether the regex engine happened to find a risky phrase.
        detected_jurisdiction: Optional[str] = (
            extraction.jurisdiction_result.detected_jurisdiction
        )
        try:
            if classification.rule_matches:
                # Run scope analysis on rule matches
                scope_result = self._scope_analyzer.analyze(
                    classification.rule_matches, contract_text
                )
                scope_data = {
                    "total_analyzed": scope_result.total_clauses_analyzed,
                    "coverage_score": scope_result.coverage_score,
                    "clause_types_found": scope_result.clause_types_found,
                    "clause_types_missing": scope_result.clause_types_missing,
                    "results": [
                        {
                            "rule_id": r.rule_id,
                            "clause_type": r.clause_type,
                            "breadth": r.breadth.value,
                            "mutuality": r.mutuality.value,
                            "financial_exposure": r.financial_exposure.value,
                            "cap_amount": r.cap_amount,
                            "duration": r.duration.value,
                            "trigger": r.trigger.value,
                            "scope_score": r.scope_score,
                            "risk_adjustment": r.risk_adjustment,
                            "notes": r.analysis_notes,
                        }
                        for r in scope_result.results
                    ],
                }
                coverage_data = self._scope_analyzer.get_coverage_report(
                    classification.rule_matches
                )

                # Apply jurisdiction overrides using the result from Stage 1 (B2)
                if detected_jurisdiction:
                    classification.rule_matches = apply_jurisdiction_overrides(
                        classification.rule_matches,
                        detected_jurisdiction,
                    )
        except Exception as e:
            logger.warning(
                "Scope analysis/jurisdiction overrides failed: %s",
                e,
                exc_info=True,
            )
            partial = True
            warnings.append(
                "Scope or jurisdiction-specific review could not be completed; "
                "treat this analysis as partial."
            )

        # ---- Phase 6 wiring (C3): conditions + dependencies + tier overrides ----
        # Operates between Stage 2 and Stage 3 so both the AI prompt and the
        # rule-engine fallback see the same overridden state.
        try:
            playbook_rules, classification.rule_matches = self._apply_phase6_wiring(
                playbook_rules=playbook_rules,
                rule_matches=classification.rule_matches,
                deal_context=deal_context,
                conditions=playbook_conditions,
                dependencies=playbook_dependencies,
                rule_tiers_by_rule=rule_tiers_by_rule,
                tier_preference=tier_preference,
            )
        except Exception as e:
            logger.error("Phase 6 wiring failed: %s", e, exc_info=True)
            if (
                playbook_conditions
                or playbook_dependencies
                or rule_tiers_by_rule
            ):
                raise RuntimeError(
                    "Playbook conditions, dependencies, or negotiation tiers "
                    "could not be applied; analysis was stopped to avoid using "
                    "the wrong legal position."
                ) from e
            partial = True
            warnings.append(
                "Advanced playbook logic could not be evaluated; treat this "
                "analysis as partial."
            )

        # ---- Pre-Stage 3: Contract type detection (deterministic) ----
        contract_type = self._detect_contract_type(contract_text)
        logger.info("Detected contract type: %s", contract_type)

        # ---- Stage 3: RISK ASSESSMENT (Gemini Pro, full AI analysis) ----
        raw_redlines: List[RawRedline] = []
        try:
            s3_start = time.monotonic()
            raw_redlines, ai_summary, s3_tokens, playbook_coverage = await self._stage3_risk_assessment(
                extraction, classification, playbook_rules, playbook_name,
                party_side, contract_type=contract_type, org_context=org_context,
            )
            executive_summary = ai_summary

            # Inject factual review context. Do not claim complete evaluation
            # unless the returned rule ledger actually proves it.
            from app.services.prompt_templates import CONTRACT_TYPE_LABELS
            type_label = CONTRACT_TYPE_LABELS.get(contract_type, contract_type)
            type_summary = (
                f"Document type: {type_label}. "
                f"Review perspective: {party_side}."
            )
            executive_summary.insert(0, type_summary)

            if playbook_coverage:
                assessed = playbook_coverage.get("assessed_rules", 0)
                total_rules = playbook_coverage.get("total_rules", 0)
                executive_summary.insert(
                    1,
                    f"Playbook coverage: {assessed} of {total_rules} selected rules received an explicit AI assessment.",
                )
                if not playbook_coverage.get("complete", True):
                    partial = True
                    unassessed = len(playbook_coverage.get("unassessed_rule_ids", []))
                    executive_summary.insert(
                        2,
                        f"Coverage warning: {unassessed} selected rule(s) require manual review.",
                    )

            total_tokens += s3_tokens
            s3_metrics = StageMetrics(
                stage_name="risk_assessment",
                duration_seconds=time.monotonic() - s3_start,
                tokens_used=s3_tokens,
                items_processed=len(raw_redlines),
                items_passed=len(raw_redlines),
            )
            stage_metrics.append(s3_metrics)
        except AIServiceUnavailable:
            logger.warning("AI service unavailable, falling back to rule-engine-only results")
            stage_metrics.append(StageMetrics(stage_name="risk_assessment", error="AI unavailable"))
            partial = True
            ai_used = False  # Rule-engine-only — frontend must show AI-down banner
            # Convert rule matches to raw redlines as fallback
            raw_redlines = self._rule_matches_to_raw_redlines(
                classification.rule_matches, playbook_rules
            )
            executive_summary = ["AI analysis unavailable. Results based on rule engine only."]
            if playbook_rules:
                playbook_coverage = self._build_playbook_coverage(playbook_rules, [])
        except Exception as e:
            logger.error("Pipeline Stage 3 (risk_assessment) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="risk_assessment", error=str(e)))
            partial = True
            ai_used = False  # Rule-engine-only — frontend must show AI-down banner
            raw_redlines = self._rule_matches_to_raw_redlines(
                classification.rule_matches, playbook_rules
            )
            executive_summary = ["AI analysis encountered an error. Results based on rule engine only."]
            if playbook_rules:
                playbook_coverage = self._build_playbook_coverage(playbook_rules, [])

        if not raw_redlines:
            return PipelineResult(
                executive_summary=warnings + (executive_summary or ["No issues found."]),
                redlines=[],
                hallucination_stats={},
                stage_metrics=stage_metrics,
                total_duration_seconds=time.monotonic() - pipeline_start,
                total_tokens_used=total_tokens,
                partial=partial,
                ai_used=ai_used,
                scope_analysis=scope_data,
                coverage_report=coverage_data,
                jurisdiction_code=detected_jurisdiction,
                jurisdiction_name=(
                    extraction.jurisdiction_result.profile.name
                    if extraction.jurisdiction_result.profile
                    else None
                ),
                contract_type=contract_type,
                review_perspective=party_side,
                playbook_coverage=playbook_coverage,
            )

        # ---- Stage 4: VERIFICATION (hallucination guard, CPU-bound → thread pool) ----
        verified_redlines: List[VerifiedRedline] = []
        try:
            s4_start = time.monotonic()
            verified_redlines, h_stats = await loop.run_in_executor(
                None, self._stage4_verification, extraction.full_text, raw_redlines
            )
            hallucination_stats = h_stats.to_dict()
            s4_metrics = StageMetrics(
                stage_name="verification",
                duration_seconds=time.monotonic() - s4_start,
                items_processed=h_stats.total_checked,
                items_passed=h_stats.total_checked - h_stats.rejected,
            )
            stage_metrics.append(s4_metrics)
        except Exception as e:
            logger.error("Pipeline Stage 4 (verification) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="verification", error=str(e)))
            partial = True
            # Pass through unverified
            verified_redlines = [
                VerifiedRedline(
                    rule_name=r.rule_name,
                    risk_level=r.risk_level,
                    original_text=r.original_text,
                    verified_text=r.original_text,
                    explanation=r.explanation,
                    recommendation=r.recommendation,
                    redline_type=r.redline_type,
                    is_deal_breaker=r.is_deal_breaker,
                    verification_status="unverified",
                    verification_confidence=0.2,  # Low confidence for completely unverified output
                    regex_matched=r.regex_matched,
                    playbook_rule=r.playbook_rule,
                    model_confidence=r.model_confidence,
                    clause_type=r.clause_type,
                    suggested_fix=r.suggested_fix,
                    rule_id=r.rule_id,
                    statutory_references=list(r.statutory_references),
                )
                for r in raw_redlines
            ]

        if playbook_coverage is not None:
            playbook_coverage = self._reconcile_playbook_coverage(
                playbook_coverage,
                raw_redlines,
                verified_redlines,
            )
            unresolved = playbook_coverage.get("unverified_finding_rule_ids", [])
            if unresolved:
                partial = True
                executive_summary.append(
                    "Verification warning: "
                    f"{len(unresolved)} playbook finding(s) could not be anchored "
                    "to verbatim contract text and require manual review."
                )

        # ---- Stage 5: ENRICHMENT (confidence scoring, CPU-bound → thread pool) ----
        try:
            s5_start = time.monotonic()
            final_redlines = await loop.run_in_executor(
                None, self._stage5_enrichment, verified_redlines
            )
            s5_metrics = StageMetrics(
                stage_name="enrichment",
                duration_seconds=time.monotonic() - s5_start,
                items_processed=len(verified_redlines),
                items_passed=len(final_redlines),
            )
            stage_metrics.append(s5_metrics)
        except Exception as e:
            logger.error("Pipeline Stage 5 (enrichment) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="enrichment", error=str(e)))
            partial = True
            # Fallback: convert verified to final without scoring
            final_redlines = [
                FinalRedline(
                    rule_name=v.rule_name,
                    risk_level=v.risk_level,
                    original_text=v.original_text,
                    verified_text=v.verified_text,
                    explanation=v.explanation,
                    recommendation=v.recommendation,
                    redline_type=v.redline_type,
                    is_deal_breaker=v.is_deal_breaker,
                    confidence=ConfidenceScore(
                        score=0.5,
                        level=ConfidenceLevel.MEDIUM,
                        breakdown=ConfidenceBreakdown(),
                    ),
                    verification_status=v.verification_status,
                    clause_type=v.clause_type,
                    suggested_fix=v.suggested_fix,
                    rule_id=v.rule_id,
                    statutory_references=list(v.statutory_references),
                )
                for v in verified_redlines
            ]

        # ---- Stage 5b: OFFSET-BASED DEDUP ----
        pre_dedup_count = len(final_redlines)
        final_redlines = self._dedupe_by_overlap(final_redlines, extraction.full_text)
        if pre_dedup_count > len(final_redlines):
            logger.info(
                "Offset-based dedup removed %d overlapping finding(s) (%d → %d)",
                pre_dedup_count - len(final_redlines),
                pre_dedup_count,
                len(final_redlines),
            )

        # ---- Stage 5c: SMRITI MCP ENRICHMENT (optional) ----
        if smriti_client.is_configured:
            try:
                s5c_start = time.monotonic()
                final_redlines = await self._stage5c_smriti_enrichment(
                    final_redlines, detected_jurisdiction
                )
                stage_metrics.append(StageMetrics(
                    stage_name="smriti_enrichment",
                    duration_seconds=time.monotonic() - s5c_start,
                    items_processed=len(final_redlines),
                    items_passed=sum(1 for r in final_redlines if r.statutory_basis or r.case_law_context),
                ))
            except Exception as e:
                logger.warning("Smriti enrichment failed (non-fatal): %s", e)
                stage_metrics.append(StageMetrics(stage_name="smriti_enrichment", error=str(e)))

        # Stage 6 (fix generation) was removed in Phase B5 — most users only apply
        # 2-3 fixes per scan, so batch-generating fixes for every redline wasted
        # 50-80% of fix-generation tokens. Fixes are now produced on demand by
        # POST /documents/generate-fix when the user clicks "Apply Fix".

        total_duration = time.monotonic() - pipeline_start

        # Prepend any warnings to executive summary
        if warnings:
            executive_summary = warnings + executive_summary

        return PipelineResult(
            executive_summary=executive_summary,
            redlines=final_redlines,
            hallucination_stats=hallucination_stats,
            stage_metrics=stage_metrics,
            total_duration_seconds=total_duration,
            total_tokens_used=total_tokens,
            partial=partial,
            ai_used=ai_used,
            scope_analysis=scope_data,
            coverage_report=coverage_data,
            jurisdiction_code=detected_jurisdiction,
            jurisdiction_name=(
                extraction.jurisdiction_result.profile.name
                if extraction.jurisdiction_result.profile
                else None
            ),
            contract_type=contract_type,
            review_perspective=party_side,
            playbook_coverage=playbook_coverage,
        )

    # ======================================================================
    # Stage 1: EXTRACTION (deterministic, no AI cost)
    # ======================================================================

    def _stage1_extraction(
        self,
        contract_text: str,
        jurisdiction_override: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract structure, defined terms, and jurisdiction. All deterministic
        — no AI cost. Jurisdiction is detected once here via the canonical
        jurisdiction_detector and reused by downstream stages (B2).
        """
        extractor = StructureExtractor()
        contract_map = extractor.extract_from_text(contract_text)

        defined_terms = self._extract_defined_terms(contract_text)
        jurisdiction_result = jurisdiction_detector.detect(
            contract_text, user_override=jurisdiction_override
        )

        return ExtractionResult(
            contract_map=contract_map,
            defined_terms=defined_terms,
            jurisdiction_result=jurisdiction_result,
            full_text=contract_text,
        )

    def _extract_defined_terms(self, text: str) -> List[DefinedTerm]:
        """Extract defined terms using regex patterns."""
        terms: List[DefinedTerm] = []
        seen_terms: set = set()

        for pattern in _DEFINED_TERM_PATTERNS:
            for match in pattern.finditer(text):
                term_name = match.group(1).strip()
                definition = match.group(2).strip()
                lower_term = term_name.lower()

                if lower_term not in seen_terms and len(term_name) > 2:
                    seen_terms.add(lower_term)
                    terms.append(DefinedTerm(
                        term=term_name,
                        definition=definition[:300],  # Truncate long definitions
                    ))

        return terms

    # ======================================================================
    # Stage 2: CLASSIFICATION (rule engine, deterministic)
    # ======================================================================

    def _stage2_classification(
        self,
        extraction: ExtractionResult,
        playbook_rules: Optional[List[Dict[str, Any]]],
    ) -> PipelineClassificationResult:
        """
        Classify clauses using both the baseline engine and the selected
        playbook's actual detection patterns.

        Playbook patterns used to be omitted from serialization and ignored by
        this stage, which meant a custom playbook affected only prompt prose.
        The selected playbook now takes precedence when it covers the same
        clause type and source region as a generic rule.
        """
        full_text = extraction.full_text
        default_matches = self._rule_engine.evaluate(full_text)
        playbook_matches: List[RuleMatch] = []
        if playbook_rules:
            playbook_engine = RuleEngine.from_rule_dicts(playbook_rules)
            playbook_matches = playbook_engine.evaluate(full_text)

        rule_matches = self._merge_rule_matches(default_matches, playbook_matches)

        # Build clause inventory from rule matches
        inventory: List[ClauseInventoryItem] = []
        for match in rule_matches:
            inventory.append(ClauseInventoryItem(
                clause_type=match.clause_type,
                text=match.match_text,
                section_index=0,
                risk_hint=match.risk_level.value,
                rule_match=match,
            ))

        return PipelineClassificationResult(
            clause_inventory=inventory,
            rule_matches=rule_matches,
        )

    @staticmethod
    def _merge_rule_matches(
        default_matches: List[RuleMatch],
        playbook_matches: List[RuleMatch],
    ) -> List[RuleMatch]:
        """Merge baseline and playbook candidates without losing legal issues.

        A playbook rule supersedes a generic rule only when both address the
        same normalized clause type and overlap the same source region.
        Different legal issues in one clause are deliberately preserved.
        """
        if not playbook_matches:
            return default_matches

        def _type(match: RuleMatch) -> str:
            raw = match.clause_type or match.rule_name
            snapped = _infer_clause_type(raw)
            return snapped if snapped != "unknown" else str(raw).strip().lower()

        kept_defaults: List[RuleMatch] = []
        for generic in default_matches:
            superseded = any(
                _type(generic) == _type(custom)
                and generic.start_offset < custom.end_offset
                and custom.start_offset < generic.end_offset
                for custom in playbook_matches
            )
            if not superseded:
                kept_defaults.append(generic)

        merged = kept_defaults + playbook_matches
        seen = set()
        unique: List[RuleMatch] = []
        for match in sorted(merged, key=lambda m: (m.start_offset, m.rule_id)):
            key = (
                match.rule_id,
                match.start_offset,
                " ".join(match.match_text.lower().split()),
            )
            if key not in seen:
                unique.append(match)
                seen.add(key)
        return unique

    # ======================================================================
    # Stage 3: RISK ASSESSMENT (Gemini Pro, full AI analysis)
    # ======================================================================

    async def _stage3_risk_assessment(
        self,
        extraction: ExtractionResult,
        classification: PipelineClassificationResult,
        playbook_rules: Optional[List[Dict[str, Any]]],
        playbook_name: str,
        party_side: str = "neutral",
        contract_type: str = "general",
        org_context: str = "",
    ) -> Tuple[List[RawRedline], List[str], int, Optional[Dict[str, Any]]]:
        """
        Full AI analysis using GeminiAnalyzer.

        Every rule in an explicitly selected playbook is sent to the model.
        The returned coverage ledger proves which rules were actually assessed.

        Returns:
            Tuple of (raw_redlines, executive_summary, tokens_used, coverage)
        """
        # Pass detected jurisdiction code from Stage 1 (B2 — single detection path)
        jurisdiction_hint = extraction.jurisdiction_result.detected_jurisdiction or None

        ai_result: AIAnalysisResult = await self._analyzer.analyze_full_contract(
            contract_text=extraction.full_text,
            # The selected playbook is authoritative.  Do not silently remove
            # rules through a generic contract-type applicability table.
            playbook_rules=playbook_rules,
            playbook_name=playbook_name,
            jurisdiction_override=jurisdiction_hint,
            party_side=party_side,
            org_context=org_context,
        )

        # Build a set of regex-matched texts for corroboration
        regex_matched_texts = set()
        for rm in classification.rule_matches:
            regex_matched_texts.add(rm.match_text.lower().strip())

        # Build playbook rule lookup by stable id and normalized name.
        playbook_lookup: Dict[str, Dict[str, Any]] = {}
        playbook_by_id: Dict[str, Dict[str, Any]] = {}
        if playbook_rules:
            for pr in playbook_rules:
                name = pr.get("name", pr.get("rule_name", "")).lower()
                if name:
                    playbook_lookup[name] = pr
                rule_id = str(pr.get("id") or pr.get("rule_id") or "")
                if rule_id:
                    playbook_by_id[rule_id] = pr

        # Convert AI redlines to RawRedline
        raw_redlines: List[RawRedline] = []
        for ai_redline in ai_result.redlines:
            # Check if regex also matched this text
            regex_matched = any(
                ai_redline.original_text.lower().strip() in rt
                or rt in ai_redline.original_text.lower().strip()
                for rt in regex_matched_texts
            ) if regex_matched_texts else False

            # IDs survive harmless formatting changes to a rule label.
            ai_rule_id = str(getattr(ai_redline, "rule_id", "") or "")
            pb_rule = playbook_by_id.get(ai_rule_id)
            if pb_rule is None:
                pb_rule = playbook_lookup.get(ai_redline.rule_name.lower())

            is_db = False
            if pb_rule:
                is_db = pb_rule.get("is_deal_breaker", False)

            # Determine clause_type from playbook rule or infer from rule name
            # — always snap through the canonical taxonomy (Phase C1).
            raw_clause_type = ""
            if pb_rule:
                raw_clause_type = pb_rule.get("clause_type", "")
            if not raw_clause_type:
                raw_clause_type = ai_redline.rule_name
            clause_type = _infer_clause_type(raw_clause_type)

            raw_redlines.append(RawRedline(
                rule_name=ai_redline.rule_name,
                risk_level=ai_redline.risk_level,
                original_text=ai_redline.original_text,
                explanation=ai_redline.explanation,
                recommendation=ai_redline.recommendation,
                redline_type=ai_redline.redline_type,
                is_deal_breaker=is_db,
                model_confidence=getattr(ai_redline, 'confidence', None),
                regex_matched=regex_matched,
                playbook_rule=pb_rule,
                clause_type=clause_type,
                rule_id=(
                    str(pb_rule.get("id") or pb_rule.get("rule_id") or "")
                    if pb_rule else ai_rule_id
                ),
                statutory_references=list(
                    getattr(ai_redline, "statutory_references", None) or []
                ),
            ))

        rule_results = list(getattr(ai_result, "rule_results", None) or [])
        coverage = (
            self._build_playbook_coverage(playbook_rules, rule_results)
            if playbook_rules else None
        )

        # Recover a finding when the model completed the rule ledger but
        # accidentally omitted its redline object.  Exact ledger evidence is
        # still passed through the hallucination guard below.
        existing_rule_ids = {r.rule_id for r in raw_redlines if r.rule_id}
        existing_rule_names = {r.rule_name.strip().lower() for r in raw_redlines}
        for outcome in rule_results:
            if not isinstance(outcome, dict):
                continue
            outcome_status = str(outcome.get("status") or "").lower()
            if outcome_status not in {"violation", "missing"}:
                continue
            outcome_id = str(outcome.get("rule_id") or "")
            outcome_name = str(outcome.get("rule_name") or "").strip()
            if outcome_id in existing_rule_ids or outcome_name.lower() in existing_rule_names:
                continue

            pb_rule = playbook_by_id.get(outcome_id) or playbook_lookup.get(outcome_name.lower())
            evidence = str(
                outcome.get("evidence")
                or outcome.get("anchor_text")
                or outcome.get("original_text")
                or ""
            ).strip()
            if not evidence:
                continue

            raw_name = outcome_name or (
                str(pb_rule.get("name") or pb_rule.get("clause_type") or "Playbook Rule")
                if pb_rule else "Playbook Rule"
            )
            raw_clause_type = str(pb_rule.get("clause_type") or raw_name) if pb_rule else raw_name
            try:
                confidence = float(outcome.get("confidence", 0.8) or 0.8)
            except (TypeError, ValueError):
                confidence = 0.8
            raw_redlines.append(RawRedline(
                rule_name=raw_name,
                risk_level=str(
                    outcome.get("risk_level")
                    or (pb_rule.get("risk_level") if pb_rule else "YELLOW")
                ).upper(),
                original_text=evidence,
                explanation=str(
                    outcome.get("reasoning")
                    or outcome.get("explanation")
                    or "The contract does not meet the selected playbook position."
                ),
                recommendation=(
                    str(pb_rule.get("primary_position") or "Review and revise to the playbook position.")
                    if pb_rule else "Review and revise to the playbook position."
                ),
                redline_type=outcome_status,
                is_deal_breaker=bool(pb_rule and pb_rule.get("is_deal_breaker", False)),
                model_confidence=max(0.0, min(confidence, 1.0)),
                regex_matched=False,
                playbook_rule=pb_rule,
                clause_type=_infer_clause_type(raw_clause_type),
                rule_id=(
                    str(pb_rule.get("id") or pb_rule.get("rule_id") or "")
                    if pb_rule else outcome_id
                ),
                statutory_references=list(outcome.get("statutory_references") or []),
            ))

        return raw_redlines, ai_result.executive_summary, ai_result.tokens_used, coverage

    @staticmethod
    def _build_playbook_coverage(
        playbook_rules: List[Dict[str, Any]],
        rule_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a transparent rule-by-rule completion ledger."""
        expected: Dict[str, str] = {}
        expected_by_name: Dict[str, str] = {}
        for rule in playbook_rules:
            rule_name = str(rule.get("name") or rule.get("rule_name") or "").strip()
            rule_id = str(
                rule.get("id") or rule.get("rule_id") or rule_name
            ).strip()
            if not rule_id:
                continue
            expected[rule_id] = rule_name
            if rule_name:
                expected_by_name[rule_name.lower()] = rule_id

        counts = {"compliant": 0, "violation": 0, "missing": 0, "not_applicable": 0}
        statuses: Dict[str, str] = {}

        for result in rule_results:
            if not isinstance(result, dict):
                continue
            status = str(result.get("status") or "").lower()
            if status not in counts:
                continue
            result_id = str(result.get("rule_id") or "").strip()
            result_name = str(result.get("rule_name") or "").strip().lower()
            if result_id not in expected:
                result_id = expected_by_name.get(result_name, "")
            # Ignore beyond-playbook ledger rows and duplicate model rows. The
            # coverage counts must never exceed the selected playbook size.
            if not result_id or result_id in statuses:
                continue
            statuses[result_id] = status

        for status in statuses.values():
            counts[status] += 1

        unassessed = [rule_id for rule_id in expected if rule_id not in statuses]
        return {
            "total_rules": len(expected),
            "assessed_rules": len(expected) - len(unassessed),
            **counts,
            "rule_statuses": statuses,
            "unassessed_rule_ids": unassessed,
            "complete": not unassessed,
        }

    @staticmethod
    def _reconcile_playbook_coverage(
        coverage: Dict[str, Any],
        raw_redlines: List[RawRedline],
        verified_redlines: List[VerifiedRedline],
    ) -> Dict[str, Any]:
        """Make coverage depend on both model assessment and source anchoring."""
        reconciled = copy.deepcopy(coverage)
        expected_ids = (
            set(reconciled.get("rule_statuses", {}))
            | set(reconciled.get("unassessed_rule_ids", []))
        )
        flagged_ids = {
            redline.rule_id
            for redline in raw_redlines
            if redline.rule_id in expected_ids
            and redline.redline_type in {"violation", "missing"}
        }
        anchored_ids = {
            redline.rule_id
            for redline in verified_redlines
            if redline.rule_id in expected_ids
            and not redline.verification_status.startswith("unverified")
        }
        unresolved = sorted(flagged_ids - anchored_ids)
        ledger_complete = bool(reconciled.get("complete", False))
        reconciled["ledger_complete"] = ledger_complete
        reconciled["verification_complete"] = not unresolved
        reconciled["unverified_finding_rule_ids"] = unresolved
        reconciled["complete"] = ledger_complete and not unresolved
        return reconciled

    # ======================================================================
    # Stage 4: VERIFICATION (hallucination guard, deterministic)
    # ======================================================================

    def _stage4_verification(
        self,
        contract_text: str,
        raw_redlines: List[RawRedline],
    ) -> Tuple[List[VerifiedRedline], HallucinationStats]:
        """
        Verify AI-generated quotes against the source contract.
        Rejects hallucinated quotes, corrects fuzzy matches.
        """
        guard = HallucinationGuard(contract_text)
        verified: List[VerifiedRedline] = []

        for redline in raw_redlines:
            # Missing clauses still need a real insertion anchor. If the anchor
            # cannot be found in the source, the finding is not actionable and
            # is surfaced through the incomplete coverage ledger instead.
            if redline.redline_type == "missing":
                result = guard.verify_quote(
                    redline.original_text,
                    is_deal_breaker=redline.is_deal_breaker,
                )
                if result.status == "rejected":
                    logger.info(
                        "Rejecting hallucinated anchor for missing clause: '%.60s...'",
                        redline.original_text,
                    )
                    continue
                verified.append(VerifiedRedline(
                    rule_name=redline.rule_name,
                    risk_level=redline.risk_level,
                    original_text=redline.original_text,
                    verified_text=result.verified_quote or redline.original_text,
                    explanation=redline.explanation,
                    recommendation=redline.recommendation,
                    redline_type=redline.redline_type,
                    is_deal_breaker=redline.is_deal_breaker,
                    verification_status=result.status,
                    verification_confidence=result.confidence,
                    regex_matched=redline.regex_matched,
                    playbook_rule=redline.playbook_rule,
                    model_confidence=redline.model_confidence,
                    clause_type=redline.clause_type,
                    suggested_fix=redline.suggested_fix,
                    rule_id=redline.rule_id,
                    statutory_references=list(redline.statutory_references),
                ))
            else:
                # Violation — strict verification
                result = guard.verify_quote(
                    redline.original_text,
                    is_deal_breaker=redline.is_deal_breaker,
                )

                if result.status == "rejected":
                    logger.info(
                        "Rejecting hallucinated quote (score=%.2f): '%.60s...'",
                        result.similarity_score,
                        redline.original_text,
                    )
                    continue

                verified.append(VerifiedRedline(
                    rule_name=redline.rule_name,
                    risk_level=redline.risk_level,
                    original_text=redline.original_text,
                    verified_text=result.verified_quote,
                    explanation=redline.explanation,
                    recommendation=redline.recommendation,
                    redline_type=redline.redline_type,
                    is_deal_breaker=redline.is_deal_breaker,
                    verification_status=result.status,
                    verification_confidence=result.confidence,
                    regex_matched=redline.regex_matched,
                    playbook_rule=redline.playbook_rule,
                    model_confidence=redline.model_confidence,
                    clause_type=redline.clause_type,
                    suggested_fix=redline.suggested_fix,
                    rule_id=redline.rule_id,
                    statutory_references=list(redline.statutory_references),
                ))

        return verified, guard.get_stats()

    # ======================================================================
    # Stage 5: ENRICHMENT (confidence scoring + cross-references)
    # ======================================================================

    def _stage5_enrichment(
        self,
        verified_redlines: List[VerifiedRedline],
    ) -> List[FinalRedline]:
        """
        Score each redline and add cross-reference information.
        """
        # Collect all flagged rule names for cross-reference scoring
        all_flagged_rules = [v.rule_name for v in verified_redlines]

        final: List[FinalRedline] = []
        for vr in verified_redlines:
            # Score
            confidence = self._scorer.score_redline(
                text_verification_confidence=vr.verification_confidence,
                regex_matched=vr.regex_matched,
                ai_flagged=True,
                playbook_rule=vr.playbook_rule,
                model_confidence=vr.model_confidence,
                related_rule_names=[vr.rule_name],
                all_flagged_rules=all_flagged_rules,
            )

            # Build cross-references: other redlines in the same clause type family
            cross_refs = self._find_cross_references(vr, verified_redlines)

            final.append(FinalRedline(
                rule_name=vr.rule_name,
                risk_level=vr.risk_level,
                original_text=vr.original_text,
                verified_text=vr.verified_text,
                explanation=vr.explanation,
                recommendation=vr.recommendation,
                redline_type=vr.redline_type,
                is_deal_breaker=vr.is_deal_breaker,
                confidence=confidence,
                verification_status=vr.verification_status,
                cross_references=cross_refs,
                clause_type=vr.clause_type,
                suggested_fix=vr.suggested_fix,
                rule_id=vr.rule_id,
                statutory_references=list(vr.statutory_references),
            ))

        # Sort by confidence (highest first), then by risk level
        risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        final.sort(key=lambda r: (
            risk_order.get(r.risk_level, 3),
            -r.confidence.score,
        ))

        return final

    # ======================================================================
    # Stage 5c: SMRITI MCP ENRICHMENT (optional)
    # ======================================================================

    async def _stage5c_smriti_enrichment(
        self,
        redlines: List[FinalRedline],
        jurisdiction: Optional[str] = None,
    ) -> List[FinalRedline]:
        """Enrich redlines with statutory basis and case law from Smriti MCP.

        Only enriches RED and YELLOW findings to limit API calls.
        Non-fatal — returns redlines unchanged if Smriti fails.
        """
        high_risk = [r for r in redlines if r.risk_level in ("RED", "YELLOW")]
        if not high_risk:
            return redlines

        # Limit to top 5 findings to avoid excessive API calls
        to_enrich = high_risk[:5]

        for redline in to_enrich:
            try:
                # Get case law for this clause type
                cases = await smriti_client.search_case_law(
                    query=f"{redline.clause_type} {redline.explanation[:100]}",
                    jurisdiction=jurisdiction,
                    max_results=2,
                )
                if cases:
                    redline.case_law_context = cases

                # Get statute text if there are statutory references in the explanation
                if redline.cross_references:
                    for ref in redline.cross_references[:1]:  # Limit to first ref
                        statute = await smriti_client.get_statute_text(
                            statute_reference=ref,
                            jurisdiction=jurisdiction,
                        )
                        if statute:
                            redline.statutory_basis = statute
                            break
            except Exception as e:
                logger.debug("Smriti enrichment failed for %s: %s", redline.rule_name, e)
                continue

        return redlines

    # ======================================================================
    # Stage 5b: OFFSET-BASED DEDUPLICATION
    # ======================================================================

    def _dedupe_by_overlap(
        self,
        redlines: List[FinalRedline],
        full_text: str,
    ) -> List[FinalRedline]:
        """Collapse only duplicate findings for the same rule and source.

        One clause can contain several independent legal defects.  Text-only
        overlap de-duplication erased those issues, so rule identity is now a
        required part of the duplicate key.
        """
        if len(redlines) <= 1:
            return redlines

        risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}

        located: List[tuple] = []  # (start, end, index, rule_key, redline)
        for i, r in enumerate(redlines):
            search_text = r.verified_text or r.original_text
            idx = full_text.find(search_text)
            rule_key = r.rule_id or " ".join(r.rule_name.lower().split())
            if idx >= 0:
                located.append((idx, idx + len(search_text), i, rule_key, r))
            else:
                located.append((-1, -1, i, rule_key, r))

        located.sort(key=lambda x: (x[0], x[1]))
        keep = set(range(len(redlines)))

        for i in range(len(located)):
            s1, e1, idx1, key1, r1 = located[i]
            if idx1 not in keep:
                continue

            for j in range(i + 1, len(located)):
                s2, e2, idx2, key2, r2 = located[j]
                if idx2 not in keep or key1 != key2:
                    continue

                overlaps = s1 >= 0 and s2 >= 0 and s1 < e2 and s2 < e1
                same_unlocated_text = (
                    s1 < 0
                    and s2 < 0
                    and " ".join((r1.verified_text or r1.original_text).lower().split())
                    == " ".join((r2.verified_text or r2.original_text).lower().split())
                )
                if not overlaps and not same_unlocated_text:
                    if s1 >= 0 and s2 >= e1:
                        break
                    continue

                rank1 = (risk_order.get(r1.risk_level, 3), -(r1.confidence.score if r1.confidence else 0))
                rank2 = (risk_order.get(r2.risk_level, 3), -(r2.confidence.score if r2.confidence else 0))

                if rank1 <= rank2:
                    keep.discard(idx2)
                else:
                    keep.discard(idx1)
                    break

        return [redlines[i] for i in sorted(keep)]

    # ======================================================================
    # Helpers
    # ======================================================================

    def _apply_phase6_wiring(
        self,
        playbook_rules: Optional[List[Dict[str, Any]]],
        rule_matches: List[Any],
        deal_context: Optional[Any],
        conditions: Optional[List[Any]],
        dependencies: Optional[List[Any]],
        rule_tiers_by_rule: Optional[Dict[str, Any]],
        tier_preference: str,
    ) -> Tuple[Optional[List[Dict[str, Any]]], List[Any]]:
        """Apply Phase-6 features to both the prompt-input dicts and RuleMatch list.

        Returns the (possibly-modified) playbook_rules and rule_matches.

        Effects, in order:
          1. Tier swap — if `tier_preference` is not "ideal" and a matching
             PlaybookRuleTier was preloaded for a rule, swap the rule's
             primary_position with the tier's position_text in the prompt
             input. The rule_matches list is left unchanged because the rule
             engine already produced its match against the contract text.
          2. Conditions + Overrides — evaluate `conditions` against
             `deal_context`; collect overrides from matching conditions and
             apply to BOTH playbook_rules dicts (so the AI sees the override)
             AND the rule_matches list (so the fallback path stays consistent).
          3. Dependencies — apply cross-rule effects to both RuleMatch objects
             and the rule dictionaries sent to the AI, including AI-only rules
             that intentionally have no deterministic match.
        """
        from app.services.playbook_conditions_engine import conditions_engine
        from app.services.dependency_resolver import dependency_resolver

        modified_rules: Optional[List[Dict[str, Any]]] = (
            copy.deepcopy(playbook_rules) if playbook_rules else None
        )

        # ---- (1) Tier swap on playbook_rules dicts ----
        tier_pref_normalized = (tier_preference or "ideal").lower()
        if (
            tier_pref_normalized != "ideal"
            and modified_rules
            and rule_tiers_by_rule
        ):
            swapped = 0
            for rule_dict in modified_rules:
                rule_id = rule_dict.get("id") or rule_dict.get("rule_id")
                if not rule_id:
                    continue
                tier = rule_tiers_by_rule.get(str(rule_id))
                if tier is None:
                    continue
                position_text = getattr(tier, "position_text", None)
                if position_text:
                    rule_dict["primary_position"] = position_text
                    swapped += 1
            if swapped:
                logger.info(
                    "Phase 6 tier swap: replaced primary_position on %d rule(s) with tier=%r",
                    swapped, tier_pref_normalized,
                )

        # ---- (2) Conditions + Overrides ----
        if deal_context is not None and conditions:
            try:
                matched = conditions_engine.evaluate_conditions(conditions, deal_context)
            except Exception as exc:
                logger.warning("Condition evaluation failed: %s", exc)
                matched = []

            if matched:
                all_overrides: List[Any] = []
                rule_id_to_clause_type: Dict[str, str] = {}
                for cond in matched:
                    for ov in getattr(cond, "rule_overrides", []) or []:
                        all_overrides.append(ov)
                        rel_rule = getattr(ov, "rule", None)
                        if rel_rule is not None:
                            rule_id_to_clause_type[str(ov.rule_id)] = rel_rule.clause_type

                if all_overrides:
                    # Apply to RuleMatch (fallback path)
                    try:
                        rule_matches = conditions_engine.apply_overrides(
                            rule_matches, all_overrides, rule_id_to_clause_type
                        )
                    except Exception as exc:
                        logger.warning("apply_overrides on RuleMatch failed: %s", exc)

                    # Apply to playbook_rules dicts (AI prompt)
                    if modified_rules:
                        modified_rules = self._apply_overrides_to_rule_dicts(
                            modified_rules, all_overrides, rule_id_to_clause_type
                        )

        # ---- (3) Dependencies ----
        if dependencies:
            try:
                rule_matches, actions = dependency_resolver.resolve(rule_matches, dependencies)
                if modified_rules and actions:
                    modified_rules = self._apply_dependency_actions_to_rule_dicts(
                        modified_rules,
                        actions,
                    )
            except Exception as exc:
                logger.warning("dependency_resolver.resolve failed: %s", exc)

        return modified_rules, rule_matches

    @staticmethod
    def _apply_dependency_actions_to_rule_dicts(
        rule_dicts: List[Dict[str, Any]],
        actions: List[Any],
    ) -> List[Dict[str, Any]]:
        """Mirror resolved dependency effects into the AI prompt rule shape."""
        working = copy.deepcopy(rule_dicts)
        suppressed: set[str] = set()

        def _matches(rule: Dict[str, Any], target: str) -> bool:
            rule_id = str(rule.get("id") or rule.get("rule_id") or "")
            clause_type = str(rule.get("clause_type") or rule.get("name") or "")
            return target in {rule_id, clause_type}

        for action in actions:
            target = str(getattr(action, "target_clause", "") or "")
            effect = str(getattr(action, "effect", "") or "")
            params = dict(getattr(action, "effect_params", None) or {})
            if not target:
                continue
            if effect == "suppress":
                suppressed.add(target)
                continue

            for rule in working:
                if not _matches(rule, target):
                    continue
                if effect == "escalate_risk" and params.get("new_risk"):
                    rule["risk_level"] = str(params["new_risk"]).upper()
                elif effect == "change_position" and params.get("new_position"):
                    rule["primary_position"] = str(params["new_position"])
                elif effect == "add_flag" and params.get("message"):
                    flags = list(rule.get("dependency_flags") or [])
                    flags.append(str(params["message"]))
                    rule["dependency_flags"] = flags
                break

        return [
            rule
            for rule in working
            if not any(_matches(rule, target) for target in suppressed)
        ]

    @staticmethod
    def _apply_overrides_to_rule_dicts(
        rule_dicts: List[Dict[str, Any]],
        overrides: List[Any],
        rule_id_to_clause_type: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Mirror conditions_engine.apply_overrides for the dict shape used in
        the AI prompt. Suppression drops the dict; risk/position/deal-breaker
        overrides mutate in place. Higher-priority overrides win (callers must
        provide a sorted list)."""
        out: List[Dict[str, Any]] = []
        suppress_ids: set = set()
        modified_ids: set = set()

        # Index dicts by id and clause_type for lookup
        for ov in overrides:
            rule_uuid = str(ov.rule_id)
            target_ct = rule_id_to_clause_type.get(rule_uuid)
            for rd in rule_dicts:
                rd_id = str(rd.get("id") or rd.get("rule_id") or "")
                rd_ct = (rd.get("clause_type") or "").strip().lower()
                target_ct_norm = (target_ct or "").strip().lower()

                matches_id = rd_id == rule_uuid
                matches_ct = bool(target_ct_norm) and rd_ct == target_ct_norm
                if not (matches_id or matches_ct):
                    continue

                key = rd_id or rd_ct
                if key in suppress_ids or key in modified_ids:
                    continue

                if getattr(ov, "suppress_rule", False):
                    suppress_ids.add(key)
                    continue
                modified_ids.add(key)

                if getattr(ov, "override_risk_level", None):
                    rd["risk_level"] = str(ov.override_risk_level).upper()
                if getattr(ov, "override_position_text", None):
                    rd["primary_position"] = ov.override_position_text
                if getattr(ov, "override_is_deal_breaker", None) is not None:
                    rd["is_deal_breaker"] = bool(ov.override_is_deal_breaker)

        for rd in rule_dicts:
            key = str(rd.get("id") or rd.get("rule_id") or "") or (rd.get("clause_type") or "").strip().lower()
            if key in suppress_ids:
                continue
            out.append(rd)
        return out

    @staticmethod
    def _detect_contract_type(text: str) -> str:
        """Detect contract type from text content.

        Scans the first 5000 characters for keyword signals and returns the
        most likely contract type.  Requires at least 2 matching signals to
        classify; otherwise falls back to ``"general"`` (send all rules).

        Returns:
            One of: ``"nda"``, ``"saas"``, ``"employment"``, ``"msa"``,
            ``"ma"``, or ``"general"``.
        """
        text_lower = text[:5000].lower()

        type_signals = {
            "dpa": [
                r"\b(data\s+processing\s+(addendum|agreement)|dpa)\b",
                r"\b(data\s+(controller|processor)|data\s+fiduciary|data\s+principal)\b",
                r"\b(data\s+subject|personal\s+data|subprocessor)\b",
            ],
            "nda": [
                r"\b(non[\s-]?disclosure|confidentiality\s+agreement|nda)\b",
                r"\b(disclosing\s+party|receiving\s+party)\b",
                r"\b(proprietary\s+information|trade\s+secret)\b",
            ],
            "saas": [
                r"\b(software\s+as\s+a\s+service|saas|subscription\s+(agreement|terms))\b",
                r"\b(service\s+level\s+agreement|sla|uptime)\b",
                r"\b(data\s+processing|api\s+(access|rights))\b",
            ],
            "employment": [
                r"\b(employment\s+(agreement|contract)|offer\s+letter)\b",
                r"\b(employee|employer|compensation|salary|benefits)\b",
                r"\b(probation|notice\s+period|resignation)\b",
            ],
            "msa": [
                r"\b(master\s+services?\s+agreement|msa|statement\s+of\s+work|sow)\b",
                r"\b(professional\s+services|consulting|deliverables)\b",
                r"\b(change\s+order|milestone|acceptance\s+criteria)\b",
            ],
            "ma": [
                r"\b(merger|acquisition|share\s+purchase|stock\s+purchase)\b",
                r"\b(due\s+diligence|closing\s+conditions|representations?\s+and\s+warranties)\b",
                r"\b(indemnification\s+escrow|earn[\s-]?out|purchase\s+price)\b",
            ],
            "consulting": [
                r"\b(consulting\s+agreement|consultant\s+agreement|independent\s+contractor)\b",
                r"\b(consultant|professional\s+services)\b",
                r"\b(deliverables|statement\s+of\s+work|milestones)\b",
            ],
            "vendor": [
                r"\b(vendor\s+agreement|procurement\s+agreement|supplier\s+agreement)\b",
                r"\b(purchase\s+order|goods|products|delivery)\b",
                r"\b(vendor|supplier|purchaser)\b",
            ],
            "joint_venture": [
                r"\b(joint\s+venture|joint\s+venture\s+agreement)\b",
                r"\b(venture\s+company|management\s+committee|reserved\s+matters)\b",
                r"\b(capital\s+contribution|profit\s+sharing|deadlock)\b",
            ],
            "lease": [
                r"\b(lease\s+agreement|leave\s+and\s+license|tenancy\s+agreement)\b",
                r"\b(landlord|tenant|lessor|lessee|licensor|licensee)\b",
                r"\b(premises|rent|security\s+deposit)\b",
            ],
            "healthcare": [
                r"\b(healthcare\s+vendor|health\s+services|hospital|clinical)\b",
                r"\b(patient\s+(data|records)|protected\s+health\s+information|hipaa)\b",
                r"\b(medical\s+records|healthcare\s+provider)\b",
            ],
            "fintech": [
                r"\b(fintech|payment\s+services|financial\s+technology)\b",
                r"\b(payment\s+aggregator|payment\s+gateway|regulated\s+entity)\b",
                r"\b(rbi|reserve\s+bank\s+of\s+india|pci[\s-]?dss)\b",
            ],
            "it_services": [
                r"\b(it\s+services\s+agreement|information\s+technology\s+services)\b",
                r"\b(system\s+integration|software\s+development|managed\s+services)\b",
                r"\b(acceptance\s+testing|source\s+code|change\s+request)\b",
            ],
        }

        scores = {}
        for contract_type, patterns in type_signals.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            scores[contract_type] = score

        best_type = max(scores, key=scores.get)
        if scores[best_type] >= 2:  # Need at least 2 signals
            if best_type == "nda":
                mutual_signals = (
                    r"\bmutual\b",
                    r"\beach\s+party\s+(?:may\s+be|is)\s+(?:a\s+)?(?:disclosing|receiving)\s+party\b",
                    r"\bboth\s+parties\b",
                )
                if any(re.search(pattern, text_lower) for pattern in mutual_signals):
                    return "nda_mutual"
                return "nda_unilateral"
            return best_type
        return "general"  # Fallback — send all rules

    @staticmethod
    def _detect_non_english(text: str) -> bool:
        """Basic check if text is primarily non-English."""
        if not text:
            return False
        ascii_chars = sum(1 for c in text[:2000] if ord(c) < 128)
        total = min(len(text), 2000)
        # If less than 60% ASCII, likely non-English
        return (ascii_chars / total) < 0.6 if total > 0 else False

    @staticmethod
    def _is_likely_contract(text: str) -> bool:
        """Basic check if text looks like a legal agreement."""
        indicators = [
            r'\b(agreement|contract|terms|party|parties|hereby|whereas|witnesseth)\b',
            r'\b(shall|obligations|liability|indemnif|warrant|represent)\b',
            r'\b(governing law|jurisdiction|arbitration|dispute)\b',
            r'\b(effective date|termination|confidential|intellectual property)\b',
        ]
        text_lower = text[:5000].lower()
        matches = sum(1 for pattern in indicators if re.search(pattern, text_lower))
        return matches >= 2  # At least 2 different indicator groups

    @staticmethod
    def _is_likely_fragment(text: str) -> bool:
        """Detect if text is likely a document fragment rather than a complete contract."""
        text_lower = text.lower().strip()
        # Fragments typically lack standard contract elements
        has_parties = bool(re.search(r'\b(between|party|parties|agreement)\b', text_lower[:500]))
        has_signature = bool(re.search(r'\b(witness|signed|executed|signature)\b', text_lower[-500:]))
        has_definitions = bool(re.search(r'\bdefinitions?\b', text_lower[:2000]))
        # If missing most structural elements AND short, likely a fragment
        structural_score = sum([has_parties, has_signature, has_definitions])
        if structural_score <= 1 and len(text) < 5000:
            return True
        return False

    @staticmethod
    def _find_cross_references(
        target: VerifiedRedline,
        all_redlines: List[VerifiedRedline],
    ) -> List[str]:
        """Find related redlines for cross-reference enrichment."""
        RELATED_GROUPS = {
            "liability": ["Unlimited Liability", "Broad Indemnification"],
            "termination": ["Unilateral Termination", "Auto-Renewal"],
            "ip": ["Broad IP Assignment", "Non-Compete Clause"],
            "restrictive": ["Non-Compete Clause", "Non-Solicitation Clause", "Exclusive Dealing"],
        }

        cross_refs: List[str] = []
        target_name = target.rule_name

        for group_name, members in RELATED_GROUPS.items():
            if target_name in members:
                for other in all_redlines:
                    if (
                        other.rule_name != target_name
                        and other.rule_name in members
                    ):
                        cross_refs.append(
                            f"Related: {other.rule_name} ({other.risk_level})"
                        )

        return cross_refs

    @staticmethod
    def _rule_matches_to_raw_redlines(
        rule_matches: List[RuleMatch],
        playbook_rules: Optional[List[Dict[str, Any]]],
    ) -> List[RawRedline]:
        """Convert rule engine matches to RawRedline (fallback when AI is unavailable)."""
        playbook_lookup: Dict[str, Dict[str, Any]] = {}
        playbook_by_id: Dict[str, Dict[str, Any]] = {}
        if playbook_rules:
            for pr in playbook_rules:
                name = pr.get("name", pr.get("rule_name", "")).lower()
                if name:
                    playbook_lookup[name] = pr
                rule_id = str(pr.get("id") or pr.get("rule_id") or "")
                if rule_id:
                    playbook_by_id[rule_id] = pr

        redlines: List[RawRedline] = []
        for rm in rule_matches:
            # Keyword matches for semantic rules are candidate locators, not a
            # legal conclusion.  Showing them as violations when AI is down
            # produces false positives for perfectly compliant clauses.
            if getattr(rm, "detection_mode", "keywords_only") != "keywords_only":
                continue
            pb_rule = playbook_by_id.get(str(rm.rule_id)) or playbook_lookup.get(rm.rule_name.lower())
            clause_type = ""
            if pb_rule:
                clause_type = pb_rule.get("clause_type", "")
            if not clause_type:
                clause_type = _infer_clause_type(rm.rule_name)
            redlines.append(RawRedline(
                rule_name=rm.rule_name,
                risk_level=rm.risk_level.value,
                original_text=rm.match_text,
                explanation=f"Rule engine detected {rm.rule_name} pattern.",
                recommendation=rm.primary_position or "Review this clause.",
                redline_type="violation",
                is_deal_breaker=rm.is_deal_breaker,
                regex_matched=True,
                playbook_rule=pb_rule,
                clause_type=clause_type,
                rule_id=str(rm.rule_id or ""),
            ))
        return redlines


    # ======================================================================
    # Clause-level pipeline methods (unified entry points for all AI calls)
    # ======================================================================

    async def analyze_clause(
        self,
        clause_text: str,
        playbook_rules: list = None,
        playbook_name: str = "Default",
        jurisdiction: str = None,
        party_side: str = "neutral",
    ) -> dict:
        """Analyze a single clause with hallucination guard + confidence scoring.

        Wraps gemini_analyzer.analyze_clause() and adds:
        - Stage 4: Hallucination verification of returned quotes
        - Stage 5: Confidence scoring on verified redlines

        Returns the same dict format as gemini_analyzer.analyze_clause()
        with additional 'confidence' and 'verification_status' per redline.
        """
        ai_result = await self._analyzer.analyze_clause(
            clause_text=clause_text,
            playbook_rules=playbook_rules,
            playbook_name=playbook_name,
            jurisdiction=jurisdiction,
            party_side=party_side,
        )

        raw_redlines = ai_result.get("redlines", [])
        if not raw_redlines or not clause_text:
            return ai_result

        # Stage 4: Verify quotes against source clause text
        guard = HallucinationGuard(clause_text)
        verified_redlines = []
        for redline in raw_redlines:
            original_text = redline.get("original_text", "")
            if not original_text:
                verified_redlines.append(redline)
                continue

            result = guard.verify_quote(original_text)
            if result.status == "rejected" and result.similarity_score < 0.5:
                logger.info(
                    "Clause analysis: rejecting hallucinated quote '%.60s...'",
                    original_text,
                )
                continue

            redline["verification_status"] = result.status
            if result.verified_quote and result.status == "fuzzy_corrected":
                redline["original_text"] = result.verified_quote

            # Stage 5: Confidence scoring
            confidence = self._scorer.score_redline(
                text_verification_confidence=result.confidence,
                regex_matched=False,
                ai_flagged=True,
                playbook_rule=None,
                model_confidence=None,
            )
            redline["confidence"] = confidence.score
            redline["confidence_level"] = confidence.level.value

            verified_redlines.append(redline)

        ai_result["redlines"] = verified_redlines
        return ai_result

    async def generate_clause(
        self,
        clause_type: str,
        contract_context: str = "",
        playbook_rules: Optional[List[Dict]] = None,
        jurisdiction_override: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate a contract clause via the unified pipeline.

        Delegates to gemini_analyzer.generate_clause() with jurisdiction awareness.
        """
        return await self._analyzer.generate_clause(
            clause_type=clause_type,
            contract_context=contract_context,
            playbook_rules=playbook_rules,
            jurisdiction_override=jurisdiction_override,
        )

    async def generate_fix(
        self,
        original_text: str,
        recommendation: str,
        rule_name: str,
        redline_type: str = "violation",
        surrounding_context: str = "",
        playbook_rules: Optional[List[Dict]] = None,
        jurisdiction_override: Optional[str] = None,
        defined_terms: str = "",
    ) -> Dict[str, Any]:
        """Generate exact replacement text via the unified pipeline.

        Delegates to gemini_analyzer.generate_fix() with jurisdiction awareness.
        """
        return await self._analyzer.generate_fix(
            original_text=original_text,
            recommendation=recommendation,
            rule_name=rule_name,
            redline_type=redline_type,
            surrounding_context=surrounding_context,
            playbook_rules=playbook_rules,
            jurisdiction_override=jurisdiction_override,
            defined_terms=defined_terms,
        )

    async def research_clause(
        self,
        clause_text: str,
        clause_type: str = "",
        jurisdiction_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Research case law for a clause via the unified pipeline.

        Delegates to gemini_analyzer.research_clause().
        """
        return await self._analyzer.research_clause(
            clause_text=clause_text,
            clause_type=clause_type,
            jurisdiction_override=jurisdiction_override,
        )

    async def assess_diff_changes(
        self,
        changes_text: str,
        rules_context: str = "",
    ) -> Optional[list]:
        """AI assessment of contract diff changes via the unified pipeline.

        Returns list of assessment dicts or None if AI unavailable.
        """
        if not self._analyzer.is_enabled:
            return None

        try:
            safe_changes = _sanitize_for_prompt(changes_text, max_length=20000)
            safe_rules = _sanitize_for_prompt(rules_context, max_length=5000) if rules_context else ""

            prompt = f"""You are a contract review expert. Analyze these changes between two versions of a contract.

{safe_rules}

{safe_changes}

For each change, provide a one-sentence assessment:
- Does this change FAVOR the reviewing party, FAVOR the counterparty, or is it NEUTRAL?
- Briefly explain why.

Return a JSON array of objects:
[
  {{"change_number": 1, "assessment": "favors_us" | "favors_them" | "neutral", "explanation": "Brief explanation"}}
]
"""
            import json as _json

            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._analyzer.client.generate_content(
                        prompt,
                        generation_config={"max_output_tokens": 4096, "temperature": 0.1},
                    ),
                ),
                timeout=120.0,
            )

            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                return None

            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return _json.loads(cleaned)

        except asyncio.TimeoutError:
            logging.getLogger(__name__).warning("assess_diff_changes timed out after 120s")
            return []
        except Exception as e:
            logging.getLogger(__name__).error("assess_diff_changes failed: %s", e)
            return []

    @property
    def is_enabled(self) -> bool:
        """Whether the AI backend is available."""
        return self._analyzer.is_enabled


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

analysis_pipeline = AnalysisPipeline()
