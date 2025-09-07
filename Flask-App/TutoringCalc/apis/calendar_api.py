import json
import datetime
from googleapiclient.discovery import build
from .helpers import *


def get_calendar_id(id_key):
    """Gets the calendar ID from the calendar-id.json file."""
    with open(ID_FILE, 'r') as file:
        data = json.load(file)
        return data[id_key]


def get_calendar_service(creds):
    """Builds and returns the Google Calendar service."""
    return build('calendar', 'v3', credentials=creds)


def get_time_range(search_date=None):
    """Returns the start and end datetime objects for the week containing the search_date."""
    target_date = datetime.datetime.now(PST)
    if search_date:
        for fmt in DATE_FORMATS:
            try:
                target_date = datetime.datetime.strptime(search_date, fmt)
                break
            except ValueError:
                continue
    target_weekday = target_date.weekday()

    # Monday is 0 and Sunday is 6.
    start_date = target_date - datetime.timedelta(days=target_weekday)
    end_date = target_date + datetime.timedelta(days=(6 - target_weekday))

    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_date_utc = start_date.astimezone(pytz.UTC)
    end_date_utc = end_date.astimezone(pytz.UTC)

    time_min = start_date_utc.isoformat()
    time_max = end_date_utc.isoformat()

    return time_min, time_max, start_date, end_date


def get_calendar_events(calendar_service, time_min, time_max, id_key):
    events_result = calendar_service.events().list(
        calendarId=get_calendar_id(id_key),
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result['items']


def get_calendar_events_info(events):
    events_info = []

    for i, event in enumerate(events, 1):
        start = datetime.datetime.fromisoformat(event['start']['dateTime'])
        end = datetime.datetime.fromisoformat(event['end']['dateTime'])
        start_pst = start.astimezone(PST)
        end_pst = end.astimezone(PST)

        total_hours = (end - start).total_seconds() / 3600
        title = event['summary']
        color_id = event.get('colorId', None)

        if not color_id and 'Tutoring' in title:
            events_info.append({
                "title": title,
                "start": start_pst.strftime(DATETIME_FORMAT),
                "end": end_pst.strftime(DATETIME_FORMAT),
                "time(hrs)": round(total_hours, 2),
                "color_id": color_id
            })

    return events_info


def summarize_calendar_events(events_info, start_date_fmtd, end_date_fmtd):
    events_by_title = {}
    week_totals = {
        "total_hrs": 0,
        "num_sessions": 0,
        "start_date": start_date_fmtd,
        "end_date": end_date_fmtd
    }

    for event in events_info:
        title = event["title"]
        hours = event["time(hrs)"]

        if title not in events_by_title:
            events_by_title[title] = {
                "total_hrs": 0,
                "num_sessions": 0
            }

        events_by_title[title]["total_hrs"] += hours
        events_by_title[title]["num_sessions"] += 1

        week_totals["total_hrs"] += hours
        week_totals["num_sessions"] += 1

    return events_by_title, week_totals


def get_full_summary(calendar_service, time_min, time_max, start_date_fmtd, end_date_fmtd):
    summary = {}
    id_keys = ['stephen_tutoring_id', 'jacob_tutoring_id']
    for id_key in id_keys:
        calendar_events = get_calendar_events(calendar_service, time_min, time_max, id_key)
        calendar_events_info = get_calendar_events_info(calendar_events)
        name = id_key.split('_')[0].capitalize()
        summary[name], _ = summarize_calendar_events(calendar_events_info, start_date_fmtd, end_date_fmtd)
    return summary