#!/usr/bin/env python3
"""
Run the Telegram bot in polling mode for local development
"""
import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if we have a token
if not os.environ.get("TELEGRAM_BOT_TOKEN"):
    logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
    print("Please set the TELEGRAM_BOT_TOKEN environment variable")
    sys.exit(1)

# Import the necessary modules
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Import the handlers
from handlers import (
    start, therapy, journal, stats, summary, report, broadcast,
    help_command, button_callback, message_handler, list_trades
)

async def main():
    """Start the bot in polling mode"""
    # Create the application
    application = ApplicationBuilder().token(
        os.environ.get("TELEGRAM_BOT_TOKEN")
    ).build()
    
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
    
    # Start polling
    logger.info("Starting bot in polling mode")
    
    # First, delete any existing webhook
    bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))
    await bot.delete_webhook()
    
    # Start polling
    await application.start()
    await application.updater.start_polling(allowed_updates=["message", "callback_query"])
    
    # Run the bot until a stop signal is received
    await application.updater.stop_when_done()
    await application.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        sys.exit(1)