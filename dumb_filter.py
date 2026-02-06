import config

def is_relevant_basic(title, description):
    title_lower = title.lower()
    desc_lower = description.lower()

    # 1. Title Dealbreakers (Instant Reject)
    # Adjust this list based on your level.
    # If you are a Junior/Graduate, reject Senior/Lead roles.
    # If you want "Data Engineer", you might reject "Frontend".
    bad_titles = [
        "senior", "lead", "principal", "manager", "leder", "sjef", 
        "head of", "architect",
        ".net", "c#"
    ]
    
    if any(bad in title_lower for bad in bad_titles):
        return False, f"Title contained: {', '.join([b for b in bad_titles if b in title_lower])}"

    # 2. Tech Stack Requirements (Must have at least ONE)
    # If a Data Engineering job doesn't mention Data, SQL or Python, it's probably wrong.
    required_keywords = ["python", "go", "sql", "etl", "elt", "data", "machine learning", "ai", "cloud"]
    
    if not any(req in desc_lower for req in required_keywords):
        return False, "Missing required tech keywords"

    # 3. Language Requirement (Optional)
    # If you strictly need English or strictly need Norwegian, you could check here.
    # For now, we skip this as it's harder to do accurately without LLM.

    return True, "Passed basic filter"
