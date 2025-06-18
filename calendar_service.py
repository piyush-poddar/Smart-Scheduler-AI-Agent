import datetime
from typing import List, Tuple
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pickle
import pytz

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar']
IST = pytz.timezone('Asia/Kolkata')
WORK_START_HOUR = 9   # 9 AM IST
WORK_END_HOUR = 22    # 10 PM IST

def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_busy_events_for_day(date: str) -> List[Tuple[datetime.datetime, datetime.datetime]]:
    service = get_calendar_service()

    # Convert IST start and end of the day → UTC for API
    day_start_ist = IST.localize(datetime.datetime.fromisoformat(date + "T00:00:00"))
    day_end_ist = IST.localize(datetime.datetime.fromisoformat(date + "T23:59:59"))

    time_min = day_start_ist.astimezone(pytz.UTC).isoformat()
    time_max = day_end_ist.astimezone(pytz.UTC).isoformat()

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    
    busy_slots = []
    for event in events:
        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')

        if start and end:
            start_dt_utc = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt_utc = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))

            # Convert UTC → IST for easy manipulation later
            busy_slots.append((
                start_dt_utc.astimezone(IST),
                end_dt_utc.astimezone(IST)
            ))

    return busy_slots

def find_free_slots(date: str, duration_minutes: int = 60) -> List[Tuple[datetime.datetime, datetime.datetime]]:
    busy_slots = get_busy_events_for_day(date)
    busy_slots.sort()

    # Working hours in IST (localized datetime)
    work_day_start = IST.localize(datetime.datetime.fromisoformat(f"{date}T{WORK_START_HOUR:02}:00:00"))
    work_day_end = IST.localize(datetime.datetime.fromisoformat(f"{date}T{WORK_END_HOUR:02}:00:00"))

    free_slots = []
    current_start = work_day_start

    for busy_start, busy_end in busy_slots:
        if busy_start > current_start:
            free_period = (current_start, busy_start)
            if (free_period[1] - free_period[0]).total_seconds() >= duration_minutes * 60:
                free_slots.append(free_period)
        current_start = max(current_start, busy_end)

    if current_start < work_day_end:
        free_period = (current_start, work_day_end)
        if (free_period[1] - free_period[0]).total_seconds() >= duration_minutes * 60:
            free_slots.append(free_period)

    return free_slots

def format_slots(slots: List[Tuple[datetime.datetime, datetime.datetime]]) -> List[str]:
    return [f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}" for start, end in slots]

def book_meeting(start_time: datetime.datetime, end_time: datetime.datetime, summary: str = "Meeting") -> str:
    service = get_calendar_service()

    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.astimezone(pytz.UTC).isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': end_time.astimezone(pytz.UTC).isoformat(),
            'timeZone': 'Asia/Kolkata'
        },
        'reminders': {
            'useDefault': True,
        }
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event.get('htmlLink', '')


if __name__ == "__main__":
    # Example usage
    date = "2025-06-14"
    duration = 60  # minutes

    free_slots = find_free_slots(date, duration)
    if free_slots:
        print("Available free slots (IST):")
        for slot in format_slots(free_slots):
            print(slot)
    else:
        print("No free slots available for this day.")
    
    # Example booking
    if free_slots:
        start_time = free_slots[0][0]  # Take the first available slot
        end_time = start_time + datetime.timedelta(minutes=duration)
        event_link = book_meeting(start_time, end_time, "Test Meeting")
        print(f"Meeting booked successfully! Event link: {event_link}")
    else:
        print("No slots available to book a meeting.")
