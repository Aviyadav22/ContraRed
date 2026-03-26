"""
AI Service - Multi-provider AI integration for clause analysis.

Supports:
- Google Gemini (primary, recommended)
- Azure OpenAI (fallback)

Provides AI-powered explanations and suggested fixes for risky clauses.
Uses strict prompts to limit response length and costs.
"""

import asyncio
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from app.core.config import settings
from app.core.vertex_client import get_generative_model, is_available, get_backend

logger = logging.getLogger(__name__)


@dataclass
class ClauseAnalysis:
    """AI-generated analysis for a clause."""
    explanation: str  # Max 20 words
    suggested_fix: Optional[str]
    tokens_used: int


# System prompts with strict length limits
EXPLAIN_SYSTEM_PROMPT = """You are a strict legal contract auditor.
Your job is to explain contract risks in ONE sentence.

Rules:
- Maximum 20 words
- Be direct and specific
- No pleasantries or filler
- Focus on the business impact

Example good response: "Unlimited liability exposes your company to uncapped financial damages from any contract breach."
Example bad response: "Well, this clause is concerning because it mentions unlimited liability which could potentially be problematic for your organization in various scenarios."
"""

SUGGEST_FIX_SYSTEM_PROMPT = """You are a contract negotiation expert.
Generate replacement clause text that protects the reviewing party.

Rules:
- Output ONLY the replacement text, no explanation
- Keep same legal style as original
- Be specific with numbers (caps, timeframes)
- Maximum 50 words

The user will provide the original clause and preferred position.
"""

# NEW: Contract Summary Prompt
CONTRACT_SUMMARY_PROMPT = """You are a senior contract analyst providing an executive summary.
Analyze the contract and identified risks to give a concise overall assessment.

Your response must include:
1. **Risk Level**: (Critical/High/Medium/Low) - One word overall assessment
2. **Key Concerns**: Top 3 issues in bullet points (max 10 words each)
3. **Recommendation**: One sentence action recommendation

Format your response exactly as:
RISK LEVEL: [Critical/High/Medium/Low]

KEY CONCERNS:
• [Concern 1]
• [Concern 2]  
• [Concern 3]

RECOMMENDATION: [Your recommendation]

Keep the entire response under 100 words.
"""

# NEW: Playbook-Aware Analysis Prompt
PLAYBOOK_AWARE_PROMPT = """You are a contract analyst working for the reviewing party.
You have a negotiation playbook with specific positions to protect your client.

PLAYBOOK CONTEXT:
{playbook_context}

Analyze the clause below. Your client's primary position is: {primary_position}
If that fails, the fallback position is: {fallback_position}

Original Clause:
"{clause_text}"

Generate a revised clause that:
1. Aligns with your client's primary position
2. Maintains legal enforceability
3. Uses professional contract language
4. Is no more than 60 words

Output ONLY the replacement clause text:
"""


