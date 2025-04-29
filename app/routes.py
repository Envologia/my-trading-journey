"""
Route definitions for the Flask app
"""
from flask import render_template, jsonify

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route('/')
    def index():
        """Render the landing page"""
        return render_template('index.html')
    
    @app.route('/status')
    def status():
        """Get the bot status"""
        from app.telegram_bot import get_bot_status
        return get_bot_status()
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Handle webhook requests from Telegram"""
        from app.telegram_bot import handle_webhook
        return handle_webhook()
    
    @app.route('/setup', methods=['GET'])
    def setup():
        """Set up the webhook for Telegram"""
        from app.telegram_bot import setup_webhook
        return setup_webhook()
    
    @app.route('/ping')
    def ping():
        """Simple ping endpoint for keep-alive mechanism"""
        return jsonify({
            'status': 'ok',
            'message': 'Server is alive'
        })