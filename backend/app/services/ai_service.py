"""
AI Service - Multi-provider integration for contract summaries.

Supports:
- Google Gemini (primary, recommended)
- Azure OpenAI (fallback)

The unified analysis pipeline owns finding explanations and fix generation.
This service remains the provider-agnostic summary adapter.
"""

import asyncio
import logging
from typing import Tuple

from app.core.config import settings
from app.core.vertex_client import get_generative_model, get_backend
from app.services.prompt_sanitizer import sanitize_for_prompt

logger = logging.getLogger(__name__)


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


class AIService:
    """
    Multi-provider contract-summary adapter.

    Finding analysis and redline generation are handled by the unified
    GeminiAnalyzer pipeline, avoiding two divergent prompt stacks.
    """
    
    def __init__(self) -> None:
        """Initialize AI client — Vertex AI (primary) or Azure OpenAI (fallback)."""
        self._gemini_client = None
        self._azure_client = None

        # Vertex AI is required for Gemini models
        self._use_gemini: bool = (
            bool(settings.VERTEX_PROJECT_ID)
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
            # Vertex AI GenerativeModel supports system_instruction natively.
            if system:
                from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]
                model_name = client._model_name if hasattr(client, '_model_name') else settings.GEMINI_MODEL
                model_with_system = GenerativeModel(
                    model_name,
                    system_instruction=system,
                )
                prompt = user
                gen_client = model_with_system
            else:
                prompt = user
                gen_client = client

            # Run in thread pool since Gemini SDK is sync, with 30s timeout
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
                timeout=30.0,
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
                timeout=30.0,
            )
            
            text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return text, tokens_used
            
        except Exception as e:
            logger.error("Azure OpenAI error: %s", e)
            return "[AI analysis unavailable — review this clause manually]", 0
    
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
            f"- {sanitize_for_prompt(r.rule_name, max_length=200)} ({r.risk_level.value}): {sanitize_for_prompt(r.match_text[:100], max_length=100)}..."
            for r in risks_found[:10]  # Top 10 risks for context
        ])
        
        # Truncate and sanitize contract for context
        contract_preview = sanitize_for_prompt(contract_text[:2000], max_length=2000)
        if len(contract_text) > 2000:
            contract_preview += "..."
        safe_playbook_name = sanitize_for_prompt(playbook_name, max_length=200)

        user_prompt = f"""Playbook Used: {safe_playbook_name}

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



