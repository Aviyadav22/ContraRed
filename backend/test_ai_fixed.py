"""Test AI Service with fixed model name."""
import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

print(f"Model from env: {os.getenv('GEMINI_MODEL')}")

# Direct test
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel(os.getenv('GEMINI_MODEL'))

print("\n--- Test 1: Simple hello ---")
r = model.generate_content('Say hello')
print(f"Response: {r.text if r.text else 'EMPTY'}")

print("\n--- Test 2: Legal clause rewrite ---")
r2 = model.generate_content('Rewrite to limit liability to 12 months fees: The Vendor shall have unlimited liability for all damages. Reply with only the rewritten clause.')
print(f"Response: {r2.text if r2.text else 'EMPTY'}")

print("\n--- Test 3: Via AIService ---")
from app.services import AIService
import asyncio

ai = AIService()
print(f"AI Provider: {ai.provider}")
print(f"AI Enabled: {ai.is_enabled}")

async def test_ai_service():
    suggested_fix, tokens = await ai.suggest_fix(
        'The Vendor shall have unlimited liability for all damages.',
        'Limit liability to 12 months fees'
    )
    print(f"Suggested Fix: {suggested_fix}")
    print(f"Tokens: {tokens}")
    return suggested_fix

fix = asyncio.run(test_ai_service())
print(f"\nFinal result - fix is empty: {not fix}")
