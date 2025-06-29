from flask import request, jsonify
import csv
import gspread
from google.oauth2.service_account import Credentials
import pytz
import datetime


def get_field(data, key, default):
    value = data.get(key)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def title_case_name(name):
    return str(name).strip().title()


def capitalize_email(email):
    if not email or '@' not in email:
        return str(email).strip()
    local, domain = email.split('@', 1)
    domain = domain[0].upper() + domain[1:] if domain else domain
    return local.strip().capitalize() + '@' + domain.strip()


def rsvp():
    invitee_data = request.form

    timestamp = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime("%d/%m/%Y %I:%M:%S %p PST")
    accepted = True if int(get_field(invitee_data, 'accepted', '')) == 1 else False
    full_name = title_case_name(get_field(invitee_data, 'full-name', 'Not Provided'))
    email = capitalize_email(get_field(invitee_data, 'email', 'Not Provided'))
    phone = str(get_field(invitee_data, 'phone-num', 'Not Provided')).strip()
    notes = str(get_field(invitee_data, 'notes', 'Not Provided')).strip()
    wedding_type = get_field(invitee_data, 'wedding-type', 'Not Provided')
    num_guests = int(get_field(invitee_data, 'num-guests', 0))

    name_guests = [
        title_case_name(get_field(invitee_data, f'guest-{i+1}', f'Not Provided'))
        for i in range(num_guests)
    ]

    row_invitee_data = [
        timestamp, accepted, full_name, email, phone, notes, wedding_type, str(num_guests)
    ] + [g.strip() for g in name_guests]

    write_to_google_sheet(row_invitee_data)
    write_to_csv(row_invitee_data)

    return jsonify({'status': 'SUCCESS', 'message': 'RSVP received'})


def write_to_csv(row_invitee_data):
    csv_path = 'WeddingInvitations/rsvp.csv'
    full_name = row_invitee_data[2]
    rows = []
    found = False

    try:
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Case-insensitive comparison for full name
                if row and row[0].strip().lower() == full_name.strip().lower():
                    rows.append(row_invitee_data)
                    found = True
                else:
                    rows.append(row)
    except FileNotFoundError:
        pass

    # If not found, append new row
    if not found:
        rows.append(row_invitee_data)

    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def write_to_google_sheet(row_invitee_data):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("WeddingInvitations/credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = '17qk8MAatFAEq9wDXWM7WfIWhO6vNlRm3QgfGXhHPc_A'
    workbook = client.open_by_key(sheet_id)
    sheet = workbook.worksheet('API Calls')

    full_name = row_invitee_data[2]
    cell = None
    try:
        cell = next((c for c in sheet.findall(full_name) if c.value.strip().lower() == full_name.strip().lower()), None)
    except Exception:
        pass

    if cell:
        # Overwrite the entire row with new data
        row_number = cell.row
        sheet.update(f'A{row_number}', [row_invitee_data])
    else:
        sheet.append_row(row_invitee_data)