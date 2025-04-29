"""
Flask app initialization
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

def create_app():
    """Create and configure the Flask app"""
    # Create the app
    app = Flask(__name__)
    
    # Set up a secret key, required by sessions
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-very-secret-key")
    
    # Configure ProxyFix for handling proxies (important for Render deployment)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize extensions
    db.init_app(app)
    
    # Register routes
    from app.routes import register_routes
    register_routes(app)
    
    # Initialize database
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        import models
        
        # Create tables
        db.create_all()
        
        # Start the keep-alive thread
        from app.keepalive import start_keep_alive
        start_keep_alive()
    
    return app