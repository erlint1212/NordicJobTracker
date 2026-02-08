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
        time.sleep(random.uniform(0.01, 0.1))
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
        top_section = soup.find('section', class_='mt-16')
        if top_section:
            p_tag = top_section.find('p', class_='mb-24')
            if p_tag: employer = p_tag.get_text(strip=True)

        # 2. Key Info Extraction
        all_list_items = soup.find_all('li')
        found_specific_title = False
        
        for li in all_list_items:
            text = li.get_text(" ", strip=True) 
            
            # Job Title (Legacy method, kept as fallback/check)
            if "Stillingstittel" in text and not found_specific_title:
                clean_title = text.replace("Stillingstittel", "").replace(":", "").strip()
                if clean_title:
                    # We prioritize the h1 extraction below, but this can be a backup
                    pass 
            
            # Deadline
            if "Frist" in text:
                clean_deadline = text.replace("Frist", "").replace(":", "").strip()
                if clean_deadline: deadline = clean_deadline

            # Location
            if "Sted" in text:
                clean_loc = text.replace("Sted", "").replace(":", "").strip()
                if clean_loc: location = clean_loc

            # Contact Person
            if "Kontaktperson" in text:
                clean_contact = text.replace("Kontaktperson", "").replace(":", "").strip()
                if clean_contact: contact = clean_contact

            # Phone
            if "Mobil" in text or "Telefon" in text:
                clean_phone = text.replace("Mobil", "").replace("Telefon", "").replace(":", "").strip()
                if clean_phone: phone = clean_phone

        # --- IMPROVED TITLE EXTRACTION ---
        # 1. Try specific data-testid (most reliable for actual Job Title)
        h1_tag = soup.find('h1', attrs={'data-testid': 'object-title'})
        
        # 2. Fallback to standard class if testid is missing
        if not h1_tag:
            h1_tag = soup.find('h1', class_='u-t2')
            
        # 3. Last resort fallback
        if not h1_tag:
             h1_tag = soup.find('h1')

        if h1_tag:
            title = h1_tag.get_text(strip=True)

        # 3. Description
        desc_div = soup.find('div', class_='import-decoration')
        if desc_div:
            full_description = desc_div.get_text(separator="\n", strip=True)
            full_description = re.sub(r'\n{3,}', '\n\n', full_description)
            short_desc = full_description[:300].replace("\n", " ") + "..."

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
