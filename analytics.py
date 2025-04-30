#!/usr/bin/env python3
"""
Analytics module for calculating trading statistics
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from app import db
from models import User, Trade

# Configure logging
logger = logging.getLogger(__name__)

def calculate_stats(user_id):
    """Calculate trading statistics for a user"""
    try:
        logger.info(f"Starting stats calculation for user_id: {user_id}")
        # Get all trades for this user
        trades = Trade.query.filter_by(user_id=user_id).all()
        logger.info(f"Retrieved {len(trades)} trades for statistics calculation")
        
        if not trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'breakevens': 0,
                'win_rate': 0,
                'loss_rate': 0,
                'net_profit_loss': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'risk_reward_ratio': 0,
                'most_traded_pair': 'None',
                'best_pair': 'None',
                'worst_pair': 'None'
            }
        
        total_trades = len(trades)
        wins = sum(1 for t in trades if t.result == 'Win')
        losses = sum(1 for t in trades if t.result == 'Loss')
        breakevens = sum(1 for t in trades if t.result == 'Breakeven')
        
        # Calculate effective wins/losses including breakeven trades with profit/loss
        effective_wins = wins + sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss > 0)
        effective_losses = losses + sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss < 0)
        
        # Calculate win/loss rates with a more reliable approach
        # Only count trades with a clear outcome
        counted_trades = wins + losses
        # Add breakeven trades that have a non-zero profit/loss value
        profitable_be = sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss > 0)
        unprofitable_be = sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss < 0)
        counted_trades += profitable_be + unprofitable_be
        
        # Log detailed calculation information for debugging
        logger.info(f"Win rate calculation details:")
        logger.info(f"Raw win count: {wins}, Raw loss count: {losses}")
        logger.info(f"Profitable breakevens: {profitable_be}, Unprofitable breakevens: {unprofitable_be}")
        logger.info(f"Effective wins: {effective_wins}, Effective losses: {effective_losses}")
        logger.info(f"Counted trades: {counted_trades}")
        
        # Calculate rates, ensuring we don't divide by zero
        if counted_trades > 0:
            win_rate = (effective_wins / counted_trades) * 100
            loss_rate = (effective_losses / counted_trades) * 100
            logger.info(f"Calculated win rate: {win_rate:.2f}%, loss rate: {loss_rate:.2f}%")
        else:
            win_rate = 0.0
            loss_rate = 0.0
            logger.info("No countable trades (wins/losses), using default rates of 0%")
        
        # Calculate profit/loss metrics
        net_profit_loss = sum(t.profit_loss or 0 for t in trades)
        
        # Calculate average win/loss including profitable breakevens in wins and loss breakevens in losses
        # Wins include Win trades and Breakeven trades with positive profit
        win_trades = [t for t in trades if 
                      (t.result == 'Win' and t.profit_loss is not None) or 
                      (t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss > 0)]
        
        # Losses include Loss trades and Breakeven trades with negative profit
        loss_trades = [t for t in trades if 
                       (t.result == 'Loss' and t.profit_loss is not None) or 
                       (t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss < 0)]
        
        # Calculate averages
        avg_win = sum(t.profit_loss for t in win_trades) / len(win_trades) if win_trades else 0
        avg_loss = abs(sum(t.profit_loss for t in loss_trades) / len(loss_trades)) if loss_trades else 0
        
        # Calculate risk/reward ratio
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Find most traded pair
        pair_counts = defaultdict(int)
        for trade in trades:
            pair_counts[trade.pair_traded] += 1
        
        most_traded_pair = max(pair_counts.items(), key=lambda x: x[1])[0] if pair_counts else 'None'
        
        # Find best and worst performing pairs with proper type handling
        pair_performance = {}
        
        for trade in trades:
            if trade.profit_loss is not None:
                pair = trade.pair_traded
                # Initialize if not exists
                if pair not in pair_performance:
                    pair_performance[pair] = {'profit_loss': 0.0, 'count': 0, 'avg': 0.0}
                
                # Update with proper types
                pair_performance[pair]['profit_loss'] += float(trade.profit_loss)
                pair_performance[pair]['count'] += 1
        
        # Calculate per-trade average for each pair
        for pair in pair_performance:
            # Get count value
            count = pair_performance[pair]['count']
            if count > 0:
                # Calculate average and update in dictionary - using direct assignment
                avg_value = float(pair_performance[pair]['profit_loss'] / count)
                # Python allows updating dict values even if initialized with different types
                pair_performance[pair] = {
                    'profit_loss': pair_performance[pair]['profit_loss'],
                    'count': count,
                    'avg': avg_value
                }
            else:
                pair_performance[pair] = {
                    'profit_loss': pair_performance[pair]['profit_loss'],
                    'count': count,
                    'avg': 0.0
                }
        
        # Find best and worst pairs (must have at least 2 trades)
        qualified_pairs = {k: v for k, v in pair_performance.items() if v['count'] >= 2}
        
        best_pair = max(qualified_pairs.items(), key=lambda x: x[1]['avg'])[0] if qualified_pairs else 'None'
        worst_pair = min(qualified_pairs.items(), key=lambda x: x[1]['avg'])[0] if qualified_pairs else 'None'
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'breakevens': breakevens,
            'effective_wins': effective_wins,
            'effective_losses': effective_losses,
            'win_rate': round(win_rate, 2),
            'loss_rate': round(loss_rate, 2),
            'net_profit_loss': net_profit_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'most_traded_pair': most_traded_pair,
            'best_pair': best_pair,
            'worst_pair': worst_pair
        }
    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        raise

def generate_weekly_report(user_id, start_date, end_date):
    """Generate a weekly report for a user"""
    try:
        logger.info(f"Generating weekly report for user_id: {user_id} from {start_date} to {end_date}")
        # Get trades for the specified date range
        trades = Trade.query.filter_by(user_id=user_id).filter(
            Trade.date >= start_date,
            Trade.date <= end_date
        ).all()
        logger.info(f"Retrieved {len(trades)} trades for weekly report")
        
        if not trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'breakevens': 0,
                'win_rate': 0,
                'net_profit_loss': 0,
                'notes': 'No trades recorded for this week.'
            }
        
        total_trades = len(trades)
        wins = sum(1 for t in trades if t.result == 'Win')
        losses = sum(1 for t in trades if t.result == 'Loss')
        breakevens = sum(1 for t in trades if t.result == 'Breakeven')
        
        # Effective win/loss counts including profitable/unprofitable breakevens
        effective_wins = wins + sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss > 0)
        effective_losses = losses + sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss < 0)
        
        # Calculate win rate using a more direct and reliable formula
        # First, only count trades with a clear outcome
        counted_trades = wins + losses
        # Add breakeven trades that have a non-zero profit/loss value
        profitable_be = sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss > 0)
        unprofitable_be = sum(1 for t in trades if t.result == 'Breakeven' and t.profit_loss is not None and t.profit_loss < 0)
        counted_trades += profitable_be + unprofitable_be
        
        # Log detailed calculation information for debugging
        logger.info(f"Weekly report win rate calculation details:")
        logger.info(f"Raw win count: {wins}, Raw loss count: {losses}")
        logger.info(f"Profitable breakevens: {profitable_be}, Unprofitable breakevens: {unprofitable_be}")
        logger.info(f"Effective wins: {effective_wins}, Effective losses: {effective_losses}")
        logger.info(f"Counted trades: {counted_trades}")
        
        # Calculate win rate, ensuring we don't divide by zero
        if counted_trades > 0:
            # Calculate using the effective wins (raw wins + profitable breakevens)
            win_rate = effective_wins / counted_trades * 100
            logger.info(f"Calculated weekly win rate: {win_rate:.2f}%")
        else:
            win_rate = 0.0  # Default to zero if no counted trades
            logger.info("No countable trades in weekly report, using default rate of 0%")
        
        # Calculate profit/loss metrics
        net_profit_loss = sum(t.profit_loss or 0 for t in trades)
        
        # Generate notes based on performance using effective win/loss numbers
        if effective_wins > effective_losses:
            notes = f"Great week! You had {effective_wins} winning trades, which is {round(win_rate, 1)}% of your trades."
        elif effective_losses > effective_wins:
            notes = f"Challenging week with {effective_losses} losing trades. Review your strategy and consider risk management."
        else:
            notes = "Mixed results this week. Focus on consistency and stick to your trading plan."
        
        if net_profit_loss > 0:
            notes += f" You made a profit of ${net_profit_loss:.2f}."
        elif net_profit_loss < 0:
            notes += f" You had a loss of ${abs(net_profit_loss):.2f}."
        else:
            notes += " You broke even this week."
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'breakevens': breakevens,
            'effective_wins': effective_wins,
            'effective_losses': effective_losses,
            'win_rate': win_rate,
            'net_profit_loss': net_profit_loss,
            'notes': notes
        }
    except Exception as e:
        logger.error(f"Error generating weekly report: {str(e)}")
        raise