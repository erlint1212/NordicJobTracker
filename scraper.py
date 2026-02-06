import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime
import config
import re

def get_job_links(query):
    formatted_query = query.replace(" ", "+")
    url = f"https://www.finn.no/job/search?q={formatted_query}"
    
    print(f"🔎 Searching for: {query}...")
    try:
        response = requests.get(url, headers=config.HEADERS)
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
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(url, headers=config.HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Defaults ---
        title = "Unknown Title"
        employer = "Unknown"
        deadline = "Se annonse"
        location = "Unknown"
        contact = ""
        phone = ""
        short_desc = ""
        full_description = ""

        # 1. Company Name
        # Usually found in the top section or metadata
        top_section = soup.find('section', class_='mt-16')
        if top_section:
            p_tag = top_section.find('p', class_='mb-24')
            if p_tag: employer = p_tag.get_text(strip=True)

        # 2. Key Info Extraction (Title, Location, Deadline, Contact)
        # Finn stores specific data in <ul> lists with class 'space-y-6' or inside grids
        
        # Strategy: Look through ALL list items on the page to find keys
        all_list_items = soup.find_all('li')
        
        found_specific_title = False
        
        for li in all_list_items:
            text = li.get_text(" ", strip=True) # Use space separator to avoid "Oslo0180"
            
            # Job Title (Stillingstittel)
            if "Stillingstittel" in text and not found_specific_title:
                # Remove the label to get just the value
                clean_title = text.replace("Stillingstittel", "").replace(":", "").strip()
                if clean_title:
                    title = clean_title
                    found_specific_title = True # Lock it so we don't overwrite
            
            # Deadline (Frist)
            if "Frist" in text:
                # Often "Frist 10.02.2026"
                clean_deadline = text.replace("Frist", "").replace(":", "").strip()
                if clean_deadline: deadline = clean_deadline

            # Location (Sted)
            if "Sted" in text:
                # Often "Sted Oslo" or "Sted Bedriftsveien 9, 0950 Oslo"
                clean_loc = text.replace("Sted", "").replace(":", "").strip()
                if clean_loc: location = clean_loc

            # Contact Person
            if "Kontaktperson" in text:
                clean_contact = text.replace("Kontaktperson", "").replace(":", "").strip()
                if clean_contact: contact = clean_contact

            # Phone (Mobil)
            if "Mobil" in text or "Telefon" in text:
                clean_phone = text.replace("Mobil", "").replace("Telefon", "").replace(":", "").strip()
                if clean_phone: phone = clean_phone

        # Fallback for Title: If we didn't find "Stillingstittel", use the H1 header
        if not found_specific_title:
            h1_tag = soup.find('h1', class_='t2')
            if h1_tag: title = h1_tag.get_text(strip=True)

        # 3. Description
        # The main body text is usually in a div with class 'import-decoration'
        desc_div = soup.find('div', class_='import-decoration')
        if desc_div:
            # get_text with separator ensures paragraphs don't merge into one blob
            full_description = desc_div.get_text(separator="\n", strip=True)
            # Remove excessive newlines
            full_description = re.sub(r'\n{3,}', '\n\n', full_description)
            
            # Create short description for Excel
            short_desc = full_description[:300].replace("\n", " ") + "..."

    job_id = url.split('/')[-1]

    # --- NEW: AI Filter Step ---
    ai_status = "Not searched" # Default
    
    # Only run AI if we have a description and the module loaded
    if HAS_AI and full_description:
        is_match, reason = ai_filter.evaluate_job(title, full_description)
        
        if not is_match:
            print(f"      🤖 Gemini rejected: {reason}")
            return None # Skip this job entirely!
        else:
            print(f"      🤖 Gemini approved: {reason}")

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
