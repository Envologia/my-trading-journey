# Deploying Your Trading Journal Bot on Render

This guide will walk you through the steps to deploy your Trading Journal Bot on Render.com.

## Prerequisites

1. A Render.com account
2. Your Telegram Bot Token (from @BotFather)
3. A Gemini API Key (for the AI features)

## Deployment Steps

### 1. Create a New Web Service on Render

1. Log in to your Render account and click on "New +"
2. Select "Web Service"
3. Connect to your GitHub repository
4. Select the repository containing your bot code

### 2. Configure Your Web Service

Fill in the following details:

- **Name**: `trading-journal-bot` (or whatever you prefer)
- **Environment**: Python
- **Region**: Choose the closest to your users
- **Branch**: main (or your preferred branch)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --reuse-port main:app`

### 3. Add Environment Variables

Add the following environment variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `GEMINI_API_KEY`: Your Gemini API key
- `FLASK_SECRET_KEY`: A random string for session security
- `DATABASE_URL`: This will be automatically set if you add PostgreSQL

### 4. Add PostgreSQL Database

1. Go to the "Add-ons" section
2. Click on "Add PostgreSQL"
3. Select your preferred plan
4. Click "Create Database"

### 5. Deploy Your Service

1. Click "Create Web Service"
2. Wait for the deployment to complete (this may take a few minutes)

### 6. Set Up Telegram Webhook

After your service is deployed:

1. Visit `https://your-render-url.onrender.com/setup`
2. This will automatically set up the webhook for your Telegram bot

## Verifying the Deployment

To verify that your bot is working:

1. Visit `https://your-render-url.onrender.com/status` to check the bot status
2. Try sending a message to your bot on Telegram
3. The bot should respond based on the handlers you've set up

## Troubleshooting

If you encounter any issues:

1. Check the Render logs for any error messages
2. Ensure all environment variables are set correctly
3. Verify that your PostgreSQL database is properly connected
4. Make sure your bot token and API keys are valid

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Python-Telegram-Bot Documentation](https://python-telegram-bot.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Gemini API Documentation](https://ai.google.dev/docs/gemini_api)