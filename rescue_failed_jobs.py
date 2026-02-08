import sqlite3
import config

def rescue_failsafe_jobs():
    print("🚑 Rescuing jobs rejected by API Quota failure...")
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()

    # Find jobs rejected specifically because the AI crashed/timed out
    # We look for the specific error string we added in main.py
    cursor.execute("""
        SELECT count(*) FROM scraped_jobs 
        WHERE status = 'Discarded (AI)' 
        AND full_description LIKE '%FAIL-SAFE%' 
        OR status = 'Discarded (AI)' -- Let's just reset all recent AI discards to be safe
    """)
    
    # Actually, let's just reset ALL 'Discarded (AI)' jobs to 'Pending AI'.
    # Why? Because if the API was failing, we might have gotten bad rejections.
    # It is safer to re-run the local AI on all 150+ jobs to be sure.
    
    cursor.execute("""
        UPDATE scraped_jobs 
        SET status = 'Pending AI' 
        WHERE status = 'Discarded (AI)'
    """)
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Reset {count} jobs from 'Discarded (AI)' back to 'Pending AI'.")
    print("🚀 Run 'python main.py' now to process them with OLLAMA.")

if __name__ == "__main__":
    rescue_failsafe_jobs()
