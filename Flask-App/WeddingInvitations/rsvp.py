from flask import request, jsonify
import csv
import gspread
from google.oauth2.service_account import Credentials
import pytz
import datetime
import re


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


def format_phone_number(phone):
    if phone == 'Not Provided':
        return phone

    phone = phone.strip()
    phone = re.sub(r'[()\-\s]', '', phone)
    if phone.startswith('+1'):
        digits = phone[2:]
        if len(digits) == 10:
            return f'+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}'
        else:
            return '+1' + digits
    elif phone.startswith('+84'):
        digits = phone[3:]
        if len(digits) == 9:
            return f'+84 {digits[:3]}-{digits[3:6]}-{digits[6:]}'
        else:
            return '+84' + digits
    elif phone.startswith('0'):
        digits = phone
        if len(digits) == 10:
            return f'{digits[:4]}-{digits[4:7]}-{digits[7:]}'
        else:
            return digits
    elif len(phone) == 10:
        return f'+1 ({phone[:3]}) {phone[3:6]}-{phone[6:]}'
    else:
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        return digits


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
        row_number = cell.row
        padded_row = row_invitee_data + [''] * (18 - len(row_invitee_data))
        sheet.update(f'A{row_number}:R{row_number}', [padded_row[:18]])
    else:
        sheet.append_row(row_invitee_data)


def rsvp_endpoint():
    invitee_data = request.form

    timestamp = datetime.datetime.now(pytz.timezone('US/Pacific')).strftime("%d/%m/%Y %I:%M:%S %p PST")
    accepted = True if int(get_field(invitee_data, 'accepted', '')) == 1 else False
    full_name = title_case_name(get_field(invitee_data, 'full-name', 'Not Provided'))
    email = capitalize_email(get_field(invitee_data, 'email', 'Not Provided'))
    phone = format_phone_number(get_field(invitee_data, 'phone-num', 'Not Provided'))
    notes = str(get_field(invitee_data, 'notes', 'Not Provided')).strip()
    wedding_type = get_field(invitee_data, 'wedding-type', '')
    num_guests = int(get_field(invitee_data, 'num-guests', 0)) if accepted else ''

    name_guests = []
    if type(num_guests) is int and num_guests >= 0:
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