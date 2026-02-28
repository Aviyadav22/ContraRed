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
from typing import List, Optional, Literal, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, DocumentRisk, DocumentStatus
from app.models.document import RiskLevel as DBRiskLevel
from app.models.audit_log import AuditLog, log_audit_event
from app.models.playbook import Playbook
from app.api.v1.endpoints.auth import get_current_user
from app.services.rule_engine import RuleEngine, RuleMatch
from app.services.ai_service import AIService
from app.services.cache_service import get_cache
from app.services.structure_extractor import StructureExtractor, ContractMap
from app.core.config import settings


router = APIRouter()

# Zero Data Retention Mode - Enable for enterprise clients
# When True: No document text is stored, only audit logs
ZDR_MODE = getattr(settings, 'ZERO_DATA_RETENTION', True)  # Default: ON for safety


# ============================================================================
# Schemas - Strict RED/YELLOW/GREEN enum
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze document text."""
    text: str
    playbook_id: Optional[str] = None
    filename: Optional[str] = "untitled.docx"


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


class RedlineResponse(BaseModel):
    """Redline suggestion response."""
    original_text: str
    suggested_text: str
    ooxml: str
    match_confidence: float = 1.0  # Confidence of text anchor match (0.0-1.0)
    match_method: str = "exact"  # "hash", "exact", or "fuzzy"


class SummaryRequest(BaseModel):
    """Request for contract summary."""
    document_id: str
    contract_text: str  # Full contract text for summary
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
    text: str  # Full contract text
    playbook_id: Optional[str] = None
    filename: Optional[str] = "untitled.docx"


class AIRedlineItem(BaseModel):
    """Single redline item from AI analysis."""
    id: str
    risk_level: Literal["RED", "YELLOW"]
    rule_name: str
    original_text: str  # Exact text from contract for search
    explanation: str
    suggested_fix: str


class AIAnalysisResponse(BaseModel):
    """Response from AI-first analysis."""
    document_id: str
    filename: str
    executive_summary: List[str]
    redlines: List[AIRedlineItem]
    total_risks: int
    risk_summary: dict  # {red: int, yellow: int}
    tokens_used: int = 0


# ============================================================================
# Analyze Endpoint - Real Implementation
# ============================================================================

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_document(
    request: AnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    from uuid import UUID as PyUUID, uuid4
    from sqlalchemy.orm import selectinload
    from app.models.playbook import Playbook
    
    # Get client info for audit
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    # Initialize services
    ai_service = AIService()
    cache = await get_cache()
    
    # Load playbook rules if specified, otherwise use defaults
    if request.playbook_id:
        try:
            playbook_uuid = PyUUID(request.playbook_id)
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
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=request.filename,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    await db.flush()
    
    try:
        # Step 1: Rule-based detection
        matches = rule_engine.evaluate(request.text)
        
        # Step 2: AI enrichment in PARALLEL (critical for performance)
        total_tokens = 0
        
        if matches:
            # Create async tasks for all matches
            async def enrich_with_cache(match: RuleMatch) -> RuleMatch:
                """Enrich a match, checking cache first."""
                nonlocal total_tokens
                
                # Check cache
                cache_key = match.cache_key()
                if cache.is_connected:
                    cached = await cache.get(cache_key)
                    if cached:
                        match.ai_explanation = cached.get("explanation")
                        match.suggested_fix = cached.get("suggested_fix")
                        return match
                
                # Call AI service
                explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
                total_tokens += tokens
                
                match.ai_explanation = explanation
                match.suggested_fix = suggested_fix
                
                # Store in cache
                if cache.is_connected and (explanation or suggested_fix):
                    await cache.set(cache_key, {
                        "explanation": explanation,
                        "suggested_fix": suggested_fix,
                    }, ttl=3600)
                
                return match
            
            # Run all AI calls in parallel using asyncio.gather
            enriched_matches = await asyncio.gather(
                *[enrich_with_cache(match) for match in matches]
            )
        else:
            enriched_matches = []
        
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
            
            await db.commit()
            await db.refresh(document)
            
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
        
    except Exception as e:
        # Mark document as failed
        document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


# ============================================================================
# AI-First Analysis Endpoint - Full Gemini Analysis
# ============================================================================

@router.post("/analyze-full", response_model=AIAnalysisResponse)
async def analyze_full_ai(
    request: AIAnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI-First contract analysis using Gemini.
    
    This endpoint sends the FULL contract text + playbook rules to Gemini
    for comprehensive analysis, returning executive summary and redlines.
    
    Unlike /analyze, this does NOT use rule-based regex matching.
    Gemini performs holistic structural analysis + surgical redlining.
    """
    from uuid import uuid4
    from sqlalchemy.orm import selectinload
    from app.services.gemini_analyzer import gemini_analyzer
    
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
                .options(selectinload(Playbook.rules))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            
            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.name,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "description": rule.description or "",
                    }
                    for rule in playbook.rules
                ]
        except Exception as e:
            print(f"Error loading playbook: {e}")
    
    # Generate document ID for tracking
    doc_id = str(uuid4())
    
    try:
        # Call Gemini analyzer with full contract + playbook
        result = await gemini_analyzer.analyze_full_contract(
            contract_text=request.text,
            playbook_rules=playbook_rules,
            playbook_name=playbook_name
        )
        
        # Log audit event (ZDR-safe: no contract text stored)
        import json
        await log_audit_event(
            db=db,
            user=current_user,  # Pass user object, not user_id
            action="ai_full_analysis",
            resource_type="contract",
            resource_name=request.filename or "untitled.docx",  # resource_name, not resource_id
            ip_address=client_ip,
            risk_count=len(result.redlines),
            details=json.dumps({
                "playbook": playbook_name,
                "redlines_count": len(result.redlines),
                "tokens_used": result.tokens_used,
            }),
        )
        
        # Build response
        redline_items = [
            AIRedlineItem(
                id=str(uuid4()),
                risk_level=r.risk_level,
                rule_name=r.rule_name,
                original_text=r.original_text,
                explanation=r.explanation,
                suggested_fix=r.suggested_fix,
            )
            for r in result.redlines
        ]
        
        risk_summary = {
            "red": sum(1 for r in result.redlines if r.risk_level == "RED"),
            "yellow": sum(1 for r in result.redlines if r.risk_level == "YELLOW"),
        }
        
        return AIAnalysisResponse(
            document_id=doc_id,
            filename=request.filename or "untitled.docx",
            executive_summary=result.executive_summary,
            redlines=redline_items,
            total_risks=len(redline_items),
            risk_summary=risk_summary,
            tokens_used=result.tokens_used,
        )
        
    except Exception as e:
        print(f"AI analysis error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}"
        )


