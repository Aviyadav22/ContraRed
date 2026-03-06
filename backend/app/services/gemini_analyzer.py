"""
Gemini Analyzer - AI-First Contract Analysis Service.

This service uses Google Gemini to perform holistic contract analysis
against a client playbook, returning structured JSON with executive
summary and redline suggestions.
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# The comprehensive ContraRed AI system prompt
CONTRARED_SYSTEM_PROMPT = """
You are ContraRed AI, a Senior Contract Attorney and Risk Compliance Officer. 
Your job is to audit legal agreements against a strict Client Playbook.

### INPUT DATA
1. **CONTRACT TEXT:** The raw text of a legal agreement.
2. **CLIENT PLAYBOOK:** A set of rules defining acceptable and unacceptable terms.

### OBJECTIVES
Perform a deep, holistic review of the document. You must execute two distinct analyses:

#### 1. HOLISTIC STRUCTURAL ANALYSIS (The "Executive Summary")
Before looking at specific clauses, analyze the document's skeleton for fundamental contradictions.
- **Title vs. Content:** Does the Title claim "Mutual" or "Standard", but the Preamble/Definitions hard-code one-sided roles (e.g., "Company is Disclosing Party")?
- **Jurisdiction Check:** Identify the Governing Law. If it conflicts with the Client's likely jurisdiction (based on context), flag it.
- **Tone & Fairness:** Is the agreement commercially reasonable, or is it aggressively one-sided?

#### 2. SURGICAL REDLINING (The "Fixes")
Scan every clause against the Playbook.
- **Strict Adherence:** If a clause violates a Playbook rule, it is a RISK.
- **Drift Prevention:** You MUST extract the *exact* substring from the text as an anchor.
- **Silence is Approval:** If a clause is safe or standard, ignore it. Do not hallucinate risks.

### OUTPUT FORMAT
You must return a SINGLE valid JSON object. Do not include markdown formatting (```json).
{
  "executive_summary": [
    "A concise, high-level bullet point about the overall risk profile.",
    "Specific structural observation (e.g., 'Drafted as Mutual but functionally Unilateral').",
    "Governing Law observation."
  ],
  "redlines": [
    {
      "risk_level": "RED" | "YELLOW",
      "rule_name": "Name of the Playbook Rule violated",
      "original_text": "EXACT COPY of 10-15 words from the source text to use as an anchor. MUST BE BYTE-PERFECT.",
      "explanation": "Brief, professional explanation of the risk.",
      "suggested_fix": "The fully redrafted clause complying with the Playbook."
    }
  ]
}

### CRITICAL CONSTRAINTS
1. **Verbatim Anchors:** The `original_text` field is used by a software search engine. If you change even one comma or capitalization, the system fails. Copy-paste exactly.
2. **No Markdown:** Output raw JSON only.
3. **Professional Tone:** Use cold, precise legal language. No "I think" or "Maybe".
"""


@dataclass
class AIRedline:
    """A single redline from AI analysis."""
    risk_level: str
    rule_name: str
    original_text: str
    explanation: str
    suggested_fix: str


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
        self._enabled = bool(settings.GEMINI_API_KEY)
    
    @property
    def client(self):
        """Lazy initialization of Gemini client."""
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
        
        lines = []
        for rule in playbook_rules:
            name = rule.get('name', rule.get('rule_name', 'Unknown'))
            risk = rule.get('risk_level', 'YELLOW')
            position = rule.get('primary_position', rule.get('description', 'Standard terms expected'))
            fallback = rule.get('fallback_position', '')
            
            line = f"- Rule: {name} | Risk: {risk} | Position: {position}"
            if fallback:
                line += f" | Fallback: {fallback}"
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
            return self._fallback_result()
        
        # Format the playbook rules
        rules_text = self.format_playbook_rules(playbook_rules or [])
        
        # Build the structured prompt
        user_prompt = f"""
CONTEXT 1: THE RULES (PLAYBOOK: {playbook_name})
{rules_text}

CONTEXT 2: THE EVIDENCE (CONTRACT)
{contract_text}

TASK:
Compare EVIDENCE against RULES.
For every violation, extract the "original_text" verbatim from the contract.
Return your analysis as a single valid JSON object.
"""
        
        try:
            import asyncio
            
            # Combine system prompt and user prompt
            full_prompt = f"{CONTRARED_SYSTEM_PROMPT}\n\n{user_prompt}"
            
            # Run in thread pool since Gemini SDK is sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.generate_content(
                    full_prompt,
                    generation_config={
                        "max_output_tokens": 16384,  # Large output for comprehensive analysis
                        "temperature": 0.2,  # Low temperature for consistent, precise output
                    }
                )
            )
            
            # Extract text from response
            response_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    response_text = candidate.content.parts[0].text
            
            if not response_text:
                logger.warning("Gemini returned empty response")
                return self._fallback_result()
            
            # Parse JSON from response
            return self._parse_response(response_text)
            
        except Exception as e:
            logger.error("Gemini analysis error: %s: %s", type(e).__name__, e)
            return self._fallback_result()
    
    def _parse_response(self, response_text: str) -> AIAnalysisResult:
        """Parse Gemini's JSON response into structured result."""
        try:
            # Clean up response - remove any markdown formatting
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Extract executive summary
            executive_summary = data.get("executive_summary", [])
            if isinstance(executive_summary, str):
                executive_summary = [executive_summary]
            
            # Extract redlines
            redlines = []
            for item in data.get("redlines", []):
                redlines.append(AIRedline(
                    risk_level=item.get("risk_level", "YELLOW"),
                    rule_name=item.get("rule_name", "Unknown Rule"),
                    original_text=item.get("original_text", ""),
                    explanation=item.get("explanation", ""),
                    suggested_fix=item.get("suggested_fix", "")
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


# Singleton instance
gemini_analyzer = GeminiAnalyzer()
