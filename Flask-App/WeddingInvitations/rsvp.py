from flask import request, jsonify
import csv
import gspread
from google.oauth2.service_account import Credentials
scopes = ["https://www.googleapis.com/auth/spreadsheets"]

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

    full_name = title_case_name(get_field(invitee_data, 'full-name', 'Full Name Not Provided'))
    email = capitalize_email(get_field(invitee_data, 'email', 'Email Not Provided'))
    phone = str(get_field(invitee_data, 'phone-num', 'Phone Number Not Provided')).strip()
    notes = str(get_field(invitee_data, 'notes', 'No Notes Provided')).strip()

    try:
        num_guests = int(get_field(invitee_data, 'num-guests', 0))
    except ValueError:
        num_guests = 0

    name_guests = [
        title_case_name(get_field(invitee_data, f'guest-{i+1}', f'Guest {i+1} Not Provided'))
        for i in range(num_guests)
    ]

    row_invitee_data = [
        full_name, email, phone, notes, str(num_guests)
    ] + [g.strip() for g in name_guests]

    write_to_google_sheet(row_invitee_data)
    write_to_csv(row_invitee_data)

    return jsonify({'status': 'SUCCESS', 'message': 'RSVP received'})


def write_to_csv(row_invitee_data):
    csv_path = 'WeddingInvitations/rsvp.csv'
    full_name = row_invitee_data[0]
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
    creds = Credentials.from_service_account_file("WeddingInvitations/credentials.json", scopes=scopes)
    client = gspread.authorize(creds)

    sheet_id = '17qk8MAatFAEq9wDXWM7WfIWhO6vNlRm3QgfGXhHPc_A'
    workbook = client.open_by_key(sheet_id)
    sheet = workbook.worksheet('API Calls')

    full_name = row_invitee_data[0]
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