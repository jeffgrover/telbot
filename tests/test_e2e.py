"""
End-to-end tests that simulate a user talking to the bot.

Mocks the Telegram objects, exercises real handlers, database, and state machine.
"""

import os
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from database import init_db, save_user_preferences, record_ping, get_user_preferences, has_responded_today
from bot.config import user_state, user_preferences, test_state
from bot.handlers import (
    handle_start_command,
    handle_setup_command,
    handle_test_command,
    handle_message,
    send_ping,
    _send_test_ping,
    _check_test_response,
)


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state():
    """Fresh database and cleared in-memory state for every test."""
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')
    init_db()
    user_state.clear()
    user_preferences.clear()
    test_state.clear()
    yield
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')


def make_update(user_id, username, text):
    """Build a mock Update that looks like a message from a user."""
    update = MagicMock()
    update.message.from_user.id = user_id
    update.message.from_user.username = username
    update.message.from_user.first_name = username
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def make_context():
    """Build a mock context with bot and job_queue."""
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.job_queue.run_once = MagicMock()
    return ctx


def last_reply(update):
    """Return the text of the most recent reply_text call."""
    return update.message.reply_text.call_args[0][0]


# -- Full setup conversation -------------------------------------------------

@pytest.mark.asyncio
async def test_full_setup_conversation():
    """Walk through the three-question setup as a new user."""
    ctx = make_context()

    # First message from a new user triggers setup
    u1 = make_update(42, 'alice', 'hello')
    await handle_message(u1, ctx)
    assert 'What time' in last_reply(u1)

    # Answer with preferred time
    u2 = make_update(42, 'alice', '9 PM')
    await handle_message(u2, ctx)
    assert '9 PM' in last_reply(u2)
    assert 'How many hours' in last_reply(u2)

    # Answer with response window
    u3 = make_update(42, 'alice', '3')
    await handle_message(u3, ctx)
    assert 'notify' in last_reply(u3).lower()

    # Answer with buddy contact
    u4 = make_update(42, 'alice', '@bob')
    await handle_message(u4, ctx)
    reply = last_reply(u4)
    assert 'configured' in reply.lower()
    assert '@bob' in reply
    assert '9 PM' in reply

    # Verify database
    prefs = get_user_preferences(42)
    assert prefs == ('21:00', 3, 'bob')
    assert has_responded_today(42)


# -- Returning user ----------------------------------------------------------

@pytest.mark.asyncio
async def test_returning_user_gets_status():
    """A user who already set up should see status, not setup questions."""
    save_user_preferences(42, 'alice', '21:00', 3, 'bob')
    ctx = make_context()

    u = make_update(42, 'alice', 'hi there')
    await handle_message(u, ctx)
    reply = last_reply(u)
    assert 'checked in' in reply.lower()
    assert '9 PM' in reply
    assert '@bob' in reply
    assert has_responded_today(42)


# -- /start command -----------------------------------------------------------

@pytest.mark.asyncio
async def test_start_new_user():
    """/start for a new user begins setup."""
    u = make_update(42, 'alice', '/start')
    await handle_start_command(u, make_context())
    assert 'What time' in last_reply(u)


@pytest.mark.asyncio
async def test_start_existing_user():
    """/start for existing user shows status."""
    save_user_preferences(42, 'alice', '21:00', 3, 'bob')
    u = make_update(42, 'alice', '/start')
    await handle_start_command(u, make_context())
    reply = last_reply(u)
    assert 'Welcome back' in reply
    assert '/setup' in reply


# -- /setup command -----------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_resets_and_restarts():
    """/setup clears preferences and starts the setup flow again."""
    save_user_preferences(42, 'alice', '21:00', 3, 'bob')
    ctx = make_context()

    u1 = make_update(42, 'alice', '/setup')
    await handle_setup_command(u1, ctx)
    assert get_user_preferences(42) is None

    # Should now be in setup flow — answer the time question
    u2 = make_update(42, 'alice', '10 AM')
    await handle_message(u2, ctx)
    assert '10 AM' in last_reply(u2)


# -- /test command ------------------------------------------------------------

@pytest.mark.asyncio
async def test_test_command_schedules_jobs():
    """/test should schedule two jobs (ping and check)."""
    save_user_preferences(42, 'alice', '21:00', 3, 'bob')
    ctx = make_context()
    ctx.job_queue.get_jobs_by_name = MagicMock(return_value=[])

    u = make_update(42, 'alice', '/test')
    await handle_test_command(u, ctx)
    assert 'test ping in 1 minute' in last_reply(u).lower()
    assert ctx.job_queue.run_once.call_count == 2


@pytest.mark.asyncio
async def test_test_command_requires_setup():
    """/test without setup should prompt the user."""
    u = make_update(42, 'alice', '/test')
    await handle_test_command(u, make_context())
    assert 'set up' in last_reply(u).lower()


# -- Test ping job callbacks --------------------------------------------------

@pytest.mark.asyncio
async def test_test_ping_callback_sends_message():
    """The _send_test_ping job callback should message the user."""
    test_state[42] = {'ping_sent': False, 'responded': False}
    ctx = make_context()
    ctx.job.data = {'user_id': 42, 'username': 'alice'}
    await _send_test_ping(ctx)
    ctx.bot.send_message.assert_called_once()
    assert 'TEST PING' in ctx.bot.send_message.call_args[1]['text']
    assert test_state[42]['ping_sent'] is True


@pytest.mark.asyncio
async def test_test_check_callback_success():
    """_check_test_response reports success when user has responded."""
    test_state[42] = {'ping_sent': True, 'responded': True}
    ctx = make_context()
    ctx.job.data = {'user_id': 42, 'username': 'alice'}
    await _check_test_response(ctx)
    assert 'successfully' in ctx.bot.send_message.call_args[1]['text'].lower()
    assert 42 not in test_state  # cleaned up


