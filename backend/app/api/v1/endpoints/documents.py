"""
Document analysis endpoints.

Real implementation using the 5-stage analysis pipeline.  All endpoints
now return the unified RedlineItem schema (RiskItem has been retired).

ZERO DATA RETENTION (ZDR) MODE:
- When enabled, document text is processed in RAM only
- Text is never written to disk or database
- Only metadata (filename, risk count) is logged for audit
"""

import asyncio
import base64
import io
import json
import logging
import re
import time
from datetime import datetime, timezone
import httpx
import zipfile
from typing import List, Optional, Literal, Dict
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.document import Document, DocumentRisk, DocumentVersion, DocumentComparison, DocumentStatus
from app.models.document import RiskLevel as DBRiskLevel
from app.models.audit_log import log_audit_event
from app.models.playbook import Playbook
from app.api.v1.endpoints.auth import get_current_user, limiter
from app.api.v1.endpoints.billing import check_and_increment_quota
from app.core.permissions import require_permission
from app.services.rule_engine import RuleEngine, RuleMatch
from app.services.ai_service import AIService
from app.services.cache_service import get_cache
from app.services.playbook_cache import (
    get_default_rule_engine,
    get_cached_rule_engine,
    get_cached_rules_dicts,
    load_playbook,
    load_default_playbook_for_type,
)
from app.services.analysis_pipeline import (
    analysis_pipeline,
    PipelineResult,
    AIServiceError,
    AIServiceUnavailable,
    AIRateLimited,
    AIServiceTimeout,
    _sanitize_for_prompt,
)
from app.services.prompt_sanitizer import validate_contract_length
from app.services.structure_extractor import StructureExtractor, ContractMap
from app.core.config import settings

logger = logging.getLogger(__name__)


router = APIRouter()

# Zero Data Retention Mode - Enable for enterprise clients
# When True: No document text is stored, only audit logs
ZDR_MODE = getattr(settings, 'ZERO_DATA_RETENTION', True)  # Default: ON for safety


# ============================================================================
# Schemas - Strict RED/YELLOW/GREEN enum
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response shape for all non-2xx responses."""
    error: str
    message: str
    detail: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request to analyze document text."""
    text: str = Field(..., min_length=1, max_length=500000)
    playbook_id: Optional[str] = None
    filename: Optional[str] = Field(default="untitled.docx", max_length=255)
    party_side: Optional[str] = Field(default="buyer", pattern=r"^(buyer|seller|neutral)$")
    compliance_layers: List[str] = Field(default_factory=list, description="Compliance layer codes to activate, e.g. ['dpdp']")


class RedlineItem(BaseModel):
    """Single finding from contract analysis."""
    id: str
    risk_level: Literal["RED", "YELLOW", "GREEN"]
    rule_name: str
    clause_text: str              # Exact verbatim text from contract (verified)
    clause_type: str = ""
    explanation: str               # Why this is risky
    recommendation: str = ""       # Lawyer-readable guidance
    suggested_fix: Optional[str] = None  # Exact replacement text (generated)
    redline_type: Literal["violation", "missing"] = "violation"
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    confidence_breakdown: Optional[dict] = None  # Per-factor confidence scores (source trail)
    verification_status: Optional[str] = None
    is_deal_breaker: bool = False
    cross_references: Optional[List[str]] = None
    statutory_references: Optional[List[str]] = None  # Statute section citations (source trail)
    paragraph_hash: Optional[str] = None


class AnalysisResult(BaseModel):
    """Unified analysis response."""
    document_id: str
    filename: str
    executive_summary: List[str] = []
    risks: List[RedlineItem]
    total_risks: int
    risk_summary: dict  # {red: int, yellow: int, green: int}
    tokens_used: int = 0
    jurisdiction: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    pipeline_partial: bool = False
    source_type: str = "text"
    paragraph_hashes: Optional[Dict[str, str]] = None
    hallucination_stats: Optional[dict] = None  # Verification stage stats (source trail)
    compliance_scores: Optional[Dict[str, dict]] = None  # {layer_code: {score, compliant, ...}}


class RedlineRequest(BaseModel):
    """Request to generate redline suggestion."""
    document_id: str
    risk_id: str
    original_text: Optional[str] = None  # For ZDR mode when risk not in DB
    suggested_text: Optional[str] = None  # For ZDR mode
    paragraph_hash: Optional[str] = None  # For anchor search
    redline_type: Literal["violation", "missing"] = "violation"


class RedlineResponse(BaseModel):
    """Redline suggestion response."""
    original_text: str
    suggested_text: str
    ooxml: str
    match_confidence: float = 1.0  # Confidence of text anchor match (0.0-1.0)
    match_method: str = "exact"  # "hash", "exact", or "fuzzy"
    redline_type: str = "violation"  # "violation" or "missing"


class SummaryRequest(BaseModel):
    """Request for contract summary."""
    document_id: str
    contract_text: str = Field(..., min_length=1, max_length=500000)
    playbook_id: Optional[str] = None


class SummaryResponse(BaseModel):
    """AI-generated contract summary."""
    document_id: str
    summary: str
    risk_level: str  # Critical/High/Medium/Low
    key_concerns: List[str]
    recommendation: str
    tokens_used: int = 0


class ClauseAnalyzeRequest(BaseModel):
    """Request to analyze a single clause/selection."""
    clause_text: str = Field(..., min_length=20, max_length=10000)
    playbook_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    document_id: Optional[str] = None


class ClauseAnalyzeResponse(BaseModel):
    """Response from single-clause analysis."""
    risks: List[RedlineItem]
    tokens_used: int = 0
    analysis_time_ms: int = 0


class ExportReportRequest(BaseModel):
    """Request to generate a DOCX risk report."""
    filename: str = Field(..., max_length=255)
    executive_summary: List[str]
    redlines: List[Dict]
    risk_summary: Dict[str, int]


# ============================================================================
# Document List Endpoint - Scan History
# ============================================================================

class DocumentListItem(BaseModel):
    id: str
    filename: str
    status: str
    total_risks: int
    risk_summary: Optional[Dict] = None
    created_at: str
    version_number: int = 1
    content_hash: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentListItem]
    total: int


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's scanned documents (metadata only, ZDR-safe)."""
    # Set RLS context for tenant isolation
    from app.middleware.tenant_context import set_tenant_context
    await set_tenant_context(
        db=db,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
    )

    # Total count
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    query = (
        select(Document)
        .options(selectinload(Document.risks))
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[
            DocumentListItem(
                id=str(d.id),
                filename=d.filename,
                status=d.status.value if hasattr(d.status, 'value') else str(d.status),
                total_risks=d.total_risks or 0,
                risk_summary=d.risk_summary,
                created_at=d.created_at.isoformat() if d.created_at else "",
                version_number=d.version_number or 1,
                content_hash=d.content_hash,
            )
            for d in docs
        ],
        total=total,
    )


# ============================================================================
# Analyze Endpoint - Real Implementation
# ============================================================================

