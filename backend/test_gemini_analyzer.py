"""Quick test for gemini_analyzer."""
import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

import asyncio

async def test():
    from app.services.gemini_analyzer import gemini_analyzer
    
    print(f"Analyzer enabled: {gemini_analyzer.is_enabled}")
    
    if not gemini_analyzer.is_enabled:
        print("Gemini not configured!")
        return
    
    test_contract = """
    CONFIDENTIALITY AGREEMENT
    
    This Agreement is entered into by Company ("Disclosing Party") and Recipient.
    
    1. CONFIDENTIALITY: Recipient shall hold all information in strict confidence.
    
    2. LIABILITY: The Vendor shall have unlimited liability for all damages arising 
    from this Agreement.
    
    3. TERM: This agreement shall remain in effect perpetually.
    
    4. GOVERNING LAW: This Agreement shall be governed by the laws of the State of Delaware.
    """
    
    playbook_rules = [
        {"name": "Unlimited Liability", "risk_level": "RED", "primary_position": "Limit to 12 months fees"},
        {"name": "Perpetual Term", "risk_level": "RED", "primary_position": "Maximum 3 year term"},
    ]
    
    print("\nStarting AI analysis...")
    print("(This may take 30-60 seconds for Gemini 3 Pro)")
    
    result = await gemini_analyzer.analyze_full_contract(
        contract_text=test_contract,
        playbook_rules=playbook_rules,
        playbook_name="Test Playbook"
    )
    
    print(f"\n=== AI Analysis Result ===")
    print(f"Tokens used: {result.tokens_used}")
    print(f"Executive Summary items: {len(result.executive_summary)}")
    print(f"Redlines found: {len(result.redlines)}")
    
    print("\n--- Executive Summary ---")
    for item in result.executive_summary:
        print(f"  • {item}")
    
    print("\n--- Redlines ---")
    for r in result.redlines:
        print(f"  [{r.risk_level}] {r.rule_name}")
        print(f"    Original: {r.original_text[:50]}...")
    
    if not result.redlines and not result.executive_summary:
        print("\n!!! NO RESULTS - Check raw response:")
        print(result.raw_response[:500] if result.raw_response else "EMPTY")

asyncio.run(test())
