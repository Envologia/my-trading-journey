#!/usr/bin/env python3
"""
Run the Telegram bot in polling mode for local development
"""
import asyncio
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Start the bot in polling mode"""
    from app.telegram_bot import application
    
    # Initialize the application
    await application.initialize()
    
    # Make sure we have handlers
    from handlers import (
        start, therapy, journal, stats, summary, report, 
        help_command, button_callback, message_handler
    )
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    
    # Clear any existing handlers to avoid duplicates
    application.handlers.clear()
    
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
    
    # Start polling
    logger.info("Starting bot in polling mode")
    await application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    # Check if we have a token
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        print("Please set the TELEGRAM_BOT_TOKEN environment variable")
        exit(1)
        
    # Run the bot
    asyncio.run(main())