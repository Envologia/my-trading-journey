#!/usr/bin/env python3
"""
Command handlers for the Telegram bot
"""
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app import db
from models import User, Trade, TherapySession, WeeklyReport, UserState
from states import (
    REGISTRATION_STATES, JOURNAL_STATES, THERAPY_STATES,
    get_user_state, set_user_state, clear_user_state
)
import ai_therapy
import analytics

# Configure logging
logger = logging.getLogger(__name__)

# Helper function to get or create user
def get_or_create_user(telegram_id, full_name=None):
    """Get or create a user by Telegram ID"""
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    if not user:
        # Create a new user
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            registration_complete=False
        )
        db.session.add(user)
        db.session.commit()
        logger.info(f"Created new user: {user}")
    
    return user

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the registration process or welcome back returning users"""
    user = get_or_create_user(
        update.effective_user.id,
        f"{update.effective_user.first_name} {update.effective_user.last_name if update.effective_user.last_name else ''}"
    )
    
    if user.registration_complete:
        # Welcome back a registered user
        await update.message.reply_text(
            f"Welcome back {user.full_name}! How can I help you today?\n\n"
            f"Use /journal to log a new trade\n"
            f"Use /stats to see your trading statistics\n"
            f"Use /therapy to talk about trading psychology\n"
            f"Use /summary to get an AI analysis of your trading patterns\n"
            f"Use /report to generate a weekly report\n"
            f"Use /help to see available commands"
        )
    else:
        # Start registration process
        await update.message.reply_text(
            f"Hello {update.effective_user.first_name}! Welcome to Trading Journal Bot.\n\n"
            f"I'm here to help you track your trades, analyze your performance, "
            f"and provide support for the psychological aspects of trading.\n\n"
            f"Let's start by setting up your profile. What is your full name?"
        )
        
        # Set user state to collect full name
        set_user_state(user.id, REGISTRATION_STATES.FULL_NAME)

# Therapy command
async def therapy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start or continue an AI therapy session"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    await update.message.reply_text(
        "Welcome to your trading psychology session. "
        "How are you feeling about your trading today? "
        "Feel free to share any thoughts, concerns, or emotions."
    )
    
    # Set user state to therapy mode
    set_user_state(user.id, THERAPY_STATES.ACTIVE)

# Journal command
async def journal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the trade journaling process"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    await update.message.reply_text(
        "Let's journal a new trade. First, what date did you take this trade? "
        "Please use the format YYYY-MM-DD (e.g., 2025-04-29), or enter 'today' for today's date."
    )
    
    # Set user state to collect trade date
    set_user_state(user.id, JOURNAL_STATES.DATE)

# Stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show trading statistics and analytics"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    try:
        # Get stats using analytics module
        stats = analytics.calculate_stats(user.id)
        
        if not stats.get('total_trades', 0):
            await update.message.reply_text(
                "You haven't recorded any trades yet. Use /journal to log your first trade."
            )
            return
        
        # Format the statistics
        stats_text = (
            f"📊 *Trading Statistics* 📊\n\n"
            f"Total Trades: {stats['total_trades']}\n"
            f"Wins: {stats['wins']} (Raw) / {stats['effective_wins']} (Effective)\n"
            f"Losses: {stats['losses']} (Raw) / {stats['effective_losses']} (Effective)\n"
            f"Breakeven: {stats['breakevens']}\n"
            f"Win Rate: {stats['win_rate']}%\n\n"
            f"Net Profit/Loss: ${stats['net_profit_loss']:.2f}\n"
            f"Average Win: ${stats['avg_win']:.2f}\n"
            f"Average Loss: ${stats['avg_loss']:.2f}\n"
            f"Risk/Reward Ratio: {stats['risk_reward_ratio']:.2f}\n\n"
            f"Most Traded Pair: {stats['most_traded_pair']}\n"
            f"Best Performing Pair: {stats['best_pair']}\n"
            f"Worst Performing Pair: {stats['worst_pair']}\n"
        )
        
        await update.message.reply_text(
            stats_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        await update.message.reply_text(
            "Sorry, there was an error calculating your statistics. Please try again later."
        )

# Summary command
async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide AI-based summary and analysis of trading behavior"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    try:
        # Get all trades for this user
        trades = Trade.query.filter_by(user_id=user.id).all()
        
        if not trades:
            await update.message.reply_text(
                "You haven't recorded any trades yet. Use /journal to log your first trade."
            )
            return
        
        # Format trades for AI analysis
        trades_data = [
            {
                'date': t.date.strftime('%Y-%m-%d'),
                'pair': t.pair_traded,
                'result': t.result,
                'profit_loss': t.profit_loss,
                'notes': t.notes
            }
            for t in trades
        ]
        
        # Get loading message
        loading_message = await update.message.reply_text(
            "Analyzing your trading patterns... This might take a moment."
        )
        
        # Get AI summary
        summary_text = ai_therapy.get_summary_analysis(user, trades_data)
        
        # Send the summary
        await loading_message.delete()
        await update.message.reply_text(summary_text)
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        await update.message.reply_text(
            "Sorry, there was an error generating your trading summary. Please try again later."
        )

# Report command
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display weekly trading report"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    try:
        # Get date range for the current week
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Get or generate weekly report
        report = WeeklyReport.query.filter_by(
            user_id=user.id,
            week_start=start_of_week,
            week_end=end_of_week
        ).first()
        
        if not report:
            # Generate a new report
            report_data = analytics.generate_weekly_report(
                user.id, start_of_week, end_of_week
            )
            
            if not report_data.get('total_trades', 0):
                await update.message.reply_text(
                    f"No trades found for the current week ({start_of_week} to {end_of_week}). "
                    f"Use /journal to log your trades."
                )
                return
            
            # Create a new report
            report = WeeklyReport(
                user_id=user.id,
                week_start=start_of_week,
                week_end=end_of_week,
                total_trades=report_data.get('total_trades', 0),
                wins=report_data.get('wins', 0),
                losses=report_data.get('losses', 0),
                breakevens=report_data.get('breakevens', 0),
                win_rate=report_data.get('win_rate', 0.0),
                net_profit_loss=report_data.get('net_profit_loss', 0.0),
                notes=report_data.get('notes', '')
            )
            
            db.session.add(report)
            db.session.commit()
        
        # Format the report
        report_text = (
            f"📝 *Weekly Trading Report* 📝\n"
            f"Week: {report.week_start} to {report.week_end}\n\n"
            f"Total Trades: {report.total_trades}\n"
            f"Wins: {report.wins}\n"
            f"Losses: {report.losses}\n"
            f"Breakevens: {report.breakevens}\n"
            f"Effective Win Rate: {report.win_rate:.2f}%\n"
            f"Net P/L: ${report.net_profit_loss:.2f}\n\n"
            f"Notes: {report.notes}"
        )
        
        await update.message.reply_text(
            report_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await update.message.reply_text(
            "Sorry, there was an error generating your weekly report. Please try again later."
        )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help information about available commands"""
    help_text = (
        "🤖 *Trading Journal Bot Help* 🤖\n\n"
        "Here are the available commands:\n\n"
        "/start - Start registration or return to main menu\n"
        "/journal - Log a new trade\n"
        "/stats - View your trading statistics\n"
        "/therapy - Get AI-powered trading psychology support\n"
        "/summary - Get AI analysis of your trading patterns\n"
        "/report - Generate weekly trading report\n"
        "/help - Show this help message\n\n"
        "If you have any issues or suggestions, please contact support."
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )

