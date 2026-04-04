"""Configuration and constants for the Telegram Ping Bot."""

import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# State constants for the setup conversation
STATE_NONE = 0
STATE_ASKED_ROLE = 1
STATE_ASKED_BUDDY_FOR = 2
STATE_ASKED_TIME = 3
STATE_ASKED_HOURS = 4
STATE_ASKED_NOTIFY = 5

# In-memory state tracking (per user_id)
user_state = {}
user_preferences = {}
test_state = {}  # {user_id: {'ping_sent': True, 'responded': False}}
