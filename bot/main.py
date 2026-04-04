#!/usr/bin/env python3
"""Telegram Ping Bot - main entry point."""

import os
import logging
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from bot.handlers import (
    handle_start_command,
    handle_setup_command,
    handle_test_command,
    handle_message,
    send_ping,
)
from database import init_db, check_integrity

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error('TELEGRAM_BOT_TOKEN environment variable not set')
        return

    init_db()
    check_integrity()

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler('start', handle_start_command))
    application.add_handler(CommandHandler('setup', handle_setup_command))
    application.add_handler(CommandHandler('test', handle_test_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Check for pings every 60 seconds
    application.job_queue.run_repeating(send_ping, interval=60, first=10)

    logger.info('Bot started')
    application.run_polling()


if __name__ == '__main__':
    main()
