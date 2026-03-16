# dumb_filter.py

def is_relevant_basic(title, description):
    """
    Returns (True, "Reason") if the job passes the basic keyword checks.
    Returns (False, "Reason") if it fails.
    """
    title_lower = title.lower()
    desc_lower = description.lower()

    # --- 1. NEGATIVE FILTERS (Instant Rejects) ---
    # We check if any of these substrings exist in the Job Title.

    # A. Management & Executive (The "Boss" Filter)
    bad_management = [
        "manager", "management", "director", "direktør", 
        "head of", "chief", "vp", "president", "c-level",
        "partner", "founder", "owner", "chair", "board",
        "leder", "sjef", "bestyrer", "ansvarlig" # "Ansvarlig" often implies "Manager" (e.g. Salgsansvarlig)
    ]

    # B. Seniority (The "Too Experienced" Filter)
    bad_seniority = [
        "senior", "principal", "lead", "staff engineer", 
        "distinguished", "architect", "arkitekt", 
        "expert", "erfaren", "spesialist" 
    ]

    # C. Non-Technical / Wrong Domain (The "Wrong Department" Filter)
    bad_domain = [
        "sales", "salg", "account", "konto", "business development", "forretningsutvikling",
        "hr", "human resources", "personal", "talent", "recruiter", "rekruttering",
        "marketing", "marked", "content", "innhold", "design", "ux", "ui", "graphic",
        "finance", "økonomi", "regnskap", "controller", "auditor", "revisor",
        "legal", "advokat", "jurist",
        "support", "service", "kundeservice", "customer",
        "professor", "phd", "research fellow", "stipendiat", "faculty", "lecturer"
    ]

    # D. Tech Stack Mismatch (The "Wrong Language" Filter)
    # Only applies to TITLE. (e.g. A Python job might mention Java in description as "Nice to have", which is fine)
    bad_stack = [
        ".net", "c#", "java ", "java-", # "java" with space/hyphen avoids matching "javascript" (though you might want to ban that too)
        "php", "ruby", "wordpress", "drupal",
        "frontend", "front-end", "fullstack", "full-stack", # Remove if you want Fullstack
        "hardware", "embedded", "firmware", "signal", "fpga", "iot",
        "network", "nettverk", "cisco", "sysadmin", "system administrator",
        "erp", "sap", "crm", "salesforce", "sharepoint"
    ]

    # Combine lists
    all_bad_titles = bad_management + bad_seniority + bad_domain + bad_stack

    for bad in all_bad_titles:
        if bad in title_lower:
            return False, f"Title contained blacklist term: '{bad}'"


    # --- 2. POSITIVE FILTERS (Must Have) ---
    # The description must contain at least ONE of these to be relevant.
    
    required_keywords = [
        # Languages
        "python", "sql", "go", "rust",
        # Data & Tools
        "data", "etl", "elt", "pipeline", "spark", "pandas", "numpy", 
        "airflow", "dbt", "snowflake", "kafka", "hadoop",
        # Infrastructure
        "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "linux",
        # Concepts
        "machine learning", "ai", "artificial intelligence", "scikit", 
        "backend", "back-end", "api", "rest", "devops"
    ]

    if not any(req in desc_lower for req in required_keywords):
        return False, "Description missing required tech keywords"

    return True, "Passed basic filter"
