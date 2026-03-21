import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

# Direct raw test without AIService
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

model_name = os.getenv('GEMINI_MODEL')
model = genai.GenerativeModel(model_name)

results = []
results.append(f"Model: {model_name}")

# Test 1: Simple hello
try:
    r = model.generate_content("Say hello")
    results.append(f"Test1 candidates: {len(r.candidates) if r.candidates else 0}")
    if r.candidates:
        c = r.candidates[0]
        results.append(f"Test1 finish_reason: {c.finish_reason}")
        if c.content and c.content.parts:
            results.append(f"Test1 text: {c.content.parts[0].text[:100]}")
except Exception as e:
    results.append(f"Test1 error: {e}")

# Test 2: Legal clause with 500 tokens (matching our new setting)
try:
    r2 = model.generate_content(
        "Rewrite this clause to limit liability to 12 months fees: The Vendor shall have unlimited liability for all damages. ONLY output the rewritten clause.",
        generation_config={"max_output_tokens": 500, "temperature": 0.3}
    )
    results.append(f"Test2 candidates: {len(r2.candidates) if r2.candidates else 0}")
    if r2.candidates:
        c = r2.candidates[0]
        results.append(f"Test2 finish_reason: {c.finish_reason}")
        if c.content and c.content.parts:
            text = c.content.parts[0].text
            results.append(f"Test2 text_length: {len(text)}")
            results.append(f"Test2 text: {text}")
        else:
            results.append("Test2 NO CONTENT/PARTS")
    else:
        results.append("Test2 NO CANDIDATES")
except Exception as e:
    results.append(f"Test2 error: {type(e).__name__}: {e}")

# Test 3: Via AIService with updated tokens
results.append("--- Via AIService ---")
try:
    from app.services import AIService
    import asyncio
    
    ai = AIService()
    results.append(f"AIService provider: {ai.provider}")
    results.append(f"AIService enabled: {ai.is_enabled}")
    
    async def test_ai():
        fix, tokens = await ai.suggest_fix(
            'The Vendor shall have unlimited liability for all damages.',
            'Limit liability to 12 months fees'
        )
        return fix, tokens
    
    fix, tokens = asyncio.run(test_ai())
    results.append(f"AIService tokens: {tokens}")
    results.append(f"AIService fix_length: {len(fix)}")
    results.append(f"AIService fix: {fix}")
except Exception as e:
    results.append(f"AIService error: {type(e).__name__}: {e}")

# Write results
with open("gemini_test_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("Results written to gemini_test_results.txt")
