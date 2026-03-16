import argparse
import sqlite3
import time
from datetime import datetime

import config
import database
import file_manager
import scraper

# Import filters
try:
    from rag import dumb_filter

    HAS_DUMB_FILTER = True
except ImportError:
    HAS_DUMB_FILTER = False
    print("⚠️ dumb_filter.py not found.")

try:
    from rag import ai_filter

    HAS_AI = True
except ImportError:
    HAS_AI = False
    print("⚠️ ai_filter.py not found.")


def is_not_expired(deadline_str):
    """Returns True if the deadline is still in the future or unparseable."""
    if not deadline_str:
        return True

    cleaned = deadline_str.strip().lower()
    # Skip non-date strings like "Se annonse", "Snarest", "N/A"
    if not cleaned[0].isdigit():
        return True

    try:
        # Handle both "15.3.2026" and "30.03.2026"
        parts = cleaned.split(".")
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        deadline = datetime(year, month, day)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return deadline >= today
    except (ValueError, IndexError):
        return True  # Can't parse, keep the job


def generate_reports(report_dumb=False):
    """
    Generates the Excel and Text files based on the requested strictness.
    """
    print("\n📝 Regenerating Excel and Text files...")

    # 1. Update Excel (Always contains everything for tracking)
    file_manager.save_to_excel(None)

    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()

    # 2. Select Jobs for Text File based on Flag
    if report_dumb:
        print(
            "   📂 Report Mode: DUMB FILTER (Showing all jobs that passed Basic Filter)"
        )
        # Get everything that was NOT discarded by the Basic filter.
        # This includes: 'Pending AI', 'Not searched' (Approved), and 'Discarded (AI)'
        cursor.execute("""
            SELECT title, employer, deadline, location, link, full_description, status 
            FROM scraped_jobs 
            WHERE status != 'Discarded (Basic)'
            ORDER BY status DESC, title ASC
        """)
    else:
        print("   📂 Report Mode: AI APPROVED (Showing only jobs approved by AI)")
        # Standard: Only show what the AI (or you) marked as "Not searched" (Approved)
        cursor.execute("""
            SELECT title, employer, deadline, location, link, full_description, status 
            FROM scraped_jobs 
            WHERE status = 'Not searched'
            ORDER BY title ASC
        """)

    candidates = cursor.fetchall()
    conn.close()

    if candidates:
        candidate_list = [
            {
                "Stillingstittel": r[0],
                "Arbeidsgiver": r[1],
                "Søknadsfrist": r[2],
                "Arbeidssted": r[3],
                "Lenke": r[4],
                "Full beskrivelse": r[5],
                "Status": r[6],
            }
            for r in candidates
            if is_not_expired(r[2])
        ]

        # Save to a specific filename so you don't overwrite the other one blindly
        filename = (
            "output/jobs_dumb_filtered.txt"
            if report_dumb
            else "output/gemini_context.txt"
        )

        file_manager.save_to_txt(candidate_list, filename=filename)
        print(f"✨ Done! {len(candidate_list)} jobs saved to: {filename}")
    else:
        print("✨ Done! No jobs found for this report criteria.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q", "--query", type=str, help="Scrape ONLY this specific query."
    )
    parser.add_argument("--sync", action="store_true", help="Sync Excel to DB.")

    # AI Control Flags
    parser.add_argument(
        "--local", action="store_true", help="Force local Ollama model (Batch Size 1)."
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI check and approve all pending jobs.",
    )

    # Reporting Flags
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Skip Scraper & AI. Just generate reports.",
    )
    parser.add_argument(
        "--report-dumb",
        action="store_true",
        help="Output file includes ALL jobs that passed Dumb Filter (ignores AI rejection).",
    )

    args = parser.parse_args()

    # 1. Setup
    database.setup_database()

    # If we are only regenerating, skip the heavy lifting
    if args.regenerate:
        generate_reports(report_dumb=args.report_dumb)
        return

    if args.sync:
        database.sync_excel_to_db()

    # 2. SCRAPING PHASE
    if args.query:
        search_list = [args.query]
    else:
        search_list = config.SEARCH_QUERIES

    processed_ids = database.get_existing_ids()

    if args.local:
        print("🏠 LOCAL MODE: Using Ollama (Batch Size: 1).")
    elif not args.no_ai:
        print("☁️ CLOUD MODE: Using Gemini (Batch Size: 10).")

    for query in search_list:
        links = scraper.get_job_links(query)
        new_links = [l for l in links if l.split("/")[-1] not in processed_ids]

        if not new_links:
            continue

        print(f"   - Found {len(new_links)} new jobs for '{query}'.")

        for i, link in enumerate(new_links):
            details = scraper.scrape_ad_details(link)
            if details:
                status = "Pending AI"
                if HAS_DUMB_FILTER:
                    is_ok, reason = dumb_filter.is_relevant_basic(
                        details["Stillingstittel"], details["Full beskrivelse"]
                    )
                    if not is_ok:
                        print(f"     ❌ Dumb Filter Reject: {reason}")
                        status = "Discarded (Basic)"
                    else:
                        print(f"     ✅ Dumb Filter Pass -> Pending AI")

                details["Status"] = status
                database.add_job_to_db(details)
                processed_ids.add(details["ID"])

    # 3. AI PROCESSING PHASE
    if args.no_ai:
        print("\n⚡ SKIPPING AI. Approving all 'Pending AI' jobs.")
        conn = sqlite3.connect(config.DB_FILENAME)
        conn.execute(
            "UPDATE scraped_jobs SET status = 'Not searched' WHERE status = 'Pending AI'"
        )
        conn.commit()
        conn.close()

    elif HAS_AI:
        conn = sqlite3.connect(config.DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ID, title, full_description, employer FROM scraped_jobs WHERE status = 'Pending AI'"
        )
        rows = cursor.fetchall()
        conn.close()

        jobs_to_check = [
            {
                "ID": str(r[0]),
                "Stillingstittel": r[1],
                "Full beskrivelse": r[2],
                "Arbeidsgiver": r[3],
            }
            for r in rows
        ]

        if jobs_to_check:
            BATCH_SIZE = 1 if args.local else 10
            print(
                f"🤖 Processing {len(jobs_to_check)} jobs in batches of {BATCH_SIZE}..."
            )

            for i in range(0, len(jobs_to_check), BATCH_SIZE):
                batch = jobs_to_check[i : i + BATCH_SIZE]

                ai_input = [
                    {
                        "id": str(job["ID"]),
                        "title": job["Stillingstittel"],
                        "employer": job["Arbeidsgiver"],
                        "description": job["Full beskrivelse"][:3000],
                    }
                    for job in batch
                ]

                ai_results = ai_filter.evaluate_batch(ai_input, force_local=args.local)

                conn = sqlite3.connect(config.DB_FILENAME)
                cursor = conn.cursor()

                for job in batch:
                    job_id = str(job["ID"])
                    # Default score is 0 if AI fails
                    default_result = {
                        "match": True,
                        "reason": "⚠️ FAIL-OPEN: AI Error",
                        "score": 0,
                    }
                    result = ai_results.get(job_id, default_result)

                    score = result.get("score", 0)  # <--- Extract Score

                    if result.get("match"):
                        new_status = "Not searched"
                        print(
                            f"      👍 Approved (Score: {score}): {job['Stillingstittel']}"
                        )
                    else:
                        new_status = "Discarded (AI)"
                        print(
                            f"      👎 Rejected (Score: {score}): {job['Stillingstittel']} ({result.get('reason')})"
                        )

                    # UPDATE QUERY INCLUDES SCORE
                    cursor.execute(
                        "UPDATE scraped_jobs SET status = ?, score = ? WHERE ID = ?",
                        (new_status, score, job_id),
                    )

                conn.commit()
                conn.close()

                if not args.local:
                    time.sleep(1)

    # 4. REPORT GENERATION (Uses the new function)
    generate_reports(report_dumb=args.report_dumb)


if __name__ == "__main__":
    main()
