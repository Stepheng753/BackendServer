from flask import request, jsonify
import csv

def get_field(data, key, default):
    value = data.get(key)
    if value is None or str(value).strip() == "":
        return default
    return value

def rsvp():
    invitee_data = request.form

    full_name = get_field(invitee_data, 'full-name', 'Full Name Not Provided')
    email = get_field(invitee_data, 'email', 'Email Not Provided')
    phone = get_field(invitee_data, 'phone-num', 'Phone Number Not Provided')
    notes = get_field(invitee_data, 'notes', 'No Notes Provided')

    try:
        num_guests = int(get_field(invitee_data, 'num-guests', 0))
    except ValueError:
        num_guests = 0

    name_guests = [
        get_field(invitee_data, f'guest-{i+1}', f'Guest {i+1} Not Provided')
        for i in range(num_guests)
    ]

    row_invitee_data = [
        full_name, email, phone, notes, str(num_guests)
    ] + name_guests

    with open('WeddingInvitations/rsvp.csv', 'a+', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row_invitee_data)

    return jsonify({'status': 'SUCCESS', 'message': 'RSVP received'})