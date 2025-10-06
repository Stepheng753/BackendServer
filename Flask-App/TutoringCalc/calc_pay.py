from flask import request, jsonify
from .apis.auth_api import *
from .apis.calendar_api import *
from .apis.drive_api import *
from .apis.sheets_api import *
from .apis.helpers import *


def calc_tutoring_pay(search_date=None):
    creds = get_credentials()
    time_min, time_max, start_date, end_date = get_time_range(search_date)
    start_date_frmtd = start_date.strftime(DATE_FORMAT)
    end_date_frmtd = end_date.strftime(DATE_FORMAT)

    calendar_service = get_calendar_service(creds)
    calendar_events_summary = get_full_summary(
        calendar_service,
        time_min,
        time_max,
        start_date_frmtd,
        end_date_frmtd
    )

    drive_service = get_drive_service(creds)
    student_pay_file_id = get_file_id(drive_service, 'Student Pay')
    year_pay_file_id = get_file_id(drive_service, '2025')
    new_pay_file_name = f'{start_date_frmtd} - {end_date_frmtd} GEN'
    new_pay_file = copy_file(
        drive_service,
        student_pay_file_id,
        new_pay_file_name,
        year_pay_file_id
    )
    new_pay_file_id = new_pay_file['id']

    sheets_service = get_sheets_service(creds)
    update_sheet_hours(sheets_service, new_pay_file_id, calendar_events_summary, start_date_frmtd, end_date_frmtd)


def calc_tutoring_pay_endpoint():
    creds = get_credentials()
    if not creds:
        return login_oauth('calc_tutoring_pay')

    search_date = request.args.get('search_date')
    try:
        calc_tutoring_pay(search_date)
        return jsonify({"status": "success", "message": "Tutoring pay calculated successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500