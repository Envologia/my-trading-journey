#!/usr/bin/env python3
"""
Main bot controller for webhook mode
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for
from telegram import Bot, Update

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the bot token from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# Create a Flask app for handling webhook requests
app = Flask(__name__)

@app.route('/')
def index():
    """Render a simple HTML page for bot verification"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Display bot statistics and user count in a simple dashboard"""
    from models import User
    
    # Get count of all users
    total_users = User.query.count()
    
    # Get count of completed registrations
    registered_users = User.query.filter_by(registration_complete=True).count()
    
    # Get recent users (last 10)
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Create a function to get current time
    def now():
        return datetime.utcnow()
    
    return render_template('dashboard.html', 
                           total_users=total_users,
                           registered_users=registered_users,
                           recent_users=recent_users,
                           now=now)

@app.route('/status')
def bot_status():
    """Get the status of the bot"""
    from app.telegram_bot import get_bot_status
    return get_bot_status()

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle webhook requests from Telegram"""
    from app.telegram_bot import handle_webhook
    return handle_webhook()

@app.route('/setup', methods=['GET'])
def setup_webhook():
    """Setup the Telegram webhook for Render deployment"""
    from app.telegram_bot import setup_webhook
    return setup_webhook()

@app.route('/ping')
def ping_handler():
    """Handle ping requests from keep-alive mechanism"""
    return jsonify({
        "status": "ok",
        "message": "Server is alive"
    })

# Start the keep-alive mechanism
from app.keepalive import start_keep_alive

# Get host from the request in the setup route, so we'll initialize it there
# start_keep_alive() 

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)