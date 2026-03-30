"""Tests for the database module."""

import os
from datetime import datetime, date
import pytest
from database import (
    init_db, save_user_preferences, get_user_preferences,
    record_ping, get_todays_ping, has_responded_today,
    get_all_users_with_ping_preferences, get_user_by_username,
)


@pytest.fixture(autouse=True)
def clean_database():
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')
    init_db()
    yield
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')


def test_save_and_get_preferences():
    save_user_preferences(123, 'alice', '21:00', 3, 'bob')
    assert get_user_preferences(123) == ('21:00', 3, 'bob')


def test_nonexistent_user_returns_none():
    assert get_user_preferences(999) is None


def test_ping_upsert_preserves_fields():
    today = date.today().isoformat()
    now = datetime.now()
    record_ping(123, today, ping_sent=now)
    record_ping(123, today, response_received=now)
    result = get_todays_ping(123)
    assert result[1] is not None  # ping_sent kept
    assert result[2] is not None  # response_received added


def test_has_responded_today():
    today = date.today().isoformat()
    record_ping(123, today, ping_sent=datetime.now())
    assert has_responded_today(123) is False
    record_ping(123, today, response_received=datetime.now())
    assert has_responded_today(123) is True


def test_get_user_by_username():
    save_user_preferences(123, 'alice', '21:00', 3)
    assert get_user_by_username('alice') == 123
    assert get_user_by_username('nobody') is None


def test_get_all_users():
    save_user_preferences(1, 'alice', '09:00', 3)
    save_user_preferences(2, 'bob', '21:00', 2)
    assert len(get_all_users_with_ping_preferences()) == 2
