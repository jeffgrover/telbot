"""
Unit tests for database module.
"""
import os
import sqlite3
from datetime import datetime, date
import pytest

from database import (
    init_db,
    save_user_preferences,
    get_user_preferences,
    record_wellness_check,
    get_todays_wellness_check,
    has_responded_today,
)


@pytest.fixture
def cleanup_database():
    """Remove test database before and after each test."""
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')
    yield
    if os.path.exists('bot_database.sqlite'):
        os.remove('bot_database.sqlite')


@pytest.fixture
def sample_date():
    """Return a sample date string for testing."""
    return date.today().isoformat()


@pytest.fixture
def sample_datetime():
    """Return a sample datetime for testing."""
    return datetime.now()


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_init_db_creates_tables(self, cleanup_database):
        """Test that init_db creates the required tables."""
        init_db()
        
        conn = sqlite3.connect('bot_database.sqlite')
        cursor = conn.cursor()
        
        # Check users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None, "Users table not created"
        
        # Check wellness_checks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wellness_checks'")
        assert cursor.fetchone() is not None, "Wellness_checks table not created"
        
        conn.close()


class TestUserPreferences:
    """Tests for user preferences CRUD operations."""
    
    def test_save_and_get_preferences(self, cleanup_database):
        """Test saving and retrieving user preferences."""
        init_db()
        
        # Save preferences with emergency contact
        save_user_preferences(123456, 'alice', '9 PM', 3, 'bob')
        
        # Retrieve and verify
        prefs = get_user_preferences(123456)
        assert prefs == ('9 PM', 3, 'bob'), f"Expected ('9 PM', 3, 'bob'), got {prefs}"
    
    def test_save_preferences_without_contact(self, cleanup_database):
        """Test saving preferences without emergency contact."""
        init_db()
        
        # Save preferences without emergency contact
        save_user_preferences(789012, 'bob', '10 AM', 5)
        
        # Retrieve and verify
        prefs = get_user_preferences(789012)
        assert prefs == ('10 AM', 5, None), f"Expected ('10 AM', 5, None), got {prefs}"
    
    def test_update_preferences(self, cleanup_database):
        """Test updating existing preferences."""
        init_db()
        
        # Save initial preferences
        save_user_preferences(123456, 'alice', '9 PM', 3, 'bob')
        
        # Update preferences
        save_user_preferences(123456, 'alice', '11 PM', 2, 'charlie')
        
        # Verify update
        prefs = get_user_preferences(123456)
        assert prefs == ('11 PM', 2, 'charlie'), f"Expected ('11 PM', 2, 'charlie'), got {prefs}"
    
    def test_get_nonexistent_user(self, cleanup_database):
        """Test getting preferences for non-existent user."""
        init_db()
        
        prefs = get_user_preferences(999999)
        assert prefs is None, f"Expected None for non-existent user, got {prefs}"


class TestWellnessCheckTracking:
    """Tests for wellness check tracking."""
    
    def test_record_wellness_check(self, cleanup_database, sample_date, sample_datetime):
        """Test recording a wellness check event."""
        init_db()
        
        # Record a check with response
        record_wellness_check(123456, sample_date, response_received=sample_datetime)
        
        # Verify it was recorded
        conn = sqlite3.connect('bot_database.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wellness_checks WHERE user_id = ?", [123456])
        record = cursor.fetchone()
        
        assert record is not None, "Wellness check not recorded"
        assert record[0] > 0, "Invalid ID"
        assert record[1] == 123456, "Wrong user_id"
        assert record[2] == sample_date, "Wrong date"
        assert record[4] is not None, "Response not recorded"
        
        conn.close()
    
    def test_record_check_without_response(self, cleanup_database, sample_date):
        """Test recording a check without response."""
        init_db()
        
        # Record a check without response
        record_wellness_check(123456, sample_date)
        
        # Verify it was recorded
        conn = sqlite3.connect('bot_database.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wellness_checks WHERE user_id = ?", [123456])
        record = cursor.fetchone()
        
        assert record is not None, "Wellness check not recorded"
        assert record[3] is None, "Response should be None"
        assert record[4] is None, "Notified contact should be None"
        
        conn.close()
    
    def test_get_todays_check(self, cleanup_database, sample_date, sample_datetime):
        """Test getting today's wellness check."""
        init_db()
        
        # Record a check for today
        record_wellness_check(123456, sample_date, response_received=sample_datetime)
        
        # Get today's check
        result = get_todays_wellness_check(123456)
        
        assert result is not None, "Today's check not retrieved"
        assert result[0] == sample_date, f"Wrong date: {result[0]}"
        assert result[2] is not None, "Response should be recorded"
    
    def test_get_todays_check_nonexistent(self, cleanup_database):
        """Test getting today's check for user with no record."""
        init_db()
        
        result = get_todays_wellness_check(999999)
        assert result is None, f"Expected None, got {result}"
    
    def test_has_responded_today(self, cleanup_database, sample_date, sample_datetime):
        """Test checking if user has responded today."""
        init_db()
        
        # User who has responded
        record_wellness_check(123456, sample_date, response_received=sample_datetime)
        assert has_responded_today(123456) is True, "User should have responded"
        
        # User who hasn't responded
        assert has_responded_today(789012) is False, "User shouldn't have responded"
    
    def test_has_responded_today_no_prompt_sent(self, cleanup_database, sample_date):
        """Test that user hasn't responded if only prompt was sent."""
        init_db()
        
        # Record check with prompt sent but no response
        record_wellness_check(123456, sample_date, prompt_sent=datetime.now())
        assert has_responded_today(123456) is False, "User shouldn't have responded"


class TestIntegration:
    """Integration tests for multiple database operations."""
    
    def test_complete_workflow(self, cleanup_database, sample_date, sample_datetime):
        """Test a complete workflow of saving preferences and tracking checks."""
        init_db()
        
        # Save user preferences
        save_user_preferences(123456, 'alice', '9 PM', 3, 'bob')
        
        # Verify preferences saved
        prefs = get_user_preferences(123456)
        assert prefs == ('9 PM', 3, 'bob'), f"Preferences not saved correctly: {prefs}"
        
        # Record multiple checks for same user
        record_wellness_check(123456, sample_date, response_received=sample_datetime)
        
        # Verify can get today's check
        todays_check = get_todays_wellness_check(123456)
        assert todays_check is not None, "Today's check not retrieved"
        assert todays_check[2] is not None, "Response not recorded"
        
        # Verify has responded today
        assert has_responded_today(123456) is True, "Should have responded today"
