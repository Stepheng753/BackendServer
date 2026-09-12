import base64
import datetime
import pytz
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .. import config
from ..config import PST

DATE_FORMATS = [
    "%m.%d.%y",
    "%m-%d-%y",
    "%m/%d/%y",
    "%m.%d.%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%Y-%m-%d"
]


def parse_date_string(date_str):
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date string: {date_str}. Supported formats include MM.DD.YY, MM/DD/YY, YYYY-MM-DD.")


def get_calendar_time_range(start_date_str, end_date_str):
    start_date = parse_date_string(start_date_str)
    end_date = parse_date_string(end_date_str)

    start_dt = PST.localize(datetime.datetime.combine(start_date, datetime.time.min))
    end_dt = PST.localize(datetime.datetime.combine(end_date, datetime.time.max))

    start_utc = start_dt.astimezone(pytz.UTC).isoformat()
    end_utc = end_dt.astimezone(pytz.UTC).isoformat()

    return start_utc, end_utc


def get_calendar_service(creds):
    return build('calendar', 'v3', credentials=creds)


def resolve_calendar_id(calendar_service):
    cal_id = config.GOOGLE_CALENDAR_ID
    if cal_id:
        cal_id = cal_id.strip()
        # If it's a base64-encoded calendar ID (e.g., copied from web URL without @)
        if '@' not in cal_id:
            try:
                padded = cal_id + '=' * (-len(cal_id) % 4)
                decoded = base64.b64decode(padded).decode('utf-8')
                if '@' in decoded:
                    return decoded
            except Exception:
                pass
        return cal_id

    # Fallback to searching user's calendar list for a calendar named "Tutoring"
    try:
        calendars = calendar_service.calendarList().list().execute().get('items', [])
        for cal in calendars:
            if cal.get('summary', '').strip().lower() == 'tutoring':
                return cal['id']
    except Exception as e:
        print(f"Could not search calendarList: {e}")

    return 'primary'


def calculate_tutoring_hours(creds, start_date_str, end_date_str):
    """
    Queries tutoring calendar for events in range, filters for events ending in 'Tutoring'
    with primary color (colorId is None), and consolidates hours by first word of summary.
    """
    calendar_service = get_calendar_service(creds)
    calendar_id = resolve_calendar_id(calendar_service)
    time_min, time_max = get_calendar_time_range(start_date_str, end_date_str)

    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            # Automatic fallback: find "Tutoring" in the user's calendars
            calendars = calendar_service.calendarList().list().execute().get('items', [])
            tutoring_cal = next(
                (c for c in calendars if c.get('summary', '').strip().lower() == 'tutoring'),
                None
            )
            if not tutoring_cal:
                tutoring_cal = next(
                    (c for c in calendars if 'tutoring' in c.get('summary', '').lower()),
                    None
                )
            if tutoring_cal:
                calendar_id = tutoring_cal['id']
                events_result = calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
            else:
                raise
        else:
            raise

    events = events_result.get('items', [])
    hours_by_student = {}

    for event in events:
        summary = event.get('summary', '').strip()
        words = summary.split()
        if not words:
            continue

        # Check last word == 'Tutoring' (case-insensitive)
        if words[-1].lower() != 'tutoring':
            continue

        # Check for primary/default color (colorId is not set or None)
        color_id = event.get('colorId')
        if color_id is not None:
            continue

        start_raw = event['start'].get('dateTime') or event['start'].get('date')
        end_raw = event['end'].get('dateTime') or event['end'].get('date')

        if not start_raw or not end_raw:
            continue

        if 'T' not in start_raw:
            start_dt = PST.localize(datetime.datetime.combine(datetime.date.fromisoformat(start_raw), datetime.time.min))
            end_dt = PST.localize(datetime.datetime.combine(datetime.date.fromisoformat(end_raw), datetime.time.min))
        else:
            start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
            end_dt = datetime.datetime.fromisoformat(end_raw.replace('Z', '+00:00'))

        duration_hours = (end_dt - start_dt).total_seconds() / 3600.0

        # Grab the first word of the event title which is their name
        student_first_name = words[0].capitalize()
        hours_by_student[student_first_name] = round(
            hours_by_student.get(student_first_name, 0.0) + duration_hours, 2
        )

    return hours_by_student

