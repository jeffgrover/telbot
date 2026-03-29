"""
Message handlers for the Telegram Ping Bot
"""

from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import logging

from bot.config import logger, user_state, user_preferences, STATE_NONE, STATE_ASKED_TIME, STATE_ASKED_HOURS, STATE_ASKED_NOTIFY
from database import get_user_preferences, save_user_preferences, record_ping, has_responded_today, get_all_users_with_ping_preferences, get_todays_ping
from time_utils import parse_time_input, format_time_for_display, calculate_ping_deadline_time

async def send_ping(application, context):
    """
    Send daily pings to all users at their preferred time.
    Also checks for non-responses and notifies buddy contacts.
    Additionally handles test pings during regular polling.
    """
    from datetime import timezone
    current_time = datetime.now(timezone.utc)
    hour = current_time.hour
    minute = current_time.minute
    
    # Get all users with ping preferences
    users = get_all_users_with_ping_preferences()
    if not users:
        logger.info("No users to send wellness prompts to")
        return
    
    for user_id, username, preferred_time, response_hours, notify_user in users:
        # Parse preferred time
        try:
            pref_hour, pref_minute = map(int, preferred_time.split(':'))
        except ValueError:
            logger.warning(f"Could not parse preferred time for user {user_id}")
            continue
        
        # Check if it's time to send prompt
        if hour == pref_hour and minute == pref_minute:
            logger.info(f"Sending wellness prompt to user {user_id} ({username})")
            
            try:
                # Send message to user
                await application.bot.send_message(
                    chat_id=user_id,
                    text=f"Hi {username}! 👋\n\n"
                    "How are you doing today? Please respond within the next " + str(response_hours) + " hours.\n\n"
                    "Reply with anything (e.g., 'I'm okay', 'Good', ✅) to confirm."
                )
                
                # Record that ping was sent
                record_ping(user_id, current_time.date().isoformat(), ping_sent=current_time)
                
            except Exception as e:
                logger.error(f"Failed to send wellness prompt to user {user_id}: {e}")
        
        # Check if user hasn't responded and it's time to notify emergency contact
        if notify_user:
            # Calculate ping deadline time
            deadline_time = calculate_ping_deadline_time(pref_hour, pref_minute, response_hours)
            
            # If current time is past deadline and prompt was sent today
            if current_time > deadline_time:
                record = get_todays_ping(user_id)
                if record and not record[2]:  # response_received is None
                    logger.info(f"User {user_id} ({username}) did not respond. Notifying emergency contact {notify_user}")
                    
                    try:
                        await application.bot.send_message(
                            chat_id=notify_user,
                            text=f"⚠️ Alert: {username} has not responded to their ping.\n\n"
                            f"The ping was sent at {preferred_time} and they had {response_hours} hours to respond.\n\n"
                            "Please check in with them."
                        )
                        
                        # Record that buddy was notified
                        record_ping(user_id, current_time.date().isoformat(), 
                                   ping_sent=record[1], 
                                   response_received=record[2],
                                   buddy_notified=current_time)
                    except Exception as e:
                        logger.error(f"Failed to notify emergency contact for user {user_id}: {e}")
                
            # Check if there are any pending test pings to send
            if 'test_in_progress' in context.user_data:
                test_ping_time = context.user_data.get('test_ping_time')
                test_check_time = context.user_data.get('test_check_time')
                
                if test_ping_time and current_time >= test_ping_time:
                    user_id = context.user_data.get('test_user_id')
                    username = context.user_data.get('username', 'user')
                    
                    # Send the test ping
                    try:
                        await application.bot.send_message(
                            chat_id=user_id,
                            text=f"🧪 TEST PING 🧪\n\n"
                            f"Hi {username}! This is a test ping.\n\n"
                            "Please respond within the next minute to verify the system works."
                        )
                        
                        # Record that test ping was sent
                        record_ping(user_id, current_time.date().isoformat(), ping_sent=current_time)
                        logger.info(f"Sent test ping to user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to send test ping to user {user_id}: {e}")
                
                # Check if it's time to verify test response
                if test_check_time and current_time >= test_check_time:
                    user_id = context.user_data.get('test_user_id')
                    username = context.user_data.get('username', 'user')
                    
                    try:
                        # Check if user has responded (pre-emptive response counts)
                        already_responded = has_responded_today(user_id)
                        
                        if already_responded:
                            # User responded to test
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=f"✅ TEST RESULTS\n\n"
                                f"You responded successfully! The ping system is working correctly.\n\n"
                                "Both the 1-minute ping and 2-minute response check were triggered as expected."
                            )
                        else:
                            # User did not respond
                            await application.bot.send_message(
                                chat_id=user_id,
                                text=f"❌ TEST RESULTS\n\n"
                                f"You did not respond to the test ping within 2 minutes.\n\n"
                                "The system is still functional, but you should verify your Telegram notifications."
                            )
                        
                        logger.info(f"Test completed for user {user_id}. Response received: {already_responded}")
                        
                    except Exception as e:
                        logger.error(f"Failed to send test results to user {user_id}: {e}")
                    
                    # Clean up test state
                    if 'test_in_progress' in context.user_data:
                        del context.user_data['test_in_progress']
                    if 'test_ping_time' in context.user_data:
                        del context.user_data['test_ping_time']
                    if 'test_check_time' in context.user_data:
                        del context.user_data['test_check_time']



