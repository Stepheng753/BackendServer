#!/usr/bin/env python3
"""
Cron Script 1: Run every Monday at 4:00 AM
Flow:
1. Calculates previous Monday to Sunday date range.
2. Copies template sheet into year folder named 'MM.DD.YY - MM.DD.YY CALCULATED', setting C1 and D1.
3. Updates sheet hours from Google Calendar and rolls over previous unpaid balances.
4. Sends an email to stepheng753@gmail.com with links to review.
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
from TutoringCalculator.apis.calendar_api import calculate_tutoring_hours
from TutoringCalculator.apis.drive_sheets_api import (
    copy_template_sheet,
    get_previous_balances,
    update_sheet_hours_and_balances,
    get_sheet_details
)
from TutoringCalculator.apis.email_api import send_calculation_email


def main():
    print("--- Starting Tutoring Pay Calculation Script ---")
    creds = get_credentials()
    if not creds:
        print("ERROR: Google credentials missing or expired. Please visit /login_oauth to authorize.")
        sys.exit(1)

    dates = calculate_billing_dates()
    start_date = dates['start_date']
    end_date = dates['end_date']
    print(f"Target billing week: {start_date} - {end_date}")

    # 1. Copy Template
    print("Copying template sheet...")
    copy_res = copy_template_sheet(creds, start_date, end_date)
    sheet_id = copy_res['sheet_id']
    sheet_url = copy_res['sheet_url']
    year_folder_id = copy_res.get('year_folder_id')
    if not year_folder_id:
        sheet_meta = get_sheet_details(creds, sheet_id)
        year_folder_id = sheet_meta.get('parents', [''])[0]
    print(f"Created sheet: {copy_res.get('title')} (ID: {sheet_id})")

    # 2. Calculate Calendar Hours
    print("Calculating tutoring hours from calendar...")
    hours = calculate_tutoring_hours(creds, start_date, end_date)
    print(f"Hours calculated: {hours}")

    # 3. Retrieve Previous Balances
    print("Retrieving previous unpaid balances...")
    prev_balances = get_previous_balances(creds, start_date, end_date)
    print(f"Previous balances: {prev_balances}")

    # 4. Update Sheet
    print("Updating sheet with hours and remaining balances...")
    update_res = update_sheet_hours_and_balances(creds, sheet_id, hours, prev_balances)
    print(f"Updated {len(update_res.get('updated_students', []))} student records.")

    # 5. Send Notification Email
    print("Sending calculation email notification...")
    email_res = send_calculation_email(
        creds=creds,
        sheet_id=sheet_id,
        sheet_url=sheet_url,
        year_folder_id=year_folder_id,
        start_date_str=start_date,
        end_date_str=end_date,
        updated_students=update_res.get('updated_students'),
        total_balance=update_res.get('total_balance')
    )
    print(f"Total balance recorded: {update_res.get('total_balance')}")
    print(f"Email status: {email_res.get('status')}")
    print("--- Calculation Script Completed Successfully ---")


if __name__ == "__main__":
    main()
