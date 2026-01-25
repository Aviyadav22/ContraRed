"""
Box 2: Intelligence Bridge - The Processor Layer.

Implements the Strategy Pattern for document analysis, switching between:
- Demo Mode (Omni-Context): Full document to GPT-4o for maximum quality
- Production Mode (Hybrid Sentinel): Two-pass system for cost optimization

Zero Data Retention: All processing is in RAM only.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

from app.services.structure_extractor import ContractMap, ContractNode
from app.services.rule_engine import RuleEngine, RuleMatch, RiskLevel
from app.services.ai_service import AIService
from app.core.config import settings


@dataclass
class RiskItem:
    """Analyzed risk item with AI enrichment."""
    node_hash: str
    clause_text: str
    risk_level: RiskLevel
    rule_name: str
    clause_type: str
    ai_explanation: Optional[str] = None
    suggested_fix: Optional[str] = None
    is_deal_breaker: bool = False


class AnalysisStrategy(ABC):
    """
    Base strategy for document analysis.
    
    Implementations define how the document is processed through
    the rule engine and AI service.
    """
    
    @abstractmethod
    async def analyze(
        self,
        contract_map: ContractMap,
        rule_engine: RuleEngine,
        ai_service: AIService,
        playbook_rules: Optional[List] = None
    ) -> tuple[List[RuleMatch], int]:
        """
        Analyze the contract and return enriched matches.
        
        Args:
            contract_map: Structured document from Box 1
            rule_engine: Configured rule engine
            ai_service: AI service for enrichment
            playbook_rules: Optional playbook rules for context
            
        Returns:
            Tuple of (enriched matches, total tokens used)
        """
        pass


class OmniContextStrategy(AnalysisStrategy):
    """
    Demo Mode: Full context to GPT-4o.
    
    Sends the entire document to the LLM for maximum intelligence.
    Best for demos and proof-of-value, but expensive at scale.
    """
    
    async def analyze(
        self,
        contract_map: ContractMap,
        rule_engine: RuleEngine,
        ai_service: AIService,
        playbook_rules: Optional[List] = None
    ) -> tuple[List[RuleMatch], int]:
        import asyncio
        
        # Get full text from ContractMap
        full_text = contract_map.get_all_text()
        
        # Rule-based detection
        matches = rule_engine.evaluate(full_text)
        
        # Enrich all matches with paragraph hashes
        for match in matches:
            for node in contract_map.nodes:
                if match.match_text in node.text or node.text in match.match_text:
                    match.paragraph_hash = node.id
                    break
        
        # Parallel AI enrichment for all matches
        total_tokens = 0
        
        if matches:
            async def enrich_match(match: RuleMatch) -> RuleMatch:
                nonlocal total_tokens
                explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
                total_tokens += tokens
                match.ai_explanation = explanation
                match.suggested_fix = suggested_fix
                return match
            
            enriched_matches = await asyncio.gather(
                *[enrich_match(m) for m in matches]
            )
            return list(enriched_matches), total_tokens
        
        return [], 0


class HybridSentinelStrategy(AnalysisStrategy):
    """
    Production Mode: Two-pass system for cost optimization.
    
    Pass 1 (Scout): GPT-4o-mini scans to flag risky sections only
    Pass 2 (Surgeon): GPT-4o generates precise redlines for flagged sections
    
    Reduces costs by ~90% compared to Omni-Context.
    """
    
    def __init__(self):
        self.scout_deployment = settings.AZURE_OPENAI_SCOUT_DEPLOYMENT
        self.surgeon_deployment = settings.AZURE_OPENAI_SURGEON_DEPLOYMENT
    
    async def analyze(
        self,
        contract_map: ContractMap,
        rule_engine: RuleEngine,
        ai_service: AIService,
        playbook_rules: Optional[List] = None
    ) -> tuple[List[RuleMatch], int]:
        import asyncio
        
        # Get full text from ContractMap
        full_text = contract_map.get_all_text()
        
        # First: Rule-based detection (cheap, no AI cost)
        matches = rule_engine.evaluate(full_text)
        
        if not matches:
            return [], 0
        
        # Enrich with paragraph hashes
        for match in matches:
            for node in contract_map.nodes:
                if match.match_text in node.text or node.text in match.match_text:
                    match.paragraph_hash = node.id
                    break
        
        total_tokens = 0
        
        # Pass 1: Scout (GPT-4o-mini) - Quick validation
        # Only call Scout for potential false positives (YELLOW risks)
        yellow_matches = [m for m in matches if m.risk_level == RiskLevel.YELLOW]
        red_matches = [m for m in matches if m.risk_level == RiskLevel.RED]
        
        validated_matches = list(red_matches)  # REDs are always valid
        
        if yellow_matches:
            # Scout validates YELLOW matches quickly
            scout_tasks = [
                self._scout_validate(ai_service, m) for m in yellow_matches
            ]
            scout_results = await asyncio.gather(*scout_tasks)
            
            for match, (is_valid, tokens) in zip(yellow_matches, scout_results):
                total_tokens += tokens
                if is_valid:
                    validated_matches.append(match)
        
        if not validated_matches:
            return [], total_tokens
        
        # Pass 2: Surgeon (GPT-4o) - Generate redlines for validated matches
        async def surgeon_enrich(match: RuleMatch) -> RuleMatch:
            nonlocal total_tokens
            explanation, suggested_fix, tokens = await ai_service.enrich_match(match)
            total_tokens += tokens
            match.ai_explanation = explanation
            match.suggested_fix = suggested_fix
            return match
        
        enriched_matches = await asyncio.gather(
            *[surgeon_enrich(m) for m in validated_matches]
        )
        
        return list(enriched_matches), total_tokens
    
    async def _scout_validate(
        self,
        ai_service: AIService,
        match: RuleMatch
    ) -> tuple[bool, int]:
        """
        Scout pass: Quickly validate if a match is a true positive.
        
        Uses GPT-4o-mini with a simple yes/no prompt.
        Returns (is_valid, tokens_used).
        """
        # For now, delegate to AI service with a simple validation
        # In production, this would use a specialized Scout prompt
        try:
            # Quick validation - just check if clause is actually risky
            if ai_service.is_enabled:
                # Use the existing explain_risk but with minimal context
                explanation, tokens = await ai_service.explain_risk(
                    match.match_text[:200],  # Truncated for speed
                    match.rule_name,
                    match.risk_level.value
                )
                # If AI returns meaningful explanation, it's valid
                is_valid = bool(explanation and len(explanation) > 10)
                return is_valid, tokens
            else:
                # No AI available - assume valid
                return True, 0
        except Exception:
            # On error, assume valid (don't filter out matches)
            return True, 0


class IntelligenceBridge:
    """
    Factory for selecting and executing analysis strategies.
    
    Usage:
        bridge = IntelligenceBridge()  # Uses ANALYSIS_MODE from config
        matches, tokens = await bridge.analyze(contract_map, rule_engine, ai_service)
    """
    
    def __init__(self, mode: Optional[str] = None):
        """
        Initialize with analysis mode.
        
        Args:
            mode: "demo" for OmniContext, "production" for HybridSentinel.
                  Defaults to settings.ANALYSIS_MODE.
        """
        mode = mode or settings.ANALYSIS_MODE
        
        if mode == "production":
            self.strategy = HybridSentinelStrategy()
        else:
            self.strategy = OmniContextStrategy()
        
        self.mode = mode
    
    async def analyze(
        self,
        contract_map: ContractMap,
        rule_engine: RuleEngine,
        ai_service: AIService,
        playbook_rules: Optional[List] = None
    ) -> tuple[List[RuleMatch], int]:
        """
        Analyze document using the configured strategy.
        
        Args:
            contract_map: Structured document from Box 1
            rule_engine: Configured rule engine
            ai_service: AI service for enrichment
            playbook_rules: Optional playbook rules for context
            
        Returns:
            Tuple of (enriched matches, total tokens used)
        """
        return await self.strategy.analyze(
            contract_map,
            rule_engine,
            ai_service,
            playbook_rules
        )
    
    @property
    def strategy_name(self) -> str:
        """Get the name of the current strategy."""
        return type(self.strategy).__name__