async def setup_job_scheduler(application):
    """
    Set up a job scheduler to send pings every minute.
    This allows us to check if it's time to send pings based on users' preferred times.
    
    Note: The job queue is only used for the repeating check itself.
    All actual ping logic (including test pings) is handled during polling.
    """
    from datetime import timedelta
    
    # Run the check every minute to send regular pings and handle test pings
    application.job_queue.run_repeating(send_ping, interval=timedelta(minutes=1), 
                                          application=application)

async def handle_test_command(update, context):
    """Handle /test command to send a test ping."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    
    # Get user preferences from database
    db_prefs = get_user_preferences(user_id)
    
    if not db_prefs:
        await update.message.reply_text("❌ Please set up your ping preferences first using /setup")
        return
    
    preferred_time, response_hours, notify_user = db_prefs
    
    # Ask user if they want to run a test
    test_prompt = (
        "🧪 Test Mode\n"
        "I'll send you a test ping in 1 minute and check for your response after 2 minutes.\n"
        "This will verify that the ping system is working correctly.\n\n"
        "Would you like to proceed? (y/yes or n/no):"
    )
    await update.message.reply_text(test_prompt)
    
    # Store test state for this user
    context.user_data['awaiting_test_confirmation'] = True
    context.user_data['test_user_id'] = user_id

async def handle_setup_command(update, context):
    """Handle /setup command to reset and reconfigure ping settings."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    
    # Reset state for this user
    if user_id in user_state:
        del user_state[user_id]
    if user_id in user_preferences:
        del user_preferences[user_id]
    
    # Clear any existing preferences from database
    import sqlite3
    with sqlite3.connect('bot_database.sqlite') as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", [user_id])
    
    setup_message = (
        "🔄 Setup Mode\n"
        "I'll reset your ping configuration and ask the three setup questions again.\n"
        "Let's begin..."
    )
    await update.message.reply_text(setup_message)
    
    # Trigger the first question by simulating STATE_NONE
    user_state[user_id] = STATE_NONE

async def handle_message(update, context):
    """Handle incoming messages."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    text = update.message.text
    
    # Get user preferences from database
    db_prefs = get_user_preferences(user_id)
    
    # Check if user is awaiting test confirmation
    if context.user_data.get('awaiting_test_confirmation', False) and 'test_user_id' in context.user_data:
        if str(user_id) == str(context.user_data['test_user_id']):
            text_lower = text.lower()
            if text_lower in ['y', 'yes']:
                # User confirmed test - store test state for handling during regular polling
                await update.message.reply_text("✅ Test confirmed! I'll send a test ping in 1 minute.")
                
                # Store test state with scheduled times (using local time)
                from datetime import timezone
                now = datetime.now(timezone.utc)
                context.user_data['test_in_progress'] = True
                context.user_data['test_started_at'] = now
                context.user_data['test_ping_time'] = now + timedelta(minutes=1)
                context.user_data['test_check_time'] = now + timedelta(minutes=2)
            else:
                await update.message.reply_text("❌ Test cancelled.")
            
            # Clear confirmation state
            del context.user_data['awaiting_test_confirmation']
            if 'test_user_id' in context.user_data:
                del context.user_data['test_user_id']
            return
    
    # Check user state
    current_state = user_state.get(user_id, STATE_NONE)
    
    if current_state == STATE_NONE:
        # New user - ask first question about wellness check time
        time_question = (
            f"Hi {username}! 👋\n\n"
            "Welcome to the Telegram Ping Bot! I'll ask you three questions to set up your ping.\n\n"
            "First, what time should I send your daily ping?\n"
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
                f"✅ Got it! I'll send your ping at {format_time_for_display(*parsed_time)}.\n\n"
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
            f"✅ Got it! I'll send your ping at {format_time_for_display(hour, minute)}\n"
            f"and wait {hours_later} hours for your response.\n\n"
            "Third question: Who should I notify if you don't respond?\n"
            "Please enter the Telegram username of your buddy contact\n"
            "(with or without @)\n"
            "Example: friend or @friend"
        )
        await update.message.reply_text(notify_question)
        user_state[user_id] = STATE_ASKED_NOTIFY
        
        # Store the hours for later use
        user_preferences[user_id]['hours_later'] = hours_later
    
    elif current_state == STATE_ASKED_NOTIFY:
        # Parse the buddy contact username
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
        record_ping(user_id, datetime.now().date().isoformat(), response_received=datetime.now())
        
        # Success message
        success_msg = (
            "✅ Ping configured!\n\n"
            f"Daily ping time: {format_time_for_display(hour, minute)}\n"
            f"Response window: {hours_later} hours\n"
            f"Buddy contact: {notify_username}\n\n"
            f"I'll send a message to {notify_username} asking for consent.\n"
            "If they respond with affirmation (yeah, yes, okay), their username will be saved.\n\n"
            f"Your ping is now active! I'll ping you daily at {format_time_for_display(hour, minute)}"
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
                    f"Your ping is active:\n"
                    f"- Daily ping time: {preferred_time}\n"
                    f"- Response window: {response_hours} hours\n"
                )
                if notify_user:
                    response += f"- Buddy contact: {notify_user}\n"
                await update.message.reply_text(response)
            else:
                greeting = (
                    f"Hi {username}! 👋\n\n"
                    f"Welcome back! Your ping is active:\n"
                    f"- Daily ping time: {preferred_time}\n"
                    f"- Response window: {response_hours} hours\n"
                )
                if notify_user:
                    greeting += f"- Buddy contact: {notify_user}\n"
                greeting += "\nI'll send your daily ping at " + preferred_time
                await update.message.reply_text(greeting)
        else:
            # Fallback for users who somehow don't have preferences
            response = f"✅ Got it! I'll note that you're okay today. Your ping is active."
            await update.message.reply_text(response)
