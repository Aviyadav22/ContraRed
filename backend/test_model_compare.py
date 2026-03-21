import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

results = []

# Test with both models
for model_name in ['gemini-3-pro-preview', 'gemini-3-flash-preview']:
    results.append(f"\n=== Testing {model_name} ===")
    model = genai.GenerativeModel(model_name)
    
    # Simple legal rewrite - shorter prompt
    try:
        prompt = "Rewrite: 'unlimited liability' to limit liability to 12 months fees. Output ONLY the rewritten text."
        r = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 100, "temperature": 0.3}
        )
        results.append(f"Candidates: {len(r.candidates) if r.candidates else 0}")
        if r.candidates:
            c = r.candidates[0]
            results.append(f"Finish reason: {c.finish_reason}")
            if c.content and c.content.parts:
                text = c.content.parts[0].text
                results.append(f"Text: {text}")
            else:
                results.append("NO CONTENT")
    except Exception as e:
        results.append(f"Error: {type(e).__name__}: {e}")

# Write results
with open("gemini_model_comparison.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("Results written to gemini_model_comparison.txt")
