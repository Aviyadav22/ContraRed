"""
ContraRed Services Package

Uses lazy imports to avoid loading heavy modules (AI clients, ML libraries)
at import time. Access any service via attribute access on this module:

    from app.services import AIService
    from app.services import RuleEngine
"""

import importlib
from typing import Any

# Maps public names to their (module_path, attribute_name) for lazy loading.
_LAZY_IMPORTS = {
    # Core services
    "RuleEngine": ("app.services.rule_engine", "RuleEngine"),
    "RuleMatch": ("app.services.rule_engine", "RuleMatch"),
    "RiskLevel": ("app.services.rule_engine", "RiskLevel"),
    "AIService": ("app.services.ai_service", "AIService"),
    "CacheService": ("app.services.cache_service", "CacheService"),
    "get_cache": ("app.services.cache_service", "get_cache"),
    "StructureExtractor": ("app.services.structure_extractor", "StructureExtractor"),
    "ContractMap": ("app.services.structure_extractor", "ContractMap"),
    "ContractNode": ("app.services.structure_extractor", "ContractNode"),
    # Analysis pipeline (unified AI-first)
    "analysis_pipeline": ("app.services.analysis_pipeline", "analysis_pipeline"),
    "AnalysisPipeline": ("app.services.analysis_pipeline", "AnalysisPipeline"),
    "PipelineResult": ("app.services.analysis_pipeline", "PipelineResult"),
    "RedlineImplementer": ("app.services.redline_implementer", "RedlineImplementer"),
    "RedlineResult": ("app.services.redline_implementer", "RedlineResult"),
    "TextAnchor": ("app.services.redline_implementer", "TextAnchor"),
    "GeminiAnalyzer": ("app.services.gemini_analyzer", "GeminiAnalyzer"),
    "gemini_analyzer": ("app.services.gemini_analyzer", "gemini_analyzer"),
    "AIAnalysisResult": ("app.services.gemini_analyzer", "AIAnalysisResult"),
    "AIRedline": ("app.services.gemini_analyzer", "AIRedline"),
    # Phase 4 — AI Output Quality
    "JurisdictionDetector": ("app.services.jurisdiction_detector", "JurisdictionDetector"),
    "jurisdiction_detector": ("app.services.jurisdiction_detector", "jurisdiction_detector"),
    "JurisdictionProfile": ("app.services.jurisdiction_detector", "JurisdictionProfile"),
    "JurisdictionDetectionResult": ("app.services.jurisdiction_detector", "JurisdictionDetectionResult"),
    "JURISDICTION_PROFILES": ("app.services.jurisdiction_detector", "JURISDICTION_PROFILES"),
    "DefinedTermsResolver": ("app.services.defined_terms_resolver", "DefinedTermsResolver"),
    "defined_terms_resolver": ("app.services.defined_terms_resolver", "defined_terms_resolver"),
    "DefinedTerm": ("app.services.defined_terms_resolver", "DefinedTerm"),
    "DefinedTermsResult": ("app.services.defined_terms_resolver", "DefinedTermsResult"),
    "ClauseClassifier": ("app.services.clause_classifier", "ClauseClassifier"),
    "clause_classifier": ("app.services.clause_classifier", "clause_classifier"),
    "ClauseType": ("app.services.clause_classifier", "ClauseType"),
    "ClauseGroup": ("app.services.clause_classifier", "ClauseGroup"),
    "ClassifiedClause": ("app.services.clause_classifier", "ClassifiedClause"),
    "ClassificationResult": ("app.services.clause_classifier", "ClassificationResult"),
    "SYSTEM_PROMPT_V2": ("app.services.prompt_templates", "SYSTEM_PROMPT_V2"),
    "LEGACY_PROMPT": ("app.services.prompt_templates", "LEGACY_PROMPT"),
    "render_system_prompt": ("app.services.prompt_templates", "render_system_prompt"),
    "render_user_prompt": ("app.services.prompt_templates", "render_user_prompt"),
    "render_fix_prompt": ("app.services.prompt_templates", "render_fix_prompt"),
    "render_clause_generation_prompt": ("app.services.prompt_templates", "render_clause_generation_prompt"),
    "render_research_prompt": ("app.services.prompt_templates", "render_research_prompt"),
    # Phase 5 — Contract Coverage
    "ScopeAnalyzer": ("app.services.scope_analyzer", "ScopeAnalyzer"),
    "scope_analyzer": ("app.services.scope_analyzer", "scope_analyzer"),
    "ScopeResult": ("app.services.scope_analyzer", "ScopeResult"),
    "ScopeAnalysisResult": ("app.services.scope_analyzer", "ScopeAnalysisResult"),
    "Breadth": ("app.services.scope_analyzer", "Breadth"),
    "Mutuality": ("app.services.scope_analyzer", "Mutuality"),
    "FinancialExposure": ("app.services.scope_analyzer", "FinancialExposure"),
    "Duration": ("app.services.scope_analyzer", "Duration"),
    "TriggerType": ("app.services.scope_analyzer", "TriggerType"),
    "ALL_RULES": ("app.services.rules_library", "ALL_RULES"),
    "get_rules_by_category": ("app.services.rules_library", "get_rules_by_category"),
    "get_rule_by_id": ("app.services.rules_library", "get_rule_by_id"),
    "get_all_categories": ("app.services.rules_library", "get_all_categories"),
    "get_category_summary": ("app.services.rules_library", "get_category_summary"),
}

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        # Cache in module globals so subsequent accesses are fast
        globals()[name] = value
        return value
    raise AttributeError(f"module 'app.services' has no attribute {name!r}")
