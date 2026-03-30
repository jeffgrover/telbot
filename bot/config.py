"""Configuration and constants for the Telegram Ping Bot."""

import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# State constants for the setup conversation
STATE_NONE = 0
STATE_ASKED_TIME = 1
STATE_ASKED_HOURS = 2
STATE_ASKED_NOTIFY = 3

# In-memory state tracking (per user_id)
user_state = {}
user_preferences = {}
