"""
Gemini Analyzer - AI-First Contract Analysis Service.

This service uses Google Gemini to perform holistic contract analysis
against a client playbook, returning structured JSON with executive
summary and redline suggestions.
"""

import asyncio
import json
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from app.core.config import settings
from app.core.vertex_client import get_generative_model, is_available, get_backend
from app.services.jurisdiction_detector import jurisdiction_detector, JurisdictionDetectionResult
from app.services.defined_terms_resolver import defined_terms_resolver, DefinedTermsResult
from app.services.prompt_templates import (
    render_system_prompt,
    render_user_prompt,
    render_fix_prompt,
    render_clause_generation_prompt,
    render_research_prompt,
    LEGACY_PROMPT,
)


class AIServiceError(Exception):
    """Base exception for AI service failures."""
    def __init__(self, message: str, error_code: str = "ai_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AIServiceUnavailable(AIServiceError):
    """AI service is not configured or unreachable."""
    def __init__(self, message: str = "AI service is not configured. Please set GEMINI_API_KEY."):
        super().__init__(message, "ai_not_configured")


class AIRateLimited(AIServiceError):
    """AI service rate limited."""
    def __init__(self, message: str = "AI service is temporarily rate limited. Please try again in a minute."):
        super().__init__(message, "ai_rate_limited")


class AIServiceTimeout(AIServiceError):
    """AI service timed out."""
    def __init__(self, message: str = "AI analysis timed out. Please try with a shorter document."):
        super().__init__(message, "ai_timeout")

logger = logging.getLogger(__name__)


def _sanitize_for_prompt(text: str, max_length: int = 50000) -> str:
    """Sanitize user-supplied text before interpolating into AI prompts.

    Strips control characters and truncates to max_length to reduce prompt
    injection surface. Does not guarantee injection prevention — defense in
    depth via structured prompts and output validation is also needed.
    """
    if not text:
        return ""
    # Strip ASCII control chars except newline/tab
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return cleaned[:max_length]


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json and ``` markdown fences from AI responses.

    Gemini sometimes wraps JSON output in markdown code fences even when
    instructed not to.  This helper normalises that before JSON parsing.
    """
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _classify_gemini_error(e: Exception) -> AIServiceError:
    """Classify a generic exception into the appropriate AI error type.

    Inspects the stringified exception for keywords that indicate rate
    limiting, timeouts, or authentication issues and returns the matching
    concrete ``AIServiceError`` subclass instance.
    """
    error_msg = str(e).lower()
    if "429" in str(e) or "rate" in error_msg or "quota" in error_msg:
        return AIRateLimited()
    if "timeout" in error_msg or "deadline" in error_msg:
        return AIServiceTimeout()
    if "api key" in error_msg or ("invalid" in error_msg and "key" in error_msg):
        return AIServiceUnavailable("AI API key is invalid. Please check your configuration.")
    return AIServiceError(f"AI operation failed: {type(e).__name__}: {e}", "ai_error")


_VALID_RISK_LEVELS = {"RED", "YELLOW", "GREEN"}

# Legacy prompt kept as fallback — new code uses prompt_templates.py
CONTRARED_SYSTEM_PROMPT = LEGACY_PROMPT


@dataclass
class AIRedline:
    """A single redline from AI analysis."""
    risk_level: str
    rule_name: str
    original_text: str
    explanation: str
    recommendation: str  # Lawyer-readable guidance (not exact replacement text)
    redline_type: str = "violation"  # "violation" or "missing"
    # Phase 4: confidence and verification fields
    confidence: Optional[float] = None  # AI self-reported confidence (0-1)
    confidence_level: Optional[str] = None  # HIGH/MEDIUM/LOW (set by pipeline)
    verification_status: Optional[str] = None  # exact/normalized/fuzzy_corrected/rejected
    verified_text: Optional[str] = None  # Corrected text after hallucination guard
    is_deal_breaker: bool = False


@dataclass
class AIAnalysisResult:
    """Complete AI analysis result."""
    executive_summary: List[str]
    redlines: List[AIRedline]
    tokens_used: int
    raw_response: str
    # Phase 4: pipeline metadata
    jurisdiction_code: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    hallucination_stats: Optional[Dict[str, Any]] = None
    stage_metrics: Optional[List[Dict[str, Any]]] = None
    partial: bool = False  # True if pipeline degraded gracefully


class GeminiAnalyzer:
    """
    AI-First contract analyzer using Google Gemini.

    Sends full contract + playbook to Gemini and receives
    structured JSON with executive summary and redlines.
    """

    def __init__(self) -> None:
        """Initialize AI client — prefers Vertex AI, falls back to consumer Gemini."""
        self._client = None
        self._analysis_client = None
        # Enabled if *either* Vertex AI credentials or consumer API key is set
        self._enabled: bool = bool(settings.VERTEX_PROJECT_ID) or bool(settings.GEMINI_API_KEY)

    @property
    def client(self):
        """Lazy initialization of fast/cheap model client (for subtasks like fix generation)."""
        if self._client is None and self._enabled:
            try:
                self._client = get_generative_model(settings.GEMINI_MODEL)
                logger.info("AI subtask client ready (backend=%s, model=%s)", get_backend(), settings.GEMINI_MODEL)
            except RuntimeError:
                logger.warning("No AI backend available for subtask client")
                self._enabled = False
        return self._client

    @property
    def analysis_client(self):
        """Lazy initialization of Pro model client (for full contract analysis)."""
        if self._analysis_client is None and self._enabled:
            try:
                self._analysis_client = get_generative_model(settings.GEMINI_ANALYSIS_MODEL)
                logger.info("AI analysis client ready (backend=%s, model=%s)", get_backend(), settings.GEMINI_ANALYSIS_MODEL)
            except RuntimeError:
                logger.warning("No AI backend available for analysis client")
                self._enabled = False
        return self._analysis_client

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def format_playbook_rules(self, playbook_rules: List[Dict]) -> str:
        """Format playbook rules into structured text for Gemini, branching on detection_mode."""
        if not playbook_rules:
            return "No specific playbook rules provided. Apply standard commercial contract best practices."

        lines = [f"Total rules to check: {len(playbook_rules)}. Evaluate EACH rule against the contract.\n"]
        for i, rule in enumerate(playbook_rules, 1):
            name = rule.get('name', rule.get('rule_name', 'Unknown'))
            risk = rule.get('risk_level', 'YELLOW')
            position = rule.get('primary_position', rule.get('description', 'Standard terms expected'))
            fallback = rule.get('fallback_position', '')
            deal_breaker = rule.get('is_deal_breaker', False)
            verification = rule.get('verification_prompt', '')
            detection_mode = rule.get('detection_mode', 'keywords_only')
            risk_description = rule.get('risk_description', '')
            acceptable_pos = rule.get('acceptable_position', '')
            unacceptable = rule.get('unacceptable_signals', [])
            acceptable = rule.get('acceptable_signals', [])
            clause_context = rule.get('clause_context', '')

            line = f"Rule #{i}: {name} | Risk: {risk}"
            if deal_breaker:
                line += " | DEAL-BREAKER (must flag if violated)"

            # AI-primary rules: inject natural language description
            if detection_mode in ('ai_only', 'ai_with_keywords') and risk_description:
                line += f"\n  RISK TO DETECT: {risk_description}"
                if clause_context:
                    line += f"\n  CONTEXT: {clause_context}"
                if unacceptable:
                    line += f"\n  RED FLAGS: {', '.join(unacceptable)}"
                if acceptable:
                    line += f"\n  SAFE SIGNALS: {', '.join(acceptable)}"
                if acceptable_pos:
                    line += f"\n  ACCEPTABLE IF: {acceptable_pos}"

            # Position info (always included)
            line += f"\n  Position: {position}"
            if fallback:
                line += f"\n  Fallback: {fallback}"
            if verification:
                line += f"\n  Check: {verification}"

            lines.append(line)

        return "\n".join(lines)

    async def analyze_full_contract(
        self,
        contract_text: str,
        playbook_rules: Optional[List[Dict]] = None,
        playbook_name: str = "Default",
        jurisdiction_override: Optional[str] = None,
        party_side: str = "seller",
    ) -> AIAnalysisResult:
        """
        Perform full AI analysis of a contract.

        Phase 4 enhancements:
        - Auto-detects jurisdiction from contract text (or uses override)
        - Extracts and resolves defined terms
        - Uses V2 structured prompt with jurisdiction context and defined terms
        - Includes AI self-reported confidence scores

        Args:
            contract_text: The complete contract text
            playbook_rules: List of playbook rule dictionaries
            playbook_name: Name of the playbook for context
            jurisdiction_override: Optional jurisdiction code/name to skip auto-detection

        Returns:
            AIAnalysisResult with executive summary, redlines, and jurisdiction info
        """
        if not self._enabled:
            raise AIServiceUnavailable()

        # --- Phase 4: Jurisdiction detection (deterministic, no AI cost) ---
        jurisdiction_result: JurisdictionDetectionResult = jurisdiction_detector.detect(
            contract_text, user_override=jurisdiction_override
        )
        jurisdiction_context = jurisdiction_result.prompt_context()
        jurisdiction_name = jurisdiction_result.profile.name if jurisdiction_result.profile else "applicable"

        # --- Phase 4: Defined terms extraction (deterministic, no AI cost) ---
        terms_result: DefinedTermsResult = defined_terms_resolver.resolve(contract_text)
        defined_terms_context = terms_result.to_prompt_context()

        # Format the playbook rules
        rules_text = self.format_playbook_rules(playbook_rules or [])

        # Sanitize user-supplied inputs before prompt interpolation
        truncation_warning = None
        safe_contract_text = _sanitize_for_prompt(contract_text, max_length=200000)
        if len(contract_text) > 200000:
            truncation_warning = f"Document truncated: Only the first ~{200000 // 1000}K characters ({200000 // 4000} pages) were analyzed. Later sections may contain unreviewed risks."
        safe_playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        # --- Phase 4: Build V2 structured prompts ---
        system_prompt = render_system_prompt(
            jurisdiction_context=jurisdiction_context,
            defined_terms=defined_terms_context,
            party_side=party_side,
        )
        user_prompt = render_user_prompt(
            contract_text=safe_contract_text,
            playbook_rules=rules_text,
            playbook_name=safe_playbook_name,
        )

        try:
            # Use clear delimiters for stronger prompt hierarchy separation
            full_prompt = f"<SYSTEM_INSTRUCTIONS>\n{system_prompt}\n</SYSTEM_INSTRUCTIONS>\n\n<USER_REQUEST>\n{user_prompt}\n</USER_REQUEST>"

            # Run in thread pool since Gemini SDK is sync, with timeout
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.analysis_client.generate_content(
                        full_prompt,
                        generation_config={
                            "max_output_tokens": 32768,  # Large output for exhaustive rule-by-rule analysis
                            "temperature": 0.1,  # Very low temperature for precise, consistent output
                        }
                    )
                ),
                timeout=90.0,
            )

            # Extract text from response
            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                logger.warning("Gemini returned empty response")
                raise AIServiceError("AI returned an empty response. Please try again.", "ai_empty_response")

            # Parse JSON from response
            result = self._parse_response(response_text)

            # Attach truncation warning if document was truncated
            if truncation_warning:
                result.executive_summary.insert(0, truncation_warning)

            # Attach jurisdiction metadata
            result.jurisdiction_code = jurisdiction_result.detected_jurisdiction
            result.jurisdiction_name = jurisdiction_name

            return result

        except (AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout):
            raise
        except asyncio.TimeoutError:
            raise AIServiceTimeout()
        except Exception as e:
            logger.error("Gemini analysis error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)

    def _parse_response(self, response_text: str) -> AIAnalysisResult:
        """Parse Gemini's JSON response into structured result."""
        try:
            # Clean up response - remove any markdown formatting
            cleaned = _strip_markdown_fences(response_text)

            # Parse JSON
            data = json.loads(cleaned)

            # Extract executive summary
            executive_summary = data.get("executive_summary", [])
            if isinstance(executive_summary, str):
                executive_summary = [executive_summary]

            # Extract redlines
            redlines = []
            for item in data.get("redlines", []):
                rtype = item.get("redline_type", "violation")
                if rtype not in ("violation", "missing"):
                    rtype = "violation"

                # Validate risk_level — default to YELLOW if invalid
                risk_level = item.get("risk_level", "YELLOW")
                if risk_level not in _VALID_RISK_LEVELS:
                    risk_level = "YELLOW"

                # Phase 4: extract AI self-reported confidence from V2 prompt
                ai_confidence = item.get("confidence")
                if ai_confidence is not None:
                    try:
                        ai_confidence = float(ai_confidence)
                        ai_confidence = max(0.0, min(1.0, ai_confidence))
                    except (ValueError, TypeError):
                        ai_confidence = None

                redlines.append(AIRedline(
                    risk_level=risk_level,
                    rule_name=item.get("rule_name", "Unknown Rule"),
                    original_text=item.get("original_text", ""),
                    explanation=item.get("explanation", ""),
                    recommendation=item.get("recommendation", "") or item.get("suggested_fix", ""),
                    redline_type=rtype,
                    confidence=ai_confidence,
                ))

            # Estimate tokens used
            tokens_estimate = len(response_text.split())

            return AIAnalysisResult(
                executive_summary=executive_summary,
                redlines=redlines,
                tokens_used=tokens_estimate,
                raw_response=response_text
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON: %s", e)
            logger.debug("Raw response: %s...", response_text[:500])
            return self._fallback_result(response_text)

    def _fallback_result(self, raw_response: str = "") -> AIAnalysisResult:
        """Return a fallback result when AI analysis fails."""
        return AIAnalysisResult(
            executive_summary=["AI analysis unavailable. Please try again."],
            redlines=[],
            tokens_used=0,
            raw_response=raw_response
        )

    async def generate_clause(
        self,
        clause_type: str,
        contract_context: str = "",
        playbook_rules: Optional[List[Dict]] = None,
        jurisdiction_override: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate a contract clause using AI.

        Phase 4: Uses jurisdiction-aware prompt templates.

        Returns dict with 'clause_text' and 'reasoning'.
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_clause_type = _sanitize_for_prompt(clause_type, max_length=200)
        safe_context = _sanitize_for_prompt(contract_context, max_length=3000) if contract_context else ""

        # Phase 4: Detect jurisdiction from context (if available)
        jurisdiction_result = jurisdiction_detector.detect(
            contract_context or "", user_override=jurisdiction_override
        )
        j_context = jurisdiction_result.prompt_context()
        j_name = jurisdiction_result.profile.name if jurisdiction_result.profile else "applicable"

        rules_context = ""
        if playbook_rules:
            matching = [r for r in playbook_rules if r.get("name", "").lower() == safe_clause_type.lower()]
            if not matching:
                words = safe_clause_type.lower().split()
                matching = [r for r in playbook_rules if any(w in r.get("name", "").lower() for w in words)]
            if matching:
                rules_context = "\n".join(
                    f"- {_sanitize_for_prompt(r['name'], 200)}: Position: {_sanitize_for_prompt(r.get('primary_position', ''), 500)}. "
                    f"Fallback: {_sanitize_for_prompt(r.get('fallback_position', ''), 500)}. "
                    f"Risk level: {_sanitize_for_prompt(r.get('risk_level', ''), 50)}."
                    for r in matching
                )

        # Phase 4: Use jurisdiction-aware prompt template
        prompt = render_clause_generation_prompt(
            clause_type=safe_clause_type,
            jurisdiction_context=j_context,
            jurisdiction_name=j_name,
            playbook_guidance=rules_context,
            contract_context=safe_context,
        )
        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": 4096,
                            "temperature": 0.3,
                        }
                    )
                ),
                timeout=90.0,
            )

            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                raise AIServiceError("AI returned an empty response.", "ai_empty_response")

            # Parse JSON
            cleaned = _strip_markdown_fences(response_text)

            data = json.loads(cleaned)
            return {
                "clause_text": data.get("clause_text", ""),
                "reasoning": data.get("reasoning", ""),
            }

        except (AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout):
            raise
        except asyncio.TimeoutError:
            raise AIServiceTimeout()
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract the clause from raw text
            logger.warning("Failed to parse clause generation JSON, using raw text")
            return {
                "clause_text": response_text.strip(),
                "reasoning": "Generated clause (raw format — JSON parsing failed).",
            }
        except Exception as e:
            logger.error("Clause generation error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)

    async def generate_fix(
        self,
        original_text: str,
        recommendation: str,
        rule_name: str,
        redline_type: str = "violation",
        surrounding_context: str = "",
        playbook_rules: Optional[List[Dict[str, Any]]] = None,
        jurisdiction_override: Optional[str] = None,
        defined_terms: str = "",
    ) -> Dict[str, Any]:
        """
        Generate exact replacement/insertion text for a specific risk.

        Phase 4: Uses jurisdiction-aware prompt templates.
        Uses Flash-Lite model (self.client) for fast, cheap per-issue fix generation.
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_original = _sanitize_for_prompt(original_text, max_length=3000)
        safe_recommendation = _sanitize_for_prompt(recommendation, max_length=2000)
        safe_rule_name = _sanitize_for_prompt(rule_name, max_length=200)
        safe_context = _sanitize_for_prompt(surrounding_context, max_length=5000) if surrounding_context else ""

        # Phase 4: Detect jurisdiction from context
        jurisdiction_result = jurisdiction_detector.detect(
            surrounding_context or original_text, user_override=jurisdiction_override
        )
        j_context = jurisdiction_result.prompt_context()
        j_name = jurisdiction_result.profile.name if jurisdiction_result.profile else "applicable"

        # Build playbook guidance if available
        playbook_guidance = ""
        if playbook_rules:
            matching_rules = [r for r in playbook_rules if r.get("name", "").lower() in rule_name.lower() or rule_name.lower() in r.get("name", "").lower()]
            if matching_rules:
                rule = matching_rules[0]
                playbook_guidance = (
                    f"- Preferred Position: {rule.get('primary_position', 'N/A')}\n"
                    f"- Fallback Position: {rule.get('fallback_position', 'N/A')}\n"
                    f"- Deal Breaker: {'Yes' if rule.get('is_deal_breaker') else 'No'}\n"
                    f"Align the fix with the preferred position where possible."
                )

        # Phase 4: Use jurisdiction-aware prompt template
        prompt = render_fix_prompt(
            redline_type=redline_type,
            original_text=safe_original,
            recommendation=safe_recommendation,
            rule_name=safe_rule_name,
            jurisdiction_context=j_context,
            jurisdiction_name=j_name,
            surrounding_context=safe_context,
            playbook_guidance=playbook_guidance,
            defined_terms=defined_terms,
        )

        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": 4096,
                            "temperature": 0.2,
                        }
                    )
                ),
                timeout=90.0,
            )

            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                raise AIServiceError("AI returned an empty response.", "ai_empty_response")

            # Parse JSON
            cleaned = _strip_markdown_fences(response_text)

            data = json.loads(cleaned)
            fix_text = data.get("fix_text", "").strip()
            if not fix_text:
                raise AIServiceError("AI returned empty fix text.", "ai_empty_fix")

            return {
                "fix_text": fix_text,
                "reasoning": data.get("reasoning", ""),
            }

        except (AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout):
            raise
        except asyncio.TimeoutError:
            raise AIServiceTimeout()
        except json.JSONDecodeError:
            # If JSON parsing fails, try to use raw text as fix
            logger.warning("Failed to parse fix generation JSON, using raw text")
            raw = response_text.strip()
            if raw:
                return {
                    "fix_text": raw,
                    "reasoning": "Generated fix (raw format — JSON parsing failed).",
                }
            raise AIServiceError("Failed to parse AI response.", "ai_parse_error")
        except Exception as e:
            logger.error("Fix generation error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)

    async def analyze_clause(
        self,
        clause_text: str,
        playbook_rules: list = None,
        playbook_name: str = "Default",
        jurisdiction: str = None,
    ) -> dict:
        """
        Analyze a single clause/text selection for risks.

        Lightweight alternative to analyze_full_contract — designed for
        inline selection scanning from the Word Add-in.

        Returns dict with 'redlines' list and 'tokens_used' count.
        """
        if not self._enabled:
            raise AIServiceUnavailable()

        safe_clause = _sanitize_for_prompt(clause_text, max_length=10000)

        # Build playbook rules section (limit to 20 rules)
        rules_section = ""
        if playbook_rules:
            limited_rules = playbook_rules[:20]
            rules_lines = [f"Playbook: {_sanitize_for_prompt(playbook_name, 200)} ({len(limited_rules)} rules)\n"]
            for i, rule in enumerate(limited_rules, 1):
                name = rule.get("name", rule.get("rule_name", "Unknown"))
                risk = rule.get("risk_level", "YELLOW")
                position = rule.get("primary_position", rule.get("description", ""))
                rules_lines.append(f"  Rule #{i}: {name} | Risk: {risk} | Position: {position}")
            rules_section = "\n".join(rules_lines)
        else:
            rules_section = "No specific playbook rules provided. Apply standard commercial contract best practices."

        # Build jurisdiction context
        jurisdiction_section = ""
        if jurisdiction:
            safe_jurisdiction = _sanitize_for_prompt(jurisdiction, max_length=100)
            jurisdiction_section = f"\nJurisdiction: {safe_jurisdiction}. Flag any jurisdiction-specific risks.\n"

        prompt = f"""You are a senior contract lawyer performing a focused risk analysis on a SINGLE clause.

Analyze the following clause text and identify any risks, issues, or deviations from the playbook rules.

{rules_section}
{jurisdiction_section}
CLAUSE TEXT:
\"\"\"
{safe_clause}
\"\"\"

Return a JSON array of risk objects. Each object must have these fields:
- "id": unique string identifier (e.g. "clause-risk-1")
- "risk_level": "RED" or "YELLOW"
- "rule_name": name of the violated rule or issue category
- "original_text": the exact problematic text from the clause
- "explanation": why this is a risk (1-2 sentences)
- "recommendation": what should be changed (lawyer-readable guidance)
- "redline_type": "violation" or "missing"

If the clause has NO risks, return an empty array: []

IMPORTANT: Return ONLY the JSON array, no markdown fences, no commentary."""

        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": 4096,
                            "temperature": 0.1,
                        }
                    )
                ),
                timeout=30.0,
            )

            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                raise AIServiceError("AI returned an empty response.", "ai_empty_response")

            # Parse JSON response
            cleaned = _strip_markdown_fences(response_text)
            data = json.loads(cleaned)

            # Handle both array and object responses
            if isinstance(data, list):
                redlines = data
            elif isinstance(data, dict):
                redlines = data.get("redlines", data.get("risks", []))
            else:
                redlines = []

            # Validate risk levels
            for item in redlines:
                if item.get("risk_level") not in _VALID_RISK_LEVELS:
                    item["risk_level"] = "YELLOW"

            tokens_estimate = len(response_text.split())

            return {
                "redlines": redlines,
                "tokens_used": tokens_estimate,
            }

        except (AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout):
            raise
        except asyncio.TimeoutError:
            raise AIServiceTimeout()
        except json.JSONDecodeError:
            logger.warning("Failed to parse clause analysis JSON, returning empty")
            return {
                "redlines": [],
                "tokens_used": 0,
            }
        except Exception as e:
            logger.error("Clause analysis error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)

    async def research_clause(
        self,
        clause_text: str,
        clause_type: str = "",
        jurisdiction_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Research relevant case law for a given clause.

        Phase 4: Uses jurisdiction-aware prompts — no longer hardcoded to Indian law.
        Uses Gemini's knowledge to suggest relevant judicial decisions.
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_clause_type = _sanitize_for_prompt(clause_type, max_length=200) if clause_type else "Contract Clause"
        safe_clause_text = _sanitize_for_prompt(clause_text, max_length=2000)

        # Phase 4: Detect jurisdiction from clause text
        jurisdiction_result = jurisdiction_detector.detect(
            clause_text, user_override=jurisdiction_override
        )
        j_context = jurisdiction_result.prompt_context()
        j_name = jurisdiction_result.profile.name if jurisdiction_result.profile else "applicable"

        # Phase 4: Use jurisdiction-aware prompt template
        prompt = render_research_prompt(
            clause_text=safe_clause_text,
            clause_type=safe_clause_type,
            jurisdiction_context=j_context,
            jurisdiction_name=j_name,
        )
        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": 4096,
                            "temperature": 0.2,
                        }
                    )
                ),
                timeout=90.0,
            )

            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text

            if not response_text:
                raise AIServiceError("AI returned an empty response.", "ai_empty_response")

            cleaned = _strip_markdown_fences(response_text)

            data = json.loads(cleaned)
            return {
                "cases": data.get("cases", []),
                "legal_principle": data.get("legal_principle", ""),
                "disclaimer": f"AI-suggested references for {j_name} law \u2014 verify all citations independently before relying on them in legal proceedings.",
            }

        except (AIServiceError, AIServiceUnavailable, AIRateLimited, AIServiceTimeout):
            raise
        except asyncio.TimeoutError:
            raise AIServiceTimeout()
        except json.JSONDecodeError:
            logger.warning("Failed to parse research JSON, returning raw")
            return {
                "cases": [],
                "legal_principle": response_text.strip()[:500],
                "disclaimer": f"AI-suggested references for {j_name} law \u2014 verify all citations independently before relying on them in legal proceedings.",
            }
        except Exception as e:
            logger.error("Research clause error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)


# Singleton instance
gemini_analyzer = GeminiAnalyzer()
