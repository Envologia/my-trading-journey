#!/usr/bin/env python3
"""
Handle user states and conversation flows
"""
import json
import logging
from app import db
from models import UserState

# Configure logging
logger = logging.getLogger(__name__)

class REGISTRATION_STATES:
    FULL_NAME = 'registration_full_name'
    AGE = 'registration_age'
    TRADING_YEARS = 'registration_trading_years'
    EXPERIENCE = 'registration_experience'
    ACCOUNT_TYPE = 'registration_account_type'
    PHASE = 'registration_phase'
    PROFIT_TARGET = 'registration_profit_target'
    INITIAL_BALANCE = 'registration_initial_balance'

class JOURNAL_STATES:
    DATE = 'journal_date'
    PAIR = 'journal_pair'
    SL = 'journal_sl'
    TP = 'journal_tp'
    RESULT = 'journal_result'
    SCREENSHOT = 'journal_screenshot'
    NOTES = 'journal_notes'

class THERAPY_STATES:
    ACTIVE = 'therapy_active'
    COMPLETED = 'therapy_completed'

def get_user_state(user_id):
    """Get the current state for a user"""
    state = UserState.query.filter_by(user_id=user_id).first()
    return state

def set_user_state(user_id, state, data=None):
    """Set the state for a user with optional data"""
    user_state = UserState.query.filter_by(user_id=user_id).first()
    
    if not user_state:
        user_state = UserState(user_id=user_id, state=state)
        db.session.add(user_state)
    else:
        user_state.state = state
    
    if data is not None:
        user_state.set_data(data)
    
    db.session.commit()
    logger.debug(f"Set state for user {user_id}: {state} with data: {data}")
    
    return user_state

def clear_user_state(user_id):
    """Clear the state for a user"""
    user_state = UserState.query.filter_by(user_id=user_id).first()
    
    if user_state:
        db.session.delete(user_state)
        db.session.commit()
        logger.debug(f"Cleared state for user {user_id}")
    
    return True