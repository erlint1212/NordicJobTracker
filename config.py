import os

# --- Search Settings ---
SEARCH_QUERIES = [
    # The Classics
    "Data Science",
    "Data Engineer",
    "Backend Engineer",
    "backend",
    "software engineer",
    
    # The Norwegian Titles (High Priority)
    "Utvikler",             # Developer
    "Systemutvikler",       # System Developer
    "Dataanalytiker",       # Data Analyst
    "IT-konsulent",         # IT Consultant
    
    # The "Skill" Hunters
    "Python SQL",
    "DBT Snowflake"
]

# --- File System ---
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Automatically create folders when config is imported
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

TXT_FILENAME = os.path.join(OUTPUT_DIR, "jobs_for_gemini.txt")
EXCEL_FILENAME = os.path.join(DATA_DIR, "job_application_tracker.xlsx")
DB_FILENAME = os.path.join(DATA_DIR, "jobs.db")

# --- Excel & Data Structure ---
COLUMNS = [
    'Stillingstittel', 
    'Fra dato', 
    'Søknadsfrist', 
    'Arbeidsgiver', 
    'Kontaktperson', 
    'Mobil',
    'Arbeidssted', 
    'Full beskrivelse',
    'Lenke', 
    'Status',
    'ID'
]

STATUS_OPTIONS = [
    "Not searched", 
    "Sent Application", 
    "1. Interview", 
    "2. Interview", 
    "Offer", 
    "Accepted",
    "Rejected",
    "Not Interested"
]

# --- Scraper Settings ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
