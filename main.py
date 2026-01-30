import config
import database
import scraper
import file_manager

def main():
    print("🚀 Starting Advanced Job Crawler...")
    
    # 1. Setup Data/Output folders and DB
    database.setup_database()
    database.sync_excel_to_db()
    
    # 2. Get currently processed IDs (The "Brain")
    processed_ids = database.get_existing_ids()
    print(f"💾 Database currently holds {len(processed_ids)} jobs.")

    # We will accumulate all new jobs here to write to Excel/TXT once at the end
    all_newly_scraped_jobs = []

    # 3. Loop through queries and update DB continuously
    for query in config.SEARCH_QUERIES:
        links = scraper.get_job_links(query)
        
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
            details = scraper.scrape_ad_details(link)
            
            if details:
                # Add to master list for file saving
                all_newly_scraped_jobs.append(details)
                
                # IMPORTANT: Update DB and Memory IMMEDIATELY
                database.add_job_to_db(details)
                processed_ids.add(details['ID']) 

    # 4. Save to files (only if we actually found something)
    # We call save_to_excel regardless of whether we found new jobs, 
    # just in case the file was deleted and needs rebuilding from DB.
    file_manager.save_to_excel(all_newly_scraped_jobs)
    
    if all_newly_scraped_jobs:
        file_manager.save_to_txt(all_newly_scraped_jobs)
        print("\n✨ Done! Files updated.")
    else:
        print("\n✨ Done! No new jobs found on web, but Excel check complete.")

if __name__ == "__main__":
    main()
