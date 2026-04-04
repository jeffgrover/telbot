"""Message and command handlers for the Telegram Ping Bot."""

from datetime import datetime, timedelta
from telegram.ext import ContextTypes

from bot.config import (
    logger, user_state, user_preferences, test_state,
    STATE_NONE, STATE_ASKED_TIME, STATE_ASKED_HOURS, STATE_ASKED_NOTIFY,
)
from database import (
    get_user_preferences, save_user_preferences, record_ping,
    has_responded_today, get_all_users_with_ping_preferences,
    get_latest_unanswered_ping, get_user_by_username,
)
from time_utils import parse_time_input, format_time_for_display


# ---------------------------------------------------------------------------
# Periodic job: send pings & check deadlines
# ---------------------------------------------------------------------------

async def send_ping(context: ContextTypes.DEFAULT_TYPE):
    """Called every minute by the job queue. Sends pings and checks deadlines."""
    now = datetime.now()
    hour, minute = now.hour, now.minute

    users = get_all_users_with_ping_preferences()
    for user_id, username, preferred_time, response_hours, notify_user in users:
        try:
            pref_hour, pref_minute = map(int, preferred_time.split(':'))
        except ValueError:
            continue

        # Send ping at the scheduled minute
        if hour == pref_hour and minute == pref_minute:
            if not has_responded_today(user_id):
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Hi {username}! How are you doing today?\n\n"
                            f"Please respond within {response_hours} hours."
                        ),
                    )
                    record_ping(user_id, now.date().isoformat(), ping_sent=now)
                    logger.info(f"Sent ping to {username} ({user_id})")
                except Exception as e:
                    logger.error(f"Failed to send ping to {user_id}: {e}")

        # Check for missed responses past the deadline
        if not notify_user:
            continue
        record = get_latest_unanswered_ping(user_id)
        if not record:
            continue
        ping_sent_time = datetime.fromisoformat(record[1])
        deadline = ping_sent_time + timedelta(hours=response_hours)
        if now <= deadline:
            continue

        buddy_id = get_user_by_username(notify_user)
        if not buddy_id:
            logger.warning(f"Buddy @{notify_user} not registered with bot")
            continue
        try:
            display_time = format_time_for_display(pref_hour, pref_minute)
            await context.bot.send_message(
                chat_id=buddy_id,
                text=(
                    f"Alert: {username} hasn't responded to their daily check-in.\n"
                    f"Ping sent at {display_time}, "
                    f"{response_hours}-hour window expired."
                ),
            )
            record_ping(user_id, now.date().isoformat(), buddy_notified=now)
            logger.info(f"Notified buddy @{notify_user} about {username}")
        except Exception as e:
            logger.error(f"Failed to notify buddy @{notify_user}: {e}")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def handle_start_command(update, context):
    """Handle /start command."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    db_prefs = get_user_preferences(user_id)

    if db_prefs:
        await _show_status(update, username, db_prefs)
    else:
        await _ask_time_question(update, user_id, username)


async def handle_setup_command(update, context):
    """Handle /setup - reset and reconfigure."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name

    user_state.pop(user_id, None)
    user_preferences.pop(user_id, None)

    import sqlite3
    with sqlite3.connect('bot_database.sqlite') as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", [user_id])

    await update.message.reply_text("Setup reset. Let's reconfigure your ping.\n")
    await _ask_time_question(update, user_id, username)


