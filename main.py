import argparse
import time
import config
import database
import scraper
import file_manager

# Import filters with error handling just in case
try:
    import dumb_filter
    HAS_DUMB_FILTER = True
except ImportError:
    HAS_DUMB_FILTER = False
    print("⚠️ dumb_filter.py not found. Skipping Stage 1 filtering.")

try:
    import ai_filter
    HAS_AI = True
except ImportError:
    HAS_AI = False
    print("⚠️ ai_filter.py not found or API key missing. Skipping Stage 2 filtering.")

def main():
    parser = argparse.ArgumentParser(description="Finn.no Job Scraper")
    parser.add_argument("-q", "--query", type=str, help="Scrape ONLY this specific query.")
    parser.add_argument("--sync", action="store_true", help="Read Excel file and update Database statuses before scraping.")
    args = parser.parse_args()

    # 1. Setup
    database.setup_database()

    # 2. Optional: Sync Excel changes back to DB
    if args.sync:
        print("📥 --sync flag detected. Importing manual changes from Excel to DB...")
        database.sync_excel_to_db()

    # 3. Determine Scope
    if args.query:
        print(f"🎯 TARGETED MODE: Searching only for '{args.query}'")
        search_list = [args.query]
    else:
        print("🚀 STANDARD MODE: Running all configured queries...")
        search_list = config.SEARCH_QUERIES

    processed_ids = database.get_existing_ids()
    print(f"💾 Database currently holds {len(processed_ids)} jobs.")

    # Buffers
    jobs_for_ai_review = []
    final_approved_jobs = []

    # 4. Search & Scrape Loop
    for query in search_list:
        links = scraper.get_job_links(query)
        
        # Filter duplicates
        new_links_for_query = []
        for link in links:
            job_id = link.split('/')[-1]
            if job_id not in processed_ids:
                new_links_for_query.append(link)
        
        if not new_links_for_query:
            print(f"   - No new jobs for '{query}' (all duplicates).")
            continue

        print(f"   - Found {len(new_links_for_query)} NEW jobs for '{query}'. Crawling...")

        for i, link in enumerate(new_links_for_query):
            print(f"     [{i+1}/{len(new_links_for_query)}]", end=" ")
            details = scraper.scrape_ad_details(link)
            
            if details:
                # --- STAGE 1: DUMB FILTER ---
                if HAS_DUMB_FILTER:
                    is_relevant, reason = dumb_filter.is_relevant_basic(
                        details['Stillingstittel'], 
                        details['Full beskrivelse']
                    )
                    
                    if not is_relevant:
                        print(f"❌ Discarded (Basic): {reason}")
                        details['Status'] = "Discarded (Basic)"
                        database.add_job_to_db(details)
                        processed_ids.add(details['ID'])
                        continue # Skip AI step
                    else:
                        print(f"✅ Passed Basic Filter")
                
                # If passed basic filter (or filter missing), queue for AI
                jobs_for_ai_review.append(details)

    # 5. Batch AI Processing (Stage 2)
    if HAS_AI and jobs_for_ai_review:
        BATCH_SIZE = 10
        print(f"\n🤖 Starting AI Batch Processing on {len(jobs_for_ai_review)} candidates...")
        
        for i in range(0, len(jobs_for_ai_review), BATCH_SIZE):
            batch = jobs_for_ai_review[i : i + BATCH_SIZE]
            print(f"   Processing batch {i//BATCH_SIZE + 1} ({len(batch)} jobs)...")
            
            # Prepare minimal data for AI to save tokens
            ai_input = [{
                'id': job['ID'],
                'title': job['Stillingstittel'],
                'description': job['Full beskrivelse'][:2000] 
            } for job in batch]
            
            # Call AI
            ai_results = ai_filter.evaluate_batch(ai_input)
            
            # Process Results
            for job in batch:
                job_id = job['ID']
                # Default to True if AI glitches, so we don't lose data
                result = ai_results.get(job_id, {"match": True, "reason": "AI Error/Default"})
                
                if result.get('match'):
                    job['Status'] = "Not searched" # Ready for manual review
                    final_approved_jobs.append(job)
                    print(f"      👍 Approved: {job['Stillingstittel']}")
                else:
                    job['Status'] = "Discarded (AI)"
                    print(f"      👎 Rejected: {job['Stillingstittel']} ({result.get('reason')})")
                
                # Save to DB
                database.add_job_to_db(job)
                processed_ids.add(job_id)
            
            time.sleep(2) # Be nice to API

    elif jobs_for_ai_review:
        # Fallback if no AI module found: Approve everything passed by dumb filter
        print("\n⚠️ AI module missing. Approving all jobs that passed basic filter.")
        for job in jobs_for_ai_review:
            job['Status'] = "Not searched"
            final_approved_jobs.append(job)
            database.add_job_to_db(job)
            processed_ids.add(job['ID'])

    # 6. Save to files
    # We always regenerate Excel from DB to keep it in sync
    file_manager.save_to_excel(final_approved_jobs)
    
    if final_approved_jobs:
        file_manager.save_to_txt(final_approved_jobs)
        print(f"\n✨ Done! Added {len(final_approved_jobs)} relevant jobs.")
    else:
        print("\n✨ Done! No new relevant jobs found.")

if __name__ == "__main__":
    main()
