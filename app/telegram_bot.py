"""
Telegram bot implementation
"""
import os
import json
import logging
import asyncio
from flask import request, jsonify

from telegram import Bot, Update
import telegram.error
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Configure logging
logger = logging.getLogger(__name__)

# Get the bot token from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'dummy_token_for_development')

if not TELEGRAM_BOT_TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN is not set in environment variables, using dummy token for development")

# Create a global event loop for all async operations
# Instead of creating and closing loops for each request, we'll use a single long-running loop
# This helps avoid "Event loop is closed" errors
def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()
        raise

# Initialize the bot and application with proper connection pooling
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = (ApplicationBuilder()
              .token(TELEGRAM_BOT_TOKEN)
              .concurrent_updates(False)
              .connection_pool_size(8)  # Increase connection pool size
              .connect_timeout(10.0)    # Increase timeout
              .pool_timeout(10.0)       # Increase pool timeout
              .read_timeout(7.0)        # Set read timeout
              .write_timeout(7.0)       # Set write timeout
              .build())

def get_bot_status():
    """Get the status of the bot"""
    # Check if we're in development mode
    if TELEGRAM_BOT_TOKEN == 'dummy_token_for_development':
        return jsonify({
            'success': True,
            'development_mode': True,
            'message': 'Bot is running in development mode'
        })
    
    try:
        # Use direct API calls with requests
        import requests
        
        # Get bot info
        get_me_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        me_response = requests.post(get_me_url)
        me_data = me_response.json().get('result', {})
        
        # Get webhook info
        get_webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        webhook_response = requests.post(get_webhook_url)
        webhook_data = webhook_response.json().get('result', {})
        
        # Format the response
        return jsonify({
            'success': True,
            'bot_info': {
                'id': me_data.get('id'),
                'username': me_data.get('username'),
                'first_name': me_data.get('first_name'),
                'is_bot': me_data.get('is_bot', True)
            },
            'webhook_info': webhook_data,
            'development_mode': False
        })
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'development_mode': (TELEGRAM_BOT_TOKEN == 'dummy_token_for_development')
        })

async def process_update(update_data):
    """Process incoming Telegram updates"""
    # Initialize the application and bot if needed
    if not getattr(application, "_initialized", False):
        try:
            # Initialize the bot first
            await bot.initialize()
            
            # Then initialize the application
            await application.initialize()
            setattr(application, "_initialized", True)
            
            # Import handlers here to avoid circular imports
            from handlers import (
                start, therapy, journal, stats, summary, report, broadcast,
                help_command, button_callback, message_handler, list_trades
            )
            
            # Register handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("therapy", therapy))
            application.add_handler(CommandHandler("journal", journal))
            application.add_handler(CommandHandler("trades", list_trades))
            application.add_handler(CommandHandler("stats", stats))
            application.add_handler(CommandHandler("summary", summary))
            application.add_handler(CommandHandler("report", report))
            application.add_handler(CommandHandler("broadcast", broadcast))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CallbackQueryHandler(button_callback))
            application.add_handler(MessageHandler(filters.ALL, message_handler))
            
            logger.info("Bot and application successfully initialized")
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}")
            return f"Error: {str(e)}"
    
    # Process the update
    try:
        update = Update.de_json(update_data, bot)
        await application.process_update(update)
    except telegram.error.TimedOut as e:
        logger.error(f"Timeout error: {str(e)}")
        # For timeouts, we need to reset connections
        try:
            if hasattr(application.bot.request, 'connection_pool'):
                application.bot.request.connection_pool.dispose()
                logger.info("Reset connection pool due to timeout")
        except Exception as inner_e:
            logger.error(f"Failed to reset connection pool: {str(inner_e)}")
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
    
    return 'OK'

def handle_webhook():
    """Handle webhook requests from Telegram"""
    if request.method == 'POST':
        # Check if we're in development mode
        if TELEGRAM_BOT_TOKEN == 'dummy_token_for_development':
            logger.info("Development mode active. Webhook request simulated.")
            return 'Development Mode - Update simulated'
        
        try:
            update_data = request.get_json()
            
            if not update_data:
                logger.warning("Received empty update data")
                return jsonify({
                    'success': False,
                    'error': 'Empty update data'
                })
                
            logger.debug(f"Received update: {json.dumps(update_data, indent=2)}")
            
            # Get or create an event loop (reusing the global loop when possible)
            loop = get_or_create_eventloop()
            
            try:
                # Run bot.initialize() at the beginning to ensure bot is ready
                async def init_and_process():
                    try:
                        # Initialize bot if needed
                        if not getattr(bot, "_initialized", False):
                            await bot.initialize()
                            setattr(bot, "_initialized", True)
                            
                        # Process the update
                        return await process_update(update_data)
                    except Exception as e:
                        logger.error(f"Error in init_and_process: {str(e)}")
                        return f"Error: {str(e)}"
                
                result = loop.run_until_complete(init_and_process())
                logger.debug(f"Webhook processing result: {result}")
            except Exception as e:
                logger.error(f"Error in async execution: {str(e)}")
                
            return 'OK'
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            # Return a 200 response regardless of errors to prevent Telegram from retrying
            return jsonify({
                'success': False,
                'error': str(e)
            })
            
    return 'Only POST requests are accepted'

def setup_webhook():
    """Set up the webhook for Telegram"""
    # Check if we're in development mode
    if TELEGRAM_BOT_TOKEN == 'dummy_token_for_development':
        return jsonify({
            'success': False,
            'message': 'Development mode active. No webhook set up. Please set TELEGRAM_BOT_TOKEN environment variable for production.',
            'mode': 'development'
        })
    
    # For Render deployment, get the hostname from the request
    host = request.headers.get('Host')
    webhook_url = f"https://{host}/webhook"
    
    # Store the host in our keepalive module for self-pinging
    try:
        from app.keepalive import keep_alive_thread
        keep_alive_thread.set_host(host)
        logger.info(f"Keep-alive thread updated with host: {host}")
    except Exception as e:
        logger.error(f"Failed to update keep-alive thread with host: {str(e)}")
    
    try:
        # Create separate API calls rather than using asyncio
        import requests
        
        # Delete existing webhook
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
        delete_response = requests.post(delete_url)
        
        # Set new webhook
        set_webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        set_webhook_params = {"url": webhook_url}
        set_response = requests.post(set_webhook_url, json=set_webhook_params)
        
        # Get webhook info
        get_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        info_response = requests.post(get_info_url)
        
        webhook_info = info_response.json().get('result', {})
        
        # Initialize the bot if not already done
        loop = get_or_create_eventloop()
        async def init_bot_if_needed():
            try:
                if not getattr(bot, "_initialized", False):
                    await bot.initialize()
                    setattr(bot, "_initialized", True)
                    logger.info("Bot initialized during webhook setup")
            except Exception as e:
                logger.error(f"Error initializing bot during setup: {str(e)}")
        
        try:
            loop.run_until_complete(init_bot_if_needed())
        except Exception as e:
            logger.error(f"Error in async execution during setup: {str(e)}")
        
        return jsonify({
            'success': True,
            'webhook_url': webhook_url,
            'delete_response': delete_response.json(),
            'set_response': set_response.json(),
            'webhook_info': webhook_info
        })
    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })