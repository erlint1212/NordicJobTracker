import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime
import config

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

        # Defaults
        title = "Unknown Title"
        employer = "Unknown"
        deadline = "Se annonse"
        location = "Unknown"
        contact = ""
        phone = ""
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

        # 6. Description (Full only)
        desc_div = soup.find('div', class_='import-decoration')
        if desc_div:
            full_description = desc_div.get_text(separator="\n", strip=True)

        job_id = url.split('/')[-1]

        return {
            'Stillingstittel': title,
            'Fra dato': datetime.now().strftime("%d.%m.%Y"),
            'Søknadsfrist': deadline,
            'Arbeidsgiver': employer,
            'Kontaktperson': contact,
            'Mobil': phone,
            'Arbeidssted': location,
            'Full beskrivelse': full_description,
            'Lenke': url,
            'Status': "Not searched",
            'ID': job_id
        }

    except Exception as e:
        print(f"❌ Error scraping ad {url}: {e}")
        return None
