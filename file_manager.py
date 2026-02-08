import pandas as pd
import sqlite3
import os
import config

def save_to_excel(ignored_argument=None):
    """
    Exports the database to Excel with specific formatting:
    1. Excludes 'Discarded (Basic)' jobs.
    2. Collapses (Groups) the long 'Full Description' column so it's readable.
    """
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    file_path = "data/job_application_tracker.xlsx"

    conn = sqlite3.connect(config.DB_FILENAME)

    # 1. FETCH DATA (Filtering out Dumb Filter Rejections)
    query = """
        SELECT 
            ID, 
            title AS Stillingstittel, 
            employer AS Arbeidsgiver, 
            status AS Status, 
            deadline AS Søknadsfrist, 
            location AS Arbeidssted, 
            link AS Lenke,
            full_description AS 'Full beskrivelse'
        FROM scraped_jobs 
        WHERE status != 'Discarded (Basic)'
        ORDER BY 
            CASE WHEN status = 'Not searched' THEN 1  -- Approved jobs first
                 WHEN status = 'Pending AI' THEN 2    -- Pending second
                 ELSE 3 END,                          -- Rejections last
            title ASC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("⚠️ No relevant jobs found to save.")
        return

    # 2. WRITE TO EXCEL WITH FORMATTING
    # We use 'xlsxwriter' engine to enable grouping/collapsing
    try:
        writer = pd.ExcelWriter(file_path, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Job Applications')

        workbook = writer.book
        worksheet = writer.sheets['Job Applications']

        # --- FORMATTING ---
        
        # Define formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        link_format = workbook.add_format({'font_color': 'blue', 'underline': True})
        
        # Apply Header Format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Set Column Widths (A=0, B=1, etc.)
        worksheet.set_column('A:A', 10)  # ID
        worksheet.set_column('B:B', 40)  # Title (Wider)
        worksheet.set_column('C:C', 25)  # Employer
        worksheet.set_column('D:D', 20)  # Status
        worksheet.set_column('E:E', 15)  # Deadline
        worksheet.set_column('F:F', 20)  # Location
        worksheet.set_column('G:G', 50)  # Link (Wide)

        # --- COLLAPSE THE DESCRIPTION COLUMN (H) ---
        # 'level': 1 adds it to a group. 'hidden': True hides it by default.
        # This creates a [+] button above/left of the column to expand it.
        worksheet.set_column('H:H', 20, None, {'level': 1, 'hidden': True})

        writer.close()
        print(f"✅ Saved clean Excel to {file_path} (Descriptions collapsed).")
        
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")

def save_to_txt(job_list, filename="output/jobs_for_gemini.txt"):
    """
    Saves a list of job dictionaries to a text file.
    """
    if not job_list:
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Generated Report: {filename}\n")
        f.write(f"Total Jobs: {len(job_list)}\n")
        f.write("==========================================================================\n\n")
        
        for i, job in enumerate(job_list):
            f.write(f"JOB TITLE: {job.get('Stillingstittel', 'N/A')}\n")
            f.write(f"COMPANY: {job.get('Arbeidsgiver', 'N/A')}\n")
            f.write(f"STATUS: {job.get('Status', 'Unknown')}\n")
            f.write(f"DEADLINE: {job.get('Søknadsfrist', 'N/A')}\n")
            f.write(f"LOCATION: {job.get('Arbeidssted', 'N/A')}\n")
            f.write(f"LINK: {job.get('Lenke', '#')}\n")
            f.write("DESCRIPTION:\n")
            # Limit description length in TXT for readability
            desc = job.get('Full beskrivelse', '') or ""
            f.write(f"{desc[:3000]}\n") 
            f.write("\n--------------------------------------------------------------------------\n\n")
    
    print(f"✅ Saved text report to {filename}")
