#!/usr/bin/env python3
"""
A simple script to test the Telegram bot
"""
import os
import logging
import asyncio
from telegram import Bot

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Test the bot by sending a message to yourself"""
    # Get the bot token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        print("Please set the TELEGRAM_BOT_TOKEN environment variable")
        return
    
    # Create a bot instance
    bot = Bot(token=token)
    
    # Get bot info
    me = await bot.get_me()
    print(f"Bot information: {me.to_dict()}")
    
    # Get updates
    print("Getting updates... (this might take a moment)")
    updates = await bot.get_updates(limit=5)
    
    if not updates:
        print("No recent updates found. Try sending a message to the bot first.")
    else:
        print(f"Found {len(updates)} recent updates:")
        for update in updates:
            print(f"Update ID: {update.update_id}")
            if update.message:
                print(f"From: {update.message.from_user.username or update.message.from_user.first_name}")
                print(f"Text: {update.message.text}")
                print("---")
    
    # Get chat IDs from the updates
    chat_ids = []
    for update in updates:
        if update.message and update.message.chat.id not in chat_ids:
            chat_ids.append(update.message.chat.id)
    
    if chat_ids:
        # Ask user which chat to reply to
        print("\nAvailable chat IDs:")
        for i, chat_id in enumerate(chat_ids):
            print(f"{i+1}. {chat_id}")
        
        try:
            choice = input("\nEnter number to select chat (or press enter to skip): ")
            if choice:
                idx = int(choice) - 1
                if 0 <= idx < len(chat_ids):
                    chat_id = chat_ids[idx]
                    message = "Hello! This is a test message from the Trading Journal Bot."
                    print(f"Sending test message to chat ID {chat_id}...")
                    await bot.send_message(chat_id=chat_id, text=message)
                    print("Message sent successfully!")
        except (ValueError, IndexError):
            print("Invalid selection.")
    else:
        print("No chat IDs found in recent updates.")

if __name__ == "__main__":
    asyncio.run(main())