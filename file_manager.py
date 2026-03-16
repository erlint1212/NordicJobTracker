import os
import sqlite3
from datetime import datetime

import pandas as pd

import config


def _is_not_expired(deadline_str):
    """
    Returns True if the job deadline is today or in the future.
    Returns True for unparseable values (Snarest, ASAP, Se annonse, etc.)
    so we don't accidentally drop jobs with unknown deadlines.
    """
    if not deadline_str:
        return True

    cleaned = deadline_str.strip()

    # Skip non-date strings like "Snarest", "ASAP", "Se annonse", ""
    if not cleaned or not cleaned[0].isdigit():
        return True

    try:
        # Handles both "8.3.2026" and "08.03.2026"
        parts = cleaned.split(".")
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        deadline_date = datetime(year, month, day).date()
        today = datetime.now().date()
        return deadline_date >= today
    except (ValueError, IndexError):
        return True


def save_to_excel(ignored_argument=None):
    """
    Exports to Excel in DARK MODE with Dropdowns and Scores.
    """
    os.makedirs("data", exist_ok=True)
    file_path = "data/job_application_tracker.xlsx"

    conn = sqlite3.connect(config.DB_FILENAME)

    # Fetch Data including SCORE
    query = """
        SELECT 
            ID, 
            score AS Score,  -- <--- Added Score
            title AS Stillingstittel, 
            employer AS Arbeidsgiver, 
            status AS Status, 
            called as 'Har ringt',
            deadline AS Søknadsfrist, 
            location AS Arbeidssted, 
            contact as Kontaktperson,
            phone as Mobil,
            link AS Lenke
        FROM scraped_jobs 
        WHERE status != 'Discarded (Basic)'
        ORDER BY 
            CASE WHEN status = 'Not searched' THEN 1 ELSE 2 END, 
            score DESC,   -- <--- Sort by Score (High to Low)
            title ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("⚠️ No relevant jobs found to save.")
        return

    # Fill NaNs
    df["Har ringt"] = df["Har ringt"].fillna("Nei")
    df["Score"] = df["Score"].fillna(0)

    try:
        writer = pd.ExcelWriter(file_path, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Job Applications")

        workbook = writer.book
        worksheet = writer.sheets["Job Applications"]

        # --- DARK MODE STYLES ---
        # Background: Dark Grey (#262626), Text: Light Gray (#E0E0E0)
        dark_bg = "#262626"
        light_text = "#E0E0E0"

        # Base Format (Applied to everything)
        base_format = workbook.add_format(
            {
                "bg_color": dark_bg,
                "font_color": light_text,
                "border": 1,
                "border_color": "#404040",
            }
        )

        # Header Format (Slightly lighter, Bold)
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#404040", "font_color": "#FFFFFF", "border": 1}
        )

        # Score Format (Center align, Bold for emphasis)
        score_format = workbook.add_format(
            {
                "bg_color": dark_bg,
                "font_color": "#FFD700",  # Gold color for the score
                "bold": True,
                "align": "center",
                "border": 1,
                "border_color": "#404040",
            }
        )

        # "Yes" Format (Pleasant Green Text for positive action)
        # We can't conditionally format easily without write_row,
        # so we stick to the dark theme for the cell, but the user selects from dropdown.

        # --- APPLY FORMATTING ---

        # 1. Apply Base Format to all data cells
        for row in range(1, len(df) + 1):
            worksheet.set_row(row, None, base_format)

        # 2. Write Headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # 3. Set Column Widths & Specific Formats
        worksheet.set_column("A:A", 5, base_format)  # ID
        worksheet.set_column("B:B", 8, score_format)  # Score (Gold text)
        worksheet.set_column("C:C", 35, base_format)  # Title
        worksheet.set_column("D:D", 20, base_format)  # Employer
        worksheet.set_column("E:E", 15, base_format)  # Status
        worksheet.set_column("F:F", 12, base_format)  # Har ringt
        worksheet.set_column("G:G", 15, base_format)  # Deadline
        worksheet.set_column("H:H", 15, base_format)  # Location
        worksheet.set_column("I:I", 20, base_format)  # Kontakt
        worksheet.set_column("J:J", 12, base_format)  # Mobil
        worksheet.set_column("K:K", 10, base_format)  # Link

        # --- DROPDOWN FOR 'HAR RINGT' ---
        end_row = len(df) + 1
        worksheet.data_validation(
            f"F2:F{end_row}",
            {  # Note: Column F is now 'Har ringt' because Score inserted at B
                "validate": "list",
                "source": ["Ja", "Nei", "Svarte ikke"],
                "input_title": "Status",
                "input_message": "Did you call?",
            },
        )

        writer.close()
        print(f"✅ Saved Dark Mode Excel with Scores to {file_path}")

    except Exception as e:
        print(f"❌ Error saving Excel: {e}")


def save_to_txt(job_list, filename="output/jobs_for_gemini.txt"):
    """
    Saves a list of job dictionaries to a text file.
    """
    # Filter out jobs with expired deadlines
    job_list = [job for job in job_list if _is_not_expired(job.get("Søknadsfrist", ""))]

    if not job_list:
        print("⚠️ All jobs have expired deadlines. No text file generated.")
        return

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Generated Report: {filename}\n")
        f.write(f"Total Jobs: {len(job_list)}\n")
        f.write(
            "==========================================================================\n\n"
        )

        for i, job in enumerate(job_list):
            f.write(f"JOB TITLE: {job.get('Stillingstittel', 'N/A')}\n")
            f.write(f"COMPANY: {job.get('Arbeidsgiver', 'N/A')}\n")
            f.write(f"STATUS: {job.get('Status', 'Unknown')}\n")
            f.write(f"DEADLINE: {job.get('Søknadsfrist', 'N/A')}\n")
            f.write(f"LOCATION: {job.get('Arbeidssted', 'N/A')}\n")
            f.write(f"LINK: {job.get('Lenke', '#')}\n")
            f.write("DESCRIPTION:\n")
            # Limit description length in TXT for readability
            desc = job.get("Full beskrivelse", "") or ""
            f.write(f"{desc[:3000]}\n")
            f.write(
                "\n--------------------------------------------------------------------------\n\n"
            )

    print(f"✅ Saved text report to {filename}")
