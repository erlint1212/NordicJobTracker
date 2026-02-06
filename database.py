import sqlite3
import pandas as pd
import os
from datetime import datetime
import config

def get_db_connection():
    return sqlite3.connect(config.DB_FILENAME)

def setup_database():
    """Checks schema and runs migration if necessary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scraped_jobs'")
    if not cursor.fetchone():
        _create_new_table(cursor)
        print("✅ Database created with Typed Schema (Int, Date, Text).")
    else:
        # Check if we need to migrate. 
        # We check if ID is of type "TEXT" (Old) vs "INTEGER" (New)
        cursor.execute("PRAGMA table_info(scraped_jobs)")
        columns_info = cursor.fetchall()
        
        # columns_info structure: (cid, name, type, notnull, dflt_value, pk)
        id_type = next((col[2] for col in columns_info if col[1] == 'ID'), 'TEXT')
        col_names = [col[1] for col in columns_info]

        if id_type == 'TEXT' or 'short_desc' in col_names:
            print("⚠️ Old schema detected (Text IDs or Short Desc). Migrating to Typed Schema...")
            _migrate_schema(conn, cursor)
        else:
            print("✅ Database schema is up to date.")

    conn.commit()
    conn.close()

def _create_new_table(cursor):
    """Creates the clean table with specific types."""
    cursor.execute('''
        CREATE TABLE scraped_jobs (
            ID INTEGER PRIMARY KEY,
            title TEXT,
            employer TEXT,
            full_description TEXT,
            date_added DATE,
            deadline TEXT,
            location TEXT,
            contact TEXT,
            phone TEXT,
            link TEXT,
            status TEXT
        )
    ''')

def _migrate_schema(conn, cursor):
    """
    Refactors the database to use INTEGER IDs and removes short_desc.
    """
    try:
        # 1. Rename old table
        conn.execute("ALTER TABLE scraped_jobs RENAME TO scraped_jobs_old")
        
        # 2. Create new table with proper types
        _create_new_table(cursor)
        
        # 3. Copy data over. 
        # SQLite is flexible; it will try to cast the TEXT ID to INTEGER automatically.
        cursor.execute('''
            INSERT INTO scraped_jobs (ID, title, employer, full_description, date_added, deadline, location, contact, phone, link, status)
            SELECT 
                CAST(ID AS INTEGER), 
                title, 
                employer, 
                full_description, 
                date_added, 
                deadline, 
                location, 
                contact, 
                phone, 
                link, 
                status
            FROM scraped_jobs_old
        ''')
        
        # 4. Drop old table
        conn.execute("DROP TABLE scraped_jobs_old")
        print("✅ Migration successful: IDs converted to INTEGER, Schema cleaned.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Restoring might require manual intervention.")

def cleanup_expired_jobs():
    """
    Deletes jobs that are:
    1. EXPIRED (Deadline < Today)
    2. AND Status is 'Not searched'
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT ID, deadline, status FROM scraped_jobs")
        jobs = cursor.fetchall()
        
        ids_to_delete = []
        today = datetime.now()
        
        for job_id, deadline_str, status in jobs:
            if status != "Not searched":
                continue
                
            try:
                # Handle "Se annonse", "Snarest" etc.
                if not deadline_str or not any(char.isdigit() for char in deadline_str):
                    continue 
                
                # Try parsing standard Norwegian format dd.mm.yyyy
                deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y")
                
                if deadline_date < today:
                    ids_to_delete.append(job_id)
            except ValueError:
                continue
        
        if ids_to_delete:
            print(f"🧹 Cleaning up {len(ids_to_delete)} expired jobs...")
            cursor.executemany("DELETE FROM scraped_jobs WHERE ID=?", [(i,) for i in ids_to_delete])
            conn.commit()
            print("✅ Cleanup complete.")
            
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")
    finally:
        conn.close()

def get_existing_ids():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ID FROM scraped_jobs')
        rows = cursor.fetchall()
        # Return as strings for comparison with scraper, even though DB is int
        return {str(row[0]) for row in rows}
    finally:
        conn.close()

def add_job_to_db(details):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure date_added is stored as ISO YYYY-MM-DD for the DATE column
    # The scraper gives us strings, so we re-generate or parse.
    iso_date = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO scraped_jobs (
                ID, title, employer, full_description, date_added,
                deadline, location, contact, phone, link, status
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(details['ID']),  # Force Integer
            details['Stillingstittel'], 
            details['Arbeidsgiver'], 
            details['Full beskrivelse'], 
            iso_date,
            details['Søknadsfrist'],
            details['Arbeidssted'],
            details['Kontaktperson'],
            details['Mobil'],
            details['Lenke'],
            details['Status']
        ))
        conn.commit()
    except Exception as e:
        print(f"⚠️ DB Insert Error: {e}")
    finally:
        conn.close()

def get_all_jobs_dataframe():
    conn = get_db_connection()
    try:
        # We assume date_added is YYYY-MM-DD in DB, but we might want dd.mm.yyyy for Excel?
        # For now, we pull it raw.
        query = '''
            SELECT 
                title as Stillingstittel,
                date_added as "Fra dato",
                deadline as Søknadsfrist,
                employer as Arbeidsgiver,
                contact as Kontaktperson,
                phone as Mobil,
                location as Arbeidssted,
                full_description as "Full beskrivelse",
                link as Lenke,
                status as Status,
                ID
            FROM scraped_jobs
        '''
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"⚠️ Error reading from DB: {e}")
        return pd.DataFrame(columns=config.COLUMNS)
    finally:
        conn.close()

def sync_excel_to_db():
    """Syncs existing Excel rows to Database to prevent re-scraping old jobs."""
    if not os.path.exists(config.EXCEL_FILENAME):
        return

    print("🔄 Syncing existing Excel rows to Database...")
    try:
        # FIX: Read strictly as data, no formatting parsing if possible
        # We catch the specific Value error just in case
        try:
            df = pd.read_excel(config.EXCEL_FILENAME, engine='openpyxl')
        except ValueError:
            # If openpyxl fails on formatting, we try a fallback or just pass
            # There is no easy way to force openpyxl to ignore broken validation on read
            # except by fixing the file or catching the error.
            print("   - Warning: Could not parse Excel formatting. Skipping sync (Database should be source of truth).")
            return

        if 'ID' not in df.columns:
            return

        conn = sqlite3.connect(config.DB_FILENAME)
        cursor = conn.cursor()
        count = 0
        
        for _, row in df.iterrows():
            job_id = str(row.get('ID', ''))
            
            cursor.execute('''
                INSERT OR IGNORE INTO scraped_jobs (
                    ID, title, employer, full_description, date_added,
                    deadline, location, contact, phone, short_desc, link, status
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, 
                row.get('Stillingstittel', 'Imported'),
                row.get('Arbeidsgiver', 'Unknown'),
                "", 
                row.get('Fra dato', datetime.now().strftime("%Y-%m-%d")),
                row.get('Søknadsfrist', ''),
                row.get('Arbeidssted', ''),
                row.get('Kontaktperson', ''),
                row.get('Mobil', ''),
                row.get('Kort beskrivelse', ''),
                row.get('Lenke', ''),
                row.get('Status', 'Not searched')
            ))
            
            if cursor.rowcount > 0:
                count += 1
        
        conn.commit()
        conn.close()
        if count > 0:
            print(f"   - Imported {count} existing jobs from Excel to DB.")
            
    except Exception as e:
        print(f"   - Warning: Could not sync Excel to DB: {e}")
