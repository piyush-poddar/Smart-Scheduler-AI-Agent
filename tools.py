import parsedatetime
import datetime
from calendar_service import find_free_slots, format_slots


def get_free_slots(date: str, duration_minutes: int = 60) -> dict:
    """
    Find available free time slots for a meeting on the specified date.

    Args:
        date (str): Date in 'YYYY-MM-DD' format.
        duration_minutes (int): Duration of the meeting in minutes.

    Returns:
        dict: List of free slots in human-readable format (IST).
    """
    print(f"Tool Call: Finding free slots for {date} with duration {duration_minutes} minutes")
    slots = find_free_slots(date, duration_minutes)
    
    tool_response = {'free_slots': format_slots(slots)}
    print(f"Tool Response: {tool_response}")

    return tool_response

def parse_datetime(text: str) -> datetime.datetime:
    """
    Parse a natural language date/time string into a datetime object.
    Use this tool to interpret user input like "today", "next Tuesday" or "in 2 hours".

    Args:
        text (str): Natural language date/time string.

    Returns:
        datetime.datetime: Parsed datetime object, or None if parsing fails.
    """
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(text)
    
    if parse_status == 0:
        return None
    
    dt = datetime.datetime(*time_struct[:6])
    
    return dt
