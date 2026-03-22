# Telegram Echo Bot

A simple Telegram bot that echoes user messages with a greeting on first contact.

## Setup Instructions

### 1. Create a Telegram Bot
- Open Telegram and search for @BotFather
- Send `/newbot` command to create a new bot
- Follow the instructions to name your bot
- BotFather will give you a token (save this for later)

### 2. Install Dependencies
```bash
pip install python-telegram-bot
```

### 3. Run the Bot
```bash
# Set your bot token as an environment variable
export TELEGRAM_BOT_TOKEN='your_bot_token_here'

# Start the bot
python bot.py
```

The bot will run continuously and respond to messages.

## How It Works
- First message from a user gets a welcome greeting
- Subsequent messages are echoed with "You said: " prefix
- Bot runs as a long-lived Python process using polling

## Stopping the Bot
Press Ctrl+C in the terminal where it's running.