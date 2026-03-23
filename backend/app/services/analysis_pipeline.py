"""
Multi-Stage Analysis Pipeline - 5-stage orchestrator for AI contract analysis.

Replaces the single-shot Gemini call with a structured pipeline:

  Stage 1: EXTRACTION     -> ContractMap + DefinedTerms + JurisdictionHint  (deterministic, no AI)
  Stage 2: CLASSIFICATION -> ClauseInventory via rule engine + Gemini Flash-Lite  (cheap + fast)
  Stage 3: RISK ASSESSMENT-> RawRedlines with confidence scores (Gemini Pro, high quality)
  Stage 4: VERIFICATION   -> VerifiedRedlines (hallucinations killed)  (deterministic, no AI)
  Stage 5: ENRICHMENT     -> FinalRedlines with cross-references (Gemini Flash-Lite per-redline)

Each stage is a separate async method.  The pipeline tracks timing and costs per stage.
Graceful degradation: if a stage fails, return partial results from completed stages.

This is a NEW orchestrator — it does NOT modify gemini_analyzer.py. It USES
GeminiAnalyzer internally for AI calls.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.gemini_analyzer import (
    AIAnalysisResult,
    AIRedline,
    AIServiceError,
    AIServiceUnavailable,
    AIRateLimited,
    AIServiceTimeout,
    GeminiAnalyzer,
    gemini_analyzer,
    _sanitize_for_prompt,
)
from app.services.hallucination_guard import (
    HallucinationGuard,
    HallucinationStats,
    VerificationResult,
)
from app.services.confidence_scorer import (
    ConfidenceBreakdown,
    ConfidenceLevel,
    ConfidenceScore,
    ConfidenceScorer,
)
from app.services.rule_engine import RuleEngine, RuleMatch, RiskLevel
from app.services.structure_extractor import ContractMap, StructureExtractor
from app.services.scope_analyzer import ScopeAnalyzer, ScopeAnalysisResult, scope_analyzer
from app.services.jurisdiction_detector import apply_jurisdiction_overrides, jurisdiction_detector

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
class JurisdictionHint:
    """Jurisdiction information extracted from the contract."""
    governing_law: str = ""
    jurisdiction: str = ""
    arbitration_seat: str = ""
    is_indian: bool = False
    raw_text: str = ""


@dataclass
class ExtractionResult:
    """Stage 1 output."""
    contract_map: ContractMap
    defined_terms: List[DefinedTerm]
    jurisdiction_hint: JurisdictionHint
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
    # Phase 5: Scope analysis and coverage report
    scope_analysis: Optional[Dict[str, Any]] = None
    coverage_report: Optional[Dict[str, Any]] = None
    jurisdiction_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "executive_summary": self.executive_summary,
            "redlines": [
                {
                    "rule_name": r.rule_name,
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
                }
                for r in self.redlines
            ],
            "hallucination_stats": self.hallucination_stats,
            "stage_metrics": [m.to_dict() for m in self.stage_metrics],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "total_tokens_used": self.total_tokens_used,
            "partial": self.partial,
        }
        if self.scope_analysis:
            d["scope_analysis"] = self.scope_analysis
        if self.coverage_report:
            d["coverage_report"] = self.coverage_report
        if self.jurisdiction_code:
            d["jurisdiction_code"] = self.jurisdiction_code
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

_JURISDICTION_PATTERNS = [
    re.compile(
        r"(?:govern(?:ed|ing)\s+(?:by\s+)?(?:the\s+)?laws?\s+of\s+)([A-Z][A-Za-z\s,]+?)(?:\.|;|,\s+and)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:jurisdiction\s+of\s+(?:the\s+)?(?:courts?\s+(?:of|in|at)\s+)?)([A-Z][A-Za-z\s,]+?)(?:\.|;)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:arbitration\s+(?:shall\s+)?(?:be\s+)?(?:held|conducted|seated)\s+(?:in|at)\s+)([A-Z][A-Za-z\s,]+?)(?:\.|;)",
        re.IGNORECASE,
    ),
]

_INDIAN_JURISDICTION_MARKERS = [
    "india", "indian", "mumbai", "delhi", "new delhi", "bangalore", "bengaluru",
    "chennai", "hyderabad", "kolkata", "pune", "ahmedabad",
    "indian contract act", "arbitration and conciliation act",
    "information technology act", "dpdp act",
]


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
        party_side: str = "seller",
    ) -> PipelineResult:
        """
        Run the full 5-stage pipeline.

        Graceful degradation: if any stage fails, returns partial results
        from completed stages with `partial=True`.
        """
        pipeline_start = time.monotonic()
        stage_metrics: List[StageMetrics] = []
        total_tokens = 0
        partial = False
        executive_summary: List[str] = []
        final_redlines: List[FinalRedline] = []
        hallucination_stats: Dict[str, Any] = {}
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
            extraction = await loop.run_in_executor(None, self._stage1_extraction, contract_text)
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
        detected_jurisdiction: Optional[str] = None
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

                # Apply jurisdiction overrides to rule matches
                jur_result = jurisdiction_detector.detect(contract_text)
                if jur_result.detected_jurisdiction:
                    detected_jurisdiction = jur_result.detected_jurisdiction
                    classification.rule_matches = apply_jurisdiction_overrides(
                        classification.rule_matches,
                        jur_result.detected_jurisdiction,
                    )
        except Exception as e:
            logger.warning("Scope analysis/jurisdiction overrides failed (non-fatal): %s", e)

        # ---- Stage 3: RISK ASSESSMENT (Gemini Pro, full AI analysis) ----
        raw_redlines: List[RawRedline] = []
        try:
            s3_start = time.monotonic()
            raw_redlines, ai_summary, s3_tokens = await self._stage3_risk_assessment(
                extraction, classification, playbook_rules, playbook_name, party_side
            )
            executive_summary = ai_summary
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
            # Convert rule matches to raw redlines as fallback
            raw_redlines = self._rule_matches_to_raw_redlines(
                classification.rule_matches, playbook_rules
            )
            executive_summary = ["AI analysis unavailable. Results based on rule engine only."]
        except Exception as e:
            logger.error("Pipeline Stage 3 (risk_assessment) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="risk_assessment", error=str(e)))
            partial = True
            raw_redlines = self._rule_matches_to_raw_redlines(
                classification.rule_matches, playbook_rules
            )
            executive_summary = ["AI analysis encountered an error. Results based on rule engine only."]

        if not raw_redlines:
            return PipelineResult(
                executive_summary=executive_summary or ["No issues found."],
                redlines=[],
                hallucination_stats={},
                stage_metrics=stage_metrics,
                total_duration_seconds=time.monotonic() - pipeline_start,
                total_tokens_used=total_tokens,
                partial=partial,
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
                )
                for r in raw_redlines
            ]

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
                )
                for v in verified_redlines
            ]

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
            scope_analysis=scope_data,
            coverage_report=coverage_data,
            jurisdiction_code=detected_jurisdiction,
        )

    # ======================================================================
    # Stage 1: EXTRACTION (deterministic, no AI cost)
    # ======================================================================

    def _stage1_extraction(self, contract_text: str) -> ExtractionResult:
        """
        Extract structure, defined terms, and jurisdiction hints.
        All deterministic regex — no AI cost.
        """
        extractor = StructureExtractor()
        contract_map = extractor.extract_from_text(contract_text)

        # Extract defined terms
        defined_terms = self._extract_defined_terms(contract_text)

        # Extract jurisdiction hint
        jurisdiction_hint = self._extract_jurisdiction(contract_text)

        return ExtractionResult(
            contract_map=contract_map,
            defined_terms=defined_terms,
            jurisdiction_hint=jurisdiction_hint,
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

    def _extract_jurisdiction(self, text: str) -> JurisdictionHint:
        """Extract governing law and jurisdiction hints."""
        hint = JurisdictionHint()
        text_lower = text.lower()

        for pattern in _JURISDICTION_PATTERNS:
            match = pattern.search(text)
            if match:
                location = match.group(1).strip()
                if not hint.governing_law:
                    hint.governing_law = location
                    hint.raw_text = match.group(0)
                elif not hint.jurisdiction:
                    hint.jurisdiction = location
                elif not hint.arbitration_seat:
                    hint.arbitration_seat = location

        # Check if Indian jurisdiction
        hint.is_indian = any(
            marker in text_lower for marker in _INDIAN_JURISDICTION_MARKERS
        )

        return hint

    # ======================================================================
    # Stage 2: CLASSIFICATION (rule engine, deterministic)
    # ======================================================================

    def _stage2_classification(
        self,
        extraction: ExtractionResult,
        playbook_rules: Optional[List[Dict[str, Any]]],
    ) -> PipelineClassificationResult:
        """
        Classify clauses using rule engine pattern matching.
        """
        full_text = extraction.full_text
        rule_matches = self._rule_engine.evaluate(full_text)

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

    # ======================================================================
    # Stage 3: RISK ASSESSMENT (Gemini Pro, full AI analysis)
    # ======================================================================

    async def _stage3_risk_assessment(
        self,
        extraction: ExtractionResult,
        classification: PipelineClassificationResult,
        playbook_rules: Optional[List[Dict[str, Any]]],
        playbook_name: str,
        party_side: str = "seller",
    ) -> Tuple[List[RawRedline], List[str], int]:
        """
        Full AI analysis using GeminiAnalyzer.

        Returns:
            Tuple of (raw_redlines, executive_summary, tokens_used)
        """
        # Pass jurisdiction hint from stage 1 to avoid redundant detection
        jurisdiction_hint = None
        if extraction.jurisdiction_hint and extraction.jurisdiction_hint.governing_law:
            jurisdiction_hint = extraction.jurisdiction_hint.governing_law

        ai_result: AIAnalysisResult = await self._analyzer.analyze_full_contract(
            contract_text=extraction.full_text,
            playbook_rules=playbook_rules,
            playbook_name=playbook_name,
            jurisdiction_override=jurisdiction_hint,
            party_side=party_side,
        )

        # Build a set of regex-matched texts for corroboration
        regex_matched_texts = set()
        for rm in classification.rule_matches:
            regex_matched_texts.add(rm.match_text.lower().strip())

        # Build playbook rule lookup by name
        playbook_lookup: Dict[str, Dict[str, Any]] = {}
        if playbook_rules:
            for pr in playbook_rules:
                name = pr.get("name", pr.get("rule_name", "")).lower()
                if name:
                    playbook_lookup[name] = pr

        # Convert AI redlines to RawRedline
        raw_redlines: List[RawRedline] = []
        for ai_redline in ai_result.redlines:
            # Check if regex also matched this text
            regex_matched = any(
                ai_redline.original_text.lower().strip() in rt
                or rt in ai_redline.original_text.lower().strip()
                for rt in regex_matched_texts
            ) if regex_matched_texts else False

            # Find matching playbook rule
            pb_rule = playbook_lookup.get(ai_redline.rule_name.lower())

            is_db = False
            if pb_rule:
                is_db = pb_rule.get("is_deal_breaker", False)

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
            ))

        return raw_redlines, ai_result.executive_summary, ai_result.tokens_used

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
            # Missing clauses won't have exact quotes — verify more leniently
            if redline.redline_type == "missing":
                # For missing clauses, we verify the anchor text exists
                result = guard.verify_quote(
                    redline.original_text,
                    is_deal_breaker=redline.is_deal_breaker,
                )
                # Be lenient for missing clauses — only reject if completely bogus
                if result.status == "rejected" and result.similarity_score < 0.5:
                    logger.info(
                        "Rejecting hallucinated anchor for missing clause: '%.60s...'",
                        redline.original_text,
                    )
                    continue
                # Accept missing clause even with fuzzy match
                verified.append(VerifiedRedline(
                    rule_name=redline.rule_name,
                    risk_level=redline.risk_level,
                    original_text=redline.original_text,
                    verified_text=result.verified_quote or redline.original_text,
                    explanation=redline.explanation,
                    recommendation=redline.recommendation,
                    redline_type=redline.redline_type,
                    is_deal_breaker=redline.is_deal_breaker,
                    verification_status=result.status if result.passed else "fuzzy_accepted",
                    verification_confidence=max(result.confidence, 0.6),
                    regex_matched=redline.regex_matched,
                    playbook_rule=redline.playbook_rule,
                    model_confidence=redline.model_confidence,
                ))
            else:
                # Violation — strict verification
                result = guard.verify_quote(
                    redline.original_text,
                    is_deal_breaker=redline.is_deal_breaker,
                )

                if result.status == "rejected":
                    if guard.needs_requery(result, redline.is_deal_breaker):
                        # Deal-breaker: keep with degraded status rather than silently dropping
                        logger.warning(
                            "Deal-breaker quote rejected (score=%.2f) — kept with low confidence: '%.60s...'",
                            result.similarity_score,
                            redline.original_text,
                        )
                        verified.append(VerifiedRedline(
                            rule_name=redline.rule_name,
                            risk_level=redline.risk_level,
                            original_text=redline.original_text,
                            verified_text=redline.original_text,
                            explanation="⚠️ UNVERIFIED QUOTE — The exact text could not be located in the document. Review the original contract to confirm this finding. " + redline.explanation,
                            recommendation=redline.recommendation,
                            redline_type=redline.redline_type,
                            is_deal_breaker=True,
                            verification_status="unverified_deal_breaker",
                            verification_confidence=0.3,
                            regex_matched=redline.regex_matched,
                            playbook_rule=redline.playbook_rule,
                            model_confidence=redline.model_confidence,
                        ))
                        continue
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
            ))

        # Sort by confidence (highest first), then by risk level
        risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        final.sort(key=lambda r: (
            risk_order.get(r.risk_level, 3),
            -r.confidence.score,
        ))

        return final

    # ======================================================================
    # Helpers
    # ======================================================================

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
        if playbook_rules:
            for pr in playbook_rules:
                name = pr.get("name", pr.get("rule_name", "")).lower()
                if name:
                    playbook_lookup[name] = pr

        redlines: List[RawRedline] = []
        for rm in rule_matches:
            pb_rule = playbook_lookup.get(rm.rule_name.lower())
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

        prompt = f"""You are a contract review expert. Analyze these changes between two versions of a contract.

{rules_context}

{changes_text}

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
        response = await loop.run_in_executor(
            None,
            lambda: self._analyzer.client.generate_content(
                prompt,
                generation_config={"max_output_tokens": 4096, "temperature": 0.1},
            ),
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

    @property
    def is_enabled(self) -> bool:
        """Whether the AI backend is available."""
        return self._analyzer.is_enabled


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

analysis_pipeline = AnalysisPipeline()
