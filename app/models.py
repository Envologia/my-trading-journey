"""
Database models for the application
"""
from datetime import datetime
from enum import Enum
import json
from app import db

class ExperienceLevel(Enum):
    BEGINNER = 'Beginner'
    INTERMEDIATE = 'Intermediate'
    ADVANCED = 'Advanced'

class AccountType(Enum):
    PERSONAL = 'Personal'
    FUNDED = 'Funded'

class Phase(Enum):
    PHASE1 = 'Phase 1'
    PHASE2 = 'Phase 2'

class TradeResult(Enum):
    WIN = 'Win'
    LOSS = 'Loss'
    BREAKEVEN = 'Breakeven'

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    trading_years = db.Column(db.Float, nullable=True)
    experience_level = db.Column(db.String(20), nullable=True)
    account_type = db.Column(db.String(20), nullable=True)
    phase = db.Column(db.String(20), nullable=True)
    profit_target = db.Column(db.Float, nullable=True)
    initial_balance = db.Column(db.Float, nullable=True)
    current_balance = db.Column(db.Float, nullable=True)
    therapy_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    registration_complete = db.Column(db.Boolean, default=False)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy=True)
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"

class Trade(db.Model):
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    pair_traded = db.Column(db.String(50), nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)  # in USD
    take_profit = db.Column(db.Float, nullable=False)  # in USD
    result = db.Column(db.String(20), nullable=False)  # Win, Loss, Breakeven
    screenshot_id = db.Column(db.String(255), nullable=True)  # Telegram file_id for screenshot
    notes = db.Column(db.Text, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)  # Calculated P/L
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade {self.id} for User {self.user_id}>"

class TherapySession(db.Model):
    __tablename__ = 'therapy_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Store the conversation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('therapy_sessions', lazy=True))
    
    def __repr__(self):
        return f"<TherapySession {self.id} for User {self.user_id}>"

class WeeklyReport(db.Model):
    __tablename__ = 'weekly_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    breakevens = db.Column(db.Integer, default=0)
    win_rate = db.Column(db.Float, default=0.0)
    net_profit_loss = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('weekly_reports', lazy=True))
    
    def __repr__(self):
        return f"<WeeklyReport {self.id} for User {self.user_id}>"

class UserState(db.Model):
    __tablename__ = 'user_states'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    data = db.Column(db.Text, nullable=True)  # JSON serialized data
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('state', uselist=False, lazy=True))
    
    def get_data(self):
        """Get the deserialized data"""
        if self.data:
            return json.loads(self.data)
        return {}
    
    def set_data(self, data_dict):
        """Serialize and set the data"""
        self.data = json.dumps(data_dict)
    
    def __repr__(self):
        return f"<UserState {self.id} for User {self.user_id}>"