@pytest.mark.asyncio
async def test_test_check_callback_failure():
    """_check_test_response reports failure when user hasn't responded."""
    test_state[42] = {'ping_sent': True, 'responded': False}
    ctx = make_context()
    ctx.job.data = {'user_id': 42, 'username': 'alice'}
    await _check_test_response(ctx)
    assert 'no response' in ctx.bot.send_message.call_args[1]['text'].lower()
    assert 42 not in test_state  # cleaned up


# -- send_ping periodic job ---------------------------------------------------

@pytest.mark.asyncio
async def test_send_ping_at_scheduled_time():
    """send_ping should message a user when current time matches their pref."""
    now = datetime.now()
    pref_time = f"{now.hour:02d}:{now.minute:02d}"
    save_user_preferences(42, 'alice', pref_time, 3, 'bob')

    ctx = make_context()
    await send_ping(ctx)

    ctx.bot.send_message.assert_called_once()
    call_kwargs = ctx.bot.send_message.call_args[1]
    assert call_kwargs['chat_id'] == 42
    assert 'How are you doing' in call_kwargs['text']


@pytest.mark.asyncio
async def test_send_ping_skips_if_already_responded():
    """send_ping should not message a user who already responded today."""
    now = datetime.now()
    pref_time = f"{now.hour:02d}:{now.minute:02d}"
    save_user_preferences(42, 'alice', pref_time, 3, 'bob')
    record_ping(42, date.today().isoformat(), response_received=now)

    ctx = make_context()
    await send_ping(ctx)
    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_ping_skips_wrong_time():
    """send_ping should not message users when it's not their scheduled time."""
    now = datetime.now()
    other_hour = (now.hour + 6) % 24
    save_user_preferences(42, 'alice', f"{other_hour:02d}:00", 3, 'bob')

    ctx = make_context()
    await send_ping(ctx)
    ctx.bot.send_message.assert_not_called()


# -- Buddy notification -------------------------------------------------------

@pytest.mark.asyncio
async def test_buddy_notified_after_deadline():
    """send_ping should notify the buddy when the response window expires."""
    # Set preferred time to 2 hours ago so deadline (1 hour window) has passed
    two_hours_ago = datetime.now() - timedelta(hours=2)
    pref_time = f"{two_hours_ago.hour:02d}:{two_hours_ago.minute:02d}"

    # alice's buddy is bob — bob must also be registered
    save_user_preferences(42, 'alice', pref_time, 1, 'bob')
    save_user_preferences(99, 'bob', '08:00', 3)

    # Record that a ping was sent but not responded to
    record_ping(42, date.today().isoformat(), ping_sent=two_hours_ago)

    ctx = make_context()
    await send_ping(ctx)

    # Bob (user_id 99) should have been messaged
    ctx.bot.send_message.assert_called_once()
    call_kwargs = ctx.bot.send_message.call_args[1]
    assert call_kwargs['chat_id'] == 99
    assert 'alice' in call_kwargs['text'].lower()


@pytest.mark.asyncio
async def test_buddy_not_notified_twice():
    """Once the buddy has been notified, don't notify again."""
    two_hours_ago = datetime.now() - timedelta(hours=2)
    pref_time = f"{two_hours_ago.hour:02d}:{two_hours_ago.minute:02d}"

    save_user_preferences(42, 'alice', pref_time, 1, 'bob')
    save_user_preferences(99, 'bob', '08:00', 3)

    # Ping sent AND buddy already notified
    record_ping(42, date.today().isoformat(), ping_sent=two_hours_ago)
    record_ping(42, date.today().isoformat(), buddy_notified=datetime.now())

    ctx = make_context()
    await send_ping(ctx)
    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_buddy_not_notified_if_unregistered():
    """If the buddy hasn't started the bot, we can't message them."""
    two_hours_ago = datetime.now() - timedelta(hours=2)
    pref_time = f"{two_hours_ago.hour:02d}:{two_hours_ago.minute:02d}"

    save_user_preferences(42, 'alice', pref_time, 1, 'stranger')
    record_ping(42, date.today().isoformat(), ping_sent=two_hours_ago)

    ctx = make_context()
    await send_ping(ctx)
    ctx.bot.send_message.assert_not_called()


# -- Input validation during setup --------------------------------------------

@pytest.mark.asyncio
async def test_bad_time_reprompts():
    """Invalid time input should re-ask, not crash."""
    ctx = make_context()

    u1 = make_update(42, 'alice', 'hi')
    await handle_message(u1, ctx)

    u2 = make_update(42, 'alice', 'banana')
    await handle_message(u2, ctx)
    assert "couldn't understand" in last_reply(u2).lower()

    # Valid time should still work after the bad attempt
    u3 = make_update(42, 'alice', '9 PM')
    await handle_message(u3, ctx)
    assert '9 PM' in last_reply(u3)


@pytest.mark.asyncio
async def test_bad_hours_reprompts():
    """Invalid hours input should re-ask."""
    ctx = make_context()

    u1 = make_update(42, 'alice', 'hi')
    await handle_message(u1, ctx)
    u2 = make_update(42, 'alice', '9 PM')
    await handle_message(u2, ctx)

    u3 = make_update(42, 'alice', '99')
    await handle_message(u3, ctx)
    assert 'between 1 and 12' in last_reply(u3)

    u4 = make_update(42, 'alice', '3')
    await handle_message(u4, ctx)
    assert 'notify' in last_reply(u4).lower()
