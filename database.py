import sqlite3
import pandas as pd
import os
from datetime import datetime
import config

def setup_database():
    """Creates the SQLite database with full history and description storage."""
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_jobs (
            ID TEXT PRIMARY KEY,
            title TEXT,
            employer TEXT,
            full_description TEXT,
            date_added TEXT,
            deadline TEXT,
            location TEXT,
            contact TEXT,
            phone TEXT,
            short_desc TEXT,
            link TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_existing_ids():
    """Fetches all Job IDs currently in the database."""
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT ID FROM scraped_jobs')
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()
    finally:
        conn.close()

def add_job_to_db(details):
    """Adds a newly scraped job dictionary to the database."""
    conn = sqlite3.connect(config.DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO scraped_jobs (
                ID, title, employer, full_description, date_added,
                deadline, location, contact, phone, short_desc, link, status
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            details['ID'], 
            details['Stillingstittel'], 
            details['Arbeidsgiver'], 
            details['Full beskrivelse'], 
            datetime.now().strftime("%Y-%m-%d"),
            details['Søknadsfrist'],
            details['Arbeidssted'],
            details['Kontaktperson'],
            details['Mobil'],
            details['Kort beskrivelse'],
            details['Lenke'],
            details['Status']
        ))
        conn.commit()
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
    finally:
        conn.close()

def get_all_jobs_dataframe():
    """Reads all jobs from the database for Excel reconstruction."""
    conn = sqlite3.connect(config.DB_FILENAME)
    try:
        query = '''
            SELECT 
                title as Stillingstittel,
                date_added as "Fra dato",
                deadline as Søknadsfrist,
                employer as Arbeidsgiver,
                contact as Kontaktperson,
                phone as Mobil,
                location as Arbeidssted,
                short_desc as "Kort beskrivelse",
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
        df = pd.read_excel(config.EXCEL_FILENAME)
        # Ensure ID column exists
        if 'ID' not in df.columns:
            return

        conn = sqlite3.connect(config.DB_FILENAME)
        cursor = conn.cursor()
        count = 0
        
        for _, row in df.iterrows():
            job_id = str(row.get('ID', ''))
            
            # Insert logic matching the schema, filling missing data with defaults
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
                "", # Description usually blank in excel import
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
