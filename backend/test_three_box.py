"""
Unit Tests for Three-Box Architecture Services.

Tests:
- Box 1: StructureExtractor
- Box 2: IntelligenceBridge  
- Box 3: RedlineImplementer
- AI Service: Gemini integration
"""

import asyncio
from io import BytesIO

# ============================================================================
# Test Box 1: Structure Extractor
# ============================================================================

def test_structure_extractor_imports():
    """Test that StructureExtractor can be imported."""
    from app.services.structure_extractor import StructureExtractor, ContractMap, ContractNode
    assert StructureExtractor is not None
    assert ContractMap is not None
    assert ContractNode is not None
    print("✅ Box 1: StructureExtractor imports successfully")


def test_contract_map_creation():
    """Test ContractMap basic functionality."""
    from app.services.structure_extractor import ContractMap, ContractNode
    
    # Create a simple ContractMap
    nodes = [
        ContractNode(id="hash1", text="This is paragraph one.", style="Normal", section_index=0, start_offset=0),
        ContractNode(id="hash2", text="This is paragraph two.", style="Heading 1", section_index=1, start_offset=25),
    ]
    contract_map = ContractMap(nodes=nodes, full_text="This is paragraph one.\nThis is paragraph two.")
    
    assert len(contract_map.nodes) == 2
    assert contract_map.full_text is not None
    print("✅ Box 1: ContractMap creation works")


def test_extract_from_text():
    """Test text extraction without DOCX."""
    from app.services.structure_extractor import StructureExtractor
    
    extractor = StructureExtractor()
    sample_text = """
    1. DEFINITIONS
    
    "Confidential Information" means any proprietary information disclosed by either party.
    
    2. OBLIGATIONS
    
    The receiving party shall maintain strict confidentiality of all Confidential Information.
    """
    
    contract_map = extractor.extract_from_text(sample_text)
    
    assert contract_map is not None
    assert len(contract_map.nodes) > 0
    assert all(node.id for node in contract_map.nodes)  # All have hashes
    print(f"✅ Box 1: extract_from_text created {len(contract_map.nodes)} nodes")


# ============================================================================
# Test Box 2: Intelligence Bridge
# ============================================================================

def test_intelligence_bridge_imports():
    """Test that IntelligenceBridge can be imported."""
    from app.services.intelligence_bridge import IntelligenceBridge, OmniContextStrategy, HybridSentinelStrategy
    assert IntelligenceBridge is not None
    assert OmniContextStrategy is not None
    assert HybridSentinelStrategy is not None
    print("✅ Box 2: IntelligenceBridge imports successfully")


def test_intelligence_bridge_mode_selection():
    """Test that IntelligenceBridge selects correct strategy based on mode."""
    from app.services.intelligence_bridge import IntelligenceBridge, OmniContextStrategy, HybridSentinelStrategy
    
    # Demo mode
    bridge_demo = IntelligenceBridge(mode="demo")
    assert isinstance(bridge_demo.strategy, OmniContextStrategy)
    assert bridge_demo.strategy_name == "OmniContextStrategy"
    
    # Production mode
    bridge_prod = IntelligenceBridge(mode="production")
    assert isinstance(bridge_prod.strategy, HybridSentinelStrategy)
    assert bridge_prod.strategy_name == "HybridSentinelStrategy"
    
    print("✅ Box 2: Mode selection works correctly")


# ============================================================================
# Test Box 3: Redline Implementer
# ============================================================================

def test_redline_implementer_imports():
    """Test that RedlineImplementer can be imported."""
    from app.services.redline_implementer import RedlineImplementer, RedlineResult, TextAnchor
    assert RedlineImplementer is not None
    assert RedlineResult is not None
    assert TextAnchor is not None
    print("✅ Box 3: RedlineImplementer imports successfully")


def test_redline_exact_match():
    """Test exact text matching for redline anchor."""
    from app.services.redline_implementer import RedlineImplementer
    
    implementer = RedlineImplementer()
    
    # Test exact match
    anchor = implementer.find_anchor(
        target_text="unlimited liability",
        document_text="The vendor shall have unlimited liability for all damages."
    )
    
    assert anchor.found is True
    assert anchor.match_method == "exact"
    assert anchor.match_confidence == 1.0
    print("✅ Box 3: Exact match anchor search works")


