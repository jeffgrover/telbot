#!/usr/bin/env python3
"""
Telegram Ping Bot - Main Entry Point

This bot performs friendly check-ins via Telegram:
1. Asks three questions on first contact (preferred ping time, response window, buddy contact)
2. Sends daily pings at preferred time
3. Waits for user response within specified hours
4. Notifies designated buddy if no response received
5. Stores all preferences in SQLite database
"""

import os
import logging
import sys
import atexit
import asyncio
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

from bot.config import logger
from bot.handlers import (
    handle_message,
    handle_test_command,
    handle_check_command,
    handle_setup_command,
    send_ping
)
from database import init_db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def cleanup_lockfile():
    """Remove the lock file on exit."""
    lock_file = 'bot.lock'
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except OSError as e:
            logger.warning(f'Failed to remove lock file: {e}')

def main():
    """Start the bot."""
    # Get token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error('TELEGRAM_BOT_TOKEN environment variable not set')
        return

    # Check for existing lock file to prevent multiple instances
    lock_file = 'bot.lock'
    if os.path.exists(lock_file):
        logger.error('Another bot instance is already running. Exiting to prevent conflicts.')
        sys.exit(1)

    # Create lock file and register cleanup handler
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(cleanup_lockfile)
    except IOError as e:
        logger.error(f'Failed to create lock file: {e}')
        sys.exit(1)

    # Initialize database on first run
    if not os.path.exists('bot_database.sqlite'):
        init_db()

    # Create application and add handlers
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('test', handle_test_command))
    application.add_handler(CommandHandler('check', handle_check_command))
    application.add_handler(CommandHandler('setup', handle_setup_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))



    logger.info('Bot started and running...')
    application.run_polling()

if __name__ == '__main__':
    main()
