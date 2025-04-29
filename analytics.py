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
        # Get all trades for this user
        trades = Trade.query.filter_by(user_id=user_id).all()
        
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
        
        # Calculate win/loss rates
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        loss_rate = (losses / total_trades) * 100 if total_trades > 0 else 0
        
        # Calculate profit/loss metrics
        net_profit_loss = sum(t.profit_loss or 0 for t in trades)
        
        # Calculate average win/loss
        win_trades = [t for t in trades if t.result == 'Win' and t.profit_loss is not None]
        loss_trades = [t for t in trades if t.result == 'Loss' and t.profit_loss is not None]
        
        avg_win = sum(t.profit_loss for t in win_trades) / len(win_trades) if win_trades else 0
        avg_loss = abs(sum(t.profit_loss for t in loss_trades) / len(loss_trades)) if loss_trades else 0
        
        # Calculate risk/reward ratio
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Find most traded pair
        pair_counts = defaultdict(int)
        for trade in trades:
            pair_counts[trade.pair_traded] += 1
        
        most_traded_pair = max(pair_counts.items(), key=lambda x: x[1])[0] if pair_counts else 'None'
        
        # Find best and worst performing pairs
        pair_performance = defaultdict(lambda: {'profit_loss': 0, 'count': 0})
        
        for trade in trades:
            if trade.profit_loss is not None:
                pair = trade.pair_traded
                pair_performance[pair]['profit_loss'] += trade.profit_loss
                pair_performance[pair]['count'] += 1
        
        # Calculate per-trade average for each pair
        for pair in pair_performance:
            if pair_performance[pair]['count'] > 0:
                pair_performance[pair]['avg'] = pair_performance[pair]['profit_loss'] / pair_performance[pair]['count']
            else:
                pair_performance[pair]['avg'] = 0
        
        # Find best and worst pairs (must have at least 2 trades)
        qualified_pairs = {k: v for k, v in pair_performance.items() if v['count'] >= 2}
        
        best_pair = max(qualified_pairs.items(), key=lambda x: x[1]['avg'])[0] if qualified_pairs else 'None'
        worst_pair = min(qualified_pairs.items(), key=lambda x: x[1]['avg'])[0] if qualified_pairs else 'None'
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'breakevens': breakevens,
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
        # Get trades for the specified date range
        trades = Trade.query.filter_by(user_id=user_id).filter(
            Trade.date >= start_date,
            Trade.date <= end_date
        ).all()
        
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
        
        # Calculate win/loss rates
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Calculate profit/loss metrics
        net_profit_loss = sum(t.profit_loss or 0 for t in trades)
        
        # Generate notes based on performance
        if wins > losses:
            notes = f"Great week! You had {wins} winning trades, which is {round(win_rate, 2)}% of your total trades."
        elif losses > wins:
            notes = f"Challenging week with {losses} losing trades. Review your strategy and consider risk management."
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
            'win_rate': win_rate,
            'net_profit_loss': net_profit_loss,
            'notes': notes
        }
    except Exception as e:
        logger.error(f"Error generating weekly report: {str(e)}")
        raise