async def handle_test_command(update, context):
    """Handle /test - send a test ping in 1 min, check response after 2 min."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name

    if not get_user_preferences(user_id):
        await update.message.reply_text("Please set up your ping first with /start")
        return

    # Cancel any previous test jobs for this user
    job_name = f"test_{user_id}"
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    # Reset test state
    test_state[user_id] = {'ping_sent': False, 'responded': False}

    await update.message.reply_text(
        "Test started! I'll send a test ping in 1 minute "
        "and check for your response after 2 minutes."
    )
    context.job_queue.run_once(
        _send_test_ping, 60, name=job_name,
        data={'user_id': user_id, 'username': username},
    )
    context.job_queue.run_once(
        _check_test_response, 120, name=job_name,
        data={'user_id': user_id, 'username': username},
    )


# ---------------------------------------------------------------------------
# Text message handler
# ---------------------------------------------------------------------------

async def handle_message(update, context):
    """Handle all non-command text messages."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    text = update.message.text

    db_prefs = get_user_preferences(user_id)
    current_state = user_state.get(user_id, STATE_NONE)

    # Returning user who already completed setup
    if current_state == STATE_NONE and db_prefs:
        # If a test ping is active, mark the test as responded
        if user_id in test_state and test_state[user_id]['ping_sent']:
            test_state[user_id]['responded'] = True
        record_ping(user_id, datetime.now().date().isoformat(),
                    response_received=datetime.now())
        preferred_time, response_hours, notify_user = db_prefs
        pref_hour, pref_minute = map(int, preferred_time.split(':'))
        display_time = format_time_for_display(pref_hour, pref_minute)
        msg = (
            f"Got it, {username}! You're checked in for today.\n"
            f"Your ping is active:\n"
            f"- Daily ping time: {display_time}\n"
            f"- Response window: {response_hours} hours\n"
        )
        if notify_user:
            msg += f"- Buddy contact: @{notify_user}\n"
        await update.message.reply_text(msg)
        return

    # New user, no prefs - start setup
    if current_state == STATE_NONE:
        await _ask_time_question(update, user_id, username)
        return

    # Setup flow: waiting for preferred time
    if current_state == STATE_ASKED_TIME:
        parsed = parse_time_input(text)
        if parsed is None:
            await update.message.reply_text(
                "I couldn't understand that time format.\n"
                "Try: 10 AM, 9pm, 22:00, 3:30 PM"
            )
            return
        user_preferences[user_id] = {'hour': parsed[0], 'minute': parsed[1]}
        display = format_time_for_display(*parsed)
        await update.message.reply_text(
            f"Got it! Daily ping at {display}.\n\n"
            "How many hours should I wait for your response? (1-12)"
        )
        user_state[user_id] = STATE_ASKED_HOURS
        return

    # Setup flow: waiting for response window
    if current_state == STATE_ASKED_HOURS:
        try:
            hours = int(text)
            if not 1 <= hours <= 12:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please enter a number between 1 and 12.")
            return

        prefs = user_preferences.get(user_id, {})
        hour, minute = prefs.get('hour', 0), prefs.get('minute', 0)
        display = format_time_for_display(hour, minute)
        user_preferences[user_id]['hours'] = hours
        await update.message.reply_text(
            f"Got it! Ping at {display}, {hours}-hour response window.\n\n"
            "Who should I notify if you don't respond?\n"
            "Enter their Telegram username (with or without @):"
        )
        user_state[user_id] = STATE_ASKED_NOTIFY
        return

    # Setup flow: waiting for buddy contact
    if current_state == STATE_ASKED_NOTIFY:
        buddy = text.strip().lstrip('@')
        if not buddy:
            await update.message.reply_text("Please enter a valid username.")
            return

        prefs = user_preferences.get(user_id, {})
        hour, minute = prefs.get('hour', 0), prefs.get('minute', 0)
        hours = prefs.get('hours', 3)
        display = format_time_for_display(hour, minute)

        save_user_preferences(user_id, username, f"{hour:02d}:{minute:02d}", hours, buddy)
        record_ping(user_id, datetime.now().date().isoformat(),
                    response_received=datetime.now())

        await update.message.reply_text(
            f"Ping configured!\n\n"
            f"- Daily ping time: {display}\n"
            f"- Response window: {hours} hours\n"
            f"- Buddy contact: @{buddy}\n\n"
            f"Your ping is now active!"
        )
        user_state.pop(user_id, None)
        user_preferences.pop(user_id, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _ask_time_question(update, user_id, username):
    """Send the first setup question."""
    await update.message.reply_text(
        f"Hi {username}!\n\n"
        "Welcome to Ping Bot! I'll ask three questions to set up your daily check-in.\n\n"
        "What time should I send your daily ping?\n"
        "Examples: 10 AM, 9pm, 22:00, 3:30 PM"
    )
    user_state[user_id] = STATE_ASKED_TIME


async def _show_status(update, username, db_prefs):
    """Show current ping configuration."""
    preferred_time, response_hours, notify_user = db_prefs
    pref_hour, pref_minute = map(int, preferred_time.split(':'))
    display_time = format_time_for_display(pref_hour, pref_minute)
    msg = (
        f"Welcome back, {username}! Your ping is active:\n"
        f"- Daily ping time: {display_time}\n"
        f"- Response window: {response_hours} hours\n"
    )
    if notify_user:
        msg += f"- Buddy contact: @{notify_user}\n"
    msg += "\nUse /setup to reconfigure."
    await update.message.reply_text(msg)


async def _send_test_ping(context: ContextTypes.DEFAULT_TYPE):
    """Job callback: send a test ping."""
    data = context.job.data
    user_id = data['user_id']
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="TEST PING: Please reply to confirm the system works.",
        )
        if user_id in test_state:
            test_state[user_id]['ping_sent'] = True
    except Exception as e:
        logger.error(f"Failed to send test ping: {e}")


async def _check_test_response(context: ContextTypes.DEFAULT_TYPE):
    """Job callback: check if the user responded to the test ping."""
    data = context.job.data
    user_id = data['user_id']
    state = test_state.pop(user_id, {})
    try:
        if state.get('responded'):
            msg = "Test complete! You responded successfully. The system is working."
        else:
            msg = "Test complete: No response detected. Check your notifications."
        await context.bot.send_message(chat_id=user_id, text=msg)
    except Exception as e:
        logger.error(f"Failed to send test results: {e}")
