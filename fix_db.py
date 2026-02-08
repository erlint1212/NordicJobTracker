import sqlite3
import config

def nuclear_cleanup():
    print("☢️  Starting cleanup of bad scraper data...")
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()
    
    # 1. Delete jobs with obviously wrong titles (caused by scraper bug)
    bad_titles = ['CTO', 'CEO', 'COO', 'Partner', 'Unknown Title', 'Department Head']
    placeholders = ', '.join(['?'] * len(bad_titles))
    
    cursor.execute(f"SELECT count(*) FROM scraped_jobs WHERE title IN ({placeholders})", bad_titles)
    count = cursor.fetchone()[0]
    
    cursor.execute(f"DELETE FROM scraped_jobs WHERE title IN ({placeholders})", bad_titles)
    print(f"🗑️  Deleted {count} rows with titles: {bad_titles}")

    # 2. Reset "Pending AI" jobs to be re-checked by the Dumb Filter
    # (In case you improved the dumb filter and want to re-run it on everything)
    cursor.execute("UPDATE scraped_jobs SET status = 'Pending AI' WHERE status = 'Discarded (AI)'")
    
    conn.commit()
    conn.close()
    print("✅ Cleanup complete. Now run 'python main.py' to re-scrape correctly.")

if __name__ == "__main__":
    nuclear_cleanup()
