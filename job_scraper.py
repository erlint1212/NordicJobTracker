import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime

# --- Configuration ---
SEARCH_QUERIES = [
    "Data Science", 
    "Data Engineer", 
    "Backend Engineer", 
    "SWE"
]

# File names
TXT_FILENAME = "jobs_for_gemini.txt"
EXCEL_FILENAME = "job_applications_tracker.xlsx"

# Status Options for the Dropdown
STATUS_OPTIONS = [
    "Not searched", 
    "Sent Application", 
    "1. Interview", 
    "2. Interview", 
    "Offer", 
    "Accepted"
]

def get_finn_jobs(query):
    """Scrapes job listings from Finn.no based on a query."""
    formatted_query = query.replace(" ", "+")
    url = f"https://www.finn.no/job/search?q={formatted_query}"
    
    # User-Agent is required to look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    jobs = []
    
    # Based on the HTML you provided, ads are in 'article' tags
    # The container usually has class 'job-card'
    ad_articles = soup.find_all('article')
    
    for article in ad_articles:
        try:
            # 1. Title and Link
            link_tag = article.find('a', class_='job-card-link')
            if not link_tag: continue
            
            title = link_tag.get_text(strip=True)
            href = link_tag['href']
            
            # Ensure full URL
            if href.startswith("/"):
                full_link = f"https://www.finn.no{href}"
            else:
                full_link = href

            # Extract unique ID from URL for deduplication
            job_id = href.split('/')[-1]

            # 2. Employer / Company
            company_div = article.find('div', class_='text-caption')
            company = company_div.get_text(strip=True) if company_div else "Unknown"

            # 3. Location and Deadline (Inside footer pills)
            footer = article.find('footer')
            location = "Unknown"
            deadline_text = "Se annonse" # Default
            
            if footer:
                pills = footer.find_all('li')
                if len(pills) > 0:
                    location = pills[0].get_text(strip=True)
                # Sometimes the second pill is time posted, sometimes deadline. 
                # On search results, specific deadline is often not shown, just "2 days ago"
                # We will set a placeholder
            
            jobs.append({
                'ID': job_id,
                'Stillingstittel': title,
                'Arbeidsgiver': company,
                'Arbeidssted': location,
                'Lenke': full_link,
                'Fra dato': datetime.now().strftime("%d.%m.%Y"),
                'Søknadsfrist': deadline_text,
                'Kontaktperson': "", # Not available on search result page
                'Status': "Not searched" # Default status
            })
            
        except Exception as e:
            continue

    return jobs

def save_to_txt(all_jobs):
    """Saves jobs to a text file for Gemini."""
    with open(TXT_FILENAME, 'w', encoding='utf-8') as f:
        f.write("Here is a list of recent job postings. Please prioritize them based on relevance:\n\n")
        for job in all_jobs:
            f.write(f"Title: {job['Stillingstittel']}\n")
            f.write(f"Company: {job['Arbeidsgiver']}\n")
            f.write(f"Location: {job['Arbeidssted']}\n")
            f.write(f"Link: {job['Lenke']}\n")
            f.write("-" * 20 + "\n")
    print(f"✅ Text file created: {TXT_FILENAME}")

def save_to_excel(new_jobs):
    """Saves jobs to Excel with Dropdowns and Color Coding."""
    
    # 1. Load existing data if file exists to prevent duplicates
    if os.path.exists(EXCEL_FILENAME):
        try:
            existing_df = pd.read_excel(EXCEL_FILENAME)
            # Create a list of existing IDs
            existing_ids = existing_df['ID'].astype(str).tolist()
            
            # Filter out jobs that are already in the excel file
            unique_new_jobs = [job for job in new_jobs if str(job['ID']) not in existing_ids]
            
            if not unique_new_jobs:
                print("No new jobs to add to Excel.")
                return
            
            # Combine old and new
            new_df = pd.DataFrame(unique_new_jobs)
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        except Exception as e:
            print(f"Error reading existing Excel: {e}. Creating new one.")
            final_df = pd.DataFrame(new_jobs)
    else:
        final_df = pd.DataFrame(new_jobs)

    # 2. Write to Excel using XlsxWriter engine (required for formatting)
    writer = pd.ExcelWriter(EXCEL_FILENAME, engine='xlsxwriter')
    final_df.to_excel(writer, index=False, sheet_name='Jobb')
    
    workbook = writer.book
    worksheet = writer.sheets['Jobb']
    
    # 3. Define Formats (Colors)
    green_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}) # Accepted / Offer
    yellow_fmt = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'}) # Interviews
    blue_fmt = workbook.add_format({'bg_color': '#BDD7EE', 'font_color': '#000000'}) # Sent Application
    red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}) # Not searched (Default)

    # 4. Data Validation (Dropdown List)
    # Applying validation to the 'Status' column (Assumed to be the last column)
    status_col_index = final_df.columns.get_loc('Status')
    # Convert index to Excel letter (e.g., 8 -> 'I')
    status_col_letter = chr(65 + status_col_index) 
    
    row_count = len(final_df) + 1 # +1 for header
    
    worksheet.data_validation(f'{status_col_letter}2:{status_col_letter}{row_count+100}', {
        'validate': 'list',
        'source': STATUS_OPTIONS,
    })

    # 5. Conditional Formatting
    # Range of the status column
    status_range = f'{status_col_letter}2:{status_col_letter}{row_count+100}'

    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Not searched"', 'format': red_fmt})
    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Sent Application"', 'format': blue_fmt})
    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"1. Interview"', 'format': yellow_fmt})
    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"2. Interview"', 'format': yellow_fmt})
    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Offer"', 'format': green_fmt})
    worksheet.conditional_format(status_range, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Accepted"', 'format': green_fmt})

    # Adjust column widths for readability
    worksheet.set_column('A:A', 10) # ID
    worksheet.set_column('B:B', 40) # Title
    worksheet.set_column('C:C', 20) # Employer
    worksheet.set_column('E:E', 50) # Link
    worksheet.set_column('I:I', 20) # Status

    writer.close()
    print(f"✅ Excel file updated: {EXCEL_FILENAME}")

# --- Main Execution ---
if __name__ == "__main__":
    print("🚀 Starting Job Scraper...")
    all_found_jobs = []
    
    for query in SEARCH_QUERIES:
        print(f"Searching for: {query}")
        jobs = get_finn_jobs(query)
        all_found_jobs.extend(jobs)
    
    # Remove duplicates within the current search results (in case overlap between "Data Science" and "Data Engineer")
    # We use a dictionary keyed by ID to ensure uniqueness
    unique_jobs_dict = {job['ID']: job for job in all_found_jobs}
    unique_jobs_list = list(unique_jobs_dict.values())
    
    print(f"Found {len(unique_jobs_list)} unique jobs.")
    
    if unique_jobs_list:
        save_to_txt(unique_jobs_list)
        save_to_excel(unique_jobs_list)
        print("Done! You can now open the .xlsx file in LibreOffice or Excel.")
    else:
        print("No jobs found. Check your internet connection or search terms.")
