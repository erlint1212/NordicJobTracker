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
    """Updates the Excel tracker. Rebuilds from DB if missing."""
    
    # 1. Determine the Base Data
    if not os.path.exists(config.EXCEL_FILENAME):
        print(f"⚠️ {config.EXCEL_FILENAME} not found. Rebuilding from Database...")
        existing_df = database.get_all_jobs_dataframe()
        print(f"   - Recovered {len(existing_df)} jobs from DB.")
    else:
        try:
            existing_df = pd.read_excel(config.EXCEL_FILENAME)
            if 'ID' in existing_df.columns:
                existing_df['ID'] = existing_df['ID'].astype(str)
            # Ensure columns match new config
            for col in config.COLUMNS:
                if col not in existing_df.columns:
                    existing_df[col] = ""
        except Exception as e:
            print(f"Error reading Excel: {e}. Starting fresh.")
            existing_df = pd.DataFrame(columns=config.COLUMNS)

    # 2. Filter New Jobs against Existing Data
    existing_ids = existing_df['ID'].tolist() if 'ID' in existing_df else []
    unique_jobs_list = [j for j in new_jobs if str(j['ID']) not in existing_ids]

    if not unique_jobs_list and os.path.exists(config.EXCEL_FILENAME):
        return

    # 3. Create DataFrame for new jobs
    if unique_jobs_list:
        excel_data = []
        for job in unique_jobs_list:
            # Only grab columns defined in config (ignores temp vars)
            row = {k: job.get(k, "") for k in config.COLUMNS}
            excel_data.append(row)
            
        new_df = pd.DataFrame(excel_data)
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        final_df = existing_df

    # 4. Write and Format using XlsxWriter
    writer = pd.ExcelWriter(config.EXCEL_FILENAME, engine='xlsxwriter')
    
    # Ensure only config columns are written
    final_df = final_df[config.COLUMNS]
    
    final_df.to_excel(writer, index=False, sheet_name='Tracker')
    
    workbook = writer.book
    worksheet = writer.sheets['Tracker']

    # --- Colors ---
    format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    format_blue = workbook.add_format({'bg_color': '#BDD7EE', 'font_color': '#000000'})
    format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
    format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    format_gray = workbook.add_format({'bg_color': '#E7E6E6', 'font_color': '#000000'})

    # Column Widths
    worksheet.set_column('A:A', 30) # Tittel
    worksheet.set_column('B:B', 12) # Fra dato
    worksheet.set_column('C:C', 15) # Frist
    worksheet.set_column('D:D', 25) # Arbeidsgiver
    worksheet.set_column('E:E', 20) # Kontaktperson
    worksheet.set_column('F:F', 15) # Mobil
    worksheet.set_column('G:G', 15) # Sted
    worksheet.set_column('H:H', 20) # Full Beskrivelse (Keep narrow, it's huge)
    worksheet.set_column('I:I', 40) # Lenke
    worksheet.set_column('J:J', 20) # Status
    worksheet.set_column('K:K', 0)  # Hide ID column

    # Dropdown on Status (Column J)
    status_col = 'J' # Changed from previous logic because column index shifted
    # Check column index just to be safe
    try:
        status_idx = config.COLUMNS.index('Status')
        import string
        status_col = string.ascii_uppercase[status_idx]
    except:
        pass

    data_len = len(final_df) + 100
    
    worksheet.data_validation(f'{status_col}2:{status_col}{data_len}', {
        'validate': 'list',
        'source': config.STATUS_OPTIONS
    })

    # Conditional Formatting
    range_str = f'{status_col}2:{status_col}{data_len}'
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Not searched"', 'format': format_red})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Sent Application"', 'format': format_blue})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"1. Interview"', 'format': format_yellow})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Offer"', 'format': format_green})
    worksheet.conditional_format(range_str, {'type': 'cell', 'criteria': 'equal_to', 'value': '"Rejected"', 'format': format_gray})

    writer.close()
    
    action = "Rebuilt" if not os.path.exists(config.EXCEL_FILENAME) and not unique_jobs_list else "Updated"
    print(f"✅ {action} {config.EXCEL_FILENAME} with {len(final_df)} total jobs.")
