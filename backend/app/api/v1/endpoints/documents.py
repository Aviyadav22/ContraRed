"""
Document analysis endpoints.

Real implementation using RuleEngine + AIService with parallel processing.

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
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentRisk, DocumentVersion, DocumentComparison, DocumentStatus
from app.models.document import RiskLevel as DBRiskLevel
from app.models.audit_log import log_audit_event
from app.models.playbook import Playbook
from app.api.v1.endpoints.auth import get_current_user, limiter
from app.api.v1.endpoints.billing import check_and_increment_quota
from app.services.rule_engine import RuleEngine, RuleMatch
from app.services.ai_service import AIService
from app.services.cache_service import get_cache
from app.services.gemini_analyzer import gemini_analyzer, AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout, _sanitize_for_prompt
from app.services.analysis_pipeline import analysis_pipeline, PipelineResult
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

class AnalyzeRequest(BaseModel):
    """Request to analyze document text."""
    text: str = Field(..., min_length=1, max_length=500000)
    playbook_id: Optional[str] = None
    filename: Optional[str] = Field(default="untitled.docx", max_length=255)


class RiskItem(BaseModel):
    """Individual risk item with strict risk_level enum."""
    id: str
    clause_text: str  # match_text for Word highlighting
    risk_level: Literal["RED", "YELLOW", "GREEN"]  # Strict enum
    rule_name: str
    clause_type: str
    paragraph_hash: Optional[str] = None  # SHA-256 for drift detection
    ai_explanation: Optional[str] = None
    suggested_fix: Optional[str] = None
    is_deal_breaker: bool = False


class AnalysisResult(BaseModel):
    """Analysis result with risks."""
    document_id: str
    filename: str
    total_risks: int
    risk_summary: dict  # {red: int, yellow: int, green: int}
    risks: List[RiskItem]
    tokens_used: int = 0  # For usage tracking
    paragraph_hashes: Optional[Dict[str, str]] = None  # hash -> text for drift detection
    source_type: str = "text"  # "text" or "docx"


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


# ============================================================================
# AI-First Analysis Schemas
# ============================================================================

class AIAnalyzeRequest(BaseModel):
    """Request for AI-first full contract analysis."""
    text: str = Field(..., min_length=1, max_length=500000)
    playbook_id: Optional[str] = None
    filename: Optional[str] = Field(default="untitled.docx", max_length=255)


class AIRedlineItem(BaseModel):
    """Single redline item from AI analysis."""
    id: str
    risk_level: Literal["RED", "YELLOW"]
    rule_name: str
    original_text: str  # Exact text from contract for search
    explanation: str
    recommendation: str  # Lawyer-readable guidance (not exact replacement text)
    redline_type: Literal["violation", "missing"] = "violation"
    # Phase 4: confidence and verification fields
    confidence: Optional[float] = None  # Weighted score 0-1
    confidence_level: Optional[str] = None  # HIGH/MEDIUM/LOW
    verification_status: Optional[str] = None  # exact/normalized/fuzzy_corrected
    is_deal_breaker: bool = False
    cross_references: Optional[List[str]] = None


class AIAnalysisResponse(BaseModel):
    """Response from AI-first analysis."""
    document_id: str
    filename: str
    executive_summary: List[str]
    redlines: List[AIRedlineItem]
    total_risks: int
    risk_summary: dict  # {red: int, yellow: int}
    tokens_used: int = 0
    # Phase 4: pipeline metadata
    jurisdiction: Optional[str] = None  # Detected jurisdiction code
    jurisdiction_name: Optional[str] = None  # Human-readable jurisdiction name
    hallucination_stats: Optional[dict] = None
    pipeline_partial: bool = False  # True if pipeline degraded gracefully


class ClauseAnalyzeRequest(BaseModel):
    """Request to analyze a single clause/selection."""
    clause_text: str = Field(..., min_length=20, max_length=10000)
    playbook_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    document_id: Optional[str] = None


class ClauseAnalyzeResponse(BaseModel):
    """Response from single-clause analysis."""
    risks: List[AIRedlineItem]
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


@router.get("/list", response_model=List[DocumentListItem])
async def list_documents(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's scanned documents (metadata only, ZDR-safe)."""
    query = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(query)
    docs = result.scalars().all()

    return [
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
    ]


# ============================================================================
# Analyze Endpoint - Real Implementation
# ============================================================================

