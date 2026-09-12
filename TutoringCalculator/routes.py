import datetime
from flask import Blueprint, request, jsonify, redirect, url_for, Response
from .config import PST, NOTIFICATION_EMAIL
from .apis.google_auth import (
    get_credentials,
    initiate_oauth_flow,
    process_oauth_callback,
    get_redirect_uri
)
from .apis.calendar_api import calculate_tutoring_hours
from .apis.drive_sheets_api import (
    copy_template_sheet,
    get_previous_balances as fetch_previous_balances,
    update_sheet_hours_and_balances,
    update_sheet_pay_status,
    get_pending_text_recipients,
    get_sheet_details
)
from .apis.twilio_api import send_sms, get_text_logs as read_text_logs
from .apis.email_api import send_calculation_email

tutoring_bp = Blueprint('tutoring', __name__)


def calculate_billing_dates():
    """
    Calculates previous Monday (if today is Monday, calculates the previous Monday 7 days back)
    and the following Sunday.
    """
    now = datetime.datetime.now(PST)
    today = now.date()
    weekday = today.weekday()  # Monday=0, Sunday=6

    days_since_prev_monday = 7 if weekday == 0 else weekday
    prev_monday = today - datetime.timedelta(days=days_since_prev_monday)
    prev_sunday = prev_monday + datetime.timedelta(days=6)

    return {
        "start_date": prev_monday.strftime("%m.%d.%y"),
        "end_date": prev_sunday.strftime("%m.%d.%y"),
        "start_date_full": prev_monday.isoformat(),
        "end_date_full": prev_sunday.isoformat()
    }


def require_google_creds():
    creds = get_credentials()
    if not creds:
        return None, jsonify({
            "status": "unauthenticated",
            "message": "Google credentials missing or expired. Please authorize at /login_oauth or /TutoringCalculator/login_oauth.",
            "auth_url": url_for('tutoring.login_oauth_route', _external=True)
        }), 401
    return creds, None, None


# --- OAUTH ROUTES ---

@tutoring_bp.route("/login_oauth")
def login_oauth_route():
    redirect_uri = get_redirect_uri()
    if 'code' in request.args:
        try:
            process_oauth_callback(redirect_uri, request.url)
            return redirect(url_for('swagger.swagger_ui'))
        except Exception as e:
            return jsonify({"status": "error", "message": f"OAuth callback failed: {str(e)}"}), 400

    try:
        auth_url = initiate_oauth_flow(redirect_uri, state='swagger')
        return redirect(auth_url)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to initiate OAuth flow: {str(e)}"}), 500


# --- CORE ENDPOINTS ---

@tutoring_bp.route("/dates", methods=["GET"])
def get_dates():
    dates = calculate_billing_dates()
    return jsonify(dates), 200


@tutoring_bp.route("/copy-template", methods=["POST"])
def copy_template():
    creds, err_resp, err_code = require_google_creds()
    if err_resp:
        return err_resp, err_code

    req_data = request.get_json(silent=True) or {}
    start_date = request.args.get('start_date') or req_data.get('start_date')
    end_date = request.args.get('end_date') or req_data.get('end_date')

    if not start_date or not end_date:
        calc_dates = calculate_billing_dates()
        start_date = start_date or calc_dates['start_date']
        end_date = end_date or calc_dates['end_date']

    try:
        res = copy_template_sheet(creds, start_date, end_date)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tutoring_bp.route("/calc-hours", methods=["GET"])
def calc_hours():
    creds, err_resp, err_code = require_google_creds()
    if err_resp:
        return err_resp, err_code

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        calc_dates = calculate_billing_dates()
        start_date = start_date or calc_dates['start_date']
        end_date = end_date or calc_dates['end_date']

    try:
        hours = calculate_tutoring_hours(creds, start_date, end_date)
        return jsonify(hours), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tutoring_bp.route("/previous-balances", methods=["GET"])
def previous_balances():
    creds, err_resp, err_code = require_google_creds()
    if err_resp:
        return err_resp, err_code

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date:
        calc_dates = calculate_billing_dates()
        start_date = calc_dates['start_date']
        end_date = calc_dates['end_date']

    try:
        balances = fetch_previous_balances(creds, start_date, end_date)
        return jsonify(balances), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tutoring_bp.route("/update-sheet", methods=["POST"])
