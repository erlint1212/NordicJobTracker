import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import random
import sqlite3
from datetime import datetime

# --- Configuration ---
SEARCH_QUERIES = [
    # The Classics
    "Data Science",
    "Data Engineer",
    "Backend Engineer",
    "software engineer",
    
    # The Norwegian Titles (High Priority)
    "Utvikler",             # Developer
    "Systemutvikler",       # System Developer
    "Dataanalytiker",       # Data Analyst
    "IT-konsulent",         # IT Consultant (Huge market in Norway)
    
    # The "Skill" Hunters
    "Python SQL",           # Finds roles requiring both
    "Snowflake DBT"
]

# --- Project Structure & Paths ---
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

TXT_FILENAME = os.path.join(OUTPUT_DIR, "jobs_for_gemini.txt")
EXCEL_FILENAME = os.path.join(DATA_DIR, "job_application_tracker.xlsx")
DB_FILENAME = os.path.join(DATA_DIR, "jobs.db")

COLUMNS = [
    'Stillingstittel', 
    'Fra dato', 
    'Søknadsfrist', 
    'Arbeidsgiver', 
    'Kontaktperson', 
    'Mobil',
    'Arbeidssted', 
    'Kort beskrivelse', 
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
    "Accepted"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- Database Functions ---

def setup_database():
    """Creates the SQLite database with full history and description storage."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # We now store full_description so we never lose the raw data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_jobs (
            ID TEXT PRIMARY KEY,
            title TEXT,
            employer TEXT,
            full_description TEXT,
            date_added TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_existing_ids():
    """Fetches all Job IDs currently in the database."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ID FROM scraped_jobs')
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()
    finally:
        conn.close()

def add_job_to_db(job_id, title, employer, description):
    """Adds a newly scraped job ID to the database."""
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO scraped_jobs (ID, title, employer, full_description, date_added) 
            VALUES (?, ?, ?, ?, ?)
        ''', (job_id, title, employer, description, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
    finally:
        conn.close()

def sync_excel_to_db():
    """Syncs existing Excel rows to Database to prevent re-scraping old jobs."""
    if not os.path.exists(EXCEL_FILENAME):
        return

    print("🔄 Syncing existing Excel rows to Database...")
    try:
        df = pd.read_excel(EXCEL_FILENAME)
        if 'ID' in df.columns:
            conn = sqlite3.connect(DB_FILENAME)
            cursor = conn.cursor()
            count = 0
            for _, row in df.iterrows():
                job_id = str(row['ID'])
                # We use placeholders for missing text if syncing from Excel
                cursor.execute('''
                    INSERT OR IGNORE INTO scraped_jobs (ID, title, employer, full_description, date_added) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (job_id, "Imported from Excel", "Unknown", "", datetime.now().strftime("%Y-%m-%d")))
                
                if cursor.rowcount > 0:
                    count += 1
            conn.commit()
            conn.close()
            if count > 0:
                print(f"   - Imported {count} existing jobs from Excel to DB.")
    except Exception as e:
        print(f"   - Warning: Could not sync Excel to DB: {e}")

# --- Scraper Functions ---

def get_job_links(query):
    formatted_query = query.replace(" ", "+")
    url = f"https://www.finn.no/job/search?q={formatted_query}"
    
    print(f"🔎 Searching for: {query}...")
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        articles = soup.find_all('article')
        
        for article in articles:
            link_tag = article.find('a', class_='job-card-link')
            if link_tag and link_tag.has_attr('href'):
                href = link_tag['href']
                if href.startswith("/"):
                    href = f"https://www.finn.no{href}"
                links.append(href)
        
        return list(set(links))
    except Exception as e:
        print(f"❌ Error searching {query}: {e}")
        return []

