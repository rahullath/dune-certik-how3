import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from app import db
from models import Protocol, RevenueData, UserData, Category, Score
from dune_client import DuneClient
from config import get_config
from utils import normalize_score

logger = logging.getLogger(__name__)

class DataProcessor:
    """Class for processing and storing data from Dune Analytics"""
    
    def __init__(self):
        self.config = get_config()
        self.dune_client = DuneClient()
    
    def process_revenue_data(self, protocol_name):
        """Process and store revenue data for a protocol"""
        try:
            protocol = Protocol.query.filter_by(name=protocol_name).first()
            if not protocol:
                logger.error(f"Protocol {protocol_name} not found in database")
                return False
            
            # Get revenue data from Dune Analytics
            revenue_df = self.dune_client.get_monthly_revenue_data(protocol_name)
            if revenue_df is None or revenue_df.empty:
                logger.error(f"Failed to get revenue data for {protocol_name}")
                return False
            
            # Process each month's data
            for _, row in revenue_df.iterrows():
                month_date = pd.to_datetime(row['month']).date()
                
                # Check if we already have data for this month
                existing_data = RevenueData.query.filter_by(
                    protocol_id=protocol.id,
                    month=month_date,
                    revenue_source=row.get('source', 'total')
                ).first()
                
                if existing_data:
                    # Update existing record
                    existing_data.revenue = row['total_fees']
                    existing_data.stability_score = row.get('mom_change', 0)
                else:
                    # Create new record
                    new_data = RevenueData(
                        protocol_id=protocol.id,
                        month=month_date,
                        revenue=row['total_fees'],
                        revenue_source=row.get('source', 'total'),
                        stability_score=row.get('mom_change', 0)
                    )
                    db.session.add(new_data)
            
            # Calculate and update magnitude score relative to category peers
            self._calculate_revenue_magnitude(protocol)
            
            # Commit changes
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing revenue data for {protocol_name}: {str(e)}")
            return False
    
    def process_user_data(self, protocol_name):
        """Process and store user growth data for a protocol"""
        try:
            protocol = Protocol.query.filter_by(name=protocol_name).first()
            if not protocol:
                logger.error(f"Protocol {protocol_name} not found in database")
                return False
            
            # Get user growth data from Dune Analytics
            user_df = self.dune_client.get_user_growth_data(protocol_name)
            if user_df is None or user_df.empty:
                logger.error(f"Failed to get user data for {protocol_name}")
                return False
            
            # Process each month's data
            for _, row in user_df.iterrows():
                month_date = pd.to_datetime(row['month']).date()
                
                # Check if we already have data for this month
                existing_data = UserData.query.filter_by(
                    protocol_id=protocol.id,
                    month=month_date
                ).first()
                
                # Prepare data dictionary
                data = {
                    'active_addresses': row.get('active_addresses', 0),
                    'transaction_count': row.get('transaction_count', 0),
                    'transaction_volume': row.get('transaction_volume', 0),
                    'active_address_growth': row.get('active_address_growth_rate', 0),
                    'transaction_count_growth': row.get('transaction_count_growth_rate', 0),
                    'transaction_volume_growth': row.get('transaction_volume_growth_rate', 0)
                }
                
                if existing_data:
                    # Update existing record
                    for key, value in data.items():
                        setattr(existing_data, key, value)
                else:
                    # Create new record
                    new_data = UserData(
                        protocol_id=protocol.id,
                        month=month_date,
                        **data
                    )
                    db.session.add(new_data)
            
            # Commit changes
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing user data for {protocol_name}: {str(e)}")
            return False
    
    def update_protocol_market_data(self, protocol_name, market_cap, price):
        """Update market cap and price data for a protocol"""
        try:
            protocol = Protocol.query.filter_by(name=protocol_name).first()
            if not protocol:
                logger.error(f"Protocol {protocol_name} not found in database")
                return False
            
            protocol.market_cap = market_cap
            protocol.price = price
            protocol.updated_at = datetime.utcnow()
            
            # Calculate annual revenue
            self._calculate_annual_revenue(protocol)
            
            # Commit changes
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating market data for {protocol_name}: {str(e)}")
            return False
    
    def update_all_protocols(self):
        """Update data for all protocols in the database"""
        protocols = Protocol.query.all()
        
        success_count = 0
        for protocol in protocols:
            revenue_success = self.process_revenue_data(protocol.name)
            user_success = self.process_user_data(protocol.name)
            
            if revenue_success and user_success:
                success_count += 1
                
        logger.info(f"Updated {success_count}/{len(protocols)} protocols successfully")
        return success_count
    
    def _calculate_revenue_magnitude(self, protocol):
        """Calculate revenue magnitude score relative to category peers"""
        try:
            # Get protocols in the same category
            category_protocols = Protocol.query.filter_by(category=protocol.category).all()
            if len(category_protocols) <= 1:
                return
            
            # For each protocol, get the most recent month's total revenue
            protocol_revenues = []
            for p in category_protocols:
                latest_revenue = RevenueData.query.filter_by(protocol_id=p.id) \
                    .order_by(RevenueData.month.desc()).first()
                
                if latest_revenue:
                    protocol_revenues.append((p.id, latest_revenue.revenue))
            
            if not protocol_revenues:
                return
            
            # Calculate percentile ranks
            protocol_ids, revenues = zip(*protocol_revenues)
            revenues = np.array(revenues)
            percentiles = {protocol_ids[i]: np.percentile(revenues, i * 100 / (len(revenues)-1)) 
                          for i in range(len(revenues))}
            
            # Update magnitude scores for all protocols in the category
            for p_id, revenue in protocol_revenues:
                magnitude_score = percentiles[p_id] / 100
                
                # Update all revenue data for this protocol
                RevenueData.query.filter_by(protocol_id=p_id).update({
                    'magnitude_score': magnitude_score
                })
                
        except Exception as e:
            logger.error(f"Error calculating revenue magnitude: {str(e)}")
    
    def _calculate_annual_revenue(self, protocol):
        """Calculate annual revenue for a protocol"""
        try:
            # Get the last 12 months of revenue data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=365)
            
            annual_revenue = db.session.query(db.func.sum(RevenueData.revenue)) \
                .filter(RevenueData.protocol_id == protocol.id) \
                .filter(RevenueData.month >= start_date) \
                .filter(RevenueData.month <= end_date) \
                .scalar() or 0
            
            protocol.annual_revenue = annual_revenue
            
        except Exception as e:
            logger.error(f"Error calculating annual revenue for {protocol.name}: {str(e)}")
