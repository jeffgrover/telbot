import sqlite3
from pathlib import Path

DB_PATH = Path("bot_database.sqlite")

def init_db():
    """Initialize database with users table."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                preferred_time TEXT,
                response_hours INTEGER,
                notify_user TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wellness_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                check_date DATE,
                prompt_sent TIMESTAMP,
                response_received TIMESTAMP,
                notified_contact TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )

def get_user_preferences(user_id):
    """Get stored preferences for a user."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT preferred_time, response_hours, notify_user FROM users WHERE user_id = ?",
            [user_id]
        )
        return cursor.fetchone()

def save_user_preferences(user_id, username, preferred_time, response_hours, notify_user=None):
    """Save or update user preferences."""
    # Convert display format to database format (HH:MM 24-hour)
    from datetime import datetime
    
    # Parse the time string to get hour and minute
    try:
        if 'AM' in preferred_time.upper() or 'PM' in preferred_time.upper():
            # Handle 12-hour format
            time_part, period = preferred_time.split()
            if ':' in time_part:
                hour_str, min_str = time_part.split(':')
                hour = int(hour_str)
                minute = int(min_str)
            else:
                hour = int(time_part)
                minute = 0
            
            # Convert to 24-hour
            if period == 'PM' and hour != 12:
                hour += 12
            elif period == 'AM' and hour == 12:
                hour = 0
        else:
            # Handle 24-hour format
            if ':' in preferred_time:
                hour, minute = map(int, preferred_time.split(':'))
            else:
                hour = int(preferred_time)
                minute = 0
    except Exception as e:
        print(f"Error parsing time: {e}")
        hour, minute = 9, 0  # Default to 9 AM
    
    db_preferred_time = f"{hour:02d}:{minute:02d}"
    
    with sqlite3.connect(DB_PATH) as conn:
        if notify_user is None:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, preferred_time, response_hours)
                VALUES (?, ?, ?, ?)
                """,
                [user_id, username, db_preferred_time, response_hours]
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, preferred_time, response_hours, notify_user)
                VALUES (?, ?, ?, ?, ?)
                """,
                [user_id, username, db_preferred_time, response_hours, notify_user]
            )

def record_ping(user_id, ping_date, ping_sent=None, response_received=None, buddy_notified=None):
    """
    Record a ping event.
    
    Parameters:
        user_id: Telegram user ID
        ping_date: Date of the ping (YYYY-MM-DD)
        ping_sent: When the ping was sent (datetime)
        response_received: When user responded (datetime)
        buddy_notified: When buddy contact was notified (datetime)
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO wellness_checks (user_id, check_date, prompt_sent, response_received, notified_contact)
            VALUES (?, ?, ?, ?, ?)
            """,
            [user_id, ping_date, ping_sent, response_received, buddy_notified]
        )

def get_todays_ping(user_id):
    """
    Get today's ping record for a user.
    
    Returns:
        Tuple of (ping_date, ping_sent, response_received, buddy_notified) or None if no record
    """
    from datetime import date
    today = date.today().isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT check_date, prompt_sent, response_received, notified_contact FROM wellness_checks "
            "WHERE user_id = ? AND check_date = ?",
            [user_id, today]
        )
        return cursor.fetchone()

def has_responded_today(user_id):
    """
    Check if user has already responded today.
    
    Returns:
        True if user has responded today, False otherwise
    """
    record = get_todays_ping(user_id)
    return record is not None and record[2] is not None

def get_all_users_with_ping_preferences():
    """
    Get all users with their ping preferences.
    
    Returns:
        List of tuples: (user_id, username, preferred_ping_time, response_hours, buddy_user)
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT user_id, username, preferred_time, response_hours, notify_user FROM users"
        )
        return cursor.fetchall()
