import json
import os
import re
from profile import CANDIDATE_PROFILE

import lmstudio as lms

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-3-flash-preview"

LOCAL_MODEL_NAME = "qwen/qwen3.5-9b"

if GEMINI_API_KEY:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
else:
    model = None


def clean_json_text(text):
    """Clean JSON string from Markdown or chatter."""
    text = text.strip()
    
    # NEW: Ruthlessly slice out any <think> blocks and their contents
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    if "```" in text:
        text = re.sub(r"```json|```", "", text).strip()

    start_brace = text.find("{")
    end_brace = text.rfind("}")
    if start_brace != -1 and end_brace != -1:
        text = text[start_brace:end_brace+1]

    # Fix common LLM JSON mistakes
    text = text.replace("'", '"')               
    text = re.sub(r'\bTrue\b', 'true', text)         
    text = re.sub(r'\bFalse\b', 'false', text)       
    text = re.sub(r'\bNone\b', 'null', text)         
    text = re.sub(r',\s*}', '}', text)               
    text = re.sub(r',\s*]', ']', text)               

    return text

def evaluate_batch(job_list, force_local=False, think=False):
    """
    Evaluates jobs.
    - If force_local=True: Uses LM Studio SDK (Batch Size 1 expected).
    - think: If True, enables Qwen3.5 extended thinking via chat_template_kwargs.
             Defaults to False (thinking disabled, faster).
    - If force_local=False: Uses Gemini with Batch Prompt.
    """

    # 1. LOCAL LM STUDIO PATH
    if force_local:
        job = job_list[0]
        
        # NEW: Inject the Qwen 3.5 specific soft-toggle directive
        think_directive = "/think\n" if think else "/no_think\n"
        
        prompt = f"""{think_directive}ROLE: STRICT TECHNICAL RECRUITER.
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
           10 = Perfect Entry Level role

        OUTPUT JSON ONLY:
        {{
            "{job['id']}": {{ "match": true/false, "reason": "Short reason", "score": 5 }}
        }}
        """
        try:
            llm = lms.llm(LOCAL_MODEL_NAME)
            chat = lms.Chat()
            chat.add_user_message(prompt)

            # You can safely leave this config here, but the prompt directive does the heavy lifting now
            config = {"temperature": 0.0, "chat_template_kwargs": {"enable_thinking": False}}
            if think:
                config["chat_template_kwargs"] = {"enable_thinking": True}

            result = llm.respond(
                chat,
                config=config,
            )
            raw = str(result)
            print(f"      🔍 RAW: {raw[:300]}")
            return json.loads(clean_json_text(raw))

        except Exception as e:
            print(f"   ❌ LM Studio Failed: {e}")
            return {}

    # 2. GEMINI CLOUD PATH
    if model:
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
        try:
            response = model.generate_content(prompt)
            return json.loads(clean_json_text(response.text))
        except Exception as e:
            if "429" in str(e):
                print(f"   ⏳ Gemini Quota Hit. Failing open.")
            else:
                print(f"   ⚠️ Gemini Error: {e}")
            return {}

    return {}