def update_sheet():
    creds, err_resp, err_code = require_google_creds()
    if err_resp:
        return err_resp, err_code

    req_data = request.get_json(silent=True) or {}
    sheet_id = request.args.get('sheet_id') or req_data.get('sheet_id')
    action = request.args.get('action') or req_data.get('action')

    if not sheet_id or not action:
        return jsonify({"status": "error", "message": "Parameters 'sheet_id' and 'action' are required."}), 400

    if action == "update_hours":
        try:
            # Read C1 and D1 from the sheet if start_date/end_date not explicitly supplied
            start_date = request.args.get('start_date') or req_data.get('start_date')
            end_date = request.args.get('end_date') or req_data.get('end_date')

            if not start_date or not end_date:
                from .apis.drive_sheets_api import get_sheets_service
                sheets_svc = get_sheets_service(creds)
                dates_res = sheets_svc.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range='C1:D1'
                ).execute().get('values', [[]])
                if dates_res and len(dates_res[0]) >= 2:
                    start_date = dates_res[0][0]
                    end_date = dates_res[0][1]

            if not start_date or not end_date:
                calc_dates = calculate_billing_dates()
                start_date = calc_dates['start_date']
                end_date = calc_dates['end_date']

            hours_by_student = calculate_tutoring_hours(creds, start_date, end_date)
            prev_balances = fetch_previous_balances(creds, start_date, end_date)

            res = update_sheet_hours_and_balances(creds, sheet_id, hours_by_student, prev_balances)

            # Send automated email notification upon calculation
            sheet_meta = get_sheet_details(creds, sheet_id)
            year_folder_id = sheet_meta.get('parents', [''])[0]
            send_calculation_email(
                creds=creds,
                sheet_id=sheet_id,
                sheet_url=res.get('sheet_url'),
                year_folder_id=year_folder_id,
                start_date_str=start_date,
                end_date_str=end_date,
                updated_students=res.get('updated_students'),
                total_balance=res.get('total_balance')
            )

            res["action"] = "update_hours"
            return jsonify(res), 200

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    elif action == "update_pay_status":
        try:
            res = update_sheet_pay_status(creds, sheet_id)
            res["action"] = "update_pay_status"
            return jsonify(res), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": f"Unknown action: '{action}'. Must be 'update_hours' or 'update_pay_status'."}), 400


@tutoring_bp.route("/send-texts", methods=["POST"])
def send_texts_route():
    creds, err_resp, err_code = require_google_creds()
    if err_resp:
        return err_resp, err_code

    req_data = request.get_json(silent=True) or {}
    sheet_id = request.args.get('sheet_id') or req_data.get('sheet_id')

    if not sheet_id:
        return jsonify({"status": "error", "message": "Parameter 'sheet_id' is required."}), 400

    try:
        pending_data = get_pending_text_recipients(creds, sheet_id)

        # Stop if sheet title contains CALCULATED
        if pending_data.get('is_pending_review'):
            return jsonify({
                "status": "skipped",
                "message": pending_data.get('message'),
                "sheet_title": pending_data.get('title')
            }), 200

        recipients = pending_data.get('recipients', [])
        if not recipients:
            return jsonify({
                "status": "success",
                "message": "No pending text recipients found (all students either paid, already notified, or zero balance).",
                "sent_count": 0
            }), 200

        sms_results = []
        for recipient in recipients:
            res = send_sms(
                to_phone=recipient['phone'],
                message_body=recipient['text'],
                student_name=recipient['student']
            )
            sms_results.append(res)

        # Convert statuses to Need to Pay
        update_sheet_pay_status(creds, sheet_id)

        return jsonify({
            "status": "success",
            "message": f"Successfully processed {len(sms_results)} messages.",
            "sent_count": len(sms_results),
            "results": sms_results
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tutoring_bp.route("/text-logs", methods=["GET"])
def get_text_logs_route():
    logs = read_text_logs()
    return Response(logs, mimetype='text/plain'), 200
