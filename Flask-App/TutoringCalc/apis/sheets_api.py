from googleapiclient.discovery import build


def get_sheets_service(creds):
    """Builds and returns the Google Sheets service."""
    return build('sheets', 'v4', credentials=creds)


def update_sheet_hours(sheets_service, spreadsheet_id, events_by_title, start_date_frmtd, end_date_frmtd):
    """Updates sheet with tutoring hours and date range."""
    NAME_COL = 'C'
    HOURS_COL = 'D'
    TUTOR_COL = 'G'
    NAME_COL_IDX = ord(NAME_COL) - ord('A')
    TUTOR_COL_IDX = ord(TUTOR_COL) - ord('A')

    date_range_update = {
        'range': f'{NAME_COL}1:{HOURS_COL}1',
        'values': [[start_date_frmtd, end_date_frmtd]]
    }

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=date_range_update['range'],
        valueInputOption='RAW',
        body=date_range_update
    ).execute()

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f'A:{TUTOR_COL}'
    ).execute()
    rows = result['values']

    updates = []
    for row_idx, row in enumerate(rows, start=0):
        row_num = row_idx + 1
        if len(row) < 1:
            continue

        sheet_student_name = row[NAME_COL_IDX] if len(row) > NAME_COL_IDX else None
        sheet_tutor_name = row[TUTOR_COL_IDX] if len(row) > TUTOR_COL_IDX else None
        if (isinstance(sheet_student_name, str) and len(sheet_student_name) > 0 and sheet_student_name != 'Student' and
                isinstance(sheet_tutor_name, str) and len(sheet_tutor_name) > 0 and sheet_tutor_name != 'Tutor'):
            student_found = False
            total_hrs = 0
            for tutor_name, tutor_summary in events_by_title.items():
                for title, data in tutor_summary.items():
                    student_name = title.split()[0]
                    student_found = student_name.lower() in sheet_student_name.lower() and \
                        tutor_name.lower() in sheet_tutor_name.lower()
                    if student_found:
                        total_hrs = data['total_hrs']
                        break
                if student_found:
                    break

            updates.append({
                'range': f'{HOURS_COL}{row_num}',
                'values': [[total_hrs]]
            })

    if updates:
        for update in updates:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=update['range'],
                valueInputOption='RAW',
                body={'values': update['values']}
            ).execute()