@router.post("/analyze", response_model=AnalysisResult)
@limiter.limit("20/minute")
async def analyze_document(
    request: Request,
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze document text for risks using the unified AI pipeline.

    Uses the 5-stage analysis pipeline (extraction, classification,
    risk assessment, hallucination verification, confidence scoring)
    with Stage 6 fix generation.

    ZERO DATA RETENTION (ZDR) MODE:
    - Document text is processed in RAM only, NEVER stored
    - Only metadata (filename, risk count) is stored for audit
    """
    # Contract size validation
    is_valid, msg = validate_contract_length(body.text, max_chars=500_000, min_chars=50)
    if not is_valid:
        raise HTTPException(
            status_code=413 if len(body.text or "") > 500_000 else 422,
            detail=msg,
        )

    # Set RLS context for tenant isolation
    from app.middleware.tenant_context import set_tenant_context
    await set_tenant_context(
        db=db,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
    )

    # Get client info for audit
    client_ip = request.client.host if request.client else None

    # Track analysis start time for processing_duration_ms
    analysis_start = time.monotonic()

    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"
    playbook = None

    if body.playbook_id:
        try:
            playbook = await load_playbook(
                db, body.playbook_id,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_name = playbook.name
                playbook_rules = get_cached_rules_dicts(playbook, include_verification=True)
        except Exception as e:
            logger.error("Error loading playbook: %s", e)

    # Auto-select a default playbook when user didn't pick one
    if not playbook_rules:
        try:
            from app.services.analysis_pipeline import AnalysisPipeline
            detected_type = AnalysisPipeline._detect_contract_type(body.text)
            if detected_type != "general":
                auto_playbook = await load_default_playbook_for_type(db, detected_type)
                if auto_playbook:
                    playbook = auto_playbook
                    playbook_name = f"{auto_playbook.name} (auto-selected)"
                    playbook_rules = get_cached_rules_dicts(auto_playbook, include_verification=True)
                    logger.info("Auto-selected playbook '%s' for contract type '%s'", auto_playbook.name, detected_type)
        except Exception as e:
            logger.warning("Auto-playbook selection failed (non-fatal): %s", e)

    # Merge compliance layer rules if requested
    compliance_layer_codes = body.compliance_layers or []
    compliance_layer_rule_names = set()  # Track which rule names came from compliance layers
    if compliance_layer_codes:
        try:
            from app.services.compliance_layer_service import get_layer_rules_as_dicts, merge_rules
            for layer_code in compliance_layer_codes:
                layer_rules = await get_layer_rules_as_dicts(db, layer_code)
                if not layer_rules:
                    logger.warning("Compliance layer '%s' not found or has no rules", layer_code)
                    continue
                compliance_layer_rule_names.update(r["name"] for r in layer_rules)
                playbook_rules = merge_rules(playbook_rules if playbook_rules else None, layer_rules)
                logger.info("Merged compliance layer '%s' (%d rules) into playbook", layer_code, len(layer_rules))
        except Exception as e:
            logger.warning("Compliance layer loading failed (non-fatal): %s", e)

    # Use playbook's party_side if set and user didn't explicitly choose
    effective_party_side = body.party_side or "buyer"
    if not body.party_side and playbook and hasattr(playbook, 'party_side') and playbook.party_side:
        effective_party_side = playbook.party_side

    try:
        # Sanitize playbook name before passing to AI
        playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        # Run the 5-stage analysis pipeline
        # Pipeline: extraction -> classification -> risk assessment ->
        # hallucination verification -> confidence scoring + fix generation
        try:
            pipeline_result: PipelineResult = await asyncio.wait_for(
                analysis_pipeline.run(
                    contract_text=body.text,
                    playbook_rules=playbook_rules,
                    playbook_name=playbook_name,
                    party_side=effective_party_side,
                ),
                timeout=600.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        risk_summary = {
            "red": sum(1 for r in pipeline_result.redlines if r.risk_level == "RED"),
            "yellow": sum(1 for r in pipeline_result.redlines if r.risk_level == "YELLOW"),
            "green": sum(1 for r in pipeline_result.redlines if r.risk_level == "GREEN"),
        }

        # Persist document metadata (ZDR-safe: no contract text stored)
        playbook_uuid = None
        if body.playbook_id:
            try:
                playbook_uuid = UUID(body.playbook_id)
            except ValueError:
                pass

        content_hash = Document.compute_content_hash(body.text)
        doc = Document(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            playbook_id=playbook_uuid,
            filename=body.filename or "untitled.docx",
            status=DocumentStatus.COMPLETED,
            total_risks=len(pipeline_result.redlines),
            risk_summary=risk_summary,
            content_hash=content_hash,
            processed_at=datetime.now(timezone.utc),
            word_count=len(body.text.split()),
            processing_duration_ms=int((time.monotonic() - analysis_start) * 1000),
        )
        db.add(doc)
        await db.flush()

        # Auto-create version snapshot
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            content_hash=content_hash,
            risk_summary=risk_summary,
            total_risks=len(pipeline_result.redlines),
            version_metadata={
                "playbook": playbook_name,
                "jurisdiction": pipeline_result.jurisdiction_code,
                "pipeline_partial": pipeline_result.partial,
            },
            created_by=current_user.id,
        )
        db.add(version)

        # Log audit event (same transaction — single commit for both)
        await log_audit_event(
            db=db,
            user=current_user,
            action="analyze",
            resource_type="contract",
            resource_name=body.filename or "untitled.docx",
            ip_address=client_ip,
            risk_count=len(pipeline_result.redlines),
            details=json.dumps({
                "playbook": playbook_name,
                "redlines_count": len(pipeline_result.redlines),
                "tokens_used": pipeline_result.total_tokens_used,
                "pipeline_partial": pipeline_result.partial,
                "stages": len(pipeline_result.stage_metrics),
            }),
        )
        await db.commit()
        await db.refresh(doc)
        doc_id = str(doc.id)

        # Build response — map FinalRedline to RedlineItem
        redline_items = [
            RedlineItem(
                id=str(uuid4()),
                risk_level=r.risk_level,
                rule_name=r.rule_name,
                clause_text=r.verified_text or r.original_text,
                clause_type=getattr(r, 'clause_type', ''),
                explanation=r.explanation,
                recommendation=r.recommendation,
                suggested_fix=getattr(r, 'suggested_fix', None),
                redline_type=r.redline_type,
                confidence=round(r.confidence.score, 3),
                confidence_level=r.confidence.level.value,
                confidence_breakdown=r.confidence.breakdown.to_dict() if hasattr(r.confidence, 'breakdown') and r.confidence.breakdown else None,
                verification_status=r.verification_status,
                is_deal_breaker=r.is_deal_breaker,
                cross_references=r.cross_references or None,
            )
            for r in pipeline_result.redlines
        ]

        # Get jurisdiction info from the pipeline result
        jurisdiction_code = pipeline_result.jurisdiction_code

        # Calculate compliance scores for each active layer
        compliance_scores = None
        if compliance_layer_codes and compliance_layer_rule_names:
            try:
                from app.services.compliance_layer_service import calculate_compliance_score
                compliance_scores = {}
                for layer_code in compliance_layer_codes:
                    # Find results that came from this layer's rules
                    layer_results = [
                        {"risk_level": r.risk_level, "is_deal_breaker": r.is_deal_breaker}
                        for r in pipeline_result.redlines
                        if getattr(r, 'rule_name', '') in compliance_layer_rule_names
                        or getattr(r, 'clause_type', '').startswith(f"{layer_code}_")
                    ]
                    if layer_results:
                        compliance_scores[layer_code] = calculate_compliance_score(layer_results)
            except Exception as e:
                logger.warning("Compliance score calculation failed (non-fatal): %s", e)

        return AnalysisResult(
            document_id=doc_id,
            filename=body.filename or "untitled.docx",
            executive_summary=pipeline_result.executive_summary,
            risks=redline_items,
            total_risks=len(redline_items),
            risk_summary=risk_summary,
            tokens_used=pipeline_result.total_tokens_used,
            pipeline_partial=pipeline_result.partial,
            jurisdiction=jurisdiction_code,
            jurisdiction_name=getattr(pipeline_result, 'jurisdiction_name', None),
            hallucination_stats=pipeline_result.hallucination_stats or None,
            compliance_scores=compliance_scores,
        )

    except HTTPException:
        raise
    except AIServiceUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": e.message, "error_code": e.error_code}
        )
    except AIRateLimited as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": e.message, "error_code": e.error_code}
        )
    except AIServiceTimeout as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"message": e.message, "error_code": e.error_code}
        )
    except AIServiceError as e:
        logger.error("AI analysis failed: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": e.message, "error_code": e.error_code}
        )
    except Exception as e:
        logger.error("Analysis failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Analysis failed. Please try again or contact support.", "error_code": "unknown_error"}
        )


# ============================================================================
# Async Analysis Endpoint (Phase 2.3) — returns 202 + job_id
# ============================================================================

class AsyncAnalyzeResponse(BaseModel):
    """Response from async analysis submission."""
    job_id: str
    document_id: str
    status: str = "queued"
    poll_url: str


class JobStatusResponse(BaseModel):
    """Job status polling response."""
    job_id: str
    status: str
    document_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@router.post("/analyze-async", response_model=AsyncAnalyzeResponse, status_code=202)
@limiter.limit("20/minute")
async def analyze_async(
    request: Request,
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Submit contract for async analysis. Returns 202 + job_id immediately.
    Poll GET /documents/jobs/{job_id} for results.
    """
    from app.workers.tasks import task_queue, AnalysisJob, JobStatus

    content_hash = Document.compute_content_hash(body.text)

    # Create document record
    playbook_uuid = None
    if body.playbook_id:
        try:
            playbook_uuid = UUID(body.playbook_id)
        except ValueError:
            pass

    doc = Document(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        playbook_id=playbook_uuid,
        filename=body.filename or "untitled.docx",
        status=DocumentStatus.PROCESSING,
        content_hash=content_hash,
    )
    db.add(doc)
    await db.flush()
    doc_id = str(doc.id)

    # Load playbook rules
    playbook_rules = []
    playbook_name = "Default"
    if body.playbook_id:
        try:
            playbook = await load_playbook(db, playbook_uuid, current_user_id=current_user.id, current_user_org_id=current_user.organization_id)
            if playbook:
                playbook_name = playbook.name
                playbook_rules = get_cached_rules_dicts(playbook, include_verification=True)
        except Exception as e:
            logger.error("Error loading playbook for async: %s", e)

    await db.commit()

    # Create job
    job = AnalysisJob(
        job_id=str(uuid4()),
        document_id=doc_id,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        contract_text=body.text,
        playbook_id=body.playbook_id,
        playbook_name=playbook_name,
        playbook_rules=playbook_rules,
    )

    await task_queue.enqueue(job)

    # If no Redis, run inline in background
    if not task_queue.is_redis_available:
        asyncio.create_task(task_queue.run_analysis_inline(job))

    return AsyncAnalyzeResponse(
        job_id=job.job_id,
        document_id=doc_id,
        status="queued",
        poll_url=f"/api/v1/documents/jobs/{job.job_id}",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll job status. Returns current status of an async analysis job."""
    from app.workers.tasks import task_queue

    status_data = await task_queue.get_job_status(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership
    if status_data.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return JobStatusResponse(
        job_id=job_id,
        status=status_data.get("status", "unknown"),
        document_id=status_data.get("document_id"),
        created_at=status_data.get("created_at"),
        completed_at=status_data.get("completed_at"),
        error=status_data.get("error"),
    )


# ============================================================================
# AI-First Analysis Endpoint - Full Gemini Analysis
# ============================================================================

@router.post("/analyze-full", response_model=AnalysisResult)
@limiter.limit("20/minute")
async def analyze_full_ai(
    request: Request,
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """AI-first analysis. Now redirects to unified /analyze endpoint.

    Kept for backward compatibility — same pipeline, same response.
    """
    return await analyze_document(
        request=request, body=body, current_user=current_user, db=db, _quota=_quota
    )


# ============================================================================
# Analyze Single Clause Endpoint (Phase 8)
# ============================================================================

@router.post("/analyze-clause", response_model=ClauseAnalyzeResponse)
@limiter.limit("30/minute")
async def analyze_clause(
    request: Request,
    body: ClauseAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze a single clause/text selection for risks.

    Lightweight alternative to /analyze — designed for inline
    selection scanning from the Word Add-in.
    """
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else None

    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"

    if body.playbook_id:
        try:
            playbook = await load_playbook(
                db, body.playbook_id,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_name = playbook.name
                playbook_rules = get_cached_rules_dicts(playbook, include_verification=True)
        except (ValueError, HTTPException):
            raise
        except Exception as e:
            logger.error("Error loading playbook for clause analysis: %s", e)

    try:
        ai_result = await asyncio.wait_for(
            analysis_pipeline.analyze_clause(
                clause_text=body.clause_text,
                playbook_rules=playbook_rules,
                playbook_name=playbook_name,
                jurisdiction=body.jurisdiction,
            ),
            timeout=30.0,
        )

        redline_items = [
            RedlineItem(
                id=item.get("id", str(uuid4())),
                risk_level=item.get("risk_level", "YELLOW"),
                rule_name=item.get("rule_name", "Unknown Rule"),
                clause_text=item.get("original_text", ""),
                clause_type=item.get("clause_type", ""),
                explanation=item.get("explanation", ""),
                recommendation=item.get("recommendation", ""),
                suggested_fix=item.get("suggested_fix"),
                redline_type=item.get("redline_type", "violation"),
            )
            for item in ai_result.get("redlines", [])
        ]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Log audit event
        await log_audit_event(
            db=db,
            user=current_user,
            action="clause_analyzed",
            resource_type="clause",
            resource_name=body.document_id or "inline-selection",
            ip_address=client_ip,
            risk_count=len(redline_items),
            details=json.dumps({
                "playbook": playbook_name,
                "risks_found": len(redline_items),
                "tokens_used": ai_result.get("tokens_used", 0),
                "analysis_time_ms": elapsed_ms,
            }),
        )
        await db.commit()

        return ClauseAnalyzeResponse(
            risks=redline_items,
            tokens_used=ai_result.get("tokens_used", 0),
            analysis_time_ms=elapsed_ms,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"message": "Clause analysis timed out. Please try again.", "error_code": "ai_timeout"},
        )
    except AIServiceUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": e.message, "error_code": e.error_code},
        )
    except AIRateLimited as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": e.message, "error_code": e.error_code},
        )
    except AIServiceError as e:
        logger.error("Clause analysis failed: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": e.message, "error_code": e.error_code},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Clause analysis failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Clause analysis failed. Please try again.", "error_code": "unknown_error"},
        )


