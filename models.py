from datetime import datetime
from app import db
from sqlalchemy import UniqueConstraint, Index

class Protocol(db.Model):
    """Model representing crypto protocols"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    market_cap = db.Column(db.BigInteger)
    annual_revenue = db.Column(db.BigInteger)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add indexes for common queries
    __table_args__ = (
        UniqueConstraint('name', name='uix_protocol_name'),
        UniqueConstraint('symbol', name='uix_protocol_symbol'),
        Index('ix_protocol_category', 'category'),
    )
    
    # Relationships
    revenue_data = db.relationship('RevenueData', backref='protocol', lazy=True, cascade="all, delete-orphan")
    user_data = db.relationship('UserData', backref='protocol', lazy=True, cascade="all, delete-orphan")
    scores = db.relationship('Score', backref='protocol', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Protocol {self.name}>'


class RevenueData(db.Model):
    """Model for storing monthly revenue data for protocols"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    total_fees = db.Column(db.BigInteger, default=0)
    source = db.Column(db.String(50))  # e.g., 'vrf', 'automation', 'fm', 'ocr', 'ccip'
    mom_change = db.Column(db.Float)  # Month-over-month change
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('protocol_id', 'month', 'source', name='uix_revenue_protocol_month_source'),
        Index('ix_revenue_protocol_month', 'protocol_id', 'month'),
    )
    
    def __repr__(self):
        return f'<RevenueData {self.protocol.name} {self.month} {self.source}>'


class UserData(db.Model):
    """Model for storing monthly user metrics for protocols"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    month = db.Column(db.Date, nullable=False)
    active_addresses = db.Column(db.Integer, default=0)
    transaction_count = db.Column(db.BigInteger, default=0)
    transaction_volume = db.Column(db.BigInteger, default=0)
    active_address_growth_rate = db.Column(db.Float)
    transaction_count_growth_rate = db.Column(db.Float)
    transaction_volume_growth_rate = db.Column(db.Float)
    active_address_percentile = db.Column(db.Float)
    transaction_count_percentile = db.Column(db.Float)
    transaction_volume_percentile = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('protocol_id', 'month', name='uix_user_protocol_month'),
        Index('ix_user_protocol_month', 'protocol_id', 'month'),
    )
    
    def __repr__(self):
        return f'<UserData {self.protocol.name} {self.month}>'


class Score(db.Model):
    """Model for storing calculated scores for protocols"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    eqs = db.Column(db.Float)  # Earnings Quality Score
    ugs = db.Column(db.Float)  # User Growth Score
    fvs = db.Column(db.Float)  # Fair Value Score
    ss = db.Column(db.Float)   # Safety Score
    how3_score = db.Column(db.Float)  # Combined score
    
    __table_args__ = (
        Index('ix_score_protocol', 'protocol_id'),
        Index('ix_score_how3', 'how3_score'),
    )
    
    def __repr__(self):
        return f'<Score {self.protocol.name} {self.calculated_at}>'


class DuneQuery(db.Model):
    """Model for storing Dune Analytics queries for different protocols"""
    id = db.Column(db.Integer, primary_key=True)
    protocol_id = db.Column(db.Integer, db.ForeignKey('protocol.id'), nullable=False)
    query_type = db.Column(db.String(20), nullable=False)  # 'revenue', 'user'
    query_id = db.Column(db.String(100), nullable=False)  # Dune query ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('protocol_id', 'query_type', name='uix_dune_protocol_type'),
    )
    
    def __repr__(self):
        return f'<DuneQuery {self.protocol.name} {self.query_type}>'
