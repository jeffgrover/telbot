# Telegram Ping Bot

A daily check-in bot: pings users at their preferred time, tracks responses, and alerts a buddy contact if no response within the configured window.

## Running

```bash
export TELEGRAM_BOT_TOKEN='...'
source .venv/bin/activate
uv run python -m bot.main
```

## Testing

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -v
```

Three test files:
- `tests/test_database.py` — database CRUD and upsert logic
- `tests/test_time_utils.py` — time parsing, formatting, deadline calculation
- `tests/test_e2e.py` — full conversation flows with mocked Telegram objects

## Project structure

```
bot/
  __init__.py
  main.py          — entry point, registers handlers and job queue
  config.py        — constants, logger, in-memory state dicts
  handlers.py      — all command/message handlers and the send_ping job
database.py        — SQLite operations (users table, wellness_checks table)
time_utils.py      — time parsing, formatting, deadline calculation
```

## Key design decisions

- Times stored in DB as `HH:MM` (24-hour), displayed to users as 12-hour (e.g. "9 PM")
- `record_ping()` upserts — one row per user per day, fields accumulate
- `send_ping()` is a job queue callback (`context: ContextTypes.DEFAULT_TYPE`), not called with `application`
- Buddy notification requires the buddy to have also started the bot (looked up by username in users table via `get_user_by_username()`)
- Setup state is in-memory (`user_state` dict); returning users with DB prefs skip setup
- `/test` uses `job_queue.run_once` for the delayed ping/check, not polling
