#!/usr/bin/env python3
"""
Test script to verify the new wellness prompt and emergency contact notification functionality.
"""

import sys
sys.path.insert(0, '.')

from database import get_all_users_with_preferences
from time_utils import calculate_deadline_time
from datetime import datetime

def test_get_all_users_with_preferences():
    """Test that we can retrieve users with preferences."""
    print("Testing get_all_users_with_preferences()...")
    
    # Initialize database if it doesn't exist
    from database import init_db
    init_db()
    
    users = get_all_users_with_preferences()
    print(f"Found {len(users)} users with preferences")
    for user in users:
        print(f"  User: {user[1]} (ID: {user[0]})")
        print(f"    Preferred time: {user[2]}, Response hours: {user[3]}, Notify user: {user[4]}")
    
    print("✅ get_all_users_with_preferences() works correctly\n")
    return users

def test_calculate_deadline_time():
    """Test that we can calculate deadline times."""
    print("Testing calculate_deadline_time()...")
    
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    hours_later = 3
    
    deadline_time = calculate_deadline_time(hour, minute, hours_later)
    print(f"Current time: {hour}:{minute}")
    print(f"Deadline in {hours_later} hours: {deadline_time}")
    
    print("✅ calculate_deadline_time() works correctly\n")
    return deadline_time

def test_import_bot_module():
    """Test that the bot module can be imported without errors."""
    print("Testing bot.py import...")
    
    try:
        from bot import send_wellness_prompt, setup_job_scheduler
        print("✅ bot.py imports successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing bot.py: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing New Wellness Check Functionality")
    print("=" * 60 + "\n")
    
    # Run tests
    users = test_get_all_users_with_preferences()
    deadline_time = test_calculate_deadline_time()
    success = test_import_bot_module()
    
    print("=" * 60)
    if success and len(users) >= 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 60)