class AIService:
    """
    Multi-provider AI integration for contract clause analysis.
    
    Supports Google Gemini (primary) and Azure OpenAI (fallback).
    
    Usage:
        ai = AIService()
        explanation = await ai.explain_risk("unlimited liability clause text", "Unlimited Liability")
        suggested_fix = await ai.suggest_fix("clause text", "Liability capped at 12 months fees")
    """
    
    def __init__(self) -> None:
        """Initialize AI client — prefers Vertex AI, falls back to consumer Gemini or Azure."""
        self._gemini_client = None
        self._azure_client = None

        # Determine which provider to use (Vertex AI or consumer key both satisfy "gemini")
        self._use_gemini: bool = (
            bool(settings.VERTEX_PROJECT_ID) or bool(settings.GEMINI_API_KEY)
        ) and settings.AI_PROVIDER == "gemini"
        self._use_azure: bool = bool(settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)
        self._enabled: bool = self._use_gemini or self._use_azure

    @property
    def gemini_client(self):
        """Lazy initialization of Gemini/Vertex client."""
        if self._gemini_client is None and self._use_gemini:
            try:
                self._gemini_client = get_generative_model(settings.GEMINI_MODEL)
                logger.info("AIService Gemini client ready (backend=%s)", get_backend())
            except RuntimeError:
                logger.warning("No AI backend available for AIService Gemini client")
                self._use_gemini = False
        return self._gemini_client
    
    @property
    def azure_client(self):
        """Lazy initialization of Azure OpenAI client."""
        if self._azure_client is None and self._use_azure:
            from openai import AsyncAzureOpenAI
            self._azure_client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-01",
            )
        return self._azure_client
    
    @property
    def is_enabled(self) -> bool:
        """Check if AI service is configured."""
        return self._enabled
    
    @property
    def provider(self) -> str:
        """Get the active AI provider."""
        if self._use_gemini:
            return "gemini"
        elif self._use_azure:
            return "azure"
        return "none"
    
    async def explain_risk(
        self,
        clause_text: str,
        rule_name: str,
        risk_level: str = "RED"
    ) -> Tuple[str, int]:
        """
        DEPRECATED: Legacy method. The unified analysis pipeline (Stage 3)
        now handles risk explanation. Retained for /analyze-file endpoint.

        Generate a concise explanation of why a clause is risky.
        
        Args:
            clause_text: The problematic clause text
            rule_name: Name of the matched rule (e.g., "Unlimited Liability")
            risk_level: RED, YELLOW, or GREEN
            
        Returns:
            Tuple of (explanation string, tokens used)
        """
        if not self._enabled:
            return self._fallback_explanation(rule_name, risk_level), 0
        
        user_prompt = f"Risk type: {rule_name} ({risk_level})\nClause: \"{clause_text}\"\n\nExplain the risk in ONE sentence (max 20 words):"
        
        if self._use_gemini:
            # Note: gemini-3-pro-preview is a 'thinking' model that uses tokens for reasoning
            # It needs higher limits to produce actual output
            return await self._gemini_generate(
                system=EXPLAIN_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=2048
            )
        else:
            return await self._azure_generate(
                system=EXPLAIN_SYSTEM_PROMPT,
                user=user_prompt,
                model=settings.AZURE_OPENAI_DEPLOYMENT_MINI,
                max_tokens=150
            )
    
    async def suggest_fix(
        self,
        clause_text: str,
        primary_position: str,
        fallback_position: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        DEPRECATED: Legacy method. The unified analysis pipeline (Stage 6)
        now handles fix generation. Retained for /analyze-file endpoint.

        Generate suggested replacement text for a risky clause.
        
        Args:
            clause_text: Original clause text
            primary_position: Preferred negotiating position from playbook
            fallback_position: Alternative position if primary is rejected
            
        Returns:
            Tuple of (suggested fix string, tokens used)
        """
        if not self._enabled:
            return self._fallback_fix(primary_position), 0
        
        position_text = primary_position
        if fallback_position:
            position_text += f" (Alternative: {fallback_position})"
        
        user_prompt = f"Original clause:\n\"{clause_text}\"\n\nPreferred position: {position_text}\n\nGenerate replacement text:"
        
        if self._use_gemini:
            # Note: gemini-3-pro-preview needs ~4000+ tokens for legal clause rewrites
            # due to internal reasoning before output
            result, tokens = await self._gemini_generate(
                system=SUGGEST_FIX_SYSTEM_PROMPT,
                user=user_prompt,
                max_tokens=4096
            )
        else:
            result, tokens = await self._azure_generate(
                system=SUGGEST_FIX_SYSTEM_PROMPT,
                user=user_prompt,
                model=settings.AZURE_OPENAI_DEPLOYMENT_GPT4,
                max_tokens=500
            )
        
        # Clean up any quotes the model might add
        result = result.strip('"\'')
        return result, tokens
    
    async def _gemini_generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 100
    ) -> Tuple[str, int]:
        """Generate response using Google Gemini."""
        try:
            # Bail early if no client available
            client = self.gemini_client
            if client is None:
                return "", 0

            # Use system_instruction for clear separation of system/user prompts.
            # Build a model instance with the system instruction baked in.
            from app.core.vertex_client import get_backend
            backend = get_backend()

            if system and backend == "consumer":
                # Consumer SDK supports system_instruction on GenerativeModel
                import google.generativeai as genai
                model_with_system = genai.GenerativeModel(
                    client.model_name if hasattr(client, 'model_name') else settings.GEMINI_MODEL,
                    system_instruction=system,
                )
                prompt = user
                gen_client = model_with_system
            else:
                # Vertex AI or no system prompt — use clear separator
                if system:
                    prompt = f"===SYSTEM INSTRUCTIONS START===\n{system}\n===SYSTEM INSTRUCTIONS END===\n\n===CONTRACT TEXT FOR ANALYSIS===\n{user}\n===END CONTRACT TEXT==="
                else:
                    prompt = user
                gen_client = client

            # Run in thread pool since Gemini SDK is sync, with 60s timeout
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: gen_client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": max_tokens,
                            "temperature": 0.3,
                        }
                    )
                ),
                timeout=60.0,
            )
            
            # Try to get text from response, handle various cases
            try:
                # Check candidates first
                if response.candidates:
                    candidate = response.candidates[0]
                    # Log finish reason for debugging
                    if hasattr(candidate, 'finish_reason'):
                        logger.debug("Gemini finish_reason: %s", candidate.finish_reason)
                    
                    # Try to get text from content.parts
                    if candidate.content and candidate.content.parts:
                        text = candidate.content.parts[0].text
                        if text:
                            estimated_tokens = len(prompt.split()) + len(text.split())
                            return text.strip(), estimated_tokens
                
                # Fallback to response.text (may raise if blocked)
                if hasattr(response, 'text') and response.text:
                    estimated_tokens = len(prompt.split()) + len(response.text.split())
                    return response.text.strip(), estimated_tokens
                
                # Log if we got here with no content
                if hasattr(response, 'prompt_feedback'):
                    logger.warning("Gemini prompt_feedback: %s", response.prompt_feedback)

                logger.warning("Gemini returned empty response (no text in candidates)")
                return "[AI analysis unavailable — review this clause manually]", 0

            except ValueError as ve:
                # This happens when response.text can't be accessed due to safety blocks
                logger.warning("Gemini response access error: %s", ve)
                if hasattr(response, 'prompt_feedback'):
                    logger.warning("Prompt feedback: %s", response.prompt_feedback)
                return "[AI analysis unavailable — review this clause manually]", 0

        except Exception as e:
            logger.error("Gemini error: %s: %s", type(e).__name__, e)
            return "[AI analysis unavailable — review this clause manually]", 0
    
    async def _azure_generate(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 100
    ) -> Tuple[str, int]:
        """Generate response using Azure OpenAI."""
        try:
            response = await asyncio.wait_for(
                self.azure_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3,
                ),
                timeout=60.0,
            )
            
            text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return text, tokens_used
            
        except Exception as e:
            logger.error("Azure OpenAI error: %s", e)
            return "[AI analysis unavailable — review this clause manually]", 0
    
    async def enrich_match(self, match) -> Tuple[str, str, int]:
        """
        DEPRECATED: Legacy method. The unified analysis pipeline (Stages 3+6)
        now handles enrichment. Retained for /analyze-file endpoint.

        Enrich a RuleMatch with AI explanation and suggested fix.

        This is the method to use with asyncio.gather for parallel processing.
        
        Args:
            match: RuleMatch object from RuleEngine
            
        Returns:
            Tuple of (explanation, suggested_fix, total_tokens)
        """
        explain_task = self.explain_risk(
            match.match_text,
            match.rule_name,
            match.risk_level.value
        )
        
        # Only suggest fix for RED and YELLOW risks
        if match.risk_level.value in ("RED", "YELLOW"):
            fix_task = self.suggest_fix(
                match.match_text,
                match.primary_position,
                match.fallback_position
            )
            (explanation, explain_tokens), (suggested_fix, fix_tokens) = await asyncio.gather(
                explain_task, fix_task
            )
            return explanation, suggested_fix, explain_tokens + fix_tokens
        else:
            explanation, explain_tokens = await explain_task
            return explanation, None, explain_tokens
    
    def _fallback_explanation(self, rule_name: str, risk_level: str) -> str:
        """Generate fallback explanation when AI is unavailable."""
        fallbacks = {
            "Unlimited Liability": "This clause exposes you to uncapped financial damages.",
            "Unilateral Termination": "Other party can terminate without notice or cause.",
            "Broad Indemnification": "You may be liable for third-party claims beyond your control.",
            "Broad IP Assignment": "You may lose ownership of your pre-existing intellectual property.",
            "Auto-Renewal": "Contract renews automatically without explicit consent.",
            "Assignment Restriction": "You cannot transfer this contract without approval.",
            "Non-Compete": "Restricts your ability to compete in the market.",
            "Exclusive Dealing": "Limits your ability to work with other parties.",
            "Perpetual Confidentiality": "Confidentiality obligations never expire.",
            "Governing Law": "Standard governing law provision.",
            "Notice Provision": "Standard notice requirements.",
        }
        return fallbacks.get(rule_name, f"{rule_name} detected - review recommended.")
    
    def _fallback_fix(self, primary_position: str) -> str:
        """Generate fallback fix when AI is unavailable."""
        return primary_position  # Use the playbook position as-is
    
    async def summarize_contract(
        self,
        contract_text: str,
        risks_found: list,
        playbook_name: str = "Default"
    ) -> Tuple[str, int]:
        """
        Generate an executive summary of the entire contract.
        
        Args:
            contract_text: Full contract text (or first 3000 chars for context)
            risks_found: List of RuleMatch objects found in the contract
            playbook_name: Name of the playbook used for analysis
            
        Returns:
            Tuple of (summary string, tokens used)
        """
        if not self._enabled:
            return self._fallback_summary(risks_found), 0
        
        # Build risk summary for context
        red_count = sum(1 for r in risks_found if r.risk_level.value == "RED")
        yellow_count = sum(1 for r in risks_found if r.risk_level.value == "YELLOW")
        green_count = sum(1 for r in risks_found if r.risk_level.value == "GREEN")
        
        risk_list = "\n".join([
            f"- {r.rule_name} ({r.risk_level.value}): {r.match_text[:100]}..."
            for r in risks_found[:10]  # Top 10 risks for context
        ])
        
        # Truncate contract for context (first 2000 chars)
        contract_preview = contract_text[:2000] + ("..." if len(contract_text) > 2000 else "")
        
        user_prompt = f"""Playbook Used: {playbook_name}

Risk Summary: {red_count} Critical, {yellow_count} Warning, {green_count} Safe

Detected Issues:
{risk_list}

Contract Preview:
{contract_preview}

Provide an executive summary following the specified format:"""
        
        if self._use_gemini:
            # Gemini 3 Pro needs high token limits for reasoning
            return await self._gemini_generate(
                system=CONTRACT_SUMMARY_PROMPT,
                user=user_prompt,
                max_tokens=8192
            )
        else:
            return await self._azure_generate(
                system=CONTRACT_SUMMARY_PROMPT,
                user=user_prompt,
                model=settings.AZURE_OPENAI_DEPLOYMENT_GPT4,
                max_tokens=200
            )
    
    async def suggest_fix_with_playbook(
        self,
        clause_text: str,
        primary_position: str,
        fallback_position: str,
        playbook_context: str
    ) -> Tuple[str, int]:
        """
        Generate a fix using full playbook context.
        
        Args:
            clause_text: The original problematic clause
            primary_position: Client's preferred position from playbook
            fallback_position: Alternative if primary is rejected
            playbook_context: Full context of relevant playbook rules
            
        Returns:
            Tuple of (suggested fix, tokens used)
        """
        if not self._enabled:
            return self._fallback_fix(primary_position), 0
        
        user_prompt = PLAYBOOK_AWARE_PROMPT.format(
            playbook_context=playbook_context,
            primary_position=primary_position,
            fallback_position=fallback_position or "None specified",
            clause_text=clause_text
        )
        
        if self._use_gemini:
            # Gemini 3 Pro needs high token limits for reasoning
            result, tokens = await self._gemini_generate(
                system="",  # Context is in user prompt
                user=user_prompt,
                max_tokens=4096
            )
        else:
            result, tokens = await self._azure_generate(
                system="",
                user=user_prompt,
                model=settings.AZURE_OPENAI_DEPLOYMENT_GPT4,
                max_tokens=150
            )
        
        return result.strip('"\''), tokens
    
    def _fallback_summary(self, risks_found: list) -> str:
        """Generate fallback summary when AI is unavailable."""
        red_count = sum(1 for r in risks_found if r.risk_level.value == "RED")
        yellow_count = sum(1 for r in risks_found if r.risk_level.value == "YELLOW")
        
        if red_count > 0:
            level = "Critical"
        elif yellow_count > 0:
            level = "High"
        else:
            level = "Low"
        
        return f"""RISK LEVEL: {level}

KEY CONCERNS:
• {red_count} critical issues requiring immediate attention
• {yellow_count} warnings to review before signing
• Review liability, IP, and termination clauses

RECOMMENDATION: Consult legal team before signing this contract."""



