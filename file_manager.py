import pandas as pd
import os
import config
import database

def save_to_txt(jobs):
    """Saves ONLY 'Not searched' jobs to text file."""
    
    relevant_jobs = [j for j in jobs if j.get('Status') == "Not searched"]
    
    if not relevant_jobs:
        return

    with open(config.TXT_FILENAME, 'w', encoding='utf-8') as f:
        f.write("I am looking for a job. Please analyze these NEW job postings and prioritize them.\n")
        f.write("==========================================================================\n\n")
        
        for job in relevant_jobs:
            f.write(f"JOB TITLE: {job['Stillingstittel']}\n")
            f.write(f"COMPANY: {job['Arbeidsgiver']}\n")
            f.write(f"DEADLINE: {job['Søknadsfrist']}\n")
            f.write(f"LOCATION: {job['Arbeidssted']}\n")
            f.write(f"LINK: {job['Lenke']}\n")
            f.write(f"DESCRIPTION:\n{job['Full beskrivelse']}\n")
            f.write("\n--------------------------------------------------------------------------\n\n")
    
    print(f"✅ Text file created at: {config.TXT_FILENAME} ({len(relevant_jobs)} jobs)")

def save_to_excel(new_jobs):
    """
    Regenerates the Excel tracker from the Database. 
    This avoids 'openpyxl' validation errors when reading existing formatted files.
    """
    
    # 1. Fetch EVERYTHING from the Database (Old + New)
    # The 'new_jobs' are already in the DB by the time this function is called in main.py
    df = database.get_all_jobs_dataframe()
    
    if df.empty:
        print("⚠️ Database is empty. Nothing to write to Excel.")
        return

    # 2. Write to Excel using XlsxWriter (Overwrites existing file)
    try:
        writer = pd.ExcelWriter(config.EXCEL_FILENAME, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Tracker')
        
        workbook = writer.book
        worksheet = writer.sheets['Tracker']

        # --- Colors ---
        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        format_blue = workbook.add_format({'bg_color': '#BDD7EE', 'font_color': '#000000'})
        format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
        format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})

        # Column Widths
        worksheet.set_column('A:A', 30) # Tittel
        worksheet.set_column('B:B', 12) # Fra dato
        worksheet.set_column('C:C', 15) # Frist
        worksheet.set_column('D:D', 25) # Arbeidsgiver
        worksheet.set_column('E:E', 20) # Kontaktperson
        worksheet.set_column('F:F', 15) # Mobil
        worksheet.set_column('G:G', 15) # Sted
        worksheet.set_column('H:H', 50) # Beskrivelse (Short)
        worksheet.set_column('I:I', 40) # Lenke
        worksheet.set_column('J:J', 20) # Status
        worksheet.set_column('K:K', 0)  # Hide ID column

        # Dropdown on Status (Column J)
        status_col = 'J'
        data_len = len(df) + 100
        
        worksheet.data_validation(f'{status_col}2:{status_col}{data_len}', {
            'validate': 'list',
            'source': config.STATUS_OPTIONS
        })

        # Conditional Formatting
        # Note: We must use specific criteria type 'cell' with 'criteria' and 'value'
        # The 'value' needs double quotes around the string for text comparison in Excel logic
        range_str = f'{status_col}2:{status_col}{data_len}'
        
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Not searched"', 'format': format_red})
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Sent Application"', 'format': format_blue})
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"1. Interview"', 'format': format_yellow})
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"2. Interview"', 'format': format_yellow})
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Offer"', 'format': format_green})
        worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Accepted"', 'format': format_green})

        writer.close()
        print(f"✅ Regenerated {config.EXCEL_FILENAME} from Database ({len(df)} jobs).")
        
    except Exception as e:
        print(f"❌ Failed to write Excel file: {e}")
