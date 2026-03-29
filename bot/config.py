"""
Configuration and constants for the Telegram Ping Bot
"""

import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State constants for question flow
STATE_NONE = 0
STATE_ASKED_TIME = 1
STATE_ASKED_HOURS = 2
STATE_ASKED_NOTIFY = 3

# Dictionaries to track user state and preferences
user_state = {}  # Tracks which question the user is answering
user_preferences = {}  # Stores parsed time data temporarily
