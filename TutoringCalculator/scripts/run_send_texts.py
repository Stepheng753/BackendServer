#!/usr/bin/env python3
"""
Cron Script 2: Run every Monday at 10:00 AM
Flow:
1. Determines target week dates (or accepts sheet_id from arguments).
2. Checks if sheet title contains CALCULATED. If so, stops (sheet pending approval).
3. If approved, sends SMS via Twilio to students with Total Balance > 0 and blank status.
4. Changes status to 'Need to Pay' and logs each text to text_messages.log.
"""

import os
import sys

# Ensure BackendServer root directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from TutoringCalculator.apis.google_auth import get_credentials
from TutoringCalculator.routes import calculate_billing_dates
from TutoringCalculator.apis.drive_sheets_api import (
    get_drive_service,
    get_or_create_year_folder,
    get_pending_text_recipients,
    update_sheet_pay_status
)
from TutoringCalculator.apis.calendar_api import parse_date_string
from TutoringCalculator.apis.twilio_api import send_sms


def find_current_week_sheet(creds, start_date_str, end_date_str):
    drive_service = get_drive_service(creds)
    start_date = parse_date_string(start_date_str)
    end_date = parse_date_string(end_date_str)
    year_folder_id = get_or_create_year_folder(drive_service, str(start_date.year))

    base_name = f"{start_date.strftime('%m.%d.%y')} - {end_date.strftime('%m.%d.%y')}"
    query = (
        f"name contains '{base_name}' and "
        f"mimeType='application/vnd.google-apps.spreadsheet' and "
        f"trashed=false and "
        f"'{year_folder_id}' in parents"
    )
    res = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = res.get('files', [])
    return files[0] if files else None


def main():
    print("--- Starting Send Texts Script ---")
    creds = get_credentials()
    if not creds:
        print("ERROR: Google credentials missing or expired.")
        sys.exit(1)

    sheet_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not sheet_id:
        dates = calculate_billing_dates()
        sheet_file = find_current_week_sheet(creds, dates['start_date'], dates['end_date'])
        if not sheet_file:
            print(f"No sheet found for week {dates['start_date']} - {dates['end_date']}.")
            sys.exit(0)
        sheet_id = sheet_file['id']
        print(f"Found sheet: {sheet_file['name']} (ID: {sheet_id})")

    pending_data = get_pending_text_recipients(creds, sheet_id)

    if pending_data.get('is_pending_review'):
        print(f"ABORTED: {pending_data.get('message')}")
        sys.exit(0)

    recipients = pending_data.get('recipients', [])
    if not recipients:
        print("No pending text recipients found. Exiting.")
        sys.exit(0)

    print(f"Found {len(recipients)} recipients to notify. Sending texts...")
    for rec in recipients:
        res = send_sms(to_phone=rec['phone'], message_body=rec['text'], student_name=rec['student'])
        print(f" -> {rec['student']} ({rec['phone']}): {res.get('status')}")

    print("Updating sheet pay statuses to 'Need to Pay'...")
    update_sheet_pay_status(creds, sheet_id)
    print("--- Send Texts Script Completed Successfully ---")


if __name__ == "__main__":
    main()
