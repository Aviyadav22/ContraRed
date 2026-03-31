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
    # is_indian removed — jurisdiction is detected from governing law clause, not keywords
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
    clause_type: str = ""
    suggested_fix: Optional[str] = None


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
    contract_type: Optional[str] = None  # Detected contract type (nda, saas, employment, msa, ma, general)

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
                    "clause_type": r.clause_type,
                    "suggested_fix": r.suggested_fix,
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
        if self.contract_type:
            d["contract_type"] = self.contract_type
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

# Removed: _INDIAN_JURISDICTION_MARKERS — jurisdiction detection is now
# handled entirely by JurisdictionDetector which reads the governing law
# clause from the contract, not keyword mentions of country names.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_clause_type(rule_name: str) -> str:
    """Map rule name to clause_type for display."""
    name = rule_name.lower()
    mapping = {
        "liability": "liability", "indemnif": "indemnification",
        "confiden": "confidentiality", "terminat": "termination",
        "ip ": "intellectual_property", "intellectual": "intellectual_property",
        "non-compete": "restrictive_covenant", "non-solicit": "restrictive_covenant",
        "govern": "governing_law", "jurisdict": "jurisdiction",
        "arbitrat": "dispute_resolution", "force majeure": "force_majeure",
        "warrant": "reps_warranties", "data": "data_protection",
        "payment": "payment", "sla": "service_level", "assign": "assignment",
    }
    for key, ctype in mapping.items():
        if key in name:
            return ctype
    return "general"


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
        org_context: str = "",
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

        # ---- Pre-Stage 3: Contract type detection (deterministic) ----
        contract_type = self._detect_contract_type(contract_text)
        logger.info("Detected contract type: %s", contract_type)

        # ---- Stage 3: RISK ASSESSMENT (Gemini Pro, full AI analysis) ----
        raw_redlines: List[RawRedline] = []
        try:
            s3_start = time.monotonic()
            raw_redlines, ai_summary, s3_tokens = await self._stage3_risk_assessment(
                extraction, classification, playbook_rules, playbook_name,
                party_side, contract_type=contract_type, org_context=org_context,
            )
            executive_summary = ai_summary

            # Inject contract-type summary line
            from app.services.prompt_templates import (
                CONTRACT_TYPE_LABELS,
                filter_rules_by_contract_type,
            )
            type_label = CONTRACT_TYPE_LABELS.get(contract_type, contract_type)
            total_rule_count = len(playbook_rules) if playbook_rules else 0
            if contract_type != "general" and playbook_rules:
                filtered_count = len(filter_rules_by_contract_type(playbook_rules, contract_type))
                type_summary = (
                    f"Document type: {type_label} "
                    f"({filtered_count} of {total_rule_count} rules applicable)"
                )
            else:
                type_summary = f"Document type: {type_label} (all {total_rule_count} rules evaluated)"
            executive_summary.insert(0, type_summary)

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
                    clause_type=r.clause_type,
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
                    clause_type=v.clause_type,
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

        # ---- Stage 6: FIX GENERATION ----
        s6_start = time.monotonic()
        try:
            final_redlines = await self._stage6_fix_generation(
                final_redlines,
                extraction=extraction,
                playbook_rules=playbook_rules,
            )
        except Exception as e:
            logger.error("Pipeline Stage 6 (fix_generation) failed: %s", e)
            stage_metrics.append(StageMetrics(stage_name="fix_generation", duration_seconds=time.monotonic() - s6_start, error=str(e)))
        else:
            s6_duration = time.monotonic() - s6_start
            stage_metrics.append(StageMetrics(
                stage_name="fix_generation",
                duration_seconds=s6_duration,
                items_processed=sum(1 for r in final_redlines if r.suggested_fix),
            ))

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
            contract_type=contract_type,
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
        contract_type: str = "general",
        org_context: str = "",
    ) -> Tuple[List[RawRedline], List[str], int]:
        """
        Full AI analysis using GeminiAnalyzer.

        When *contract_type* is not ``"general"``, playbook rules are
        pre-filtered to only those applicable to the detected type.  This
        saves 50-70% of prompt tokens for typed contracts.

        Returns:
            Tuple of (raw_redlines, executive_summary, tokens_used)
        """
        from app.services.prompt_templates import (
            CONTRACT_TYPE_LABELS,
            filter_rules_by_contract_type,
        )

        # Pre-filter playbook rules by detected contract type
        total_rules = len(playbook_rules) if playbook_rules else 0
        if playbook_rules and contract_type != "general":
            filtered_rules = filter_rules_by_contract_type(playbook_rules, contract_type)
            type_label = CONTRACT_TYPE_LABELS.get(contract_type, contract_type)
            logger.info(
                "Contract type '%s' — filtered %d → %d rules (saved %d)",
                contract_type,
                total_rules,
                len(filtered_rules),
                total_rules - len(filtered_rules),
            )
        else:
            filtered_rules = playbook_rules
            type_label = CONTRACT_TYPE_LABELS.get("general", "General Commercial Agreement")

        # Pass jurisdiction hint from stage 1 to avoid redundant detection
        jurisdiction_hint = None
        if extraction.jurisdiction_hint and extraction.jurisdiction_hint.governing_law:
            jurisdiction_hint = extraction.jurisdiction_hint.governing_law

        ai_result: AIAnalysisResult = await self._analyzer.analyze_full_contract(
            contract_text=extraction.full_text,
            playbook_rules=filtered_rules,
            playbook_name=playbook_name,
            jurisdiction_override=jurisdiction_hint,
            party_side=party_side,
            org_context=org_context,
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

            # Determine clause_type from playbook rule or infer from rule name
            clause_type = ""
            if pb_rule:
                clause_type = pb_rule.get("clause_type", "")
            if not clause_type:
                clause_type = _infer_clause_type(ai_redline.rule_name)

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
                    clause_type=redline.clause_type,
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
                            clause_type=redline.clause_type,
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
                    clause_type=redline.clause_type,
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
            ))

        # Sort by confidence (highest first), then by risk level
        risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        final.sort(key=lambda r: (
            risk_order.get(r.risk_level, 3),
            -r.confidence.score,
        ))

        return final

    # ======================================================================
    # Stage 5b: OFFSET-BASED DEDUPLICATION
    # ======================================================================

    def _dedupe_by_overlap(
        self,
        redlines: List[FinalRedline],
        full_text: str,
    ) -> List[FinalRedline]:
        """Remove duplicate findings that reference overlapping text regions.

        When two findings overlap in the source text, keep the higher-risk one.
        Tie-break by confidence score (higher wins).
        """
        if len(redlines) <= 1:
            return redlines

        risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}

        # Find character offset for each redline's text in the contract
        located: List[tuple] = []  # (start, end, index, redline)
        for i, r in enumerate(redlines):
            search_text = r.verified_text or r.original_text
            idx = full_text.find(search_text)
            if idx >= 0:
                located.append((idx, idx + len(search_text), i, r))
            else:
                # Couldn't locate — keep it (missing clause or fuzzy match)
                located.append((-1, -1, i, r))

        # Sort by start position
        located.sort(key=lambda x: (x[0], x[1]))

        keep = set(range(len(redlines)))

        for i in range(len(located)):
            if i not in keep:
                continue
            s1, e1, idx1, r1 = located[i]
            if s1 < 0:
                continue  # unlocated, always keep

            for j in range(i + 1, len(located)):
                if j not in keep:
                    continue
                s2, e2, idx2, r2 = located[j]
                if s2 < 0:
                    continue
                if s2 >= e1:
                    break  # no more overlaps (sorted by start)

                # Overlap detected — remove the lower-priority one
                rank1 = (risk_order.get(r1.risk_level, 3), -(r1.confidence.score if r1.confidence else 0))
                rank2 = (risk_order.get(r2.risk_level, 3), -(r2.confidence.score if r2.confidence else 0))

                if rank1 <= rank2:
                    keep.discard(idx2)
                else:
                    keep.discard(idx1)
                    break  # r1 was removed, stop comparing it

        return [redlines[i] for i in sorted(keep)]

    # ======================================================================
    # Stage 6: FIX GENERATION (batched AI calls)
    # ======================================================================

    _FIX_BATCH_SIZE = 10  # Max findings per batch API call

    async def _stage6_fix_generation(
        self,
        redlines: List[FinalRedline],
        extraction: "ExtractionResult",
        playbook_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> List[FinalRedline]:
        """Generate suggested_fix for RED and YELLOW redlines using batched AI calls.

        Instead of one API call per finding (N calls), batches findings into groups
        and generates fixes in bulk (N/10 calls). Dramatically reduces API usage.
        Falls back to per-finding generation if batch fails.
        """
        fixable = [r for r in redlines if r.risk_level in ("RED", "YELLOW")]
        if not fixable:
            return redlines

        defined_terms = ""
        if extraction.defined_terms:
            terms = extraction.defined_terms
            if isinstance(terms, dict):
                defined_terms = "\n".join(f"- {k}: {v}" for k, v in list(terms.items())[:20])
            elif isinstance(terms, list):
                defined_terms = "\n".join(f"- {t}" for t in terms[:20])

        # Build finding descriptors with stable IDs
        finding_map = {}  # id_str -> FinalRedline
        for i, r in enumerate(fixable):
            finding_map[f"finding-{i}"] = r

        # Batch findings into groups
        batch_items = []
        for id_str, r in finding_map.items():
            batch_items.append({
                "id": id_str,
                "rule_name": r.rule_name,
                "original_text": r.verified_text or r.original_text,
                "recommendation": r.recommendation,
            })

        fix_results: Dict[str, str] = {}
        for batch_start in range(0, len(batch_items), self._FIX_BATCH_SIZE):
            batch = batch_items[batch_start:batch_start + self._FIX_BATCH_SIZE]
            try:
                batch_fixes = await self._analyzer.generate_fixes_batch(
                    findings=batch,
                    playbook_rules=playbook_rules,
                    defined_terms=defined_terms,
                )
                fix_results.update(batch_fixes)
            except Exception as e:
                logger.warning("Batch fix generation failed for batch %d: %s",
                             batch_start // self._FIX_BATCH_SIZE + 1, e)

        # Apply fixes to redlines
        for id_str, redline in finding_map.items():
            fix = fix_results.get(id_str)
            if fix and isinstance(fix, str) and fix.strip():
                redline.suggested_fix = fix.strip()

        fixed_count = sum(1 for r in fixable if r.suggested_fix)
        logger.info("Fix generation: %d/%d findings got fixes (%d API calls)",
                    fixed_count, len(fixable),
                    (len(batch_items) + self._FIX_BATCH_SIZE - 1) // self._FIX_BATCH_SIZE)

        return redlines

    # ======================================================================
    # Helpers
    # ======================================================================

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
        }

        scores = {}
        for contract_type, patterns in type_signals.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            scores[contract_type] = score

        best_type = max(scores, key=scores.get)
        if scores[best_type] >= 2:  # Need at least 2 signals
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
        if playbook_rules:
            for pr in playbook_rules:
                name = pr.get("name", pr.get("rule_name", "")).lower()
                if name:
                    playbook_lookup[name] = pr

        redlines: List[RawRedline] = []
        for rm in rule_matches:
            pb_rule = playbook_lookup.get(rm.rule_name.lower())
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