def scrape_ad_details(url):
    print(f"   🕷️ Crawling: {url}")
    try:
        time.sleep(random.uniform(0.1, 0.5))
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Defaults (Null-safety)
        title = "Unknown Title"
        employer = "Unknown"
        deadline = "Se annonse"
        location = "Unknown"
        contact = ""
        phone = ""
        short_desc = ""
        full_description = ""

        # 1. Job Title
        title_tag = soup.find('h1', class_='t2')
        if title_tag: title = title_tag.get_text(strip=True)

        # 2. Company
        top_section = soup.find('section', class_='mt-16')
        if top_section:
            p_tag = top_section.find('p', class_='mb-24')
            if p_tag: employer = p_tag.get_text(strip=True)

        # 3. Deadline
        list_items = soup.find_all('li', class_='flex flex-col')
        for li in list_items:
            if "Frist" in li.get_text():
                span = li.find('span', class_='font-bold')
                if span: deadline = span.get_text(strip=True)

        # 4. Location & Contact Info
        info_lists = soup.find_all('ul', class_='space-y-6')
        
        for ul in info_lists:
            items = ul.find_all('li')
            
            temp_contact = ""
            temp_phone = ""
            is_contact_list = False

            for item in items:
                text = item.get_text(strip=True)
                
                if "Sted" in text:
                    location = text.replace("Sted:", "").strip()

                if "Kontaktperson" in text:
                    temp_contact = text.replace("Kontaktperson:", "").strip()
                    is_contact_list = True
                
                if "Mobil" in text or "Telefon" in text:
                    temp_phone = text.replace("Mobil:", "").replace("Telefon:", "").strip()

            if is_contact_list:
                if temp_contact and not contact: contact = temp_contact
                if temp_phone and not phone: phone = temp_phone

        # 6. Description
        desc_div = soup.find('div', class_='import-decoration')
        if desc_div:
            full_description = desc_div.get_text(separator="\n", strip=True)
            short_desc = full_description[:300] + "..." if len(full_description) > 300 else full_description

        job_id = url.split('/')[-1]

        return {
            'Stillingstittel': title,
            'Fra dato': datetime.now().strftime("%d.%m.%Y"),
            'Søknadsfrist': deadline,
            'Arbeidsgiver': employer,
            'Kontaktperson': contact,
            'Mobil': phone,
            'Arbeidssted': location,
            'Kort beskrivelse': short_desc,
            'Full beskrivelse': full_description,
            'Lenke': url,
            'Status': "Not searched",
            'ID': job_id
        }

    except Exception as e:
        print(f"❌ Error scraping ad {url}: {e}")
        return None

def save_to_txt(jobs):
    """Saves ONLY 'Not searched' jobs to text file."""
    
    # Filter only jobs that are "Not searched"
    relevant_jobs = [j for j in jobs if j.get('Status') == "Not searched"]
    
    if not relevant_jobs:
        print(f"ℹ️ No 'Not searched' jobs to write to text file.")
        return

    with open(TXT_FILENAME, 'w', encoding='utf-8') as f:
        f.write("I am looking for a job. Please analyze these NEW job postings and prioritize them.\n")
        f.write("==========================================================================\n\n")
        
        for job in relevant_jobs:
            f.write(f"JOB TITLE: {job['Stillingstittel']}\n")
            f.write(f"COMPANY: {job['Arbeidsgiver']}\n")
            f.write(f"DEADLINE: {job['Søknadsfrist']}\n")
            f.write(f"LOCATION: {job['Arbeidssted']}\n")
            f.write(f"LINK: {job['Lenke']}\n")
            f.write(f"DESCRIPTION:\n{job['Full beskrivelse']}\n")
            f.write("\n--------------------------------------------------------------------------\n\n")
    
    print(f"✅ Text file created at: {TXT_FILENAME} ({len(relevant_jobs)} jobs)")

