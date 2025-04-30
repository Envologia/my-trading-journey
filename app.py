import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_journal_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models here
    import models  # noqa: F401
    
    # Create all tables
    db.create_all()

# Import Flask utilities
from flask import jsonify, render_template, request

# Simple ping endpoint for keep-alive mechanism
def ping():
    """Simple endpoint to respond to ping requests"""
    return jsonify({"status": "ok", "message": "Bot is alive"})

# Simple index page
def index():
    """Render a simple HTML page for bot verification"""
    return render_template('index.html')

# Import the bot module without circular imports
import bot

# Register routes
app.add_url_rule('/', 'index', index, methods=['GET'])
app.add_url_rule('/webhook', 'webhook', bot.webhook_handler, methods=['POST'])
app.add_url_rule('/setup', 'setup_webhook', bot.setup_webhook, methods=['GET'])
app.add_url_rule('/status', 'bot_status', bot.bot_status, methods=['GET'])
app.add_url_rule('/ping', 'ping', ping, methods=['GET'])

# Import and start the keep-alive mechanism after app is initialized
from keepalive import start_keep_alive

# Get the host from environment if available, or wait to be set on first request
host = None
if 'HOST' in os.environ:
    host = os.environ.get('HOST')
start_keep_alive(host)
