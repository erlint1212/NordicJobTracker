# ai_filter.py
import google.generativeai as genai
import os
import json
import time
from profile import CANDIDATE_PROFILE

API_KEY = os.getenv("GEMINI_API_KEY") 

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Use flash for speed and cost
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

def evaluate_batch(job_list):
    """
    Evaluates a list of job dictionaries in one go.
    job_list structure: [{'id': '...', 'title': '...', 'description': '...'}, ...]
    """
    if not model:
        return {} # Return empty dict if no AI

    # Construct a prompt that includes ALL jobs
    jobs_json = json.dumps(job_list, indent=2)
    
    prompt = f"""
    Act as a technical recruiter for this candidate:
    {CANDIDATE_PROFILE}

    Evaluate the following list of jobs.
    For each job, determine if it is a match based on the candidate profile.
    
    **Strict Rules:**
    1. REJECT Senior/Lead roles (>3 years exp).
    2. REJECT roles with irrelevant tech stacks (e.g. Pure C#/.NET, Pure Frontend).
    3. APPROVE Junior/Graduate/Mid-level roles fitting Python/Data/Cloud.

    Input Jobs:
    {jobs_json}

    Return a JSON object where the keys are the Job IDs and the values are objects containing "match" (boolean) and "reason" (string).
    Example format:
    {{
        "12345": {{ "match": true, "reason": "Good stack fit" }},
        "67890": {{ "match": false, "reason": "Requires 10 years exp" }}
    }}
    """

    try:
        # Rate limit safety is managed by the batch size in main loop
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```"):
            text = text.strip("`").replace("json", "").strip()
            
        return json.loads(text)

    except Exception as e:
        print(f"   ⚠️ Batch AI Error: {e}")
        # If batch fails, we default to accepting them so we don't lose data
        # or you could implement a fallback to check them individually
        return {job['id']: {"match": True, "reason": "AI Batch Failed"} for job in job_list}
