import sqlite3
import config

def reset_recent_jobs():
    """
    Resets jobs from 'Not searched' back to 'Pending AI' so the AI filter runs again.
    """
    print(f"🔧 Connecting to {config.DB_FILENAME}...")
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()

    # Optional: You can filter by date if you only want to reset today's mistakes
    # today = datetime.now().strftime("%Y-%m-%d")
    # query = "UPDATE scraped_jobs SET status = 'Pending AI' WHERE status = 'Not searched' AND date_added = ?"
    
    # Reset ALL "Not searched" jobs to "Pending AI"
    # This assumes "Not searched" means "Approved by AI but not applied to yet"
    print("🔄 Resetting 'Not searched' jobs back to 'Pending AI'...")
    
    cursor.execute("UPDATE scraped_jobs SET status = 'Pending AI' WHERE status = 'Not searched'")
    affected_rows = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully reset {affected_rows} jobs.")
    print("🚀 Now run 'python main.py' to re-process them with the new model.")

if __name__ == "__main__":
    reset_recent_jobs()
