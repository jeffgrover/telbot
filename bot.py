#!/usr/bin/env python3
"""
Simple Telegram Echo Bot

This bot responds to messages with:
- A greeting message on first contact
- "You said: " followed by the user's message
"""

import os
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to track if user has sent first message
user_first_message = {}

async def handle_message(update, context):
    """Handle incoming messages."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    text = update.message.text
    
    # Check if this is the first message from this user
    if user_id not in user_first_message:
        greeting = (
            f"Hi {username}! 👋\n\n"
            "I'm a simple echo bot. I'll respond to your messages by repeating what you say.\n"
            "Just send me any message and I'll reply with: 'You said: ...'\n\n"
            "Try it now!"
        )
        await update.message.reply_text(greeting)
        user_first_message[user_id] = True
    
    # Echo the user's message
    response = f"You said: {text}"
    await update.message.reply_text(response)

def main():
    """Start the bot."""
    # Get token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error('TELEGRAM_BOT_TOKEN environment variable not set')
        return
    
    # Create application and add handlers
    application = Application.builder().token(token).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info('Bot started and running...')
    application.run_polling()

if __name__ == '__main__':
    main()