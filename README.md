# Trading Journal Telegram Bot

A production-grade Flask-based Telegram bot that transforms trading journaling into an engaging, AI-powered experience. This application provides comprehensive trade tracking, emotional support through AI therapy, and performance analytics through an intuitive Telegram interface.

## Features

- **Trade Journaling**: Log your trades with comprehensive details (pair, stop loss, take profit, results, etc.)
- **AI-Powered Trading Psychology Support**: Get emotional and psychological support for trading decisions
- **Performance Analytics**: Track your trading performance with detailed statistics
- **Weekly Reports**: Receive AI-generated weekly trading summaries and insights
- **User-Friendly Interface**: Intuitive Telegram bot commands and conversations

## Tech Stack

- **Backend**: Flask (Python)
- **Bot Framework**: Python-Telegram-Bot
- **Database**: PostgreSQL
- **AI Integration**: Google Gemini API
- **Deployment**: Render Web Service

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Gemini API Key (for AI features)

### Local Development Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/trading-journal-bot.git
   cd trading-journal-bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   export GEMINI_API_KEY=your_gemini_api_key
   export DATABASE_URL=postgresql://username:password@localhost:5432/db_name
   export FLASK_SECRET_KEY=your_secret_key
   ```

4. Initialize the database:
   ```
   python -c "from main import app, db; app.app_context().push(); db.create_all()"
   ```

5. Run the bot in development mode (polling):
   ```
   python run_bot.py
   ```

## Deployment on Render

1. Fork or push this repository to your GitHub account

2. Create a new Web Service on Render:
   - Connect to your GitHub repository
   - Set Environment to Python
   - Set Build Command to: `pip install -r requirements.txt`
   - Set Start Command to: `gunicorn --bind 0.0.0.0:$PORT --reuse-port main:app`

3. Add the following environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `GEMINI_API_KEY`: Your Gemini API key
   - `FLASK_SECRET_KEY`: A random string for session security

4. Add PostgreSQL as an add-on in Render (this will automatically set the DATABASE_URL)

5. Deploy your application

6. Once deployed, visit `https://your-render-url.onrender.com/setup` to set up the Telegram webhook

7. Test the bot by sending a message to your Telegram bot

For more detailed deployment instructions, see [RENDER_DEPLOY.md](RENDER_DEPLOY.md)

## Bot Commands

- `/start` - Start the registration process or welcome back returning users
- `/therapy` - Start or continue an AI therapy session
- `/journal` - Start the trade journaling process
- `/stats` - Show trading statistics and analytics
- `/summary` - Provide AI-based summary and analysis of trading behavior
- `/report` - Generate and display weekly trading report
- `/help` - Display help information about available commands

## Database Schema

The application uses the following main database models:

- **User**: Stores user information, trading experience, and account details
- **Trade**: Records individual trades with detailed parameters
- **TherapySession**: Tracks AI therapy conversations
- **WeeklyReport**: Stores generated weekly reports and statistics
- **UserState**: Manages user conversation states for multi-step processes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Python-Telegram-Bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Flask](https://flask.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Gemini API](https://ai.google.dev/docs/gemini_api)