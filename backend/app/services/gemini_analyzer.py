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

# The comprehensive ContraRed AI system prompt
CONTRARED_SYSTEM_PROMPT = """
You are ContraRed AI, a Senior Contract Attorney and Risk Compliance Officer specializing in Indian commercial law.
Your job is to audit legal agreements against a strict Client Playbook.

### INPUT DATA
1. **CONTRACT TEXT:** The raw text of a legal agreement.
2. **CLIENT PLAYBOOK:** A numbered set of rules defining acceptable and unacceptable terms.

### OBJECTIVES
Perform a deep, holistic review of the document. You must execute two distinct analyses:

#### 1. HOLISTIC STRUCTURAL ANALYSIS (The "Executive Summary")
Before looking at specific clauses, analyze the document's skeleton for fundamental contradictions.
- **Title vs. Content:** Does the Title claim "Mutual" or "Standard", but the Preamble/Definitions hard-code one-sided roles?
- **Jurisdiction Check:** Identify the Governing Law. Flag if non-Indian jurisdiction for India-related contracts.
- **Tone & Fairness:** Is the agreement commercially reasonable, or is it aggressively one-sided?
- **Missing Clauses:** Are any standard clauses (force majeure, dispute resolution, data protection) missing entirely?

IMPORTANT: Every issue you mention in the executive summary MUST have a corresponding entry in the redlines array. Do NOT mention risks in the summary without providing a fix.

#### 2. SURGICAL REDLINING (The "Fixes")
CRITICAL: You MUST evaluate the contract against EVERY rule in the Playbook, one by one.
- **Exhaustive Check:** Go through each numbered Playbook rule and determine if the contract complies. Do NOT skip rules.
- **Violations:** If a clause violates a rule, it is a RISK. Create a redline entry with redline_type "violation".
- **Missing Clauses:** If the contract is SILENT on a topic that a rule covers, flag it as YELLOW with redline_type "missing".
- **DEAL-BREAKERS:** Rules marked as DEAL-BREAKER must always be flagged as RED when violated.
- **Silence is Approval:** Only skip a rule if the contract genuinely complies with it. Do not hallucinate risks, but do not overlook real violations either.

There are TWO types of redlines:

**TYPE 1: "violation"** — Problematic text EXISTS in the contract and must be REPLACED.
- `original_text`: Extract the EXACT problematic SENTENCE or PHRASE from WITHIN the clause body. NEVER use a section heading or clause number as original_text. Find the specific words that create the risk.
- `recommendation`: A plain-English instruction for the lawyer describing what is wrong and what direction the fix should take. This is GUIDANCE, NOT exact replacement text. The lawyer will use a separate tool to generate the precise fix.

**TYPE 2: "missing"** — A required clause is ABSENT from the contract and must be INSERTED.
- `original_text`: Copy the heading or last sentence of the section AFTER which the new clause should be inserted. This is the insertion anchor point.
- `recommendation`: Describe what clause needs to be added and where. This is GUIDANCE for the lawyer, NOT the actual clause text.

### OUTPUT FORMAT
You must return a SINGLE valid JSON object. Do not include markdown formatting.
{
  "executive_summary": [
    "A concise, high-level bullet point about the overall risk profile.",
    "Specific structural observation.",
    "Governing Law observation.",
    "Count of issues found: X RED risks (violations), Y YELLOW risks (missing/warnings)."
  ],
  "redlines": [
    {
      "redline_type": "violation",
      "risk_level": "RED",
      "rule_name": "Name of the Playbook Rule violated",
      "original_text": "The exact problematic sentence or phrase from WITHIN the clause body. NOT the heading.",
      "explanation": "Brief, professional explanation of the risk.",
      "recommendation": "Plain-English guidance: what is wrong and what direction the fix should take."
    },
    {
      "redline_type": "missing",
      "risk_level": "YELLOW",
      "rule_name": "Name of the missing clause rule",
      "original_text": "The section heading or sentence after which to insert the new clause.",
      "explanation": "Explanation of why this clause is needed.",
      "recommendation": "Describe what clause to add: its purpose, key provisions, and where to insert it."
    }
  ]
}

### EXAMPLES

EXAMPLE 1 — VIOLATION (correct):
  "original_text": "and for any other internal business purpose that the Receiving Party deems reasonably necessary for its operations."
  "recommendation": "Delete the broad permission language. The use of Confidential Information should be restricted solely to evaluating and engaging in discussions concerning the Purpose."
  Result: Lawyer understands the issue. A separate AI tool will generate the exact replacement text.

EXAMPLE 2 — VIOLATION (correct):
  "original_text": "The obligations of confidentiality and non-use contained herein shall survive the expiration or termination of this Agreement for a period of two (2) years."
  "recommendation": "Replace the 2-year survival period with perpetual survival for trade secrets, and at least 5 years for other Confidential Information. A fixed 2-year window is inadequate for protecting sensitive IP."

EXAMPLE 3 — MISSING CLAUSE (correct):
  "original_text": "6. TERM AND TERMINATION"
  "recommendation": "Insert a Return of Materials clause prior to the Termination section. The clause should require the Receiving Party to return or certify destruction of all Confidential Information within 30 days of termination or written request by the Disclosing Party."

WRONG — Never use a heading as original_text for violations:
  "original_text": "2. NON-USE AND NON-DISCLOSURE"
  Problem: Headings cannot be replaced. For violations, extract the specific problematic SENTENCE within the clause body.

### CRITICAL CONSTRAINTS
1. **Surgical Precision:** For violations, extract the NARROWEST problematic text. Lawyers want MINIMAL redlines with MAXIMUM impact. Do NOT select entire clauses when only a phrase is problematic.
2. **Verbatim Anchors:** The original_text is used by software to locate text in Word. Copy-paste EXACTLY from the contract — same punctuation, same capitalization.
3. **Recommendation is GUIDANCE:** The recommendation field describes what should change in plain English. It is NOT the replacement text — a separate AI model generates the exact fix later. Write clear, actionable advice that a lawyer or an AI can follow.
4. **No Markdown:** Output raw JSON only.
5. **Professional Tone:** Use cold, precise legal language. No "I think" or "Maybe".
6. **Completeness:** Evaluate ALL playbook rules. Every executive summary observation must have a corresponding redline entry.
7. **Indian Law Context:** When reviewing contracts involving Indian parties, apply Indian legal standards (Indian Contract Act, DPDP Act 2023, Arbitration and Conciliation Act 1996, applicable state laws).
"""


