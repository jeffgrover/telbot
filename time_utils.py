from datetime import datetime, timedelta
import re

def parse_time_input(time_str):
    """
    Parse flexible time formats.
    Supports: "10 AM", "10:00", "22:00:00", "10am", "10pm", etc.
    Returns (hour, minute) tuple or None if invalid.
    """
    time_str_upper = time_str.upper()
    
    # Try 24-hour format with minutes: "10:30", "22:00"
    match_24h_colon = re.match(r'^(\d{1,2}):(\d{2})$', time_str_upper)
    if match_24h_colon:
        hour = int(match_24h_colon.group(1))
        minute = int(match_24h_colon.group(2))
        # Validate hour is within 0-23 range
        if 0 <= hour < 24:
            return (hour, minute)
        else:
            return None
    
    # Try 12-hour format with AM/PM and minutes: "3:30 PM", "9:45 AM"
    match_12h_ampm_colon = re.match(r'^(\d{1,2}):(\d{2})\s*(AM|PM)$', time_str_upper)
    if match_12h_ampm_colon:
        hour = int(match_12h_ampm_colon.group(1))
        minute = int(match_12h_ampm_colon.group(2))
        period = match_12h_ampm_colon.group(3)
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, minute)
    
    # Try 12-hour format with AM/PM: "10 AM", "9 PM"
    match_12h_ampm = re.match(r'^(\d{1,2})\s*(AM|PM)$', time_str_upper)
    if match_12h_ampm:
        hour = int(match_12h_ampm.group(1))
        period = match_12h_ampm.group(2)
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, 0)
    
    # Try 12-hour format with am/pm lowercase: "9am", "11pm"
    match_12h_lower = re.match(r'^(\d{1,2})\s*(am|pm)$', time_str)
    if match_12h_lower:
        hour = int(match_12h_lower.group(1))
        period = match_12h_lower.group(2).upper()
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, 0)
    
    # Try 24-hour format without minutes: "10", "22"
    match_24h_simple = re.match(r'^(\d{1,2})$', time_str_upper)
    if match_24h_simple:
        hour = int(match_24h_simple.group(1))
        return (hour, 0)
    
    # Try 12-hour format without minutes: "9 AM", "11 PM"
    match_12h_simple = re.match(r'^(\d{1,2})\s*(AM|PM)$', time_str_upper)
    if match_12h_simple:
        hour = int(match_12h_simple.group(1))
        period = match_12h_simple.group(2)
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, 0)
    
    # Try lowercase 12-hour without minutes: "9 am", "11 pm"
    match_12h_lower_simple = re.match(r'^(\d{1,2})\s*(am|pm)$', time_str)
    if match_12h_lower_simple:
        hour = int(match_12h_lower_simple.group(1))
        period = match_12h_lower_simple.group(2).upper()
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        return (hour, 0)
    
    return None

def format_time_for_display(hour, minute):
    """Format time as 12-hour or 24-hour based on hour value."""
    # Handle 24:00 as midnight (special case)
    if hour == 24:
        display_hour = 12
        period = "AM"
    else:
        # Convert to 12-hour format
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        period = "AM" if hour < 12 else "PM"
    
    if minute == 0:
        return f"{display_hour:d} {period}"
    else:
        return f"{display_hour:d}:{minute:02d} {period}"

def calculate_deadline_time(preferred_hour, preferred_minute, hours_later):
    """
    Calculate what time it will be X hours later.
    Returns formatted time string.
    """
    now = datetime.now()
    # Create a datetime for today at the preferred time
    today_at_time = datetime(now.year, now.month, now.day, preferred_hour, preferred_minute)
    
    # If that time has already passed, use tomorrow
    if today_at_time < now:
        today_at_time = today_at_time + timedelta(days=1)
    
    deadline = today_at_time + timedelta(hours=hours_later)
    return format_time_for_display(deadline.hour, deadline.minute)
