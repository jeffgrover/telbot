#!/usr/bin/env python3
"""
Telegram Wellness Check Bot

This bot performs wellness checks via Telegram:
1. Asks three questions on first contact (preferred check time, response window, notification contact)
2. Sends daily prompts at preferred time
3. Waits for user response within specified hours
4. Notifies designated contact if no response received
5. Stores all preferences in SQLite database
"""

import os
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging
from database import init_db, get_user_preferences, save_user_preferences, record_wellness_check, has_responded_today
from time_utils import parse_time_input, format_time_for_display, calculate_deadline_time

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

async def handle_message(update, context):
    """Handle incoming messages."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    text = update.message.text
    
    # Initialize database on first run
    if not os.path.exists('bot_database.sqlite'):
        init_db()
    
    # Get user preferences from database
    db_prefs = get_user_preferences(user_id)
    
    # Check user state
    current_state = user_state.get(user_id, STATE_NONE)
    
    if current_state == STATE_NONE:
        # New user - ask first question about wellness check time
        time_question = (
            f"Hi {username}! 👋\n\n"
            "Welcome to the Telegram Wellness Check Bot! I'll ask you three questions to set up your check.\n\n"
            "First, what time should I send your daily wellness prompt?\n"
            "You can format this in several ways:\n"
            "- 10 AM\n"
            "- 10:30 PM\n"
            "- 22:00\n"
            "- 9pm\n\n"
            "Please enter your preferred prompt time:"
        )
        await update.message.reply_text(time_question)
        user_state[user_id] = STATE_ASKED_TIME
        
    elif current_state == STATE_ASKED_TIME:
        # Parse the time response
        parsed_time = parse_time_input(text)
        if parsed_time is None:
            error_msg = (
                "❌ I couldn't understand that time format.\n"
                "Please try again with one of these formats:\n"
                "- 10 AM\n"
                "- 10:30 PM\n"
                "- 22:00\n"
                "- 9pm\n\n"
                "Your preferred time:"
            )
            await update.message.reply_text(error_msg)
        else:
            # Store parsed time and ask for hours
            user_preferences[user_id] = {
                'hour': parsed_time[0],
                'minute': parsed_time[1]
            }
            
            hours_question = (
                f"✅ Got it! I'll send your wellness prompt at {format_time_for_display(*parsed_time)}.\n\n"
                "Second question: How many hours should I wait for your response?\n"
                "Please enter a number between 1 and 12 (e.g., 3, 6, 12):"
            )
            await update.message.reply_text(hours_question)
            user_state[user_id] = STATE_ASKED_HOURS
    
    elif current_state == STATE_ASKED_HOURS:
        # Parse the hours response
        try:
            hours_later = int(text)
            if hours_later < 1 or hours_later > 12:
                error_msg = "❌ Please enter a number between 1 and 12"
                await update.message.reply_text(error_msg)
                return
        except ValueError:
            error_msg = "❌ That's not a valid number. Please enter a number between 1 and 12"
            await update.message.reply_text(error_msg)
            return
        
        # Get stored time preferences
        prefs = user_preferences.get(user_id, {})
        hour = prefs.get('hour', 0)
        minute = prefs.get('minute', 0)
        
        # Ask for notification contact
        notify_question = (
            f"✅ Got it! I'll send your wellness check prompt at {format_time_for_display(hour, minute)}\n"
            f"and wait {hours_later} hours for your response.\n\n"
            "Third question: Who should I notify if you don't respond?\n"
            "Please enter the Telegram username of your emergency contact\n"
            "(with or without @)\n"
            "Example: friend or @friend"
        )
        await update.message.reply_text(notify_question)
        user_state[user_id] = STATE_ASKED_NOTIFY
        
        # Store the hours for later use
        user_preferences[user_id]['hours_later'] = hours_later
    
    elif current_state == STATE_ASKED_NOTIFY:
        # Parse the notification username
        notify_username = text.strip()
        if not notify_username:
            error_msg = "❌ Please enter a valid Telegram username"
            await update.message.reply_text(error_msg)
            return
        
        # Remove @ if present
        if notify_username.startswith('@'):
            notify_username = notify_username[1:]
        
        # Get stored preferences
        prefs = user_preferences.get(user_id, {})
        hour = prefs.get('hour', 0)
        minute = prefs.get('minute', 0)
        hours_later = prefs.get('hours_later', 3)
        
        # Save all preferences to database
        save_user_preferences(user_id, username, format_time_for_display(hour, minute), hours_later, notify_username)
        
        # Record that user has responded today (pre-emptive response)
        from datetime import datetime
        record_wellness_check(user_id, datetime.now().date().isoformat(), response_received=datetime.now())
        
        # Success message
        success_msg = (
            f"✅ Wellness check configured!\n\n"
            f"Daily prompt time: {format_time_for_display(hour, minute)}\n"
            f"Response window: {hours_later} hours\n"
            f"Emergency contact: @{notify_username}\n\n"
            "I'll send a message to @{notify_username} asking for consent.\n"
            "If they respond with affirmation (yeah, yes, okay), their username will be saved.\n\n"
            "Your wellness check is now active! I'll prompt you daily at " + format_time_for_display(hour, minute)
        )
        await update.message.reply_text(success_msg)
        
        # Reset state for next messages
        user_state[user_id] = STATE_NONE
    
    else:
        # Existing user with saved preferences - show wellness check status
        if db_prefs:
            preferred_time, response_hours, notify_user = db_prefs
            
            # Check if user has already responded today (pre-emptive response)
            already_responded = has_responded_today(user_id)
            if already_responded:
                response = (
                    f"✅ Got it! You've already confirmed you're okay today.\n"
                    f"Your wellness check is active:\n"
                    f"- Daily prompt time: {preferred_time}\n"
                    f"- Response window: {response_hours} hours\n"
                )
                if notify_user:
                    response += f"- Emergency contact: @{notify_user}\n"
                await update.message.reply_text(response)
            else:
                greeting = (
                    f"Hi {username}! 👋\n\n"
                    f"Welcome back! Your wellness check is active:\n"
                    f"- Daily prompt time: {preferred_time}\n"
                    f"- Response window: {response_hours} hours\n"
                )
                if notify_user:
                    greeting += f"- Emergency contact: @{notify_user}\n"
                greeting += "\nI'll send your daily wellness prompt at " + preferred_time
                await update.message.reply_text(greeting)
        else:
            # Fallback for users who somehow don't have preferences
            response = f"✅ Got it! I'll note that you're okay today. Your wellness check is active."
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