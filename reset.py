import sqlite3
import config

def reset_approved_jobs():
    print("🔄 Resetting ALL 'Not searched' (Approved) jobs to 'Pending AI'...")
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()
    
    # Reset them so the AI checks them again
    cursor.execute("UPDATE scraped_jobs SET status = 'Pending AI' WHERE status = 'Not searched'")
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"✅ Reset {count} jobs. Now run 'python main.py --local' to filter them properly.")

if __name__ == "__main__":
    reset_approved_jobs()
