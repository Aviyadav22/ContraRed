"""Debug Gemini API responses - standalone version."""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

print("=" * 60)
print("GEMINI DEBUG TEST")
print("=" * 60)

print(f"\nAPI Key set: {bool(GEMINI_API_KEY)}")
print(f"API Key prefix: {GEMINI_API_KEY[:15]}..." if GEMINI_API_KEY else "NOT SET")
print(f"Model: {GEMINI_MODEL}")

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)

# Test simple generation
print("\n--- Simple Generation Test ---")
try:
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content("Say 'hello world' and nothing else.")
    
    print(f"Candidates: {len(response.candidates) if response.candidates else 0}")
    if response.candidates:
        c = response.candidates[0]
        print(f"Finish reason: {c.finish_reason}")
        if c.content and c.content.parts:
            print(f"Text: {c.content.parts[0].text}")
        else:
            print("No content/parts in candidate")
    else:
        print("No candidates returned")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test legal clause generation
print("\n--- Legal Clause Test ---")
try:
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = """Rewrite this clause to limit liability to 12 months fees:

"The Vendor shall have unlimited liability for all damages."

Reply with ONLY the rewritten clause."""

    response = model.generate_content(prompt)
    
    print(f"Candidates: {len(response.candidates) if response.candidates else 0}")
    if response.candidates:
        c = response.candidates[0]
        print(f"Finish reason: {c.finish_reason}")
        if c.content and c.content.parts:
            print(f"Text: {c.content.parts[0].text}")
        else:
            print("No content/parts in candidate")
    else:
        print("No candidates returned")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