@dataclass
class AIRedline:
    """A single redline from AI analysis."""
    risk_level: str
    rule_name: str
    original_text: str
    explanation: str
    recommendation: str  # Lawyer-readable guidance (not exact replacement text)
    redline_type: str = "violation"  # "violation" or "missing"


@dataclass
class AIAnalysisResult:
    """Complete AI analysis result."""
    executive_summary: List[str]
    redlines: List[AIRedline]
    tokens_used: int
    raw_response: str


class GeminiAnalyzer:
    """
    AI-First contract analyzer using Google Gemini.

    Sends full contract + playbook to Gemini and receives
    structured JSON with executive summary and redlines.
    """

    def __init__(self):
        """Initialize Gemini client."""
        self._client = None
        self._analysis_client = None
        self._enabled = bool(settings.GEMINI_API_KEY)

    @property
    def client(self):
        """Lazy initialization of Gemini Flash-Lite client (for subtasks)."""
        if self._client is None and self._enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._client = genai.GenerativeModel(settings.GEMINI_MODEL)
            except ImportError:
                logger.warning("google-generativeai not installed")
                self._enabled = False
        return self._client

    @property
    def analysis_client(self):
        """Lazy initialization of Gemini Pro client (for full contract analysis)."""
        if self._analysis_client is None and self._enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._analysis_client = genai.GenerativeModel(settings.GEMINI_ANALYSIS_MODEL)
            except ImportError:
                logger.warning("google-generativeai not installed")
                self._enabled = False
        return self._analysis_client

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def format_playbook_rules(self, playbook_rules: List[Dict]) -> str:
        """
        Format playbook rules into structured text for Gemini.

        Converts DB rules into:
        - Rule: Name | Risk: LEVEL | Position: Description
        """
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

            line = f"Rule #{i}: {name} | Risk: {risk}"
            if deal_breaker:
                line += " | DEAL-BREAKER (must flag if violated)"
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
        playbook_name: str = "Default"
    ) -> AIAnalysisResult:
        """
        Perform full AI analysis of a contract.

        Args:
            contract_text: The complete contract text
            playbook_rules: List of playbook rule dictionaries
            playbook_name: Name of the playbook for context

        Returns:
            AIAnalysisResult with executive summary and redlines
        """
        if not self._enabled:
            raise AIServiceUnavailable()

        # Format the playbook rules
        rules_text = self.format_playbook_rules(playbook_rules or [])

        # Sanitize user-supplied inputs before prompt interpolation
        safe_contract_text = _sanitize_for_prompt(contract_text, max_length=200000)
        safe_playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        # Build the structured prompt
        user_prompt = f"""
CONTEXT 1: THE RULES (PLAYBOOK: {safe_playbook_name})
{rules_text}

CONTEXT 2: THE EVIDENCE (CONTRACT)
{safe_contract_text}

TASK:
Compare EVIDENCE against RULES.
For every violation, extract the "original_text" verbatim from the contract.
Return your analysis as a single valid JSON object.
"""

        try:
            # Combine system prompt and user prompt
            full_prompt = f"{CONTRARED_SYSTEM_PROMPT}\n\n{user_prompt}"

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
            return self._parse_response(response_text)

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

                redlines.append(AIRedline(
                    risk_level=risk_level,
                    rule_name=item.get("rule_name", "Unknown Rule"),
                    original_text=item.get("original_text", ""),
                    explanation=item.get("explanation", ""),
                    recommendation=item.get("recommendation", "") or item.get("suggested_fix", ""),
                    redline_type=rtype,
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
    ) -> Dict[str, str]:
        """
        Generate a contract clause using AI.

        Returns dict with 'clause_text' and 'reasoning'.
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_clause_type = _sanitize_for_prompt(clause_type, max_length=200)
        safe_context = _sanitize_for_prompt(contract_context, max_length=3000) if contract_context else ""

        rules_context = ""
        if playbook_rules:
            matching = [r for r in playbook_rules if r.get("name", "").lower() == safe_clause_type.lower()]
            if not matching:
                # Fuzzy: include any rule whose name contains the clause type words
                words = safe_clause_type.lower().split()
                matching = [r for r in playbook_rules if any(w in r.get("name", "").lower() for w in words)]
            if matching:
                rules_context = "\n".join(
                    f"- {_sanitize_for_prompt(r['name'], 200)}: Position: {_sanitize_for_prompt(r.get('primary_position', ''), 500)}. "
                    f"Fallback: {_sanitize_for_prompt(r.get('fallback_position', ''), 500)}. "
                    f"Risk level: {_sanitize_for_prompt(r.get('risk_level', ''), 50)}."
                    for r in matching
                )

        prompt = f"""You are an expert Indian contract lawyer drafting a clause for a commercial agreement.

CLAUSE TYPE: {safe_clause_type}

{f"PLAYBOOK GUIDANCE:{chr(10)}{rules_context}" if rules_context else ""}

{f"SURROUNDING CONTRACT CONTEXT (for tone and style matching):{chr(10)}{safe_context}" if safe_context else ""}

TASK:
Draft a professional, legally sound clause of type "{safe_clause_type}" suitable for an Indian commercial contract.

Requirements:
1. The clause must be compliant with Indian law (Indian Contract Act, 1872; IT Act, 2000; DPDP Act, 2023 where relevant)
2. Use clear, professional legal language
3. Be balanced and commercially reasonable
4. If playbook guidance is provided, align with the preferred position
5. Include sub-clauses where appropriate for completeness

Return ONLY a valid JSON object with exactly these fields:
{{
  "clause_text": "The full drafted clause text, ready to insert into a contract",
  "reasoning": "Brief explanation of key choices made in drafting this clause (2-3 sentences)"
}}
"""
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
    ) -> Dict[str, Any]:
        """
        Generate exact replacement/insertion text for a specific risk.

        Uses Flash-Lite model (self.client) for fast, cheap per-issue fix generation.
        Two prompt variants: one for violations (replace text), one for missing clauses (insert text).
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_original = _sanitize_for_prompt(original_text, max_length=3000)
        safe_recommendation = _sanitize_for_prompt(recommendation, max_length=2000)
        safe_rule_name = _sanitize_for_prompt(rule_name, max_length=200)
        safe_context = _sanitize_for_prompt(surrounding_context, max_length=5000) if surrounding_context else ""

        # Build playbook guidance if available
        playbook_guidance = ""
        if playbook_rules:
            matching_rules = [r for r in playbook_rules if r.get("name", "").lower() in rule_name.lower() or rule_name.lower() in r.get("name", "").lower()]
            if matching_rules:
                rule = matching_rules[0]
                playbook_guidance = f"""
PLAYBOOK GUIDANCE:
- Preferred Position: {rule.get('primary_position', 'N/A')}
- Fallback Position: {rule.get('fallback_position', 'N/A')}
- Deal Breaker: {'Yes' if rule.get('is_deal_breaker') else 'No'}
Align the fix with the preferred position where possible.
"""

        if redline_type == "missing":
            prompt = f"""You are an expert Indian contract lawyer. Draft an EXACT clause to insert into a contract.

INSERTION POINT (insert AFTER this text):
"{safe_original}"

{f'SURROUNDING CONTEXT:{chr(10)}"{safe_context}"' if safe_context else ''}

RECOMMENDATION: {safe_recommendation}
PLAYBOOK RULE: {safe_rule_name}
{playbook_guidance}

Write the EXACT clause text to be inserted after the anchor above.
Requirements:
1. Include proper clause structure (heading, body, sub-clauses as needed)
2. Match the document's clause numbering style if visible in context
3. Compliant with Indian commercial law
4. Professional legal language matching the contract's tone
5. The clause must be complete and self-contained
6. Do NOT include the anchor text — only the NEW text to insert

Return ONLY a valid JSON object:
{{
  "fix_text": "exact clause text to insert",
  "reasoning": "2-3 sentences explaining key drafting choices"
}}
"""
        else:
            # violation — replace problematic text
            prompt = f"""You are an expert Indian contract lawyer. Produce EXACT replacement text for a problematic clause.

{f'SURROUNDING CONTEXT (the full clause for reference):{chr(10)}"{safe_context}"' if safe_context else ''}

PROBLEMATIC TEXT (to be replaced):
"{safe_original}"

RECOMMENDATION: {safe_recommendation}
PLAYBOOK RULE: {safe_rule_name}
{playbook_guidance}

Write the EXACT words that will REPLACE the problematic text above.
Requirements:
1. SAME SCOPE: if original is one sentence, replacement is one sentence. If original is a paragraph, replacement is a paragraph.
2. Must slot seamlessly into the surrounding context — grammatically and logically
3. No preamble, no instructions — just the replacement words
4. Compliant with Indian commercial law
5. Professional legal language matching the contract's tone
6. Be commercially reasonable and balanced

Return ONLY a valid JSON object:
{{
  "fix_text": "exact replacement words",
  "reasoning": "2-3 sentences explaining what was changed and why"
}}
"""

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

    async def research_clause(
        self,
        clause_text: str,
        clause_type: str = "",
    ) -> Dict[str, Any]:
        """
        Research relevant Indian case law for a given clause.

        Uses Gemini's knowledge to suggest relevant Supreme Court and
        High Court decisions. Returns cases with citations and a disclaimer.
        """
        if not self.is_enabled:
            raise AIServiceUnavailable()

        safe_clause_type = _sanitize_for_prompt(clause_type, max_length=200) if clause_type else "Contract Clause"
        safe_clause_text = _sanitize_for_prompt(clause_text, max_length=2000)

        prompt = f"""You are a senior Indian legal researcher. A lawyer has flagged the following clause in a contract review and wants to understand relevant Indian case law.

CLAUSE TYPE: {safe_clause_type}

CLAUSE TEXT:
{safe_clause_text}

TASK:
Find 3-5 relevant Indian Supreme Court (SC) or High Court (HC) decisions where similar clauses or legal principles were litigated or interpreted. Focus on:
1. Landmark decisions that are frequently cited
2. Recent decisions (last 10-15 years) where available
3. Decisions that directly address the enforceability or interpretation of such clauses under Indian law

For each case, provide:
- case_name: Full case name (e.g., "Nirma Industries Ltd. v. Securities and Exchange Board of India")
- citation: Standard Indian citation (e.g., "(2013) 8 SCC 20" or "AIR 2015 SC 1234")
- year: Year of judgment
- court: "Supreme Court" or name of High Court
- holding: 2-3 sentence summary of the relevant holding
- relevance: One sentence explaining how this case relates to the flagged clause

Return ONLY a valid JSON object:
{{
  "cases": [
    {{
      "case_name": "...",
      "citation": "...",
      "year": 2020,
      "court": "Supreme Court",
      "holding": "...",
      "relevance": "..."
    }}
  ],
  "legal_principle": "Brief summary of the applicable legal principle (1-2 sentences)"
}}
"""
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
                "disclaimer": "AI-suggested references \u2014 verify all citations independently before relying on them in legal proceedings.",
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
                "disclaimer": "AI-suggested references \u2014 verify all citations independently before relying on them in legal proceedings.",
            }
        except Exception as e:
            logger.error("Research clause error: %s: %s", type(e).__name__, e)
            raise _classify_gemini_error(e)


# Singleton instance
gemini_analyzer = GeminiAnalyzer()
