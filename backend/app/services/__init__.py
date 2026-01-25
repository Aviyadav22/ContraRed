"""
ContraRed Services Package
"""

from app.services.rule_engine import RuleEngine, RuleMatch, RiskLevel
from app.services.ai_service import AIService
from app.services.cache_service import CacheService, get_cache
from app.services.structure_extractor import StructureExtractor, ContractMap, ContractNode
from app.services.intelligence_bridge import IntelligenceBridge, OmniContextStrategy, HybridSentinelStrategy
from app.services.redline_implementer import RedlineImplementer, RedlineResult, TextAnchor
from app.services.gemini_analyzer import GeminiAnalyzer, gemini_analyzer, AIAnalysisResult, AIRedline

__all__ = [
    "RuleEngine", "RuleMatch", "RiskLevel", 
    "AIService", 
    "CacheService", "get_cache",
    "StructureExtractor", "ContractMap", "ContractNode",
    "IntelligenceBridge", "OmniContextStrategy", "HybridSentinelStrategy",
    "RedlineImplementer", "RedlineResult", "TextAnchor",
    "GeminiAnalyzer", "gemini_analyzer", "AIAnalysisResult", "AIRedline",
]
