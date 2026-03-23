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
    with sqlite3.connect(DB_PATH) as conn:
        if notify_user is None:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, preferred_time, response_hours)
                VALUES (?, ?, ?, ?)
                """,
                [user_id, username, preferred_time, response_hours]
            )
        else:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, preferred_time, response_hours, notify_user)
                VALUES (?, ?, ?, ?, ?)
                """,
                [user_id, username, preferred_time, response_hours, notify_user]
            )

def record_wellness_check(user_id, check_date, prompt_sent=None, response_received=None, notified_contact=None):
    """
    Record a wellness check event.
    
    Parameters:
        user_id: Telegram user ID
        check_date: Date of the check (YYYY-MM-DD)
        prompt_sent: When the prompt was sent (datetime)
        response_received: When user responded (datetime)
        notified_contact: When emergency contact was notified (datetime)
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO wellness_checks (user_id, check_date, prompt_sent, response_received, notified_contact)
            VALUES (?, ?, ?, ?, ?)
            """,
            [user_id, check_date, prompt_sent, response_received, notified_contact]
        )

def get_todays_wellness_check(user_id):
    """
    Get today's wellness check record for a user.
    
    Returns:
        Tuple of (check_date, prompt_sent, response_received, notified_contact) or None if no record
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
    record = get_todays_wellness_check(user_id)
    return record is not None and record[2] is not None
