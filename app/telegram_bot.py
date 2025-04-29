"""
Telegram bot implementation
"""
import os
import json
import logging
import asyncio
from flask import request, jsonify

from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Configure logging
logger = logging.getLogger(__name__)

# Get the bot token from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'dummy_token_for_development')

if not TELEGRAM_BOT_TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN is not set in environment variables, using dummy token for development")

# Initialize the bot and application
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

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
    # Initialize the application if needed
    if not getattr(application, "_initialized", False):
        await application.initialize()
        setattr(application, "_initialized", True)
        
        # Import handlers here to avoid circular imports
        from handlers import (
            start, therapy, journal, stats, summary, report, 
            help_command, button_callback, message_handler
        )
        
        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("therapy", therapy))
        application.add_handler(CommandHandler("journal", journal))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("summary", summary))
        application.add_handler(CommandHandler("report", report))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.ALL, message_handler))
    
    # Process the update
    update = Update.de_json(update_data, bot)
    await application.process_update(update)
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
            
            # We need to run this asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(process_update(update_data))
            finally:
                loop.close()
                
            return 'OK'
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
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