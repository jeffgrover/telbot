import logging
import sqlite3
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("bot_database.sqlite")


def init_db():
    """Initialize database tables (safe to call multiple times)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                preferred_time TEXT,
                response_hours INTEGER,
                notify_user TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wellness_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                check_date DATE,
                prompt_sent TIMESTAMP,
                response_received TIMESTAMP,
                notified_contact TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)


def check_integrity():
    """Log database status and flag any issues at startup."""
    db_exists = DB_PATH.exists()
    logger.info(f"Database path: {DB_PATH.resolve()}")
    if not db_exists:
        logger.info("No existing database — will be created fresh")
        return

    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute(
            "SELECT user_id, username, preferred_time, response_hours, notify_user "
            "FROM users"
        ).fetchall()

        if not users:
            logger.info("No users configured")
            return

        logger.info(f"Configured users: {len(users)}")
        for user_id, username, pref_time, hours, buddy in users:
            buddy_str = f", buddy=@{buddy}" if buddy else ""
            logger.info(f"  {username} (id={user_id}): ping={pref_time}, "
                        f"window={hours}h{buddy_str}")

            # Flag issues
            if buddy:
                buddy_id = conn.execute(
                    "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)",
                    [buddy],
                ).fetchone()
                if not buddy_id:
                    logger.warning(f"  ^ Buddy @{buddy} is NOT registered with the bot")

            if not pref_time or ':' not in pref_time:
                logger.warning(f"  ^ Invalid preferred_time format: {pref_time!r}")

        # Report recent wellness checks
        recent = conn.execute(
            "SELECT w.check_date, u.username, w.prompt_sent, "
            "w.response_received, w.notified_contact "
            "FROM wellness_checks w JOIN users u ON w.user_id = u.user_id "
            "ORDER BY w.check_date DESC, w.id DESC LIMIT 5"
        ).fetchall()
        if recent:
            logger.info("Recent wellness checks:")
            for check_date, username, sent, responded, notified in recent:
                parts = [f"sent={sent}" if sent else "not sent"]
                if responded:
                    parts.append(f"responded={responded}")
                if notified:
                    parts.append(f"buddy_notified={notified}")
                logger.info(f"  {check_date} {username}: {', '.join(parts)}")


def get_user_preferences(user_id):
    """Get (preferred_time, response_hours, notify_user) or None."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT preferred_time, response_hours, notify_user FROM users WHERE user_id = ?",
            [user_id],
        )
        return cursor.fetchone()


def save_user_preferences(user_id, username, preferred_time, response_hours, notify_user=None):
    """Save or update user preferences. preferred_time is HH:MM format."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users "
            "(user_id, username, preferred_time, response_hours, notify_user) "
            "VALUES (?, ?, ?, ?, ?)",
            [user_id, username, preferred_time, response_hours, notify_user],
        )


def record_ping(user_id, ping_date, ping_sent=None, response_received=None, buddy_notified=None):
    """Record or update a ping event. One record per user per day (upsert)."""
    sent_str = ping_sent.isoformat() if ping_sent else None
    resp_str = response_received.isoformat() if response_received else None
    notif_str = buddy_notified.isoformat() if buddy_notified else None

    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT id FROM wellness_checks WHERE user_id = ? AND check_date = ?",
            [user_id, ping_date],
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE wellness_checks SET "
                "prompt_sent = COALESCE(?, prompt_sent), "
                "response_received = COALESCE(?, response_received), "
                "notified_contact = COALESCE(?, notified_contact) "
                "WHERE id = ?",
                [sent_str, resp_str, notif_str, existing[0]],
            )
        else:
            conn.execute(
                "INSERT INTO wellness_checks "
                "(user_id, check_date, prompt_sent, response_received, notified_contact) "
                "VALUES (?, ?, ?, ?, ?)",
                [user_id, ping_date, sent_str, resp_str, notif_str],
            )


def get_todays_ping(user_id):
    """
    Get today's ping record.
    Returns (check_date, prompt_sent, response_received, notified_contact) or None.
    """
    today = date.today().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT check_date, prompt_sent, response_received, notified_contact "
            "FROM wellness_checks WHERE user_id = ? AND check_date = ?",
            [user_id, today],
        )
        return cursor.fetchone()


def has_responded_today(user_id):
    """Check if user has already responded today."""
    record = get_todays_ping(user_id)
    return record is not None and record[2] is not None


def get_all_users_with_ping_preferences():
    """
    Get all users with preferences.
    Returns list of (user_id, username, preferred_time, response_hours, notify_user).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT user_id, username, preferred_time, response_hours, notify_user FROM users"
        )
        return cursor.fetchall()


def get_latest_unanswered_ping(user_id):
    """Get the most recent ping with no response and no buddy notification."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT check_date, prompt_sent, response_received, notified_contact "
            "FROM wellness_checks "
            "WHERE user_id = ? AND prompt_sent IS NOT NULL "
            "AND response_received IS NULL AND notified_contact IS NULL "
            "ORDER BY check_date DESC LIMIT 1",
            [user_id],
        )
        return cursor.fetchone()


def get_user_by_username(username):
    """Look up a user's ID by their Telegram username (case-insensitive)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", [username]
        )
        row = cursor.fetchone()
        return row[0] if row else None
