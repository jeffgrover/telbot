from datetime import datetime, timedelta
import re


def parse_time_input(time_str):
    """
    Parse flexible time formats.
    Supports: "10 AM", "9pm", "22:00", "3:30 PM", "15:45", "10"
    Returns (hour, minute) tuple or None if invalid.
    """
    text = time_str.strip().upper()

    # "3:30 PM", "10:00 AM"
    m = re.match(r'^(\d{1,2}):(\d{2})\s*(AM|PM)$', text)
    if m:
        hour, minute, period = int(m[1]), int(m[2]), m[3]
        if hour < 1 or hour > 12 or minute > 59:
            return None
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, minute)

    # "10 AM", "9PM"
    m = re.match(r'^(\d{1,2})\s*(AM|PM)$', text)
    if m:
        hour, period = int(m[1]), m[2]
        if hour < 1 or hour > 12:
            return None
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, 0)

    # "22:00", "10:30"
    m = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if m:
        hour, minute = int(m[1]), int(m[2])
        if hour > 23 or minute > 59:
            return None
        return (hour, minute)

    # "10", "22" (bare hour, 24-hour format)
    m = re.match(r'^(\d{1,2})$', text)
    if m:
        hour = int(m[1])
        if hour > 23:
            return None
        return (hour, 0)

    return None


def format_time_for_display(hour, minute):
    """Format (hour, minute) as human-readable 12-hour time."""
    if hour == 24:
        hour = 0
    display_hour = hour % 12 or 12
    period = "AM" if hour < 12 else "PM"
    if minute == 0:
        return f"{display_hour} {period}"
    return f"{display_hour}:{minute:02d} {period}"


def calculate_ping_deadline_time(preferred_hour, preferred_minute, hours_later):
    """
    Calculate the deadline datetime for today's ping.
    Returns a datetime object for today at preferred_time + hours_later.
    """
    now = datetime.now()
    ping_time = now.replace(hour=preferred_hour, minute=preferred_minute,
                            second=0, microsecond=0)
    return ping_time + timedelta(hours=hours_later)
