#!/usr/bin/env python3
"""
Command handlers for the Telegram bot
"""
import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app import db
from models import User, Trade, TherapySession, WeeklyReport, UserState
from states import (
    REGISTRATION_STATES, JOURNAL_STATES, THERAPY_STATES, BROADCAST_STATES,
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
        # Welcome back a registered user with more emojis and engaging language
        await update.message.reply_text(
            f"🎉 Welcome back, {user.full_name}! 🎉\n\n"
            f"Ready to crush some more trades today? Here's what I can help you with:\n\n"
            f"📝 /journal - Log your latest trading victory (or lesson!)\n"
            f"📊 /stats - Check your awesome trading performance\n"
            f"🧠 /therapy - Need a trading psychology boost?\n"
            f"🔍 /summary - Get AI-powered insights on your trading style\n"
            f"📈 /trades - Browse your trading journey\n"
            f"📰 /report - See your weekly progress report\n"
            f"❓ /help - Discover all my cool features\n\n"
            f"What's your trading mission today? I'm here to make it happen! 💪"
        )
    else:
        # Start registration process with more personality
        await update.message.reply_text(
            f"👋 Hello {update.effective_user.first_name}! Super excited to meet you! ✨\n\n"
            f"I'm your new Trading Journal Bot - your personal trading companion, performance analyst, "
            f"and mindset coach all rolled into one awesome package! 🚀\n\n"
            f"Let's get your trading journey supercharged! 💯 First things first - what's your full name? "
            f"(This helps me personalize your experience!)"
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
        "🧘‍♂️ *Welcome to your Trading Mindset Therapy* 🧠\n\n"
        "Trading is as much about psychology as it is about strategy! 💭\n\n"
        "How's your trading mindset today? Feeling confident? Stressed? Uncertain? "
        "I'm here to help you process those emotions and level up your mental game! 🚀\n\n"
        "Just share whatever's on your mind - no judgment, just support! ✨"
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
        "📝 *Time to Record Your Trading Journey!* 📊\n\n"
        "Let's capture all the details of your trade to build your success blueprint! 🚀\n\n"
        "First up, when did you make this trade? 📅\n"
        "• Use format YYYY-MM-DD (like 2025-04-29)\n"
        "• Or just type 'today' for today's date\n\n"
        "Pro traders know documentation leads to domination! 💪"
    )
    
    # Set user state to collect trade date
    set_user_state(user.id, JOURNAL_STATES.DATE)

# Stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show trading statistics and analytics"""
    user = get_or_create_user(update.effective_user.id)
    
    # Special admin case to show global stats
    admin_mode = False
    if is_admin(update.effective_user.id) and context.args and context.args[0].lower() == "all":
        admin_mode = True
        await update.message.reply_text(
            "🔐 *Admin Mode Activated* 🔐\n"
            "Fetching global statistics for all users..."
        )
        
    if not admin_mode and not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    try:
        if admin_mode:
            # TODO: Implement global stats calculation
            # For now, just show basic user metrics
            total_users = User.query.count()
            registered_users = User.query.filter_by(registration_complete=True).count()
            total_trades = Trade.query.count()
            
            # Get recent trades
            recent_trades = Trade.query.order_by(Trade.created_at.desc()).limit(5).all()
            
            # Get more detailed admin statistics
            active_users_this_week = db.session.query(Trade.user_id).distinct().filter(
                Trade.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            win_trades = Trade.query.filter_by(result="Win").count()
            loss_trades = Trade.query.filter_by(result="Loss").count()
            breakeven_trades = Trade.query.filter_by(result="Breakeven").count()
            
            # Calculate platform-wide win rate with type-safe handling
            if (win_trades + loss_trades) > 0:
                overall_win_rate = (win_trades / (win_trades + loss_trades)) * 100
            else:
                overall_win_rate = 0.0
                
            # Create a performance bar for overall win rate
            win_rate_capped = max(0, min(100, overall_win_rate))
            green_blocks = round(win_rate_capped / 10)
            white_blocks = 10 - green_blocks
            performance_bar = "🟩" * green_blocks + "⬜" * white_blocks
            
            # Format admin stats with more visual appeal and organization
            admin_stats = (
                f"👑 *Trading Journal Bot - Admin Dashboard* 👑\n\n"
                f"📊 *System Overview*\n"
                f"Total Users: {total_users} accounts\n"
                f"Registered Users: {registered_users} completed\n"
                f"Active Past Week: {active_users_this_week} traders\n\n"
                
                f"📈 *Trading Activity*\n"
                f"Total Trades: {total_trades} entries\n"
                f"Platform Win Rate: {overall_win_rate:.1f}%\n"
                f"{performance_bar}\n"
                f"Wins: {win_trades} ✅ | Losses: {loss_trades} ❌ | Breakeven: {breakeven_trades} ⚖️\n\n"
                
                f"🔄 *Recent Activity*\n"
            )
            
            # Add recent activity with improved formatting
            if recent_trades:
                for trade in recent_trades:
                    user_name = User.query.get(trade.user_id).full_name or f"User {trade.user_id}"
                    # Format result with emoji
                    result_emoji = "✅" if trade.result == "Win" else "❌" if trade.result == "Loss" else "⚖️"
                    # Create formatted P/L display if available
                    pl_display = f" (${trade.profit_loss:.2f})" if trade.profit_loss is not None else ""
                    
                    admin_stats += (
                        f"• {user_name}: {trade.pair_traded} {result_emoji}{pl_display} - {trade.date}\n"
                    )
            else:
                admin_stats += "No recent trading activity.\n"
                
            await update.message.reply_text(
                admin_stats,
                parse_mode='Markdown'
            )
            return
            
        # For regular users, get personal stats
        stats = analytics.calculate_stats(user.id)
        
        if not stats.get('total_trades', 0):
            await update.message.reply_text(
                "📈 *Your Trading Journey Starts Now!* 📊\n\n"
                "Looks like you haven't recorded any trades yet! 🔍\n\n"
                "Ready to start building your trading success? Hit /journal to log your first trade! 🚀\n"
                "The best traders are the ones who track every move! 💪"
            )
            return
        
        # Create a win rate display with details on breakeven handling
        breakeven_detail = ""
        if stats['breakevens'] > 0:
            profitable_be = stats['effective_wins'] - stats['wins']
            unprofitable_be = stats['effective_losses'] - stats['losses']
            neutral_be = stats['breakevens'] - profitable_be - unprofitable_be
            
            be_details = []
            if profitable_be > 0:
                be_details.append(f"{profitable_be} profitable 📈")
            if unprofitable_be > 0:
                be_details.append(f"{unprofitable_be} unprofitable 📉") 
            if neutral_be > 0:
                be_details.append(f"{neutral_be} neutral ↔️")
                
            if be_details:
                breakeven_detail = f" ({', '.join(be_details)})"
        
        # Create a performance bar for win rate
        win_rate = stats['win_rate']
        win_rate_capped = max(0, min(100, win_rate))
        green_blocks = round(win_rate_capped / 10)
        white_blocks = 10 - green_blocks
        performance_bar = "🟩" * green_blocks + "⬜" * white_blocks
        
        # Add profit/loss emoji indicator
        pl_emoji = "🟢" if stats['net_profit_loss'] > 0 else "🔴" if stats['net_profit_loss'] < 0 else "⚪"
        
        # Format the statistics with a more engaging and visual layout
        stats_text = (
            f"📊 *Your Trading Performance Dashboard* 📊\n\n"
            f"🎯 *Overall Performance*\n"
            f"Total Trades: {stats['total_trades']} trades\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"{performance_bar}\n"
            f"{pl_emoji} Net P/L: ${stats['net_profit_loss']:.2f}\n\n"
            
            f"🔍 *Trading Breakdown*\n"
            f"Wins: {stats['wins']} ✅\n"
            f"Losses: {stats['losses']} ❌\n" 
            f"Breakeven: {stats['breakevens']}{breakeven_detail} ⚖️\n\n"
            
            f"💰 *Risk Analysis*\n"
            f"Avg Win: ${stats['avg_win']:.2f} | Avg Loss: ${stats['avg_loss']:.2f}\n"
            f"Risk/Reward: {stats['risk_reward_ratio']:.2f}\n\n"
            
            f"📈 *Trading Patterns*\n"
            f"Most Traded: {stats['most_traded_pair']}\n"
            f"Best Performer: {stats['best_pair']}\n"
            f"Needs Improvement: {stats['worst_pair']}\n\n"
            
            f"💪 Keep refining your edge! Journal consistently for the best insights."
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
    
    # Check for admin mode
    admin_mode = False
    if is_admin(update.effective_user.id) and context.args:
        # Admin can request summary for a specific user by Telegram ID
        try:
            target_telegram_id = int(context.args[0])
            target_user = User.query.filter_by(telegram_id=target_telegram_id).first()
            
            if target_user:
                user = target_user
                admin_mode = True
                await update.message.reply_text(
                    f"🔐 *Admin Mode Activated* 🔐\n"
                    f"Analyzing trading patterns for user: {user.full_name} (ID: {user.telegram_id})"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ User with Telegram ID {target_telegram_id} not found."
                )
                return
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid Telegram ID format. Please provide a numeric Telegram ID."
            )
            return
    
    if not admin_mode and not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    try:
        # Get all trades for this user
        trades = Trade.query.filter_by(user_id=user.id).all()
        
        if not trades:
            await update.message.reply_text(
                "📊 *AI Analysis Needs Data* 📊\n\n"
                "I'm ready to provide some amazing insights, but I need trades to analyze first! 🔍\n\n"
                "The magic happens after you've logged some trades. Use /journal to start recording your trading journey! 🚀\n\n"
                "Remember: The more trades you log, the more powerful the AI analysis becomes! ✨"
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
            "🧠 *AI Trade Detective at Work!* 🔍\n\n"
            "Crunching your data and spotting those hidden patterns... 💫\n"
            "This trading wizardry takes just a moment, but the insights will be worth it! ⏳"
        )
        
        # Get AI summary
        summary_text = ai_therapy.get_summary_analysis(user, trades_data)
        
        # Send the summary
        await loading_message.delete()
        await update.message.reply_text(summary_text)
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        await update.message.reply_text(
            "🤔 *AI Brain Temporarily Overloaded!* 🤖\n\n"
            "Whoa! Looks like our AI trade analyzer needs a quick coffee break! ☕\n\n"
            "This happens sometimes when my brain is processing many traders' data at once. "
            "Please try again in a moment when I've had a chance to recharge my thinking circuits! 🔄\n\n"
            "In the meantime, you can continue journaling your trades with /journal or check your stats with /stats! 📊"
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
        # Get date range for the current week with detailed logging
        today = datetime.utcnow().date()
        logger.info(f"Current date for weekly report: {today}")
        
        # Calculate the start of the week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        # Calculate the end of the week (Sunday)
        end_of_week = start_of_week + timedelta(days=6)
        
        logger.info(f"Week range: {start_of_week} to {end_of_week}")
        
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
                    f"📅 *No Trades This Week* 📅\n\n"
                    f"Looks like you haven't recorded any trades from {start_of_week} to {end_of_week}. 🔍\n\n"
                    f"Ready to change that? Hit /journal to log your first trade of the week! 🚀\n"
                    f"Consistent journaling is your secret weapon to trading success! 💪"
                )
                return
            
            # Create a new report with effective win/loss counts for more accurate reporting
            report = WeeklyReport(
                user_id=user.id,
                week_start=start_of_week,
                week_end=end_of_week,
                total_trades=report_data.get('total_trades', 0),
                wins=report_data.get('wins', 0),  # Nominal win count
                losses=report_data.get('losses', 0),  # Nominal loss count
                breakevens=report_data.get('breakevens', 0),
                win_rate=report_data.get('win_rate', 0.0),  # This is based on effective wins
                net_profit_loss=report_data.get('net_profit_loss', 0.0),
                notes=report_data.get('notes', '')
            )
            
            # Store effective counts in the notes temporarily (we can add fields to the model later if needed)
            report.effective_wins = report_data.get('effective_wins', report.wins)
            report.effective_losses = report_data.get('effective_losses', report.losses)
            
            db.session.add(report)
            db.session.commit()
        
        # Format the report with more engaging language and emojis
        # Add profit/loss emoji indicator
        pl_emoji = "🟢" if report.net_profit_loss > 0 else "🔴" if report.net_profit_loss < 0 else "⚪"
        
        # Create a more accurate performance bar using emojis
        # Ensure win_rate is within 0-100 range
        win_rate_capped = max(0, min(100, report.win_rate))
        # Round to nearest 10 for visual display
        green_blocks = round(win_rate_capped / 10)
        white_blocks = 10 - green_blocks
        performance_bar = "🟩" * green_blocks + "⬜" * white_blocks
        
        # Get effective win/loss counts if available
        effective_wins = getattr(report, 'effective_wins', report.wins)
        effective_losses = getattr(report, 'effective_losses', report.losses)
        
        # Calculate how many breakevens were profitable vs unprofitable
        profitable_breakevens = effective_wins - report.wins if effective_wins > report.wins else 0
        unprofitable_breakevens = effective_losses - report.losses if effective_losses > report.losses else 0
        neutral_breakevens = report.breakevens - profitable_breakevens - unprofitable_breakevens
        
        # Enhanced breakeven display with profit indicators
        breakeven_display = f"{report.breakevens} ⚖️"
        if profitable_breakevens > 0 or unprofitable_breakevens > 0:
            breakeven_detail = []
            if profitable_breakevens > 0:
                breakeven_detail.append(f"{profitable_breakevens} profitable 📈")
            if unprofitable_breakevens > 0:
                breakeven_detail.append(f"{unprofitable_breakevens} unprofitable 📉") 
            if neutral_breakevens > 0:
                breakeven_detail.append(f"{neutral_breakevens} neutral ↔️")
            
            breakeven_display += f" ({' / '.join(breakeven_detail)})"
        
        # Format dates for better display (YYYY-MM-DD to Month DD, YYYY)
        try:
            formatted_start = report.week_start.strftime("%b %d, %Y")
            formatted_end = report.week_end.strftime("%b %d, %Y")
        except Exception as e:
            logger.error(f"Error formatting dates: {e}")
            formatted_start = str(report.week_start)
            formatted_end = str(report.week_end)
            
        # Get user's current balance for display
        current_balance = user.current_balance
        
        # Make sure balance is valid - fetch from database if needed
        if current_balance is None:
            # Try to refresh from the database
            db.session.refresh(user)
            current_balance = user.current_balance
            
            # If still None, use initial balance or default
            if current_balance is None:
                current_balance = user.initial_balance or 10000.0
                logger.warning(f"User {user.id} has no current balance, using {current_balance}")
        
        # Format report with improved date display and balance information
        report_text = (
            f"📊 *Your Trading Week in Review* 📊\n"
            f"📅 Week: {formatted_start} to {formatted_end}\n\n"
            f"🎯 *Performance Summary*\n"
            f"Total Trades: {report.total_trades} trades\n"
            f"Wins: {report.wins} ✅ | Losses: {report.losses} ❌ | Breakeven: {breakeven_display}\n\n"
            f"Win Rate: {report.win_rate:.1f}%\n"
            f"{performance_bar}\n\n"
            f"{pl_emoji} Net P/L: ${report.net_profit_loss:.2f}\n"
            f"💰 Current Balance: ${current_balance:.2f}\n\n"
            f"📝 *Trading Notes*\n"
            f"{report.notes or 'No notes for this week.'}\n\n"
            f"Keep building those positive habits! 💪"
        )
        
        await update.message.reply_text(
            report_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await update.message.reply_text(
            "⚠️ *Oops! A Small Hiccup!* ⚠️\n\n"
            "Our trading wizards are having trouble brewing your weekly report right now. 🧙‍♂️\n\n"
            "Don't worry! This is just a temporary glitch. Please try again in a few moments, "
            "or continue capturing those awesome trades with /journal! 📝\n\n"
            "Thanks for your patience! 💪"
        )

# Broadcast command
def is_admin(telegram_id):
    """Check if a user is an admin"""
    # Get admin IDs from environment variable
    admin_ids_str = os.environ.get('ADMIN_TELEGRAM_IDS', '')
    
    if not admin_ids_str:
        # If no admin IDs are defined, log a warning
        logger.warning("No admin Telegram IDs defined in ADMIN_TELEGRAM_IDS environment variable")
        return False
        
    # Parse comma-separated admin IDs
    try:
        admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]
        return telegram_id in admin_ids
    except ValueError:
        logger.error(f"Invalid admin Telegram ID format in environment variable: {admin_ids_str}")
        return False

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a message to all users"""
    user = get_or_create_user(update.effective_user.id)
    
    # Check if user is admin
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "⚠️ Sorry, only administrators can use the broadcast command."
        )
        return
    
    # Only allow specific admins to use this command (you can customize this list)
    # For now, anyone can use it for demonstration purposes, but you should restrict it in production
    # admin_telegram_ids = [123456789]  # Replace with your Telegram ID
    # if user.telegram_id not in admin_telegram_ids:
    #     await update.message.reply_text("You don't have permission to use this command.")
    #     return
    
    await update.message.reply_text(
        "✉️ *Broadcast Message System* ✉️\n\n"
        "Please compose the message you want to send to all users. "
        "This message will be delivered as an announcement from the bot.\n\n"
        "Send your message now, or type /cancel to abort."
    )
    
    # Set user state to compose broadcast message
    set_user_state(user.id, BROADCAST_STATES.COMPOSE)

# List trades command
async def list_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List recent trades for the user"""
    user = get_or_create_user(update.effective_user.id)
    
    if not user.registration_complete:
        await update.message.reply_text(
            "Please complete your registration first with /start"
        )
        return
    
    # Get pagination parameter from context
    page = context.user_data.get('trades_page', 1)
    trades_per_page = 5
    
    # Calculate offset
    offset = (page - 1) * trades_per_page
    
    # Get trades with pagination
    trades = Trade.query.filter_by(user_id=user.id).order_by(Trade.date.desc()).offset(offset).limit(trades_per_page).all()
    total_trades = Trade.query.filter_by(user_id=user.id).count()
    total_pages = (total_trades + trades_per_page - 1) // trades_per_page
    
    if not trades:
        if page > 1:
            # If user navigated past the last page, reset to page 1
            context.user_data['trades_page'] = 1
            await list_trades(update, context)
            return
        else:
            await update.message.reply_text(
                "📖 *Your Trading Journal Awaits!* 📝\n\n"
                "Your journal is ready for its first entry! No trades recorded yet. 🔍\n\n"
                "Start capturing your trading journey with /journal and begin building your success database! 🚀\n\n"
                "Remember: Every great trader's journey begins with that first documented trade! 💯"
            )
            return
    
    # Format trades list
    trades_text = f"📖 *Your Trading Journal* (Page {page}/{total_pages if total_pages > 0 else 1})\n\n"
    
    for i, trade in enumerate(trades):
        # Format profit/loss display
        pl_display = f"${trade.profit_loss:.2f}" if trade.profit_loss is not None else "$0.00"
        
        # Format the result with emoji
        result_emoji = "✅" if trade.result == "Win" else "❌" if trade.result == "Loss" else "⚖️"
        
        trades_text += (
            f"*Trade #{trade.id}* - {trade.date}\n"
            f"Pair: {trade.pair_traded}\n"
            f"Result: {result_emoji} {trade.result} | P/L: {pl_display}\n"
            f"SL: ${trade.stop_loss:.2f} | TP: ${trade.take_profit:.2f}\n"
            f"----------------------------\n"
        )
    
    # Add pagination buttons
    keyboard = []
    pagination_row = []
    
    if page > 1:
        pagination_row.append(InlineKeyboardButton("◀️ Previous", callback_data="trades_prev_page"))
    
    if page < total_pages:
        pagination_row.append(InlineKeyboardButton("Next ▶️", callback_data="trades_next_page"))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Add buttons for trade operations
    keyboard.append([
        InlineKeyboardButton("View Trade", callback_data="view_trade"),
        InlineKeyboardButton("Edit Trade", callback_data="edit_trade"),
    ])
    
    keyboard.append([
        InlineKeyboardButton("Delete Trade", callback_data="delete_trade")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        trades_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help information about available commands"""
    # Check if user is admin
    is_user_admin = is_admin(update.effective_user.id)
    
    # Standard commands for all users with more engaging language and organization
    standard_commands = (
        "🚀 *Your Trading Command Center* 🚀\n\n"
        "Here's everything you can do with your trading assistant:\n\n"
        "📝 *Journaling Commands*\n"
        "• /journal - Record a new trading victory or lesson\n"
        "• /trades - Browse your complete trading history\n\n"
        
        "📊 *Analytics Commands*\n"
        "• /stats - See your performance metrics and win rates\n"
        "• /report - Get this week's trading performance report\n"
        "• /summary - AI analysis of your trading patterns and habits\n\n"
        
        "🧠 *Trading Psychology*\n"
        "• /therapy - Talk with AI about your trading mindset\n\n"
        
        "🔧 *System Commands*\n"
        "• /start - Begin registration or return to main menu\n"
        "• /help - Show this awesome command list\n\n"
        
        "Have questions or suggestions? I'm here to help you crush your trading goals! 💪"
    )
    
    # Admin-specific commands with more visual appeal
    admin_commands = (
        "\n\n👑 *Admin Command Center* 👑\n\n"
        "📢 *Communication*\n"
        "• /broadcast - Send important announcements to all users\n\n"
        
        "📊 *Monitoring & Analysis*\n"
        "• /stats all - View global system metrics and user activity\n"
        "• /summary [telegram_id] - Get AI analysis for specific trader\n\n"
        
        "⚙️ *Configuration*\n"
        "• Admin access controlled via ADMIN_TELEGRAM_IDS environment variable\n"
        "• Your admin powers are active and ready to use! ✅\n\n"
        
        "With great power comes great responsibility! 💫"
    )
    
    # Combine standard and admin commands if user is an admin
    help_text = standard_commands
    if is_user_admin:
        help_text += admin_commands
    
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
    
    elif current_state and current_state.state == BROADCAST_STATES.CONFIRM:
        # Handle broadcast confirmation
        if data == "broadcast_confirm":
            state_data = current_state.get_data() or {}
            message = state_data.get('message', '')
            
            if not message:
                await query.edit_message_text("Error: No message to broadcast.")
                clear_user_state(user.id)
                return
                
            # Send a progress message 
            await query.edit_message_text("Broadcasting message... Please wait.")
            
            # Get all users with a valid telegram_id
            try:
                users = User.query.filter(
                    User.registration_complete == True, 
                    User.telegram_id.isnot(None)
                ).all()
                
                if not users:
                    await query.edit_message_text("No registered users found to send message to.")
                    clear_user_state(user.id)
                    return
            except Exception as e:
                logger.error(f"Error fetching users for broadcast: {e}")
                await query.edit_message_text(f"⚠️ Error fetching users: {str(e)}")
                clear_user_state(user.id)
                return
            
            # Send the message to all users using a proper try-except structure
            sent_count = 0
            failed_count = 0
            try:
                # Process each user in a batch (to avoid timeouts)
                for recipient in users:
                    try:
                        # Make sure we have a valid telegram_id (integer)
                        if recipient.telegram_id and isinstance(recipient.telegram_id, (int, float)):
                            await context.bot.send_message(
                                chat_id=int(recipient.telegram_id),  # Ensure it's an integer
                                text=f"📢 *ANNOUNCEMENT*\n\n{message}",
                                parse_mode='Markdown'
                            )
                            sent_count += 1
                            
                            # Add a small delay to avoid rate limiting (every 5 messages)
                            if sent_count % 5 == 0:
                                await asyncio.sleep(0.5)
                        else:
                            failed_count += 1
                            logger.warning(f"Skipped user {recipient.id} - invalid telegram_id: {recipient.telegram_id}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to send broadcast to user {recipient.id}: {e}")
                
                # Confirm the results to the admin
                success_msg = f"✅ Broadcast sent successfully to {sent_count} out of {len(users)} users."
                if failed_count > 0:
                    success_msg += f"\n\nℹ️ {failed_count} messages could not be delivered. See logs for details."
                
                await query.edit_message_text(success_msg)
                
            except Exception as e:
                logger.error(f"Error during broadcast: {e}")
                await query.edit_message_text(
                    f"⚠️ Error during broadcast: {str(e)}\n\n{sent_count} messages were sent before the error occurred."
                )
            
            # Clear the state
            clear_user_state(user.id)
            
        elif data == "broadcast_cancel":
            await query.edit_message_text("Broadcast cancelled.")
            clear_user_state(user.id)
            
    elif data == "trades_prev_page":
        # Handle previous page in trade listing
        current_page = context.user_data.get('trades_page', 1)
        if current_page > 1:
            context.user_data['trades_page'] = current_page - 1
            await query.delete_message()
            await list_trades(update, context)
            
    elif data == "trades_next_page":
        # Handle next page in trade listing
        current_page = context.user_data.get('trades_page', 1)
        context.user_data['trades_page'] = current_page + 1
        await query.delete_message()
        await list_trades(update, context)
        
    elif data == "view_trade":
        # Prompt user to choose a trade to view
        await query.edit_message_text(
            "Please enter the trade ID number you want to view (e.g., 123):"
        )
        set_user_state(user.id, "view_trade_id")
        
    elif data == "edit_trade":
        # Prompt user to choose a trade to edit
        await query.edit_message_text(
            "Please enter the trade ID number you want to edit (e.g., 123):"
        )
        set_user_state(user.id, "edit_trade_id")
        
    elif data == "delete_trade":
        # Prompt user to choose a trade to delete
        await query.edit_message_text(
            "Please enter the trade ID number you want to delete (e.g., 123):"
        )
        set_user_state(user.id, "delete_trade_id")
        
    elif data.startswith("confirm_delete_"):
        # Handle deletion confirmation
        trade_id = int(data.replace("confirm_delete_", ""))
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        
        if not trade:
            await query.edit_message_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
        else:
            # Delete the trade
            trade_pair = trade.pair_traded
            db.session.delete(trade)
            db.session.commit()
            
            await query.edit_message_text(
                f"✅ Trade #{trade_id} ({trade_pair}) has been deleted."
            )
            
    elif data.startswith("cancel_delete_"):
        # Cancel deletion
        trade_id = int(data.replace("cancel_delete_", ""))
        await query.edit_message_text(
            f"Deletion of Trade #{trade_id} canceled."
        )
        
    elif data.startswith("edit_field_"):
        # Handle edit field selection
        parts = data.split("_")
        trade_id = int(parts[2])
        field = parts[3]
        
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        if not trade:
            await query.edit_message_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
            return
            
        field_prompts = {
            "date": "Please enter the new date (YYYY-MM-DD):",
            "pair": "Please enter the new trading pair:",
            "sl": "Please enter the new stop loss value (in USD):",
            "tp": "Please enter the new take profit value (in USD):",
            "result": "Please select the new result:",
            "pl": "Please enter the new profit/loss amount (in USD):",
            "notes": "Please enter the new notes for this trade:"
        }
        
        if field == "result":
            # Special handling for result field with buttons
            await query.edit_message_text(
                "Select the new result for this trade:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Win", callback_data=f"set_result_{trade_id}_Win")],
                    [InlineKeyboardButton("Loss", callback_data=f"set_result_{trade_id}_Loss")],
                    [InlineKeyboardButton("Breakeven", callback_data=f"set_result_{trade_id}_Breakeven")]
                ])
            )
        else:
            # For all other fields, ask for text input
            state_data = {"trade_id": trade_id, "field": field}
            set_user_state(user.id, "edit_trade_value", state_data)
            await query.edit_message_text(field_prompts.get(field, f"Please enter the new value for {field}:"))
            
    elif data.startswith("edit_this_trade_"):
        # Handle edit button from view trade
        trade_id = int(data.replace("edit_this_trade_", ""))
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        
        if not trade:
            await query.edit_message_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
            return
            
        # Show edit options
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Date", callback_data=f"edit_field_{trade_id}_date")],
            [InlineKeyboardButton("Pair", callback_data=f"edit_field_{trade_id}_pair")],
            [InlineKeyboardButton("Stop Loss", callback_data=f"edit_field_{trade_id}_sl")],
            [InlineKeyboardButton("Take Profit", callback_data=f"edit_field_{trade_id}_tp")],
            [InlineKeyboardButton("Result", callback_data=f"edit_field_{trade_id}_result")],
            [InlineKeyboardButton("Profit/Loss", callback_data=f"edit_field_{trade_id}_pl")],
            [InlineKeyboardButton("Notes", callback_data=f"edit_field_{trade_id}_notes")]
        ])
        
        await query.edit_message_text(
            f"Which field of Trade #{trade_id} would you like to edit?",
            reply_markup=keyboard
        )
        
    elif data.startswith("delete_this_trade_"):
        # Handle delete button from view trade
        trade_id = int(data.replace("delete_this_trade_", ""))
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        
        if not trade:
            await query.edit_message_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
            return
            
        # Ask for confirmation
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{trade_id}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data=f"cancel_delete_{trade_id}")]
        ])
        
        await query.edit_message_text(
            f"⚠️ Are you sure you want to delete Trade #{trade_id} ({trade.pair_traded})?\n"
            f"This action cannot be undone.",
            reply_markup=keyboard
        )
    
    elif data.startswith("set_result_"):
        # Handle result selection in edit mode
        parts = data.split("_")
        trade_id = int(parts[2])
        new_result = parts[3]
        
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        if not trade:
            await query.edit_message_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
            return
            
        # Update trade result
        trade.result = new_result
        db.session.commit()
        
        # If result is Breakeven, ask for P/L amount
        if new_result == "Breakeven":
            state_data = {"trade_id": trade_id, "field": "pl"}
            set_user_state(user.id, "edit_trade_value", state_data)
            await query.edit_message_text(
                "What was your exact profit/loss for this breakeven trade? "
                "Please enter a positive number for a small profit or a negative number for a small loss."
            )
        else:
            # Show success message with updated trade details
            await query.edit_message_text(
                f"✅ Trade #{trade_id} updated successfully!\n\n"
                f"*Updated Trade Details:*\n"
                f"Date: {trade.date}\n"
                f"Pair: {trade.pair_traded}\n"
                f"Result: {trade.result}\n"
                f"P/L: ${trade.profit_loss if trade.profit_loss is not None else 0:.2f}\n"
                f"SL: ${trade.stop_loss:.2f}\n"
                f"TP: ${trade.take_profit:.2f}\n"
                f"Notes: {trade.notes or 'None'}\n\n"
                f"Use /trades to view your trade journal.",
                parse_mode='Markdown'
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
    
    # Handle trade management states
    elif state == "view_trade_id":
        try:
            trade_id = int(update.message.text)
            trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
            
            if not trade:
                await update.message.reply_text(
                    f"Trade #{trade_id} not found or doesn't belong to you. Please try again with a valid ID."
                )
                clear_user_state(user.id)
                return
                
            # Format notes display, handle case with no notes
            notes_display = trade.notes if trade.notes else "None"
            
            # Format profit/loss amount with dollar sign and decimal places
            pl_display = f"${trade.profit_loss:.2f}" if trade.profit_loss is not None else "$0.00"
            
            # Format result with emoji
            result_emoji = "✅" if trade.result == "Win" else "❌" if trade.result == "Loss" else "⚖️"
            
            # Send trade details
            trade_details = (
                f"📝 *Trade #{trade.id} Details*\n\n"
                f"📅 Date: {trade.date}\n"
                f"📊 Pair: {trade.pair_traded}\n"
                f"🎯 Result: {result_emoji} {trade.result}\n"
                f"💰 Profit/Loss: {pl_display}\n"
                f"🛑 Stop Loss: ${trade.stop_loss:.2f}\n"
                f"🚀 Take Profit: ${trade.take_profit:.2f}\n"
                f"📝 Notes: {notes_display}\n"
            )
            
            # Add screenshot if available
            if trade.screenshot_id:
                await update.message.reply_photo(
                    photo=trade.screenshot_id,
                    caption=trade_details,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    trade_details,
                    parse_mode='Markdown'
                )
                
            # After viewing, provide buttons to edit or delete
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Edit This Trade", callback_data=f"edit_this_trade_{trade_id}")],
                [InlineKeyboardButton("🗑️ Delete This Trade", callback_data=f"delete_this_trade_{trade_id}")]
            ])
            
            await update.message.reply_text(
                "Would you like to edit or delete this trade?",
                reply_markup=keyboard
            )
            
            clear_user_state(user.id)
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid trade ID number."
            )
            
    elif state == "edit_trade_id":
        try:
            trade_id = int(update.message.text)
            trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
            
            if not trade:
                await update.message.reply_text(
                    f"Trade #{trade_id} not found or doesn't belong to you. Please try again with a valid ID."
                )
                clear_user_state(user.id)
                return
                
            # Show edit options
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Date", callback_data=f"edit_field_{trade_id}_date")],
                [InlineKeyboardButton("Pair", callback_data=f"edit_field_{trade_id}_pair")],
                [InlineKeyboardButton("Stop Loss", callback_data=f"edit_field_{trade_id}_sl")],
                [InlineKeyboardButton("Take Profit", callback_data=f"edit_field_{trade_id}_tp")],
                [InlineKeyboardButton("Result", callback_data=f"edit_field_{trade_id}_result")],
                [InlineKeyboardButton("Profit/Loss", callback_data=f"edit_field_{trade_id}_pl")],
                [InlineKeyboardButton("Notes", callback_data=f"edit_field_{trade_id}_notes")]
            ])
            
            await update.message.reply_text(
                f"Which field of Trade #{trade_id} would you like to edit?",
                reply_markup=keyboard
            )
            
            clear_user_state(user.id)
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid trade ID number."
            )
            
    elif state == "delete_trade_id":
        try:
            trade_id = int(update.message.text)
            trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
            
            if not trade:
                await update.message.reply_text(
                    f"Trade #{trade_id} not found or doesn't belong to you. Please try again with a valid ID."
                )
                clear_user_state(user.id)
                return
                
            # Ask for confirmation
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{trade_id}")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data=f"cancel_delete_{trade_id}")]
            ])
            
            await update.message.reply_text(
                f"⚠️ Are you sure you want to delete Trade #{trade_id} ({trade.pair_traded})?\n"
                f"This action cannot be undone.",
                reply_markup=keyboard
            )
            
            clear_user_state(user.id)
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid trade ID number."
            )
            
    elif state == "edit_trade_value":
        # Get the trade and field to edit
        trade_id = state_data.get('trade_id')
        field = state_data.get('field')
        
        if not trade_id or not field:
            await update.message.reply_text(
                "Error: Missing trade ID or field to edit."
            )
            clear_user_state(user.id)
            return
            
        trade = Trade.query.filter_by(id=trade_id, user_id=user.id).first()
        if not trade:
            await update.message.reply_text(
                f"Trade #{trade_id} not found or doesn't belong to you."
            )
            clear_user_state(user.id)
            return
            
        # Process the edit based on the field
        try:
            if field == "date":
                try:
                    # Parse date string into a date object
                    date_obj = datetime.strptime(update.message.text, "%Y-%m-%d").date()
                    trade.date = date_obj
                except ValueError:
                    await update.message.reply_text(
                        "Invalid date format. Please use YYYY-MM-DD format."
                    )
                    return
                    
            elif field == "pair":
                trade.pair_traded = update.message.text
                
            elif field == "sl":
                trade.stop_loss = float(update.message.text)
                
            elif field == "tp":
                trade.take_profit = float(update.message.text)
                
            elif field == "pl":
                trade.profit_loss = float(update.message.text)
                
            elif field == "notes":
                # Make notes mandatory for better record-keeping
                if not update.message.text or update.message.text.strip() == "":
                    await update.message.reply_text(
                        "Trade notes cannot be empty. Please provide meaningful notes about this trade."
                    )
                    return
                trade.notes = update.message.text
                
            # Save changes to the database
            db.session.commit()
            
            # Show success message with updated trade details
            await update.message.reply_text(
                f"✅ Trade #{trade_id} updated successfully!\n\n"
                f"*Updated Trade Details:*\n"
                f"Date: {trade.date}\n"
                f"Pair: {trade.pair_traded}\n"
                f"Result: {trade.result}\n"
                f"P/L: ${trade.profit_loss if trade.profit_loss is not None else 0:.2f}\n"
                f"SL: ${trade.stop_loss:.2f}\n"
                f"TP: ${trade.take_profit:.2f}\n"
                f"Notes: {trade.notes or 'None'}\n\n"
                f"Use /trades to view your trade journal.",
                parse_mode='Markdown'
            )
            
            clear_user_state(user.id)
            
        except ValueError:
            await update.message.reply_text(
                f"Invalid value for {field}. Please try again with a valid number."
            )
            
    # Handle therapy states
    # Handle broadcast states
    elif state == BROADCAST_STATES.COMPOSE:
        if update.message.text.lower() == '/cancel':
            await update.message.reply_text("Broadcast message cancelled.")
            clear_user_state(user.id)
            return
            
        # Store the broadcast message
        state_data['message'] = update.message.text
        set_user_state(user.id, BROADCAST_STATES.CONFIRM, state_data)
        
        # Ask for confirmation
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Send to All Users", callback_data="broadcast_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")]
        ])
        
        await update.message.reply_text(
            f"📢 *Preview of your broadcast message:*\n\n"
            f"{update.message.text}\n\n"
            f"Are you sure you want to send this message to all users?",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
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
                # Parse the date with better error handling
                try:
                    trade_date = datetime.strptime(update.message.text, '%Y-%m-%d').date()
                except ValueError:
                    # Try alternative date formats
                    try:
                        trade_date = datetime.strptime(update.message.text, '%m/%d/%Y').date()
                    except ValueError:
                        try:
                            trade_date = datetime.strptime(update.message.text, '%d-%m-%Y').date()
                        except ValueError:
                            raise ValueError("Invalid date format")
            
            # Validate the date is not in the future
            if trade_date > datetime.utcnow().date():
                await update.message.reply_text(
                    "⚠️ The date cannot be in the future. Please enter today's date or a past date."
                )
                return
                
            # Store date in state data as ISO format string (YYYY-MM-DD)
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
        
        # Update current balance - ensure proper types and handle edge cases
        try:
            # Initialize current_balance if it hasn't been set yet
            if user.current_balance is None and user.initial_balance is not None:
                user.current_balance = user.initial_balance
            elif user.current_balance is None and user.initial_balance is None:
                # Set default values if both are None
                user.initial_balance = 10000.0  # Default starting balance
                user.current_balance = 10000.0
                logger.warning(f"User {user.id} missing both initial and current balance, setting defaults")
            
            # Add the profit/loss to the current balance
            if profit_loss is not None:
                user.current_balance += float(profit_loss)
                logger.info(f"Updated user {user.id} balance: {user.current_balance} after P/L: {profit_loss}")
            
        except Exception as e:
            logger.error(f"Error updating balance for user {user.id}: {str(e)}")
            # Ensure we have valid balance values despite the error
            if user.current_balance is None:
                user.current_balance = user.initial_balance or 10000.0
        
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