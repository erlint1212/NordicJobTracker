import google.generativeai as genai
import os
import json
import requests
import re
from profile import CANDIDATE_PROFILE

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
GEMINI_MODEL_NAME = 'gemini-3-flash-preview'

OLLAMA_MODEL_NAME = "qwen2.5-coder:14b-instruct-q4_k_m" 
OLLAMA_URL = "http://localhost:11434/api/chat"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
else:
    model = None

def clean_json_text(text):
    """Clean JSON string from Markdown or chatter."""
    text = text.strip()
    if "```" in text:
        text = re.sub(r"```json|```", "", text).strip()
    
    # Attempt to extract just the JSON part
    start_brace = text.find("{")
    end_brace = text.rfind("}")
    if start_brace != -1 and end_brace != -1:
        text = text[start_brace:end_brace+1]
    
    return text

def evaluate_batch(job_list, force_local=False):
    """
    Evaluates jobs.
    - If force_local=True: Uses Ollama with Single-Shot Prompt (Batch Size 1 expected).
    - If force_local=False: Uses Gemini with Batch Prompt.
    """
    
    # --- PROMPT STRATEGY ---
    if force_local:
        # LOCAL PROMPT
        prompt = f"""
        ROLE: STRICT TECHNICAL RECRUITER.
        TASK: EVALUATE THIS JOB FOR A JUNIOR DATA/PYTHON/BACKEND CANDIDATE.
        
        CANDIDATE PROFILE:
        {CANDIDATE_PROFILE}

        JOB:
        Title: {job['title']}
        Employer: {job['employer']}
        Description: {job['description'][:2000]}

        INSTRUCTIONS:
        1. Decide if it's a match based on the profile.
        2. Assign a SUITABILITY SCORE (1-10). 
           1 = Irrelevant/Senior/Wrong Stack. 
           10 = Perfect Junior Python/Data Role.

        OUTPUT JSON ONLY:
        {{
            "{job['id']}": {{ "match": true/false, "reason": "Short reason", "score": 5 }}
        }}
        """
    else:
        # GEMINI BATCH PROMPT
        jobs_json = json.dumps(job_list, indent=2)
        prompt = f"""
        Act as a strict technical screener. 
        Profile: {CANDIDATE_PROFILE}
        
        Evaluate these jobs.
        1. Determine if it matches (True/False).
        2. Assign a Suitability Score (1-10), where 10 is perfect fit.
        
        Rules:
        - Reject Senior/Manager roles.
        - Prioritize Python, Data, Backend.

        Input:
        {jobs_json}

        Return JSON object mapping Job ID -> {{ "match": boolean, "reason": "string", "score": integer }}.
        """

    # --- EXECUTION PATHS ---

    # 1. LOCAL OLLAMA PATH
    if force_local:
        try:
            payload = {
                "model": OLLAMA_MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_ctx": 4096} # 0.0 temp for strictness
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()['message']['content']
            return json.loads(clean_json_text(data))
        except Exception as e:
            print(f"   ❌ Local AI Failed: {e}")
            return {} # Fail-Open handled in main.py

    # 2. GEMINI CLOUD PATH
    if model:
        try:
            response = model.generate_content(prompt)
            return json.loads(clean_json_text(response.text))
        except Exception as e:
            if "429" in str(e):
                print(f"   ⏳ Gemini Quota Hit. Failing open.")
            else:
                print(f"   ⚠️ Gemini Error: {e}")
            return {} # Fail-Open handled in main.py

    return {}