def save_to_excel(new_jobs):
    """Updates the Excel tracker in the data folder."""
    
    existing_df = pd.DataFrame(columns=COLUMNS)
    
    if os.path.exists(EXCEL_FILENAME):
        try:
            existing_df = pd.read_excel(EXCEL_FILENAME)
        except:
            pass

    if 'ID' in existing_df.columns:
        existing_df['ID'] = existing_df['ID'].astype(str)

    # Dedup against Excel
    existing_ids = existing_df['ID'].tolist() if 'ID' in existing_df else []
    unique_jobs = [j for j in new_jobs if str(j['ID']) not in existing_ids]

    if not unique_jobs:
        return

    excel_data = []
    for job in unique_jobs:
        # Use .get() to avoid errors if a key is missing
        excel_data.append({k: job.get(k, "") for k in COLUMNS})

    new_df = pd.DataFrame(excel_data)
    final_df = pd.concat([existing_df, new_df], ignore_index=True)

    writer = pd.ExcelWriter(EXCEL_FILENAME, engine='xlsxwriter')
    final_df.to_excel(writer, index=False, sheet_name='Tracker')
    
    workbook = writer.book
    worksheet = writer.sheets['Tracker']

    # --- Formatting ---
    format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    format_blue = workbook.add_format({'bg_color': '#BDD7EE', 'font_color': '#000000'})
    format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
    format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})

    worksheet.set_column('A:A', 30) # Tittel
    worksheet.set_column('B:B', 12) # Fra dato
    worksheet.set_column('C:C', 15) # Frist
    worksheet.set_column('D:D', 25) # Arbeidsgiver
    worksheet.set_column('E:E', 20) # Kontaktperson
    worksheet.set_column('F:F', 15) # Mobil
    worksheet.set_column('G:G', 15) # Sted
    worksheet.set_column('H:H', 50) # Beskrivelse (Short)
    worksheet.set_column('I:I', 40) # Lenke
    worksheet.set_column('J:J', 20) # Status
    worksheet.set_column('K:K', 0)  # Hide ID column

    # Dropdown on Status (Column J is index 9, letter J)
    status_col = 'J'
    data_len = len(final_df) + 100
    
    worksheet.data_validation(f'{status_col}2:{status_col}{data_len}', {
        'validate': 'list',
        'source': STATUS_OPTIONS
    })

    range_str = f'{status_col}2:{status_col}{data_len}'
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Not searched"', 'format': format_red})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Sent Application"', 'format': format_blue})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"1. Interview"', 'format': format_yellow})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"2. Interview"', 'format': format_yellow})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Offer"', 'format': format_green})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Accepted"', 'format': format_green})

    writer.close()
    print(f"✅ Added {len(unique_jobs)} new jobs to {EXCEL_FILENAME}")

# --- Main ---
if __name__ == "__main__":
    print("🚀 Starting Advanced Job Crawler...")
    
    # 1. Setup Data/Output folders and DB
    setup_database()
    sync_excel_to_db()
    
    # 2. Get currently processed IDs (The "Brain")
    processed_ids = get_existing_ids()
    print(f"💾 Database currently holds {len(processed_ids)} jobs.")

    # We will accumulate all new jobs here to write to Excel/TXT once at the end
    all_newly_scraped_jobs = []

    # 3. Loop through queries and update DB continuously
    for query in SEARCH_QUERIES:
        links = get_job_links(query)
        
        # Filter links specifically for THIS query against what we know
        new_links_for_query = []
        for link in links:
            job_id = link.split('/')[-1]
            if job_id not in processed_ids:
                new_links_for_query.append(link)
        
        if not new_links_for_query:
            print(f"   - No new jobs for '{query}' (all duplicates).")
            continue

        print(f"   - Found {len(new_links_for_query)} NEW jobs for '{query}'. Crawling...")

        # Scrape these specific new links
        for i, link in enumerate(new_links_for_query):
            print(f"     [{i+1}/{len(new_links_for_query)}]", end=" ")
            details = scrape_ad_details(link)
            
            if details:
                # Add to master list for file saving
                all_newly_scraped_jobs.append(details)
                
                # IMPORTANT: Update DB and Memory IMMEDIATELY
                # This ensures the next query knows about this job
                add_job_to_db(details['ID'], details['Stillingstittel'], details['Arbeidsgiver'], details['Full beskrivelse'])
                processed_ids.add(details['ID']) # Update set in memory

    # 4. Save to files (only if we actually found something)
    if all_newly_scraped_jobs:
        print(f"\n📝 Writing {len(all_newly_scraped_jobs)} unique new jobs to files...")
        save_to_txt(all_newly_scraped_jobs)
        save_to_excel(all_newly_scraped_jobs)
        print("\n✨ Done! Files updated.")
    else:
        print("\n🎉 You are completely up to date! No new jobs found.")
