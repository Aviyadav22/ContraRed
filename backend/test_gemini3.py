"""Simple test for Gemini 3 Pro via AIService."""
import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print(f"GEMINI_MODEL: {os.getenv('GEMINI_MODEL')}")
print("=" * 50)

from app.services import AIService
import asyncio

ai = AIService()
print(f"Provider: {ai.provider}")
print(f"Enabled: {ai.is_enabled}")

async def test():
    print("\n--- Testing suggest_fix ---")
    fix, tokens = await ai.suggest_fix(
        'The Vendor shall have unlimited liability for all damages.',
        'Limit liability to 12 months fees'
    )
    print(f"Tokens used: {tokens}")
    print(f"Fix empty: {not fix}")
    print(f"Suggested Fix:\n---\n{fix}\n---")
    
    print("\n--- Testing explain_risk ---")
    explanation, tokens2 = await ai.explain_risk(
        'unlimited liability for all damages',
        'Unlimited Liability',
        'RED'
    )
    print(f"Tokens used: {tokens2}")
    print(f"Explanation:\n---\n{explanation}\n---")

asyncio.run(test())
print("\nDone!")
