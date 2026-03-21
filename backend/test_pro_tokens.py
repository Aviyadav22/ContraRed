import os
import sys
os.chdir(r'd:\Startup\Redliniing\V1 addon word\backend')
sys.path.insert(0, r'd:\Startup\Redliniing\V1 addon word\backend')

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

results = []

# Test gemini-3-pro-preview with much higher token limit
model = genai.GenerativeModel('gemini-3-pro-preview')
    
prompt = "Rewrite: 'unlimited liability' to limit liability to 12 months fees. Output ONLY the rewritten text, nothing else."

for max_tokens in [500, 1000, 2000, 4000]:
    results.append(f"\n=== Pro with max_tokens={max_tokens} ===")
    try:
        r = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature": 0.3}
        )
        results.append(f"Candidates: {len(r.candidates) if r.candidates else 0}")
        if r.candidates:
            c = r.candidates[0]
            results.append(f"Finish reason: {c.finish_reason}")
            if c.content and c.content.parts:
                text = c.content.parts[0].text
                results.append(f"Text length: {len(text)}")
                results.append(f"Text: {text[:500]}")
            else:
                results.append("NO CONTENT")
    except Exception as e:
        results.append(f"Error: {type(e).__name__}: {e}")

# Write results
with open("gemini_pro_tokens_test.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("Done! Check gemini_pro_tokens_test.txt")
