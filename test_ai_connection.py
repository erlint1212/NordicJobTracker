import google.generativeai as genai
import os
import json

# 1. Setup
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = 'gemini-3-flash-preview' # Kept exactly as you requested

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY environment variable is not set.")
    exit()

print(f"Testing Model: {MODEL_NAME}")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# 2. Mock Data (Similar to what your scraper sends)
mock_jobs = [
    {"id": "123", "title": "Senior Data Engineer", "description": "Requires 10 years Java experience."},
    {"id": "456", "title": "Junior Python Developer", "description": "Entry level, Python and SQL required."}
]

prompt = f"""
Act as a technical recruiter. Evaluate these jobs.
Return a JSON object where keys are Job IDs.
Format: {{ "123": {{ "match": boolean, "reason": "string" }} }}

Jobs: {json.dumps(mock_jobs)}
"""

# 3. Test Connection
try:
    print("🚀 Sending request...")
    response = model.generate_content(prompt)
    
    print("\n--- RAW TEXT RESPONSE ---")
    print(response.text)
    print("-------------------------\n")

    # 4. Test Parsing Logic (This is likely where it fails)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "").strip()
    
    parsed = json.loads(text)
    print("✅ JSON Parsing Successful!")
    print(json.dumps(parsed, indent=2))

except Exception as e:
    print(f"\n❌ FAILED: {e}")