@router.post("/analyze", response_model=AnalysisResult)
@limiter.limit("20/minute")
async def analyze_document(
    request: AnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze document text for risks using Rule Engine + AI.
    
    ZERO DATA RETENTION (ZDR) MODE:
    - Document text is processed in RAM only, NEVER stored
    - Only metadata (filename, risk count) is stored for audit
    
    Process:
    1. RuleEngine scans text with regex patterns (from playbook or defaults)
    2. AIService enriches matches (parallel with asyncio.gather)
    3. Audit log created (ZDR: no text stored)
    """
    # Get client info for audit
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")

    # Initialize services
    ai_service = AIService()
    cache = await get_cache()

    # Load playbook rules if specified, otherwise use defaults
    if request.playbook_id:
        try:
            playbook_uuid = UUID(request.playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            
            if not playbook:
                raise HTTPException(status_code=404, detail="Playbook not found")
            
            # Check access
            if not playbook.is_public:
                if playbook.created_by != current_user.id and playbook.organization_id != current_user.organization_id:
                    raise HTTPException(status_code=403, detail="Access denied to this playbook")
            
            # Create rule engine from playbook rules
            if playbook.rules_list:
                rule_engine = RuleEngine.from_playbook_rules(playbook.rules_list)
            else:
                rule_engine = RuleEngine()  # Empty playbook, use defaults
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid playbook_id format")
    else:
        rule_engine = RuleEngine()  # Use default rules
    
    # Create document record (with org + version tracking)
    content_hash = Document.compute_content_hash(request.text)
    document = Document(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        filename=request.filename,
        status=DocumentStatus.PROCESSING,
        content_hash=content_hash,
    )
    db.add(document)
    await db.flush()
    
    try:
        # Step 1: Rule-based detection
        matches = rule_engine.evaluate(request.text)
        
        # Step 2: AI enrichment in PARALLEL (critical for performance)
        token_counts = []

        if matches:
            # Create async tasks for all matches
            # Tenant-scoped cache key prefix
            _org_id = str(current_user.organization_id) if current_user.organization_id else None

            async def enrich_with_cache(match: RuleMatch) -> RuleMatch:
                """Enrich a match, checking cache first (tenant-scoped)."""
                # Check cache
                cache_key = match.cache_key()
                if cache.is_connected:
                    cached = await cache.get(cache_key, org_id=_org_id)
                    if cached:
                        match.ai_explanation = cached.get("explanation")
                        match.suggested_fix = cached.get("suggested_fix")
                        return match

                # Call AI service
                explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
                token_counts.append(tokens)

                match.ai_explanation = explanation
                match.suggested_fix = suggested_fix

                # Store in cache (tenant-scoped)
                if cache.is_connected and (explanation or suggested_fix):
                    await cache.set(cache_key, {
                        "explanation": explanation,
                        "suggested_fix": suggested_fix,
                    }, ttl=3600, org_id=_org_id)

                return match

            # Run all AI calls in parallel using asyncio.gather
            enriched_matches = await asyncio.gather(
                *[enrich_with_cache(match) for match in matches]
            )
        else:
            enriched_matches = []

        total_tokens = sum(token_counts)
        
        # Step 3: Storage (respects ZDR_MODE)
        risk_summary = rule_engine.get_risk_summary(enriched_matches)
        
        if ZDR_MODE:
            # ZERO DATA RETENTION: Don't store document text or clause text
            # Only store: filename (for audit), risk count (for billing)
            # Generate ephemeral IDs for frontend (not persisted)
            
            document.total_risks = len(enriched_matches)
            document.risk_summary = risk_summary
            document.status = DocumentStatus.COMPLETED
            # NOTE: In ZDR mode, no clause_text is stored in DocumentRisk

            # Create audit log entry (no text, just metadata)
            await log_audit_event(
                db=db,
                user=current_user,
                action="analyze",
                resource_type="document",
                resource_name=request.filename,
                ip_address=client_ip,
                user_agent=user_agent,
                status="success",
                risk_count=len(enriched_matches),
            )
            await db.commit()
            await db.refresh(document)
            
            # Build response from RAM (text never persisted)
            return AnalysisResult(
                document_id=str(document.id),
                filename=document.filename,
                total_risks=len(enriched_matches),
                risk_summary=risk_summary,
                tokens_used=total_tokens,
                risks=[
                    RiskItem(
                        id=str(uuid4()),  # Ephemeral ID (not persisted)
                        clause_text=match.match_text,  # From RAM, not DB
                        risk_level=match.risk_level.value,
                        rule_name=match.rule_name,
                        clause_type=match.clause_type,
                        ai_explanation=match.ai_explanation,
                        suggested_fix=match.suggested_fix,
                        is_deal_breaker=match.is_deal_breaker,
                    )
                    for match in enriched_matches
                ]
            )
        else:
            # NON-ZDR MODE: Store everything (for internal/demo use)
            db_risks = []
            for match in enriched_matches:
                risk = DocumentRisk(
                    document_id=document.id,
                    clause_text=match.match_text,
                    start_offset=match.start_offset,
                    end_offset=match.end_offset,
                    risk_level=DBRiskLevel(match.risk_level.value.lower()),
                    ai_explanation=match.ai_explanation,
                    suggested_fix=match.suggested_fix,
                )
                db.add(risk)
                db_risks.append((risk, match))
            
            document.total_risks = len(enriched_matches)
            document.risk_summary = risk_summary
            document.status = DocumentStatus.COMPLETED
            
            await db.commit()
            
            for risk, _ in db_risks:
                await db.refresh(risk)
            await db.refresh(document)
            
            return AnalysisResult(
                document_id=str(document.id),
                filename=document.filename,
                total_risks=document.total_risks,
                risk_summary=document.risk_summary,
                tokens_used=total_tokens,
                risks=[
                    RiskItem(
                        id=str(risk.id),
                        clause_text=match.match_text,
                        risk_level=match.risk_level.value,
                        rule_name=match.rule_name,
                        clause_type=match.clause_type,
                        ai_explanation=match.ai_explanation,
                        suggested_fix=match.suggested_fix,
                        is_deal_breaker=match.is_deal_breaker,
                    )
                    for risk, match in db_risks
                ]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        # Mark document as failed
        logger.error("Analysis failed", exc_info=True)
        document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again or contact support."
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
    request: AIAnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Submit contract for async analysis. Returns 202 + job_id immediately.
    Poll GET /documents/jobs/{job_id} for results.
    """
    from app.workers.tasks import task_queue, AnalysisJob, JobStatus

    content_hash = Document.compute_content_hash(request.text)

    # Create document record
    playbook_uuid = None
    if request.playbook_id:
        try:
            playbook_uuid = UUID(request.playbook_id)
        except ValueError:
            pass

    doc = Document(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        playbook_id=playbook_uuid,
        filename=request.filename or "untitled.docx",
        status=DocumentStatus.PROCESSING,
        content_hash=content_hash,
    )
    db.add(doc)
    await db.flush()
    doc_id = str(doc.id)

    # Load playbook rules
    playbook_rules = []
    playbook_name = "Default"
    if request.playbook_id:
        try:
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                        "verification_prompt": rule.verification_prompt or "",
                    }
                    for rule in playbook.rules_list
                ]
        except Exception as e:
            logger.error("Error loading playbook for async: %s", e)

    await db.commit()

    # Create job
    job = AnalysisJob(
        job_id=str(uuid4()),
        document_id=doc_id,
        user_id=str(current_user.id),
        organization_id=str(current_user.organization_id) if current_user.organization_id else None,
        contract_text=request.text,
        playbook_id=request.playbook_id,
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

@router.post("/analyze-full", response_model=AIAnalysisResponse)
@limiter.limit("20/minute")
async def analyze_full_ai(
    request: AIAnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    AI-First contract analysis using Gemini.
    
    This endpoint sends the FULL contract text + playbook rules to Gemini
    for comprehensive analysis, returning executive summary and redlines.
    
    Unlike /analyze, this does NOT use rule-based regex matching.
    Gemini performs holistic structural analysis + surgical redlining.
    """
    # Get client info for audit
    client_ip = http_request.client.host if http_request.client else None
    
    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"
    
    if request.playbook_id:
        try:
            playbook_uuid = UUID(request.playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()

            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                        "verification_prompt": rule.verification_prompt or "",
                    }
                    for rule in playbook.rules_list
                ]
        except Exception as e:
            logger.error("Error loading playbook: %s", e)
    
    try:
        # Sanitize playbook name before passing to AI
        playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        # Phase 4: Use the 5-stage analysis pipeline instead of direct Gemini call
        # Pipeline includes: extraction -> classification -> risk assessment ->
        # hallucination verification -> confidence scoring + enrichment
        try:
            pipeline_result: PipelineResult = await asyncio.wait_for(
                analysis_pipeline.run(
                    contract_text=request.text,
                    playbook_rules=playbook_rules,
                    playbook_name=playbook_name,
                ),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={"message": "AI analysis timed out. Please try with a shorter document.", "error_code": "ai_timeout"},
            )

        risk_summary = {
            "red": sum(1 for r in pipeline_result.redlines if r.risk_level == "RED"),
            "yellow": sum(1 for r in pipeline_result.redlines if r.risk_level == "YELLOW"),
        }

        # Persist document metadata (ZDR-safe: no contract text stored)
        playbook_uuid = None
        if request.playbook_id:
            try:
                playbook_uuid = UUID(request.playbook_id)
            except ValueError:
                pass

        content_hash = Document.compute_content_hash(request.text)
        doc = Document(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            playbook_id=playbook_uuid,
            filename=request.filename or "untitled.docx",
            status=DocumentStatus.COMPLETED,
            total_risks=len(pipeline_result.redlines),
            risk_summary=risk_summary,
            content_hash=content_hash,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(doc)

        # Log audit event (same transaction — single commit for both)
        await log_audit_event(
            db=db,
            user=current_user,
            action="ai_full_analysis",
            resource_type="contract",
            resource_name=request.filename or "untitled.docx",
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

        # Build response — map FinalRedline to AIRedlineItem
        redline_items = [
            AIRedlineItem(
                id=str(uuid4()),
                risk_level=r.risk_level,
                rule_name=r.rule_name,
                original_text=r.verified_text or r.original_text,
                explanation=r.explanation,
                recommendation=r.recommendation,
                redline_type=r.redline_type,
                confidence=round(r.confidence.score, 3),
                confidence_level=r.confidence.level.value,
                verification_status=r.verification_status,
                is_deal_breaker=r.is_deal_breaker,
                cross_references=r.cross_references or None,
            )
            for r in pipeline_result.redlines
        ]

        # Get jurisdiction info from the pipeline's stage 3 (which calls gemini_analyzer)
        jurisdiction_code = None
        jurisdiction_name = None
        # Extract from the analyzer's last result metadata if available
        if hasattr(gemini_analyzer, '_last_jurisdiction_code'):
            jurisdiction_code = gemini_analyzer._last_jurisdiction_code
            jurisdiction_name = gemini_analyzer._last_jurisdiction_name

        return AIAnalysisResponse(
            document_id=doc_id,
            filename=request.filename or "untitled.docx",
            executive_summary=pipeline_result.executive_summary,
            redlines=redline_items,
            total_risks=len(redline_items),
            risk_summary=risk_summary,
            tokens_used=pipeline_result.total_tokens_used,
            hallucination_stats=pipeline_result.hallucination_stats or None,
            pipeline_partial=pipeline_result.partial,
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
        logger.error("AI analysis failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "AI analysis failed. Please try again.", "error_code": "unknown_error"}
        )


# ============================================================================
# Analyze Single Clause Endpoint (Phase 8)
# ============================================================================

@router.post("/analyze-clause", response_model=ClauseAnalyzeResponse)
@limiter.limit("30/minute")
async def analyze_clause(
    request: ClauseAnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze a single clause/text selection for risks.

    Lightweight alternative to /analyze-full — designed for inline
    selection scanning from the Word Add-in.
    """
    start_time = time.perf_counter()
    client_ip = http_request.client.host if http_request.client else None

    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"

    if request.playbook_id:
        try:
            playbook_uuid = UUID(request.playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()

            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                        "verification_prompt": rule.verification_prompt or "",
                    }
                    for rule in playbook.rules_list
                ]
        except Exception as e:
            logger.error("Error loading playbook for clause analysis: %s", e)

    try:
        ai_result = await asyncio.wait_for(
            gemini_analyzer.analyze_clause(
                clause_text=request.clause_text,
                playbook_rules=playbook_rules,
                playbook_name=playbook_name,
                jurisdiction=request.jurisdiction,
            ),
            timeout=30.0,
        )

        redline_items = [
            AIRedlineItem(
                id=item.get("id", str(uuid4())),
                risk_level=item.get("risk_level", "YELLOW"),
                rule_name=item.get("rule_name", "Unknown Rule"),
                original_text=item.get("original_text", ""),
                explanation=item.get("explanation", ""),
                recommendation=item.get("recommendation", ""),
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
            resource_name=request.document_id or "inline-selection",
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
    http_request: Request,
    request: GenerateClauseRequest,
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
        if request.playbook_id:
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == request.playbook_id)
                .where(
                    (Playbook.is_public == True) |
                    (Playbook.organization_id == current_user.organization_id) |
                    (Playbook.created_by == current_user.id)
                )
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                    }
                    for rule in playbook.rules_list
                ]

        try:
            generated = await asyncio.wait_for(
                gemini_analyzer.generate_clause(
                    clause_type=request.clause_type,
                    contract_context=request.contract_context or "",
                    playbook_rules=playbook_rules,
                ),
                timeout=120.0,
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
            details=json.dumps({"clause_type": request.clause_type, "playbook_id": str(request.playbook_id) if request.playbook_id else None}),
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


class GenerateFixResponse(BaseModel):
    """Response with generated fix text."""
    fix_text: str
    reasoning: str


@router.post("/generate-fix", response_model=GenerateFixResponse)
@limiter.limit("30/minute")
async def generate_fix(
    http_request: Request,
    request: GenerateFixRequest,
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
        if request.playbook_id:
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == request.playbook_id)
                .where(
                    (Playbook.is_public == True) |
                    (Playbook.organization_id == current_user.organization_id) |
                    (Playbook.created_by == current_user.id)
                )
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                    }
                    for rule in playbook.rules_list
                ]

        try:
            generated = await asyncio.wait_for(
                gemini_analyzer.generate_fix(
                    original_text=request.original_text,
                    recommendation=request.recommendation,
                    rule_name=request.rule_name,
                    redline_type=request.redline_type,
                    surrounding_context=request.surrounding_context or "",
                    playbook_rules=playbook_rules,
                ),
                timeout=120.0,
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
            action="fix_generation",
            resource_type="clause",
            details=json.dumps({"rule_name": request.rule_name, "redline_type": request.redline_type}),
        )
        await db.commit()

        return GenerateFixResponse(
            fix_text=generated["fix_text"],
            reasoning=generated["reasoning"],
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
    http_request: Request,
    request: ResearchClauseRequest,
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
                gemini_analyzer.research_clause(
                    clause_text=request.clause_text,
                    clause_type=request.clause_type or "",
                ),
                timeout=120.0,
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
            details=json.dumps({"clause_type": request.clause_type, "cases_found": len(result.get("cases", []))}),
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
    http_request: Request,
    request: CompareRequest,
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
        if request.playbook_id:
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == request.playbook_id)
                .where(
                    (Playbook.is_public == True) |
                    (Playbook.organization_id == current_user.organization_id) |
                    (Playbook.created_by == current_user.id)
                )
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                    }
                    for rule in playbook.rules_list
                ]

        diff = await compute_diff_with_ai(
            text_a=request.text_a,
            text_b=request.text_b,
            playbook_rules=playbook_rules,
        )

        # Audit log
        await log_audit_event(
            db=db,
            user=current_user,
            action="contract_comparison",
            resource_type="document",
            details=json.dumps({"total_changes": diff.total_changes, "playbook_id": str(request.playbook_id) if request.playbook_id else None}),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze uploaded DOCX file using Structure Extractor (Box 1).
    
    This endpoint preserves document structure (headings, sections) and
    generates SHA-256 paragraph hashes for drift detection during redlining.
    
    Process:
    1. Box 1: StructureExtractor parses DOCX → ContractMap
    2. Box 2: RuleEngine + AI analyzes the ContractMap
    3. Response includes paragraph_hashes for frontend drift detection
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
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse DOCX file: {str(e)}"
        )
    
    # Initialize services
    ai_service = AIService()
    cache = await get_cache()
    
    # Load playbook rules if specified
    if playbook_id:
        try:
            playbook_uuid = UUID(playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            
            if not playbook:
                raise HTTPException(status_code=404, detail="Playbook not found")
            
            if not playbook.is_public:
                if playbook.created_by != current_user.id and playbook.organization_id != current_user.organization_id:
                    raise HTTPException(status_code=403, detail="Access denied to this playbook")
            
            if playbook.rules_list:
                rule_engine = RuleEngine.from_playbook_rules(playbook.rules_list)
            else:
                rule_engine = RuleEngine()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid playbook_id format")
    else:
        rule_engine = RuleEngine()
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=filename,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    await db.flush()
    
    try:
        # Get full text from ContractMap for analysis
        full_text = contract_map.get_all_text()
        
        # Box 2: Rule-based detection on extracted text
        matches = rule_engine.evaluate(full_text)
        
        # Enrich with paragraph hashes from ContractMap
        for match in matches:
            # Find the paragraph hash for this match
            for node in contract_map.nodes:
                if match.match_text in node.text or node.text in match.match_text:
                    match.paragraph_hash = node.id
                    break
        
        # AI enrichment in parallel
        token_counts_file = []

        if matches:
            _org_id_file = str(current_user.organization_id) if current_user.organization_id else None

            async def enrich_with_cache(match: RuleMatch) -> RuleMatch:
                cache_key = match.cache_key()
                if cache.is_connected:
                    cached = await cache.get(cache_key, org_id=_org_id_file)
                    if cached:
                        match.ai_explanation = cached.get("explanation")
                        match.suggested_fix = cached.get("suggested_fix")
                        return match

                explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
                token_counts_file.append(tokens)

                match.ai_explanation = explanation
                match.suggested_fix = suggested_fix

                if cache.is_connected and (explanation or suggested_fix):
                    await cache.set(cache_key, {
                        "explanation": explanation,
                        "suggested_fix": suggested_fix,
                    }, ttl=3600, org_id=_org_id_file)

                return match

            enriched_matches = await asyncio.gather(
                *[enrich_with_cache(match) for match in matches]
            )
        else:
            enriched_matches = []

        total_tokens = sum(token_counts_file)
        
        # Build response with ContractMap metadata
        risk_summary = rule_engine.get_risk_summary(enriched_matches)
        
        # Update document
        document.total_risks = len(enriched_matches)
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
            risk_count=len(enriched_matches),
        )
        await db.commit()
        await db.refresh(document)
        
        return AnalysisResult(
            document_id=str(document.id),
            filename=filename,
            total_risks=len(enriched_matches),
            risk_summary=risk_summary,
            tokens_used=total_tokens,
            source_type="docx",
            paragraph_hashes=contract_map.to_hash_map() if not ZDR_MODE else None,
            risks=[
                RiskItem(
                    id=str(uuid4()),
                    clause_text=match.match_text,
                    risk_level=match.risk_level.value,
                    rule_name=match.rule_name,
                    clause_type=match.clause_type,
                    paragraph_hash=getattr(match, 'paragraph_hash', None),
                    ai_explanation=match.ai_explanation,
                    suggested_fix=match.suggested_fix,
                    is_deal_breaker=match.is_deal_breaker,
                )
                for match in enriched_matches
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
    request: SummaryRequest,
    http_request: Request,
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
        doc_uuid = UUID(request.document_id)
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
    if request.playbook_id:
        try:
            pb_uuid = UUID(request.playbook_id)
            pb_result = await db.execute(select(Playbook).where(Playbook.id == pb_uuid))
            playbook = pb_result.scalar_one_or_none()
            if playbook:
                playbook_name = playbook.name
        except ValueError:
            pass
    
    # Get the risks for this document from DB (or use empty list for ZDR mode)
    db_risks = []
    if document:
        try:
            doc_uuid = UUID(request.document_id)
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
        rule_engine = RuleEngine()
        matches = rule_engine.evaluate(request.contract_text)
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
        contract_text=request.contract_text,
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
    client_ip = http_request.client.host if http_request.client else None
    await log_audit_event(
        db=db, user=current_user, action="summary_generated",
        resource_type="document", resource_name=request.document_id,
        ip_address=client_ip, status="success",
    )
    await db.commit()

    return SummaryResponse(
        document_id=request.document_id,
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
async def download_manifest():
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
async def download_installer():
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
    current_user: User = Depends(get_current_user),
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
    
    # Get risks
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
            RiskItem(
                id=str(risk.id),
                clause_text=risk.clause_text,
                risk_level=risk.risk_level.value.upper(),  # Ensure uppercase
                rule_name="",  # Not stored in DB currently
                clause_type="",
                ai_explanation=risk.ai_explanation,
                suggested_fix=risk.suggested_fix,
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
    current_user: User = Depends(get_current_user),
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
            metadata=v.metadata,
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
