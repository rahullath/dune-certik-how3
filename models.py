from datetime import datetime
from app import db

class Protocol(db.Model):
    """Model for crypto protocols"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    market_cap = db.Column(db.Float)
    price = db.Column(db.Float)
    annual_revenue = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scores = db.relationship('Score', backref='protocol', lazy=True)
    revenue_data = db.relationship('RevenueData', backref='protocol', lazy=True)
    user_data = db.relationship('UserData', backref='protocol', lazy=True)
    
    def __repr__(self):
        return f"<Protocol {self.name}>"

class Score(db.Model):
    """Model for protocol scores"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    earnings_quality_score = db.Column(db.Float)
    user_growth_score = db.Column(db.Float)
    fair_value_score = db.Column(db.Float)
    safety_score = db.Column(db.Float)
    how3_score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Score {self.protocol_id}>"

class RevenueData(db.Model):
    """Model for protocol revenue data"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    revenue = db.Column(db.Float)
    revenue_source = db.Column(db.String(50))
    stability_score = db.Column(db.Float)
    magnitude_score = db.Column(db.Float)
    
    def __repr__(self):
        return f"<RevenueData {self.protocol_id} {self.month}>"

class UserData(db.Model):
    """Model for protocol user data"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    active_addresses = db.Column(db.Integer)
    transaction_count = db.Column(db.Integer)
    transaction_volume = db.Column(db.Float)
    active_address_growth = db.Column(db.Float)
    transaction_count_growth = db.Column(db.Float)
    transaction_volume_growth = db.Column(db.Float)
    
    def __repr__(self):
        return f"<UserData {self.protocol_id} {self.month}>"

class Category(db.Model):
    """Model for protocol categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    avg_revenue_multiple = db.Column(db.Float)
    avg_annual_revenue = db.Column(db.Float)
    
    def __repr__(self):
        return f"<Category {self.name}>"

class DuneQuery(db.Model):
    """Model for storing Dune Analytics query templates"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    query_type = db.Column(db.String(50), nullable=False)  # revenue, users, etc.
    query_text = db.Column(db.Text, nullable=False)
    last_executed = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<DuneQuery {self.protocol_id} {self.query_type}>"