# ============================================================================
# Analyze File Endpoint - DOCX Upload (Box 1 Integration)
# ============================================================================

@router.post("/analyze-file", response_model=AnalysisResult)
async def analyze_file(
    http_request: Request,
    file: UploadFile = File(...),
    playbook_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    from uuid import UUID as PyUUID, uuid4
    from sqlalchemy.orm import selectinload
    from app.models.playbook import Playbook
    
    # Validate file type
    filename = file.filename or "document.docx"
    content_type = file.content_type or ""
    
    if not (filename.endswith(".docx") or "wordprocessingml" in content_type):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported. For raw text, use /analyze endpoint."
        )
    
    # Get client info for audit
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    
    # Read file content
    file_bytes = await file.read()
    
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
            playbook_uuid = PyUUID(playbook_id)
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
        total_tokens = 0
        
        if matches:
            async def enrich_with_cache(match: RuleMatch) -> RuleMatch:
                nonlocal total_tokens
                
                cache_key = match.cache_key()
                if cache.is_connected:
                    cached = await cache.get(cache_key)
                    if cached:
                        match.ai_explanation = cached.get("explanation")
                        match.suggested_fix = cached.get("suggested_fix")
                        return match
                
                explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
                total_tokens += tokens
                
                match.ai_explanation = explanation
                match.suggested_fix = suggested_fix
                
                if cache.is_connected and (explanation or suggested_fix):
                    await cache.set(cache_key, {
                        "explanation": explanation,
                        "suggested_fix": suggested_fix,
                    }, ttl=3600)
                
                return match
            
            enriched_matches = await asyncio.gather(
                *[enrich_with_cache(match) for match in matches]
            )
        else:
            enriched_matches = []
        
        # Build response with ContractMap metadata
        risk_summary = rule_engine.get_risk_summary(enriched_matches)
        
        # Update document
        document.total_risks = len(enriched_matches)
        document.risk_summary = risk_summary
        document.status = DocumentStatus.COMPLETED
        
        await db.commit()
        await db.refresh(document)
        
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
        
    except Exception as e:
        document.status = DocumentStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )

# ============================================================================
# Contract Summary Endpoint - AI-Powered Executive Summary
# ============================================================================

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_contract(
    request: SummaryRequest,
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
    from uuid import UUID as PyUUID
    
    # For ZDR mode, document might not exist - that's OK for summary
    # We just need the contract text which is passed in the request
    document = None
    try:
        doc_uuid = PyUUID(request.document_id)
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
            pb_uuid = PyUUID(request.playbook_id)
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
            doc_uuid = PyUUID(request.document_id)
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
    from uuid import UUID as PyUUID
    
    # Initialize redline implementer
    implementer = RedlineImplementer()
    
    # Mode 1: ZDR Mode - text provided directly in request
    if request.original_text and request.suggested_text:
        result = implementer.apply_redline(
            original_text=request.original_text,
            suggested_text=request.suggested_text,
            paragraph_hash=request.paragraph_hash
        )
        
        if not result.success:
            # Even if anchor not found, still generate OOXML with provided text
            ooxml = implementer.generate_track_changes_ooxml(
                original=request.original_text,
                replacement=request.suggested_text
            )
            return RedlineResponse(
                original_text=request.original_text,
                suggested_text=request.suggested_text,
                ooxml=ooxml,
                match_confidence=0.0,
                match_method="direct"
            )
        
        return RedlineResponse(
            original_text=result.original,
            suggested_text=result.replacement,
            ooxml=result.track_changes_ooxml,
            match_confidence=result.anchor.match_confidence if result.anchor else 1.0,
            match_method=result.anchor.match_method if result.anchor else "direct"
        )
    
    # Mode 2: DB Mode - look up risk by ID
    try:
        risk_uuid = PyUUID(request.risk_id)
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
    
    return RedlineResponse(
        original_text=original,
        suggested_text=suggested,
        ooxml=redline_result.track_changes_ooxml,
        match_confidence=redline_result.anchor.match_confidence if redline_result.anchor else 1.0,
        match_method=redline_result.anchor.match_method if redline_result.anchor else "exact"
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
