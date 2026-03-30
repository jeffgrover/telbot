# Telegram Ping Bot

A Telegram bot that performs daily check-ins: it pings users at their preferred time and alerts a buddy contact if no response is received within a configurable window.

## Setup

### 1. Create a Telegram Bot
- Open Telegram and search for @BotFather
- Send `/newbot` and follow the prompts
- Save the token BotFather gives you

### 2. Install Dependencies

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync
```

### 3. Run the Bot

```bash
export TELEGRAM_BOT_TOKEN='your_token_here'
source .venv/bin/activate
uv run python -m bot.main
```

Press Ctrl+C to stop.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Begin setup (new user) or show current config (returning user) |
| `/setup` | Reset preferences and reconfigure from scratch |
| `/test` | Send a test ping in 1 minute, check for response after 2 minutes |

Any non-command message from a configured user counts as a check-in for the day.

## How It Works

### Setup Flow
1. User sends `/start` (or any message)
2. Bot asks for preferred daily ping time (e.g. `9 PM`, `22:00`, `3:30 PM`)
3. Bot asks how many hours to wait for a response (1-12)
4. Bot asks for a buddy contact's Telegram username

### Daily Operation
1. At the configured time, the bot sends a ping: "How are you doing today?"
2. If the user responds (any message) within the window, all is good
3. If no response by the deadline, the bot alerts the buddy contact
4. Messages sent *before* the scheduled ping count as a pre-emptive check-in

### Buddy Notification
The buddy contact must also have started the bot (sent it `/start`) so the bot has their chat ID. If the buddy hasn't interacted with the bot, the notification is logged but can't be delivered.

## Project Structure

```
bot/
  __init__.py
  main.py          — entry point, registers handlers and job queue
  config.py        — constants, logger, in-memory state dicts
  handlers.py      — command/message handlers and the periodic send_ping job
database.py        — SQLite operations (users and wellness_checks tables)
time_utils.py      — time parsing, formatting, deadline calculation
tests/
  test_database.py — database CRUD tests
  test_time_utils.py — time utility tests
  test_e2e.py      — end-to-end conversation tests with mocked Telegram
```

## Database

SQLite (`bot_database.sqlite`), two tables:

- **users** — user_id, username, preferred_time (HH:MM), response_hours, notify_user
- **wellness_checks** — one row per user per day tracking ping_sent, response_received, notified_contact

## Running Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

## Time Format Support

The bot accepts:
- 12-hour with AM/PM: `10 AM`, `9 PM`, `3:30 PM`
- 24-hour: `22:00`, `15:45`
- Compact: `9pm`, `9AM`
- Bare hour: `10`, `22`