# Button callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    user = get_or_create_user(query.from_user.id)
    current_state = get_user_state(user.id)
    
    # Extract the callback data
    data = query.data
    
    # Handle different button callbacks based on state
    if current_state and current_state.state == REGISTRATION_STATES.EXPERIENCE:
        # Handle experience level selection
        user.experience_level = data
        db.session.commit()
        
        # Move to next registration step
        await query.edit_message_text(
            "Great! What type of trading account do you have?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Personal", callback_data="Personal")],
                [InlineKeyboardButton("Funded", callback_data="Funded")]
            ])
        )
        set_user_state(user.id, REGISTRATION_STATES.ACCOUNT_TYPE)
    
    elif current_state and current_state.state == REGISTRATION_STATES.ACCOUNT_TYPE:
        # Handle account type selection
        user.account_type = data
        db.session.commit()
        
        if data == "Funded":
            # Ask for phase if funded account
            await query.edit_message_text(
                "What phase are you currently in?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Phase 1", callback_data="Phase 1")],
                    [InlineKeyboardButton("Phase 2", callback_data="Phase 2")]
                ])
            )
            set_user_state(user.id, REGISTRATION_STATES.PHASE)
        else:
            # Skip phase for personal accounts
            await query.edit_message_text(
                "What is your profit target (in USD)?"
            )
            set_user_state(user.id, REGISTRATION_STATES.PROFIT_TARGET)
    
    elif current_state and current_state.state == REGISTRATION_STATES.PHASE:
        # Handle phase selection
        user.phase = data
        db.session.commit()
        
        # Move to next registration step
        await query.edit_message_text(
            "What is your profit target (in USD)?"
        )
        set_user_state(user.id, REGISTRATION_STATES.PROFIT_TARGET)
    
    elif current_state and current_state.state == JOURNAL_STATES.RESULT:
        # Handle trade result selection
        state_data = current_state.get_data() or {}
        state_data['result'] = data
        
        if data == "Breakeven":
            # For breakeven trades, ask for the exact P/L amount
            await query.edit_message_text(
                "What was your exact profit/loss for this breakeven trade? "
                "Please enter a positive number for a small profit or a negative number for a small loss. "
                "Example: 1.5 or -0.75"
            )
            set_user_state(user.id, JOURNAL_STATES.BREAKEVEN_AMOUNT, state_data)
        else:
            set_user_state(user.id, JOURNAL_STATES.SCREENSHOT, state_data)
            
            # Ask for screenshot (optional)
            await query.edit_message_text(
                "Would you like to add a screenshot of your trade? "
                "If yes, please send the image. If no, type 'skip'."
            )
    
    else:
        # Generic fallback
        await query.edit_message_text(
            f"Button command '{data}' received. This functionality is not implemented yet."
        )

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle non-command text messages based on conversation state"""
    # Ignore non-text messages except for photos in specific states
    if not update.message.text and not (
        update.message.photo and 
        getattr(update.message, 'effective_attachment', None)
    ):
        return
    
    user = get_or_create_user(update.effective_user.id)
    current_state = get_user_state(user.id)
    
    # If no current state, ignore the message
    if not current_state:
        return
    
    state = current_state.state
    state_data = current_state.get_data() or {}
    
    # Handle registration states
    if state == REGISTRATION_STATES.FULL_NAME:
        user.full_name = update.message.text
        db.session.commit()
        
        await update.message.reply_text(
            f"Thanks, {user.full_name}. How old are you?"
        )
        set_user_state(user.id, REGISTRATION_STATES.AGE)
    
    elif state == REGISTRATION_STATES.AGE:
        try:
            user.age = int(update.message.text)
            db.session.commit()
            
            await update.message.reply_text(
                "How many years have you been trading? (Can be a decimal, e.g., 1.5)"
            )
            set_user_state(user.id, REGISTRATION_STATES.TRADING_YEARS)
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for your age."
            )
    
    elif state == REGISTRATION_STATES.TRADING_YEARS:
        try:
            user.trading_years = float(update.message.text)
            db.session.commit()
            
            await update.message.reply_text(
                "What's your trading experience level?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Beginner", callback_data="Beginner")],
                    [InlineKeyboardButton("Intermediate", callback_data="Intermediate")],
                    [InlineKeyboardButton("Advanced", callback_data="Advanced")]
                ])
            )
            set_user_state(user.id, REGISTRATION_STATES.EXPERIENCE)
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for years trading (e.g., 1.5)."
            )
    
    elif state == REGISTRATION_STATES.PROFIT_TARGET:
        try:
            user.profit_target = float(update.message.text)
            db.session.commit()
            
            await update.message.reply_text(
                "What is your initial account balance (in USD)?"
            )
            set_user_state(user.id, REGISTRATION_STATES.INITIAL_BALANCE)
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for your profit target."
            )
    
    elif state == REGISTRATION_STATES.INITIAL_BALANCE:
        try:
            user.initial_balance = float(update.message.text)
            user.current_balance = user.initial_balance  # Initialize current balance
            user.registration_complete = True
            db.session.commit()
            
            await update.message.reply_text(
                f"Great! Your profile is now complete.\n\n"
                f"Full Name: {user.full_name}\n"
                f"Age: {user.age}\n"
                f"Trading Experience: {user.trading_years} years ({user.experience_level})\n"
                f"Account Type: {user.account_type}{' - ' + user.phase if user.phase else ''}\n"
                f"Profit Target: ${user.profit_target:.2f}\n"
                f"Initial Balance: ${user.initial_balance:.2f}\n\n"
                f"You can now use all features of the Trading Journal Bot.\n\n"
                f"Use /journal to log a new trade\n"
                f"Use /stats to see your trading statistics\n"
                f"Use /therapy to talk about trading psychology\n"
                f"Use /summary to get an AI analysis of your trading patterns\n"
                f"Use /report to generate a weekly report\n"
                f"Use /help to see available commands"
            )
            
            # Clear user state after registration
            clear_user_state(user.id)
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for your initial balance."
            )
    
    # Handle therapy states
    elif state == THERAPY_STATES.ACTIVE:
        # Store the user's message in the therapy session
        therapy_session = TherapySession.query.filter_by(user_id=user.id).order_by(TherapySession.created_at.desc()).first()
        
        if not therapy_session:
            therapy_session = TherapySession(user_id=user.id)
            db.session.add(therapy_session)
        
        # Append the current message to the content
        content = json.loads(therapy_session.content or '[]')
        content.append({"user": update.message.text})
        therapy_session.content = json.dumps(content)
        db.session.commit()
        
        # Get AI response
        loading_message = await update.message.reply_text(
            "Thinking..."
        )
        
        try:
            # Get AI response with conversation history
            ai_response = ai_therapy.get_therapy_response(update.message.text, user, therapy_session)
            
            # Store the AI response
            content.append({"ai": ai_response})
            therapy_session.content = json.dumps(content)
            db.session.commit()
            
            # Send the response
            await loading_message.delete()
            await update.message.reply_text(ai_response)
        except Exception as e:
            logger.error(f"Error getting therapy response: {e}")
            await loading_message.delete()
            await update.message.reply_text(
                "I'm sorry, I couldn't process your request right now. Please try again later."
            )
    
    # Handle journaling states
    elif state == JOURNAL_STATES.DATE:
        try:
            if update.message.text.lower() == 'today':
                trade_date = datetime.utcnow().date()
            else:
                # Parse the date
                trade_date = datetime.strptime(update.message.text, '%Y-%m-%d').date()
            
            # Store date in state data
            state_data['date'] = trade_date.strftime('%Y-%m-%d')
            set_user_state(user.id, JOURNAL_STATES.PAIR, state_data)
            
            await update.message.reply_text(
                "What currency pair did you trade? (e.g., EURUSD, BTCUSD)"
            )
        except ValueError:
            await update.message.reply_text(
                "Invalid date format. Please use YYYY-MM-DD (e.g., 2025-04-29) or 'today'."
            )
    
    elif state == JOURNAL_STATES.PAIR:
        # Store pair in state data
        state_data['pair'] = update.message.text.upper()
        set_user_state(user.id, JOURNAL_STATES.SL, state_data)
        
        await update.message.reply_text(
            "What was your stop loss amount in USD?"
        )
    
    elif state == JOURNAL_STATES.SL:
        try:
            stop_loss = float(update.message.text)
            
            # Store SL in state data
            state_data['stop_loss'] = stop_loss
            set_user_state(user.id, JOURNAL_STATES.TP, state_data)
            
            await update.message.reply_text(
                "What was your take profit amount in USD?"
            )
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for stop loss."
            )
            
    elif state == JOURNAL_STATES.BREAKEVEN_AMOUNT:
        try:
            # Store the breakeven amount in state data
            breakeven_amount = float(update.message.text)
            state_data['breakeven_amount'] = breakeven_amount
            set_user_state(user.id, JOURNAL_STATES.SCREENSHOT, state_data)
            
            # Continue to screenshot
            await update.message.reply_text(
                f"Breakeven amount of ${breakeven_amount:.2f} recorded. Would you like to add a screenshot of your trade? "
                f"If yes, please send the image. If no, type 'skip'."
            )
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for the breakeven amount (e.g., 1.5 or -0.75)."
            )
    
    elif state == JOURNAL_STATES.TP:
        try:
            take_profit = float(update.message.text)
            
            # Store TP in state data
            state_data['take_profit'] = take_profit
            set_user_state(user.id, JOURNAL_STATES.RESULT, state_data)
            
            # Ask for result with inline keyboard
            await update.message.reply_text(
                "What was the result of this trade?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Win", callback_data="Win")],
                    [InlineKeyboardButton("Loss", callback_data="Loss")],
                    [InlineKeyboardButton("Breakeven", callback_data="Breakeven")]
                ])
            )
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number for take profit."
            )
    
    elif state == JOURNAL_STATES.SCREENSHOT:
        # Handle screenshot or skip
        if update.message.photo:
            # Store the file_id of the largest photo
            state_data['screenshot_id'] = update.message.photo[-1].file_id
            set_user_state(user.id, JOURNAL_STATES.NOTES, state_data)
            
            await update.message.reply_text(
                "Screenshot saved. Please provide detailed notes about this trade (required).\n\n"
                "Consider including: entry/exit reasoning, emotions during the trade, what went well, "
                "what could be improved, and any patterns you noticed."
            )
        elif update.message.text.lower() == 'skip':
            set_user_state(user.id, JOURNAL_STATES.NOTES, state_data)
            
            await update.message.reply_text(
                "No screenshot added. Please provide detailed notes about this trade (required).\n\n"
                "Consider including: entry/exit reasoning, emotions during the trade, what went well, "
                "what could be improved, and any patterns you noticed."
            )
        else:
            await update.message.reply_text(
                "Please send a screenshot image or type 'skip' to continue without a screenshot."
            )
    
    elif state == JOURNAL_STATES.NOTES:
        # Check if notes are provided and not just whitespace
        if not update.message.text or update.message.text.strip() == '':
            await update.message.reply_text(
                "⚠️ Notes are required for each trade. Please provide detailed observations or thoughts about this trade.\n\n"
                "Proper trade journaling with detailed notes is essential for improvement. Include your reasoning, "
                "emotions, market conditions, and any lessons learned."
            )
            return
            
        # Store notes in state data
        state_data['notes'] = update.message.text
        
        # Calculate P/L based on result
        profit_loss = None
        if state_data.get('result') == 'Win':
            profit_loss = state_data.get('take_profit', 0)
        elif state_data.get('result') == 'Loss':
            profit_loss = -state_data.get('stop_loss', 0)
        elif state_data.get('result') == 'Breakeven':
            profit_loss = state_data.get('breakeven_amount', 0)
        
        # Create the trade
        # Safely handle the date
        # Safe date handling - validate the date string format
        try:
            date_str = state_data.get('date')
            if date_str and isinstance(date_str, str):
                trade_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                trade_date = datetime.utcnow().date()
                logger.warning(f"Invalid date format in state data: {date_str}, using current date")
        except (ValueError, TypeError) as e:
            trade_date = datetime.utcnow().date()
            logger.warning(f"Error parsing date: {e}, using current date instead")
            
        trade = Trade(
            user_id=user.id,
            date=trade_date,
            pair_traded=state_data.get('pair', 'UNKNOWN'),
            stop_loss=state_data.get('stop_loss', 0),
            take_profit=state_data.get('take_profit', 0),
            result=state_data.get('result', 'Breakeven'),
            screenshot_id=state_data.get('screenshot_id'),
            notes=state_data.get('notes', ''),
            profit_loss=profit_loss
        )
        
        db.session.add(trade)
        
        # Update current balance
        if profit_loss:
            user.current_balance = (user.current_balance or user.initial_balance) + profit_loss
            
        db.session.commit()
        
        # Confirm and clear state
        # Format P/L correctly based on whether it's None
        pl_display = f"${trade.profit_loss:.2f}" if trade.profit_loss is not None else "$0.00"
        
        await update.message.reply_text(
            f"✅ Trade logged successfully!\n\n"
            f"Date: {trade.date}\n"
            f"Pair: {trade.pair_traded}\n"
            f"Stop Loss: ${trade.stop_loss:.2f}\n"
            f"Take Profit: ${trade.take_profit:.2f}\n"
            f"Result: {trade.result}\n"
            f"P/L: {pl_display}\n"
            f"Current Balance: ${user.current_balance:.2f}\n\n"
            f"Use /journal to log another trade or /stats to see your statistics."
        )
        
        clear_user_state(user.id)