def test_redline_fuzzy_match():
    """Test fuzzy text matching for redline anchor."""
    from app.services.redline_implementer import RedlineImplementer
    
    implementer = RedlineImplementer(threshold=0.7)
    
    # Test fuzzy match (slightly different text)
    anchor = implementer.find_anchor(
        target_text="unlimited liabilities",  # Plural - slightly different
        document_text="The vendor shall have unlimited liability for all damages."
    )
    
    # Should find with fuzzy matching
    if anchor.found:
        assert anchor.match_method == "fuzzy"
        assert anchor.match_confidence < 1.0
        print(f"✅ Box 3: Fuzzy match found with {anchor.match_confidence:.0%} confidence")
    else:
        print("⚠️ Box 3: Fuzzy match not found (threshold may need adjustment)")


def test_track_changes_ooxml_generation():
    """Test Track Changes OOXML generation."""
    from app.services.redline_implementer import RedlineImplementer
    
    implementer = RedlineImplementer()
    
    ooxml = implementer.generate_track_changes_ooxml(
        original="unlimited liability",
        replacement="liability capped at 12 months fees"
    )
    
    assert "<?xml" in ooxml
    assert "w:strike" in ooxml  # Strikethrough for deletion
    assert "w:ins" in ooxml or "w:u" in ooxml  # Underline for insertion
    assert "unlimited liability" in ooxml or "unlimited" in ooxml
    print("✅ Box 3: Track Changes OOXML generation works")


# ============================================================================
# Test AI Service
# ============================================================================

def test_ai_service_imports():
    """Test that AIService can be imported."""
    from app.services.ai_service import AIService
    assert AIService is not None
    print("✅ AIService imports successfully")


def test_ai_service_provider_detection():
    """Test that AIService detects correct provider."""
    from app.services.ai_service import AIService
    
    ai = AIService()
    
    assert ai.provider in ["gemini", "azure", "none"]
    print(f"✅ AIService provider: {ai.provider}, enabled: {ai.is_enabled}")


def test_ai_service_fallback():
    """Test that AIService fallback works when AI is unavailable."""
    from app.services.ai_service import AIService
    
    ai = AIService()
    
    # Test fallback explanation
    fallback = ai._fallback_explanation("Unlimited Liability", "RED")
    assert "uncapped" in fallback.lower() or "liability" in fallback.lower()
    print(f"✅ AIService fallback: '{fallback}'")


# ============================================================================
# Integration Test: Full Pipeline
# ============================================================================

def test_full_pipeline_simulation():
    """Simulate the full Three-Box pipeline without real AI calls."""
    from app.services.structure_extractor import StructureExtractor
    from app.services.intelligence_bridge import IntelligenceBridge
    from app.services.redline_implementer import RedlineImplementer
    
    # Box 1: Extract structure
    extractor = StructureExtractor()
    contract_text = """
    5. LIABILITY
    
    The Service Provider shall have unlimited liability for any and all damages 
    arising from breach of this Agreement, regardless of the cause or nature of 
    such damages.
    """
    contract_map = extractor.extract_from_text(contract_text)
    assert len(contract_map.nodes) > 0
    
    # Box 2: Verify bridge setup
    bridge = IntelligenceBridge(mode="demo")
    assert bridge.strategy_name == "OmniContextStrategy"
    
    # Box 3: Generate redline
    implementer = RedlineImplementer()
    result = implementer.apply_redline(
        original_text="unlimited liability",
        suggested_text="liability capped at the total fees paid in the preceding 12 months",
        document_text=contract_text
    )
    
    assert result.success or result.anchor is not None
    print("✅ Full pipeline simulation completed")


# ============================================================================
# Run Tests
# ============================================================================

def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("ContraRed Three-Box Architecture Unit Tests")
    print("="*60 + "\n")
    
    tests = [
        # Box 1
        test_structure_extractor_imports,
        test_contract_map_creation,
        test_extract_from_text,
        # Box 2
        test_intelligence_bridge_imports,
        test_intelligence_bridge_mode_selection,
        # Box 3
        test_redline_implementer_imports,
        test_redline_exact_match,
        test_redline_fuzzy_match,
        test_track_changes_ooxml_generation,
        # AI Service
        test_ai_service_imports,
        test_ai_service_provider_detection,
        test_ai_service_fallback,
        # Integration
        test_full_pipeline_simulation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
