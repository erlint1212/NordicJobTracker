# clean_db.py
import sqlite3
import rag.dumb_filter
import config

def clean_database():
    print("🧹 Cleaning database with updated Dumb Filter rules...")
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()

    # Fetch jobs that are seemingly "active"
    cursor.execute("SELECT ID, title, full_description FROM scraped_jobs WHERE status IN ('Not searched', 'Pending AI')")
    rows = cursor.fetchall()
    
    discard_count = 0
    reset_count = 0

    for r in rows:
        job_id, title, desc = r[0], r[1], r[2]
        
        # Run Updated Dumb Filter
        is_relevant, reason = dumb_filter.is_relevant_basic(title, desc or "")
        
        if not is_relevant:
            # Kill it
            cursor.execute("UPDATE scraped_jobs SET status = 'Discarded (Basic)' WHERE ID = ?", (job_id,))
            print(f"❌ Retroactively Discarded: {title}")
            discard_count += 1
        else:
            # Reset it for AI check
            cursor.execute("UPDATE scraped_jobs SET status = 'Pending AI' WHERE ID = ?", (job_id,))
            reset_count += 1
            
    conn.commit()
    conn.close()
    print(f"\nSummary: Discarded {discard_count} bad jobs. Reset {reset_count} jobs for AI re-evaluation.")

if __name__ == "__main__":
    clean_database()