# ============================================================================
# Batch Analysis Endpoints (Phase 8.6)
# ============================================================================

class BatchAnalyzeResponse(BaseModel):
    """Response from batch analysis initiation."""
    batch_id: str
    file_count: int
    status: str = "processing"


class BatchFileStatus(BaseModel):
    """Status of a single file in a batch."""
    filename: str
    status: Literal["queued", "processing", "completed", "error"]
    document_id: Optional[str] = None
    risk_summary: Optional[dict] = None
    error: Optional[str] = None


class BatchStatusResponse(BaseModel):
    """Full batch status."""
    batch_id: str
    files: List[BatchFileStatus]
    overall_progress: int  # 0-100
    status: Literal["processing", "completed", "partial_failure"]


# WARNING: In-memory batch tracking — state is lost on server restart or redeploy.
# This is acceptable for short-lived batch jobs (results polled within minutes),
# but a production-grade solution should use Redis or a database-backed store.
# Stale entries older than 1 hour are cleaned up on each new batch request.
_batch_store: Dict[str, dict] = {}


@router.post("/batch-analyze", response_model=BatchAnalyzeResponse)
@limiter.limit("5/minute")
async def batch_analyze(
    request: Request,
    files: List[UploadFile] = File(...),
    playbook_id: Optional[str] = Form(None),
    compliance_layers: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload multiple .docx files for concurrent batch analysis.

    Max 10 files per batch. Only .docx files are accepted.
    Returns immediately with a batch_id to poll for status.
    Charges 1 quota unit per valid file (not per batch).
    """
    # Parse compliance_layers from JSON string (Form doesn't support lists directly)
    compliance_layer_codes: List[str] = []
    if compliance_layers:
        try:
            compliance_layer_codes = json.loads(compliance_layers)
            if not isinstance(compliance_layer_codes, list):
                compliance_layer_codes = [str(compliance_layer_codes)]
        except (json.JSONDecodeError, TypeError):
            # Try comma-separated fallback
            compliance_layer_codes = [s.strip() for s in compliance_layers.split(",") if s.strip()]

    # Check quota upfront for all files (charge per valid file count after validation)
    # We'll charge after counting valid files below

    # Cleanup stale batch entries older than 1 hour
    now = datetime.now(timezone.utc)
    stale = [k for k, v in _batch_store.items()
             if 'completed_at' in v and (now - datetime.fromisoformat(v['completed_at'])).total_seconds() > 3600]
    for k in stale:
        del _batch_store[k]

    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Maximum 10 files per batch.", "error_code": "batch_too_large"},
        )

    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "At least one file is required.", "error_code": "no_files"},
        )

    batch_id = str(uuid4())
    file_statuses: List[dict] = []
    file_contents: List[dict] = []

    for idx, upload_file in enumerate(files):
        filename = upload_file.filename or f"file_{idx}.docx"

        # Validate file extension
        if not filename.lower().endswith(".docx"):
            file_statuses.append({
                "filename": filename,
                "status": "error",
                "document_id": None,
                "risk_summary": None,
                "error": "Only .docx files are supported.",
            })
            file_contents.append({"filename": filename, "text": None})
            continue

        # Read file and extract text from .docx
        try:
            raw_bytes = await upload_file.read()
            if len(raw_bytes) > 20 * 1024 * 1024:  # 20MB
                file_statuses.append({
                    "filename": filename,
                    "status": "error",
                    "document_id": None,
                    "risk_summary": None,
                    "error": "File exceeds 20MB limit.",
                })
                file_contents.append({"filename": filename, "text": None})
                continue
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ValueError("Invalid .docx: missing word/document.xml")
                xml_content = zf.read("word/document.xml").decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", xml_content)
                text = re.sub(r"\s+", " ", text).strip()

            if len(text) < 50:
                file_statuses.append({
                    "filename": filename,
                    "status": "error",
                    "document_id": None,
                    "risk_summary": None,
                    "error": "Document contains too little text to analyze.",
                })
                file_contents.append({"filename": filename, "text": None})
                continue

            file_statuses.append({
                "filename": filename,
                "status": "queued",
                "document_id": None,
                "risk_summary": None,
                "error": None,
            })
            file_contents.append({"filename": filename, "text": text})

        except (zipfile.BadZipFile, ValueError) as e:
            file_statuses.append({
                "filename": filename,
                "status": "error",
                "document_id": None,
                "risk_summary": None,
                "error": "Failed to read .docx file",
            })
            file_contents.append({"filename": filename, "text": None})

    # Charge quota per valid file (H5 fix: was only charging 1 for entire batch)
    valid_file_count = sum(1 for fc in file_contents if fc["text"] is not None)
    if valid_file_count > 0:
        from app.api.v1.endpoints.billing import get_plan_info, _get_user_scan_count, _increment_usage, get_user_subscription
        subscription = await get_user_subscription(current_user, db)
        plan = subscription.plan.value if subscription else current_user.subscription_tier.value
        plan_info = get_plan_info(plan)
        used = await _get_user_scan_count(current_user, db)
        limit = plan_info["scans"]

        if limit > 0 and used + valid_file_count > limit:
            overage_price = plan_info.get("overage_price_inr", 0)
            if overage_price <= 0 or plan == "free":
                raise HTTPException(
                    status_code=402,
                    detail={
                        "message": f"Insufficient quota. Need {valid_file_count} scans but only {max(0, limit - used)} remaining.",
                        "error_code": "quota_exceeded",
                        "used": used,
                        "limit": limit,
                        "needed": valid_file_count,
                    },
                )

        for _ in range(valid_file_count):
            await _increment_usage(current_user, db)

    # Store batch info (in-memory for fast polling)
    _batch_store[batch_id] = {
        "user_id": str(current_user.id),
        "files": file_statuses,
        "playbook_id": playbook_id,
        "compliance_layers": compliance_layer_codes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to database (survives restarts)
    try:
        from app.models.batch_job import BatchJob, BatchJobFile
        batch_job = BatchJob(
            id=UUID(batch_id),
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            status="processing",
            total_files=len(files),
            playbook_id=UUID(playbook_id) if playbook_id else None,
            compliance_layers=compliance_layer_codes or [],
        )
        db.add(batch_job)
        for fs in file_statuses:
            bjf = BatchJobFile(
                batch_id=UUID(batch_id),
                filename=fs["filename"],
                status=fs["status"],
                error_message=fs.get("error"),
            )
            db.add(bjf)
        await db.flush()
    except Exception as e:
        logger.warning("Failed to persist batch job to DB (non-fatal): %s", e)

    # Audit log
    await log_audit_event(
        db=db,
        user=current_user,
        action="batch_analyze",
        resource_type="document",
        details=json.dumps({"batch_id": batch_id, "file_count": len(files)}),
    )
    await db.commit()

    # Launch background processing
    asyncio.create_task(
        _process_batch(batch_id, file_contents, playbook_id, str(current_user.id), organization_id=str(current_user.organization_id) if current_user.organization_id else None, compliance_layer_codes=compliance_layer_codes)
    )

    logger.info(f"Batch {batch_id} created with {len(files)} files for user {current_user.id}")

    return BatchAnalyzeResponse(
        batch_id=batch_id,
        file_count=len(files),
        status="processing",
    )


async def _process_batch(
    batch_id: str,
    file_contents: List[dict],
    playbook_id: Optional[str],
    user_id: str,
    organization_id: Optional[str] = None,
    compliance_layer_codes: Optional[List[str]] = None,
):
    """Background task to process all files in a batch concurrently."""
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent analyses

    # Load playbook rules once if playbook_id is given
    playbook_rules = None
    playbook_name = None
    if playbook_id:
        try:
            async with AsyncSessionLocal() as db:
                from uuid import UUID as _UUID
                _uid = _UUID(user_id) if user_id else None
                _oid = _UUID(organization_id) if organization_id else None
                playbook = await load_playbook(db, playbook_id, current_user_id=_uid, current_user_org_id=_oid)
                if playbook:
                    playbook_name = playbook.name
                    playbook_rules = [
                        {"name": r.clause_type, "description": r.primary_position, "severity": r.risk_level.value}
                        for r in (playbook.rules_list or [])
                    ]
        except Exception as e:
            logger.warning("Batch %s: failed to load playbook %s: %s", batch_id, playbook_id, e)

    # Load and merge compliance layer rules once (same as single-file analyze)
    compliance_layer_rule_names: set = set()
    if compliance_layer_codes:
        try:
            async with AsyncSessionLocal() as db:
                from app.services.compliance_layer_service import get_layer_rules_as_dicts, merge_rules
                for layer_code in compliance_layer_codes:
                    layer_rules = await get_layer_rules_as_dicts(db, layer_code)
                    if layer_rules:
                        compliance_layer_rule_names.update(r["name"] for r in layer_rules)
                        playbook_rules = merge_rules(playbook_rules, layer_rules)
        except Exception as e:
            logger.warning("Batch %s: failed to load compliance layers %s: %s", batch_id, compliance_layer_codes, e)

    async def _analyze_single(idx: int, file_info: dict):
        """Analyze a single file within the batch."""
        async with semaphore:
            batch = _batch_store.get(batch_id)
            if not batch:
                return

            # Skip files that already errored during upload
            if batch["files"][idx]["status"] == "error":
                return

            if file_info["text"] is None:
                return

            batch["files"][idx]["status"] = "processing"

            try:
                file_start = time.monotonic()
                pipeline_result: PipelineResult = await asyncio.wait_for(
                    analysis_pipeline.run(
                        contract_text=file_info["text"],
                        playbook_rules=playbook_rules,
                        playbook_name=playbook_name or "Default",
                    ),
                    timeout=600.0,
                )
                file_duration_ms = int((time.monotonic() - file_start) * 1000)

                risk_summary = {
                    "red": sum(1 for r in pipeline_result.redlines if r.risk_level == "RED"),
                    "yellow": sum(1 for r in pipeline_result.redlines if r.risk_level == "YELLOW"),
                    "green": sum(1 for r in pipeline_result.redlines if r.risk_level == "GREEN"),
                    "total": len(pipeline_result.redlines),
                }

                # Persist batch file result to database so analytics fields are populated
                try:
                    async with AsyncSessionLocal() as db_session:
                        content_hash = Document.compute_content_hash(file_info["text"])
                        batch_doc = Document(
                            user_id=UUID(user_id),
                            filename=file_info["filename"],
                            status=DocumentStatus.COMPLETED,
                            total_risks=len(pipeline_result.redlines),
                            risk_summary=risk_summary,
                            content_hash=content_hash,
                            word_count=len(file_info["text"].split()),
                            processing_duration_ms=file_duration_ms,
                            processed_at=datetime.now(timezone.utc),
                        )
                        db_session.add(batch_doc)
                        # Audit log for individual batch file result
                        await log_audit_event(
                            db=db_session, user=None, action="batch_file_analyzed",
                            resource_type="document", resource_name=file_info["filename"],
                            status="success", risk_count=len(pipeline_result.redlines),
                            user_email="batch", organization_id=None,
                            details=json.dumps({"batch_id": batch_id, "file_index": idx}),
                        )
                        await db_session.commit()
                        await db_session.refresh(batch_doc)
                        doc_id = str(batch_doc.id)
                except Exception as db_err:
                    logger.warning(f"Batch {batch_id}: failed to persist doc for '{file_info['filename']}': {db_err}")
                    doc_id = str(uuid4())  # Fallback to ephemeral ID

                batch["files"][idx]["status"] = "completed"
                batch["files"][idx]["document_id"] = doc_id
                batch["files"][idx]["risk_summary"] = risk_summary

                logger.info(
                    f"Batch {batch_id} file '{file_info['filename']}': "
                    f"completed with {risk_summary['total']} risks"
                )

            except asyncio.TimeoutError:
                batch["files"][idx]["status"] = "error"
                batch["files"][idx]["error"] = "Analysis timed out after 120 seconds."
                logger.warning(f"Batch {batch_id} file '{file_info['filename']}': timed out")

            except Exception as e:
                batch["files"][idx]["status"] = "error"
                batch["files"][idx]["error"] = "Analysis failed"
                logger.error(f"Batch {batch_id} file '{file_info['filename']}': error - {e}", exc_info=True)

    # Run all file analyses concurrently (bounded by semaphore)
    tasks = [
        _analyze_single(idx, file_info)
        for idx, file_info in enumerate(file_contents)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Update overall batch status
    batch = _batch_store.get(batch_id)
    if batch:
        has_error = any(f["status"] == "error" for f in batch["files"])
        has_completed = any(f["status"] == "completed" for f in batch["files"])
        if has_error and has_completed:
            batch["overall_status"] = "partial_failure"
        elif has_error:
            batch["overall_status"] = "partial_failure"
        else:
            batch["overall_status"] = "completed"

        batch["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Batch {batch_id} finished: {batch['overall_status']}")

    # Update DB records
    try:
        async with AsyncSessionLocal() as db_session:
            from app.models.batch_job import BatchJob, BatchJobFile
            result = await db_session.execute(
                select(BatchJob).options(selectinload(BatchJob.files)).where(BatchJob.id == UUID(batch_id))
            )
            batch_job = result.scalar_one_or_none()
            if batch_job and batch:
                completed = sum(1 for f in batch["files"] if f["status"] == "completed")
                failed = sum(1 for f in batch["files"] if f["status"] == "error")
                batch_job.completed_files = completed
                batch_job.failed_files = failed
                batch_job.status = batch.get("overall_status", "completed")
                batch_job.completed_at = datetime.now(timezone.utc)
                # Aggregate risk summary
                agg = {"red": 0, "yellow": 0, "green": 0, "total": 0}
                for f in batch["files"]:
                    rs = f.get("risk_summary")
                    if rs:
                        for k in agg:
                            agg[k] += rs.get(k, 0)
                batch_job.risk_summary = agg
                # Update per-file records
                for bjf in batch_job.files:
                    for f in batch["files"]:
                        if f["filename"] == bjf.filename:
                            bjf.status = f["status"]
                            bjf.error_message = f.get("error")
                            bjf.risk_summary = f.get("risk_summary")
                            bjf.document_id = UUID(f["document_id"]) if f.get("document_id") else None
                            break
                await db_session.commit()
    except Exception as e:
        logger.warning("Failed to update batch job %s in DB: %s", batch_id, e)


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a batch analysis job.

    Returns progress and per-file status for the given batch_id.
    Checks in-memory store first, falls back to database.
    """
    batch = _batch_store.get(batch_id)

    if batch:
        # In-memory path (fast, for active batches)
        if batch["user_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Access denied.", "error_code": "forbidden"},
            )
        file_statuses = [BatchFileStatus(**f) for f in batch["files"]]
    else:
        # DB fallback (for batches after server restart)
        try:
            from app.models.batch_job import BatchJob, BatchJobFile
            result = await db.execute(
                select(BatchJob)
                .options(selectinload(BatchJob.files))
                .where(BatchJob.id == UUID(batch_id), BatchJob.user_id == current_user.id)
            )
            batch_job = result.scalar_one_or_none()
            if not batch_job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"message": "Batch not found.", "error_code": "batch_not_found"},
                )
            file_statuses = [
                BatchFileStatus(
                    filename=f.filename,
                    status=f.status,
                    document_id=str(f.document_id) if f.document_id else None,
                    risk_summary=f.risk_summary,
                    error=f.error_message,
                )
                for f in sorted(batch_job.files, key=lambda x: x.created_at)
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("DB fallback for batch %s failed: %s", batch_id, e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Batch not found.", "error_code": "batch_not_found"},
            )

    total = len(file_statuses)
    done = sum(1 for f in file_statuses if f.status in ("completed", "error"))
    progress = int((done / total) * 100) if total > 0 else 0

    if progress == 100:
        has_error = any(f.status == "error" for f in file_statuses)
        has_completed = any(f.status == "completed" for f in file_statuses)
        if has_error and has_completed:
            overall_status = "partial_failure"
        elif has_error:
            overall_status = "partial_failure"
        else:
            overall_status = "completed"
    else:
        overall_status = "processing"

    return BatchStatusResponse(
        batch_id=batch_id,
        files=file_statuses,
        overall_progress=progress,
        status=overall_status,
    )


# ============================================================================
# Batch History Endpoint
# ============================================================================


class BatchHistoryItem(BaseModel):
    """Summary of a past batch job."""
    batch_id: str
    created_at: str
    status: str
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    risk_summary: Optional[dict] = None
    compliance_layers: Optional[list] = None


class BatchHistoryResponse(BaseModel):
    """Paginated batch history."""
    batches: List[BatchHistoryItem]
    total: int
    page: int
    page_size: int


@router.get("/batches", response_model=BatchHistoryResponse)
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's past batch jobs with pagination."""
    from app.models.batch_job import BatchJob

    # Count total
    count_result = await db.execute(
        select(func.count(BatchJob.id)).where(BatchJob.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(BatchJob)
        .where(BatchJob.user_id == current_user.id)
        .order_by(BatchJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    batches = result.scalars().all()

    return BatchHistoryResponse(
        batches=[
            BatchHistoryItem(
                batch_id=str(b.id),
                created_at=b.created_at.isoformat() if b.created_at else "",
                status=b.status or "unknown",
                total_files=b.total_files or 0,
                completed_files=b.completed_files or 0,
                failed_files=b.failed_files or 0,
                risk_summary=b.risk_summary,
                compliance_layers=b.compliance_layers if isinstance(b.compliance_layers, list) else [],
            )
            for b in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Compliance Layer Endpoints
# ============================================================================


class ComplianceLayerSummary(BaseModel):
    """Summary of a compliance layer."""
    code: str
    name: str
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    version: int = 1
    rule_count: int = 0


class ComplianceLayerRuleResponse(BaseModel):
    """A single compliance layer rule."""
    clause_type: str
    risk_level: str
    is_deal_breaker: bool = False
    primary_position: str
    fallback_position: Optional[str] = None
    detection_mode: str = "ai_with_keywords"
    risk_description: Optional[str] = None


class ComplianceLayerDetail(BaseModel):
    """Detailed compliance layer with rules."""
    code: str
    name: str
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    version: int = 1
    rules: List[ComplianceLayerRuleResponse] = []


@router.get("/compliance-layers", response_model=List[ComplianceLayerSummary])
async def list_compliance_layers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all active compliance layers with rule counts."""
    from app.services.compliance_layer_service import get_active_layers
    layers = await get_active_layers(db)
    return [ComplianceLayerSummary(**layer) for layer in layers]


@router.get("/compliance-layers/{code}", response_model=ComplianceLayerDetail)
async def get_compliance_layer(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a compliance layer with its rules."""
    from app.services.compliance_layer_service import get_layer_by_code
    layer = await get_layer_by_code(db, code)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Compliance layer '{code}' not found.", "error_code": "layer_not_found"},
        )
    return ComplianceLayerDetail(
        code=layer.code,
        name=layer.name,
        description=layer.description,
        jurisdiction=layer.jurisdiction,
        version=layer.version,
        rules=[
            ComplianceLayerRuleResponse(
                clause_type=rule.clause_type,
                risk_level=rule.risk_level or "YELLOW",
                is_deal_breaker=rule.is_deal_breaker,
                primary_position=rule.primary_position,
                fallback_position=rule.fallback_position,
                detection_mode=rule.detection_mode or "ai_with_keywords",
                risk_description=rule.risk_description,
            )
            for rule in sorted(layer.rules, key=lambda r: r.sort_order)
        ],
    )


# ============================================================================
# Verification Summary Endpoint (Source Trail)
# ============================================================================


class VerificationSummaryResponse(BaseModel):
    """Verification transparency summary for source trail."""
    total_findings: int = 0
    verified_findings: int = 0
    exact_match: int = 0
    normalized_match: int = 0
    fuzzy_corrected: int = 0
    not_found: int = 0
    pass_rate: float = 0.0
    hallucination_rate: float = 0.0
    avg_confidence: float = 0.0
    confidence_distribution: dict = {}  # {HIGH: n, MEDIUM: n, LOW: n}
    industry_benchmark: str = ""


@router.get("/{document_id}/verification-summary", response_model=VerificationSummaryResponse)
async def get_verification_summary(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return verification transparency summary for a document's analysis.

    Calculates verification pass rate, hallucination rate, and confidence
    distribution from persisted risk data. Enables source trail UI.
    """
    # Verify document ownership
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Document not found.", "error_code": "not_found"},
        )

    # Load risks
    result = await db.execute(
        select(DocumentRisk).where(DocumentRisk.document_id == document_id)
    )
    risks = result.scalars().all()

    total = len(risks)
    if total == 0:
        return VerificationSummaryResponse(
            total_findings=0,
            industry_benchmark="No findings to verify.",
        )

    # Count verification statuses
    exact = sum(1 for r in risks if getattr(r, 'verification_status', '') == 'exact_match')
    normalized = sum(1 for r in risks if getattr(r, 'verification_status', '') == 'normalized_match')
    fuzzy = sum(1 for r in risks if getattr(r, 'verification_status', '') == 'fuzzy_corrected')
    not_found = sum(1 for r in risks if getattr(r, 'verification_status', '') in ('not_found', 'rejected'))
    verified = exact + normalized + fuzzy

    # Confidence distribution
    conf_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    conf_sum = 0.0
    for r in risks:
        level = getattr(r, 'confidence_level', None) or 'MEDIUM'
        conf_dist[level] = conf_dist.get(level, 0) + 1
        conf_sum += getattr(r, 'confidence', 0.0) or 0.0

    pass_rate = round(verified / total * 100, 1) if total > 0 else 0.0
    hallucination_rate = round(not_found / total * 100, 1) if total > 0 else 0.0
    avg_confidence = round(conf_sum / total, 3) if total > 0 else 0.0

    # Industry benchmark comparison
    benchmark = "Industry average hallucination rate for AI contract review is 8-15%."
    if hallucination_rate <= 5:
        benchmark += " Your analysis is EXCELLENT — well below industry average."
    elif hallucination_rate <= 10:
        benchmark += " Your analysis is GOOD — at or below industry average."
    elif hallucination_rate <= 15:
        benchmark += " Your analysis is FAIR — within industry average range."
    else:
        benchmark += " Your analysis has elevated hallucination rate — consider re-running with stricter playbook."

    return VerificationSummaryResponse(
        total_findings=total,
        verified_findings=verified,
        exact_match=exact,
        normalized_match=normalized,
        fuzzy_corrected=fuzzy,
        not_found=not_found,
        pass_rate=pass_rate,
        hallucination_rate=hallucination_rate,
        avg_confidence=avg_confidence,
        confidence_distribution=conf_dist,
        industry_benchmark=benchmark,
    )


# Generate Clause Endpoint
# ============================================================================

class GenerateClauseRequest(BaseModel):
    """Request to generate a contract clause."""
    clause_type: str = Field(..., min_length=1, max_length=200)
    playbook_id: Optional[UUID] = None
    contract_context: Optional[str] = Field(default=None, max_length=50000)


class GenerateClauseResponse(BaseModel):
    """Response with generated clause."""
    clause_text: str
    reasoning: str


@router.post("/generate-clause", response_model=GenerateClauseResponse)
@limiter.limit("30/minute")
async def generate_clause(
    request: Request,
    body: GenerateClauseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a contract clause using AI.

    Uses Gemini to draft a clause based on:
    - clause_type: The type of clause to generate (e.g., "Indemnification")
    - playbook_id: Optional playbook to align with firm's position
    - contract_context: Optional surrounding text for tone/style matching
    """
    try:
        # Load playbook rules if provided (with authorization check)
        playbook_rules = None
        if body.playbook_id:
            playbook = await load_playbook(
                db, body.playbook_id,
                auth_in_query=True,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_rules = get_cached_rules_dicts(playbook)

        try:
            generated = await asyncio.wait_for(
                analysis_pipeline.generate_clause(
                    clause_type=body.clause_type,
                    contract_context=body.contract_context or "",
                    playbook_rules=playbook_rules,
                ),
                timeout=600.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        # Audit log
        await log_audit_event(
            db=db,
            user=current_user,
            action="clause_generation",
            resource_type="clause",
            details=json.dumps({"clause_type": body.clause_type, "playbook_id": str(body.playbook_id) if body.playbook_id else None}),
        )
        await db.commit()

        return GenerateClauseResponse(
            clause_text=generated["clause_text"],
            reasoning=generated["reasoning"],
        )

    except AIServiceUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"message": e.message, "error_code": e.error_code})
    except AIRateLimited as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceTimeout as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceError as e:
        logger.error("Clause generation failed: %s", e.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"message": e.message, "error_code": e.error_code})
    except Exception as e:
        logger.error("Clause generation failed", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Clause generation failed. Please try again.", "error_code": "unknown_error"})


# ============================================================================
# Generate Fix Endpoint
# ============================================================================

class GenerateFixRequest(BaseModel):
    """Request to generate exact replacement/insertion text for a specific risk."""
    original_text: str = Field(..., min_length=1, max_length=10000)
    recommendation: str = Field(..., min_length=1, max_length=5000)
    rule_name: str = Field(..., min_length=1, max_length=200)
    redline_type: Literal["violation", "missing"] = "violation"
    surrounding_context: Optional[str] = Field(default=None, max_length=10000)
    playbook_id: Optional[UUID] = None
    contract_text: Optional[str] = Field(default=None, max_length=500000)


class GenerateFixResponse(BaseModel):
    """Response with generated fix text."""
    fix_text: str
    reasoning: str
    fix_verified: bool = True
    fix_warnings: Optional[List[str]] = None


@router.post("/generate-fix", response_model=GenerateFixResponse)
@limiter.limit("30/minute")
async def generate_fix(
    request: Request,
    body: GenerateFixRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate exact replacement/insertion text for a specific risk.

    Takes a risk's original text + recommendation (guidance) and produces
    exact text that can be inserted into the Word document.
    Uses Flash-Lite model for fast, cheap per-issue generation.
    """
    try:
        # Load playbook rules if provided (with authorization check)
        playbook_rules = None
        if body.playbook_id:
            playbook = await load_playbook(
                db, body.playbook_id,
                auth_in_query=True,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_rules = get_cached_rules_dicts(playbook)

        try:
            generated = await asyncio.wait_for(
                analysis_pipeline.generate_fix(
                    original_text=body.original_text,
                    recommendation=body.recommendation,
                    rule_name=body.rule_name,
                    redline_type=body.redline_type,
                    surrounding_context=body.surrounding_context or "",
                    playbook_rules=playbook_rules,
                ),
                timeout=600.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        # Verify the generated fix before returning
        fix_verified = True
        fix_warnings: List[str] = []
        if body.contract_text:
            from app.services.fix_verifier import FixVerifier
            verifier = FixVerifier()
            verification = verifier.verify_fix(
                fix_text=generated["fix_text"],
                original_text=body.original_text,
                contract_text=body.contract_text,
                rule_name=body.rule_name,
            )
            fix_verified = verification.passed
            fix_warnings = verification.warnings + verification.errors

        # Audit log
        await log_audit_event(
            db=db,
            user=current_user,
            action="fix_generation",
            resource_type="clause",
            details=json.dumps({"rule_name": body.rule_name, "redline_type": body.redline_type, "fix_verified": fix_verified}),
        )
        await db.commit()

        return GenerateFixResponse(
            fix_text=generated["fix_text"],
            reasoning=generated["reasoning"],
            fix_verified=fix_verified,
            fix_warnings=fix_warnings if fix_warnings else None,
        )

    except AIServiceUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"message": e.message, "error_code": e.error_code})
    except AIRateLimited as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceTimeout as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceError as e:
        logger.error("Fix generation failed: %s", e.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"message": e.message, "error_code": e.error_code})
    except Exception as e:
        logger.error("Fix generation failed", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Fix generation failed. Please try again.", "error_code": "unknown_error"})


# ============================================================================
# Research Clause Endpoint
# ============================================================================

class ResearchClauseRequest(BaseModel):
    """Request to research case law for a clause."""
    clause_text: str = Field(..., min_length=1, max_length=10000)
    clause_type: Optional[str] = Field(default=None, max_length=200)


class CaseLawItem(BaseModel):
    """A single case law reference."""
    case_name: str
    citation: str
    year: int = 0
    court: str = ""
    holding: str = ""
    relevance: str = ""


class ResearchClauseResponse(BaseModel):
    """Response with case law research results."""
    cases: List[CaseLawItem]
    legal_principle: str
    disclaimer: str


@router.post("/research-clause", response_model=ResearchClauseResponse)
@limiter.limit("30/minute")
async def research_clause(
    request: Request,
    body: ResearchClauseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Research relevant Indian case law for a flagged clause.

    Uses Gemini's knowledge to find SC/HC decisions related to the clause.
    Always includes a disclaimer about verifying citations.
    """
    try:
        try:
            result = await asyncio.wait_for(
                analysis_pipeline.research_clause(
                    clause_text=body.clause_text,
                    clause_type=body.clause_type or "",
                ),
                timeout=600.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        # Audit log
        await log_audit_event(
            db=db,
            user=current_user,
            action="clause_research",
            resource_type="clause",
            details=json.dumps({"clause_type": body.clause_type, "cases_found": len(result.get("cases", []))}),
        )
        await db.commit()

        cases = []
        for c in result.get("cases", []):
            cases.append(CaseLawItem(
                case_name=c.get("case_name", ""),
                citation=c.get("citation", ""),
                year=c.get("year", 0),
                court=c.get("court", ""),
                holding=c.get("holding", ""),
                relevance=c.get("relevance", ""),
            ))

        return ResearchClauseResponse(
            cases=cases,
            legal_principle=result.get("legal_principle", ""),
            disclaimer=result.get("disclaimer", "AI-suggested references — verify independently."),
        )

    except AIServiceUnavailable as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"message": e.message, "error_code": e.error_code})
    except AIRateLimited as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceTimeout as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail={"message": e.message, "error_code": e.error_code})
    except AIServiceError as e:
        logger.error("Research clause failed: %s", e.message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"message": e.message, "error_code": e.error_code})
    except Exception as e:
        logger.error("Research clause failed", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Research failed. Please try again.", "error_code": "unknown_error"})


# ============================================================================
# Contract Comparison Endpoint
# ============================================================================

class CompareRequest(BaseModel):
    """Request to compare two contract versions."""
    text_a: str = Field(..., min_length=1, max_length=200000)
    text_b: str = Field(..., min_length=1, max_length=200000)
    playbook_id: Optional[UUID] = None


class DiffChangeResponse(BaseModel):
    """A single change in the diff."""
    change_type: str  # "added", "removed", "modified"
    text_a: str
    text_b: str
    position: int
    similarity: float = 0.0
    ai_assessment: Optional[str] = None


class CompareResponse(BaseModel):
    """Response with diff results."""
    changes: List[DiffChangeResponse]
    total_changes: int
    paragraphs_a: int
    paragraphs_b: int
    summary: str


@router.post("/compare", response_model=CompareResponse)
@limiter.limit("30/minute")
async def compare_contracts(
    request: Request,
    body: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two contract versions.

    Returns paragraph-level diff with optional AI commentary
    on whether changes favor the user or counterparty.
    """
    from app.services.contract_differ import compute_diff_with_ai

    try:
        # Load playbook rules if provided (with authorization check)
        playbook_rules = None
        if body.playbook_id:
            playbook = await load_playbook(
                db, body.playbook_id,
                auth_in_query=True,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_rules = get_cached_rules_dicts(playbook, include_deal_breaker=False)

        diff = await compute_diff_with_ai(
            text_a=body.text_a,
            text_b=body.text_b,
            playbook_rules=playbook_rules,
        )

        # Audit log
        await log_audit_event(
            db=db,
            user=current_user,
            action="contract_comparison",
            resource_type="document",
            details=json.dumps({"total_changes": diff.total_changes, "playbook_id": str(body.playbook_id) if body.playbook_id else None}),
        )
        await db.commit()

        return CompareResponse(
            changes=[
                DiffChangeResponse(
                    change_type=c.change_type,
                    text_a=c.text_a,
                    text_b=c.text_b,
                    position=c.position,
                    similarity=c.similarity,
                    ai_assessment=c.ai_assessment,
                )
                for c in diff.changes
            ],
            total_changes=diff.total_changes,
            paragraphs_a=diff.paragraphs_a,
            paragraphs_b=diff.paragraphs_b,
            summary=diff.summary,
        )

    except Exception as e:
        logger.error("Contract comparison failed", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Comparison failed. Please try again.", "error_code": "comparison_error"})


# ============================================================================
# Analyze File Endpoint - DOCX Upload (Box 1 Integration)
# ============================================================================

@router.post("/analyze-file", response_model=AnalysisResult)
@limiter.limit("20/minute")
async def analyze_file(
    request: Request,
    file: UploadFile = File(...),
    playbook_id: Optional[str] = Form(None),
    party_side: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze uploaded DOCX file using the unified AI pipeline.

    This endpoint preserves document structure (headings, sections) and
    generates SHA-256 paragraph hashes for drift detection during redlining.

    Process:
    1. StructureExtractor parses DOCX → ContractMap (preserves structure + hashes)
    2. Full text fed into 6-stage AI pipeline (same as /analyze)
    3. Response enriched with paragraph_hashes for frontend drift detection
    """
    # Validate file type
    filename = file.filename or "document.docx"
    content_type = file.content_type or ""
    
    if not (filename.endswith(".docx") or "wordprocessingml" in content_type):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported. For raw text, use /analyze endpoint."
        )
    
    # Get client info for audit
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Read file content
    file_bytes = await file.read()

    # Validate file size (10 MB max)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail={"message": "File too large. Maximum size is 10 MB.", "error_code": "file_too_large"})

    # Validate DOCX magic bytes (ZIP/PK header)
    if not file_bytes[:4] == b'PK\x03\x04':
        raise HTTPException(status_code=400, detail={"message": "Invalid file format. Only .docx files are supported.", "error_code": "invalid_file_format"})

    # Box 1: Extract structure from DOCX
    extractor = StructureExtractor()
    try:
        contract_map = extractor.extract_from_docx(file_bytes)
    except Exception as e:
        logger.error("Failed to parse DOCX file: %s", e)
        raise HTTPException(
            status_code=400,
            detail="Failed to parse DOCX file. Please ensure the file is a valid .docx document."
        )
    
    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"
    playbook = None

    if playbook_id:
        try:
            playbook = await load_playbook(
                db, playbook_id,
                current_user_id=current_user.id,
                current_user_org_id=current_user.organization_id,
            )
            if playbook:
                playbook_name = playbook.name
                playbook_rules = get_cached_rules_dicts(playbook, include_verification=True)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid playbook_id format")
        except Exception as e:
            logger.error("Error loading playbook for file analysis: %s", e)

    # Auto-select a default playbook when user didn't pick one
    if not playbook_rules:
        try:
            from app.services.analysis_pipeline import AnalysisPipeline
            detected_type = AnalysisPipeline._detect_contract_type(contract_map.full_text)
            if detected_type != "general":
                auto_playbook = await load_default_playbook_for_type(db, detected_type)
                if auto_playbook:
                    playbook = auto_playbook
                    playbook_name = f"{auto_playbook.name} (auto-selected)"
                    playbook_rules = get_cached_rules_dicts(auto_playbook, include_verification=True)
                    logger.info("Auto-selected playbook '%s' for file analysis, type '%s'", auto_playbook.name, detected_type)
        except Exception as e:
            logger.warning("Auto-playbook selection for file failed (non-fatal): %s", e)

    # User's explicit choice wins; playbook default is fallback
    effective_party_side = party_side or "buyer"
    if not party_side and playbook and hasattr(playbook, 'party_side') and playbook.party_side:
        effective_party_side = playbook.party_side

    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=filename,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    await db.flush()

    try:
        # Get full text from ContractMap for the unified pipeline
        full_text = contract_map.get_all_text()

        # Run the unified 6-stage AI pipeline (same as /analyze)
        playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        try:
            pipeline_result: PipelineResult = await asyncio.wait_for(
                analysis_pipeline.run(
                    contract_text=full_text,
                    playbook_rules=playbook_rules,
                    playbook_name=playbook_name,
                    party_side=effective_party_side,
                ),
                timeout=600.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        # Enrich pipeline results with paragraph hashes from ContractMap
        hash_map = contract_map.to_hash_map() if not ZDR_MODE else None

        risk_summary = {
            "red": sum(1 for r in pipeline_result.redlines if r.risk_level == "RED"),
            "yellow": sum(1 for r in pipeline_result.redlines if r.risk_level == "YELLOW"),
            "green": sum(1 for r in pipeline_result.redlines if r.risk_level == "GREEN"),
        }

        # Update document
        document.total_risks = len(pipeline_result.redlines)
        document.risk_summary = risk_summary
        document.status = DocumentStatus.COMPLETED

        # Create audit log (ZDR: no text stored)
        await log_audit_event(
            db=db,
            user=current_user,
            action="analyze",
            resource_type="document",
            resource_name=filename,
            ip_address=client_ip,
            user_agent=user_agent,
            status="success",
            risk_count=len(pipeline_result.redlines),
        )
        await db.commit()
        await db.refresh(document)

        # Map paragraph hashes to redlines by matching clause text to ContractMap nodes
        def _find_paragraph_hash(clause_text: str) -> Optional[str]:
            if not contract_map or not clause_text:
                return None
            for node in contract_map.nodes:
                if clause_text in node.text or node.text in clause_text:
                    return node.id
            return None

        return AnalysisResult(
            document_id=str(document.id),
            filename=filename,
            executive_summary=pipeline_result.executive_summary,
            total_risks=len(pipeline_result.redlines),
            risk_summary=risk_summary,
            tokens_used=pipeline_result.total_tokens,
            source_type="docx",
            pipeline_partial=pipeline_result.partial,
            paragraph_hashes=hash_map,
            risks=[
                RedlineItem(
                    id=str(uuid4()),
                    clause_text=r.verified_text or r.original_text,
                    risk_level=r.risk_level,
                    rule_name=r.rule_name,
                    clause_type=r.clause_type or '',
                    paragraph_hash=_find_paragraph_hash(r.verified_text or r.original_text),
                    explanation=r.explanation,
                    recommendation=r.recommendation,
                    suggested_fix=r.suggested_fix,
                    redline_type=r.redline_type,
                    confidence=r.confidence.overall if r.confidence else None,
                    confidence_level=r.confidence.level if r.confidence else None,
                    verification_status=r.verification_status,
                    is_deal_breaker=r.is_deal_breaker,
                    cross_references=r.cross_references or [],
                )
                for r in pipeline_result.redlines
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("File analysis failed", exc_info=True)
        document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again or contact support."
        )

# ============================================================================
# Contract Summary Endpoint - AI-Powered Executive Summary
# ============================================================================

@router.post("/summarize", response_model=SummaryResponse)
@limiter.limit("30/minute")
async def summarize_contract(
    request: Request,
    body: SummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an AI-powered executive summary of the contract.
    
    Analyzes the contract text and detected risks to provide:
    - Overall risk level (Critical/High/Medium/Low)
    - Top 3 key concerns
    - Recommended action
    """
    # For ZDR mode, document might not exist - that's OK for summary
    # We just need the contract text which is passed in the request
    document = None
    try:
        doc_uuid = UUID(body.document_id)
        doc_result = await db.execute(
            select(Document)
            .where(Document.id == doc_uuid)
            .where(Document.user_id == current_user.id)
        )
        document = doc_result.scalar_one_or_none()
    except (ValueError, Exception):
        # Invalid UUID or other error - continue without document
        pass

    # Don't require document to exist - we can generate summary from text alone

    # Get playbook name if specified
    playbook_name = "Default Rules"
    if body.playbook_id:
        try:
            playbook = await load_playbook(db, body.playbook_id, current_user_id=current_user.id, current_user_org_id=current_user.organization_id)
            if playbook:
                playbook_name = playbook.name
        except ValueError:
            pass

    # Get the risks for this document from DB (or use empty list for ZDR mode)
    db_risks = []
    if document:
        try:
            doc_uuid = UUID(body.document_id)
            risks_result = await db.execute(
                select(DocumentRisk).where(DocumentRisk.document_id == doc_uuid)
            )
            db_risks = risks_result.scalars().all()
        except (ValueError, Exception):
            pass

    # Convert DB risks to a format the AI service can use
    # For ZDR mode, we need to re-run rule engine
    if not db_risks:
        # ZDR mode - re-run rule engine to get risk matches
        rule_engine = get_default_rule_engine()
        matches = rule_engine.evaluate(body.contract_text)
    else:
        # Use persisted risks
        matches = [
            type('Match', (), {
                'rule_name': r.clause_text[:30] + "..." if len(r.clause_text) > 30 else r.clause_text,
                'risk_level': type('Level', (), {'value': r.risk_level.value.upper()})(),
                'match_text': r.clause_text,
            })()
            for r in db_risks
        ]
    
    # Initialize AI service
    ai_service = AIService()
    
    # Generate AI summary
    summary_text, tokens = await ai_service.summarize_contract(
        contract_text=body.contract_text,
        risks_found=matches,
        playbook_name=playbook_name
    )
    
    # Parse the formatted summary
    risk_level = "Medium"
    key_concerns = []
    recommendation = "Review this contract with your legal team."
    
    if summary_text:
        lines = summary_text.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('RISK LEVEL:'):
                risk_level = line.replace('RISK LEVEL:', '').strip()
            elif line.strip().startswith('•') or line.strip().startswith('-'):
                concern = line.strip().lstrip('•-').strip()
                if concern:
                    key_concerns.append(concern)
            elif line.startswith('RECOMMENDATION:'):
                recommendation = line.replace('RECOMMENDATION:', '').strip()
    
    # Ensure we have at least some concerns
    if not key_concerns:
        key_concerns = ["Review detected risks before signing"]
    
    # Audit log for summary generation
    client_ip = request.client.host if request.client else None
    await log_audit_event(
        db=db, user=current_user, action="summary_generated",
        resource_type="document", resource_name=body.document_id,
        ip_address=client_ip, status="success",
    )
    await db.commit()

    return SummaryResponse(
        document_id=body.document_id,
        summary=summary_text,
        risk_level=risk_level,
        key_concerns=key_concerns[:5],  # Max 5 concerns
        recommendation=recommendation,
        tokens_used=tokens
    )


# ============================================================================
# Redline Endpoint - Using Box 3 RedlineImplementer
# ============================================================================

@router.post("/redline", response_model=RedlineResponse)
async def generate_redline(
    request: RedlineRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate OOXML redline using Box 3 RedlineImplementer.
    
    Supports two modes:
    1. DB Mode: Look up risk by risk_id in database
    2. ZDR Mode: Use original_text and suggested_text from request (RAM-only)
    
    Returns Track Changes OOXML with strikethrough (original) + underline (suggested).
    """
    from app.services.redline_implementer import RedlineImplementer

    # Initialize redline implementer
    implementer = RedlineImplementer()
    
    # Track usage and audit for redline
    async def _log_redline_usage():
        from app.models.document import UsageLog, UsageAction
        usage = UsageLog(user_id=current_user.id, action=UsageAction.REDLINE)
        db.add(usage)
        client_ip = http_request.client.host if http_request.client else None
        await log_audit_event(
            db=db, user=current_user, action="redline_generated",
            resource_type="document", resource_name=request.document_id,
            ip_address=client_ip, status="success",
        )
        await db.commit()

    # Mode 1: ZDR Mode - text provided directly in request
    if request.original_text and request.suggested_text:
        await _log_redline_usage()

        # Missing clause: generate insert-only OOXML (no deletion)
        if request.redline_type == "missing":
            ooxml = implementer.generate_insert_only_ooxml(
                new_text=request.suggested_text
            )
            return RedlineResponse(
                original_text=request.original_text,
                suggested_text=request.suggested_text,
                ooxml=ooxml,
                match_confidence=1.0,
                match_method="anchor",
                redline_type="missing"
            )

        # Violation: find anchor and generate replace OOXML
        result = implementer.apply_redline(
            original_text=request.original_text,
            suggested_text=request.suggested_text,
            paragraph_hash=request.paragraph_hash
        )

        if not result.success:
            ooxml = implementer.generate_track_changes_ooxml(
                original=request.original_text,
                replacement=request.suggested_text
            )
            return RedlineResponse(
                original_text=request.original_text,
                suggested_text=request.suggested_text,
                ooxml=ooxml,
                match_confidence=0.0,
                match_method="direct",
                redline_type="violation"
            )

        return RedlineResponse(
            original_text=result.original,
            suggested_text=result.replacement,
            ooxml=result.track_changes_ooxml,
            match_confidence=result.anchor.match_confidence if result.anchor else 1.0,
            match_method=result.anchor.match_method if result.anchor else "direct",
            redline_type="violation"
        )
    
    # Mode 2: DB Mode - look up risk by ID
    # ZDR guard: DB mode is not available in ZDR — text must be provided in request
    if ZDR_MODE:
        raise HTTPException(
            status_code=400,
            detail="Zero Data Retention mode is enabled. Provide original_text and suggested_text in the request body.",
        )

    try:
        risk_uuid = UUID(request.risk_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid risk_id format")
    
    result = await db.execute(
        select(DocumentRisk).where(DocumentRisk.id == risk_uuid)
    )
    risk = result.scalar_one_or_none()
    
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found"
        )
    
    # Verify document belongs to user
    doc_result = await db.execute(
        select(Document)
        .where(Document.id == risk.document_id)
        .where(Document.user_id == current_user.id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Generate redline using implementer
    original = risk.clause_text
    suggested = risk.suggested_fix or risk.clause_text

    redline_result = implementer.apply_redline(
        original_text=original,
        suggested_text=suggested
    )

    await _log_redline_usage()

    return RedlineResponse(
        original_text=original,
        suggested_text=suggested,
        ooxml=redline_result.track_changes_ooxml,
        match_confidence=redline_result.anchor.match_confidence if redline_result.anchor else 1.0,
        match_method=redline_result.anchor.match_method if redline_result.anchor else "exact"
    )

# ============================================================================
# Word Add-in Manifest Download Endpoint
# ============================================================================

@router.get("/manifest", response_class=Response)
async def download_manifest(current_user: User = Depends(get_current_user)):
    """
    Download the Word Add-in manifest.xml file.
    Fetches the raw file from GitHub and serves it with the correct
    Content-Disposition headers to force a download instead of displaying in browser.
    """
    github_url = "https://raw.githubusercontent.com/Aviyadav22/ContraRed/main/ContraRed-PoC/manifest.xml"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(github_url)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch manifest from repository")
            
        return Response(
            content=response.content,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="contrared-manifest.xml"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving manifest", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error serving manifest. Please try again or contact support."
        )

@router.get("/installer", response_class=Response)
async def download_installer(current_user: User = Depends(get_current_user)):
    """
    Download the ContraRed installer package as a ZIP file.
    Contains Install-ContraRed.bat and manifest.xml.
    """
    github_base = "https://raw.githubusercontent.com/Aviyadav22/ContraRed/main"
    manifest_url = f"{github_base}/ContraRed-PoC/manifest.xml"
    bat_url = f"{github_base}/dashboard/public/Install-ContraRed.bat"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            manifest_resp, bat_resp = await asyncio.gather(
                client.get(manifest_url),
                client.get(bat_url),
            )
        
        if manifest_resp.status_code != 200 or bat_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch installer files from repository")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.xml", manifest_resp.content)
            zf.writestr("Install-ContraRed.bat", bat_resp.content)
        
        zip_buffer.seek(0)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="ContraRed-Installer.zip"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating installer", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating installer. Please try again or contact support."
        )


# ============================================================================
# Export Risk Report Endpoint
# ============================================================================

@router.post("/export-report")
async def export_risk_report(
    request: ExportReportRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("document.export")),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and download a DOCX risk assessment report.

    ZDR-safe: Only receives analysis metadata, NOT the full contract text.
    """
    from app.services.report_generator import generate_risk_report

    buffer = generate_risk_report(
        filename=request.filename,
        executive_summary=request.executive_summary,
        redlines=request.redlines,
        risk_summary=request.risk_summary,
        generated_by=f"ContraRed AI for {current_user.email}",
    )

    # Audit log
    client_ip = http_request.client.host if http_request.client else None
    await log_audit_event(
        db=db, user=current_user, action="report_exported",
        resource_type="document", resource_name=request.filename,
        ip_address=client_ip, status="success",
    )
    await db.commit()

    safe_filename = re.sub(r'[^\w\-.]', '_', request.filename or 'report') + '-risk-report.docx'

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


# ============================================================================
# Excel/PDF/CSV Export Endpoints (Phase 7)
# ============================================================================

class ExportIssuesRequest(BaseModel):
    """Request body for exporting issues to Excel, CSV, or PDF."""
    filename: str = "contract"
    issues: List[dict] = Field(default_factory=list)
    summary: Optional[dict] = None
    format: Literal["xlsx", "csv", "pdf"] = "xlsx"


@router.post("/export-issues")
async def export_issues(
    request: ExportIssuesRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("document.export")),
    db: AsyncSession = Depends(get_db),
):
    """Export contract analysis issues to Excel, CSV, or PDF format."""
    safe_name = re.sub(r'[^\w\-.]', '_', request.filename or 'issues')

    if request.format == "xlsx":
        from app.services.issues_exporter import export_issues_to_xlsx
        content = export_issues_to_xlsx(request.issues, request.filename)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif request.format == "csv":
        from app.services.issues_exporter import export_issues_to_csv
        content = export_issues_to_csv(request.issues, request.filename)
        media_type = "text/csv"
        ext = "csv"
    elif request.format == "pdf":
        from app.services.pdf_report_generator import generate_pdf_report
        content = generate_pdf_report(request.issues, request.filename, request.summary)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

    await log_audit_event(
        db=db, user=current_user, action=f"issues_exported_{ext}",
        resource_type="document", resource_name=request.filename,
        ip_address=http_request.client.host if http_request.client else None,
        status="success",
    )
    await db.commit()

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-issues.{ext}"'},
    )


# ============================================================================
# Get Document Endpoint
# ============================================================================

@router.get("/{document_id}", response_model=AnalysisResult)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document analysis results."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # ZDR mode: don't return persisted risk text from DB
    if ZDR_MODE:
        return AnalysisResult(
            document_id=str(document.id),
            filename=document.filename,
            total_risks=document.total_risks,
            risk_summary=document.risk_summary or {},
            risks=[],  # ZDR: risk text not persisted, re-analyze to get risks
        )

    # Non-ZDR: return risks from DB
    result = await db.execute(
        select(DocumentRisk).where(DocumentRisk.document_id == document_id)
    )
    risks = result.scalars().all()

    return AnalysisResult(
        document_id=str(document.id),
        filename=document.filename,
        total_risks=document.total_risks,
        risk_summary=document.risk_summary or {},
        risks=[
            RedlineItem(
                id=str(risk.id),
                clause_text=risk.clause_text,
                risk_level=risk.risk_level.value.upper(),
                rule_name="",
                clause_type=getattr(risk, "clause_type", "") or "",
                explanation=risk.ai_explanation or "",
                recommendation="",
                suggested_fix=getattr(risk, "suggested_fix", None),
                redline_type="violation",
            )
            for risk in risks
        ]
    )


# ============================================================================
# Document Versioning Endpoints (Phase 2.1)
# ============================================================================

class DocumentVersionResponse(BaseModel):
    id: str
    version_number: int
    content_hash: str
    risk_summary: Optional[Dict] = None
    total_risks: int = 0
    metadata: Optional[Dict] = None
    created_at: str


class CreateVersionRequest(BaseModel):
    content_hash: Optional[str] = None
    metadata: Optional[Dict] = None


@router.post("/{document_id}/versions", response_model=DocumentVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_document_version(
    document_id: UUID,
    version_data: Optional[CreateVersionRequest] = None,
    current_user: User = Depends(require_permission("document.write")),
    db: AsyncSession = Depends(get_db),
):
    """Create an explicit version snapshot of a document's current state."""
    # Verify document access
    doc_result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(
            (Document.user_id == current_user.id)
            | (Document.organization_id == current_user.organization_id)
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    root_id = document.root_document_id or document.id

    # Determine next version number
    from sqlalchemy import func
    max_result = await db.execute(
        select(func.coalesce(func.max(DocumentVersion.version_number), 0))
        .where(DocumentVersion.document_id == root_id)
    )
    next_version = max_result.scalar() + 1

    # Build content hash from document's current state
    content_hash = (
        (version_data.content_hash if version_data else None)
        or document.content_hash
        or ""
    )

    version = DocumentVersion(
        document_id=root_id,
        version_number=next_version,
        content_hash=content_hash,
        risk_summary=document.risk_summary,
        total_risks=document.total_risks,
        version_metadata=(version_data.metadata if version_data else None),
        created_by=current_user.id,
    )

    db.add(version)

    # Update document's version_number
    document.version_number = next_version

    await log_audit_event(
        db, user=current_user, action="document_version_created",
        resource_type="document",
        resource_name=document.filename,
        details=json.dumps({"version": next_version, "document_id": str(document_id)}),
    )
    await db.commit()
    await db.refresh(version)

    return DocumentVersionResponse(
        id=str(version.id),
        version_number=version.version_number,
        content_hash=version.content_hash,
        risk_summary=version.risk_summary,
        total_risks=version.total_risks,
        metadata=version.version_metadata,
        created_at=version.created_at.isoformat() if version.created_at else "",
    )


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a document."""
    from app.models.document import DocumentVersion

    # Verify document access
    doc_result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(
            (Document.user_id == current_user.id)
            | (Document.organization_id == current_user.organization_id)
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get all versions (for the root document chain)
    root_id = document.root_document_id or document.id
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == root_id)
        .order_by(DocumentVersion.version_number.asc())
    )
    versions = result.scalars().all()

    return [
        DocumentVersionResponse(
            id=str(v.id),
            version_number=v.version_number,
            content_hash=v.content_hash,
            risk_summary=v.risk_summary,
            total_risks=v.total_risks,
            metadata=v.version_metadata,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in versions
    ]


class DiffResponse(BaseModel):
    document_id: str
    version_a: int
    version_b: int
    diff_data: Optional[Dict] = None


@router.get("/{document_id}/diff", response_model=DiffResponse)
async def get_version_diff(
    document_id: UUID,
    a: int,
    b: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get diff between two document versions."""
    from app.models.document import DocumentVersion, DocumentComparison

    # Verify access
    doc_result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(
            (Document.user_id == current_user.id)
            | (Document.organization_id == current_user.organization_id)
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    # Check cache
    root_id = document_id
    cached = await db.execute(
        select(DocumentComparison)
        .where(DocumentComparison.document_id == root_id)
        .where(DocumentComparison.version_a == a)
        .where(DocumentComparison.version_b == b)
    )
    comparison = cached.scalar_one_or_none()
    if comparison:
        return DiffResponse(
            document_id=str(document_id),
            version_a=a,
            version_b=b,
            diff_data=comparison.diff_data,
        )

    # Load both versions' risk summaries for structural diff
    va_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == root_id)
        .where(DocumentVersion.version_number == a)
    )
    vb_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == root_id)
        .where(DocumentVersion.version_number == b)
    )
    va = va_result.scalar_one_or_none()
    vb = vb_result.scalar_one_or_none()

    if not va or not vb:
        raise HTTPException(status_code=404, detail="Version not found")

    diff_data = {
        "version_a_risks": va.total_risks,
        "version_b_risks": vb.total_risks,
        "risk_delta": vb.total_risks - va.total_risks,
        "hash_changed": va.content_hash != vb.content_hash,
        "risk_summary_a": va.risk_summary,
        "risk_summary_b": vb.risk_summary,
    }

    # Cache the comparison
    comp = DocumentComparison(
        document_id=root_id,
        version_a=a,
        version_b=b,
        diff_data=diff_data,
    )
    db.add(comp)
    await db.commit()

    return DiffResponse(
        document_id=str(document_id),
        version_a=a,
        version_b=b,
        diff_data=diff_data,
    )
