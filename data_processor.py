import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from app import db
from models import Protocol, RevenueData, UserData, Score, DuneQuery
from dune_api import DuneAnalyticsAPI
from certik_api import CertikAPI
from score_calculator import ScoreCalculator

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processes data from various sources to calculate protocol scores."""
    
    def __init__(self):
        self.dune_api = DuneAnalyticsAPI()
        self.certik_api = CertikAPI()
    
    def update_protocol_data(self, protocol_id: int) -> bool:
        """Update data for a specific protocol and recalculate scores.
        
        Args:
            protocol_id: ID of the protocol to update
            
        Returns:
            Success status
        """
        try:
            # Get protocol
            protocol = Protocol.query.get(protocol_id)
            if not protocol:
                logger.error(f"Protocol with ID {protocol_id} not found")
                return False
            
            # Get Dune query IDs for this protocol
            revenue_query = DuneQuery.query.filter_by(protocol_id=protocol_id, query_type='revenue').first()
            user_query = DuneQuery.query.filter_by(protocol_id=protocol_id, query_type='user').first()
            
            if not revenue_query or not user_query:
                logger.error(f"Missing Dune queries for protocol {protocol.name}")
                return False
            
            # Fetch data from Dune
            revenue_data = self.dune_api.get_revenue_data(revenue_query.query_id, protocol.name)
            user_data = self.dune_api.get_user_data(user_query.query_id, protocol.name)
            
            # Update database with new data
            self._update_revenue_data(protocol_id, revenue_data)
            self._update_user_data(protocol_id, user_data)
            
            # Get security score from Certik
            security_data = self.certik_api.get_project_security_score(protocol.name)
            security_score = self.certik_api.normalize_security_score(security_data)
            
            # Calculate annual revenue
            annual_revenue = self._calculate_annual_revenue(protocol_id)
            
            # Update protocol with annual revenue
            protocol.annual_revenue = annual_revenue
            db.session.commit()
            
            # Calculate scores
            self._calculate_and_save_scores(protocol_id, security_score)
            
            logger.info(f"Successfully updated data for protocol {protocol.name}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating protocol data: {e}")
            db.session.rollback()
            return False
    
    def update_all_protocols(self) -> Tuple[int, int]:
        """Update data for all protocols.
        
        Returns:
            Tuple of (success_count, total_count)
        """
        protocols = Protocol.query.all()
        success_count = 0
        total_count = len(protocols)
        
        for protocol in protocols:
            if self.update_protocol_data(protocol.id):
                success_count += 1
        
        logger.info(f"Updated {success_count}/{total_count} protocols")
        return success_count, total_count
    
    def _update_revenue_data(self, protocol_id: int, revenue_data: List[Dict[str, Any]]) -> None:
        """Update revenue data for a protocol.
        
        Args:
            protocol_id: ID of the protocol
            revenue_data: List of revenue data dictionaries
        """
        try:
            for data in revenue_data:
                month_str = data.get('month')
                if not month_str:
                    continue
                
                # Parse the month string to a date object
                if isinstance(month_str, str):
                    month_date = datetime.strptime(month_str, "%Y-%m-%d").date()
                else:
                    month_date = month_str
                
                # Check if we already have this data
                existing = RevenueData.query.filter_by(
                    protocol_id=protocol_id, 
                    month=month_date,
                    source=data.get('source', '')
                ).first()
                
                if existing:
                    # Update existing record
                    existing.total_fees = data.get('total_fees', 0)
                    existing.mom_change = data.get('mom_change')
                else:
                    # Create new record
                    new_record = RevenueData(
                        protocol_id=protocol_id,
                        month=month_date,
                        total_fees=data.get('total_fees', 0),
                        source=data.get('source', ''),
                        mom_change=data.get('mom_change')
                    )
                    db.session.add(new_record)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating revenue data: {e}")
            db.session.rollback()
    
    def _update_user_data(self, protocol_id: int, user_data: List[Dict[str, Any]]) -> None:
        """Update user metrics data for a protocol.
        
        Args:
            protocol_id: ID of the protocol
            user_data: List of user metrics data dictionaries
        """
        try:
            for data in user_data:
                month_str = data.get('month')
                if not month_str:
                    continue
                
                # Parse the month string to a date object
                if isinstance(month_str, str):
                    month_date = datetime.strptime(month_str, "%Y-%m-%d").date()
                else:
                    month_date = month_str
                
                # Check if we already have this data
                existing = UserData.query.filter_by(
                    protocol_id=protocol_id, 
                    month=month_date
                ).first()
                
                if existing:
                    # Update existing record
                    existing.active_addresses = data.get('active_addresses', 0)
                    existing.transaction_count = data.get('transaction_count', 0)
                    existing.transaction_volume = data.get('transaction_volume', 0)
                    existing.active_address_growth_rate = data.get('active_address_growth_rate')
                    existing.transaction_count_growth_rate = data.get('transaction_count_growth_rate')
                    existing.transaction_volume_growth_rate = data.get('transaction_volume_growth_rate')
                    existing.active_address_percentile = data.get('active_address_percentile')
                    existing.transaction_count_percentile = data.get('transaction_count_percentile')
                    existing.transaction_volume_percentile = data.get('transaction_volume_percentile')
                else:
                    # Create new record
                    new_record = UserData(
                        protocol_id=protocol_id,
                        month=month_date,
                        active_addresses=data.get('active_addresses', 0),
                        transaction_count=data.get('transaction_count', 0),
                        transaction_volume=data.get('transaction_volume', 0),
                        active_address_growth_rate=data.get('active_address_growth_rate'),
                        transaction_count_growth_rate=data.get('transaction_count_growth_rate'),
                        transaction_volume_growth_rate=data.get('transaction_volume_growth_rate'),
                        active_address_percentile=data.get('active_address_percentile'),
                        transaction_count_percentile=data.get('transaction_count_percentile'),
                        transaction_volume_percentile=data.get('transaction_volume_percentile')
                    )
                    db.session.add(new_record)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating user data: {e}")
            db.session.rollback()
    
    def _calculate_annual_revenue(self, protocol_id: int) -> int:
        """Calculate annual revenue for a protocol.
        
        Args:
            protocol_id: ID of the protocol
            
        Returns:
            Annual revenue in USD
        """
        try:
            # Get data for the last 12 months
            today = datetime.utcnow().date()
            start_date = today - relativedelta(months=12)
            
            # Query total fees across all sources
            revenue_data = RevenueData.query.filter(
                RevenueData.protocol_id == protocol_id,
                RevenueData.month >= start_date
            ).all()
            
            # Sum the revenue
            total_revenue = sum(data.total_fees for data in revenue_data)
            
            return total_revenue
        
        except Exception as e:
            logger.error(f"Error calculating annual revenue: {e}")
            return 0
    
    def _calculate_and_save_scores(self, protocol_id: int, security_score: float) -> None:
        """Calculate and save all scores for a protocol.
        
        Args:
            protocol_id: ID of the protocol
            security_score: Security score from Certik
        """
        try:
            protocol = Protocol.query.get(protocol_id)
            if not protocol:
                logger.error(f"Protocol with ID {protocol_id} not found")
                return
            
            # Get the last 12 months of data
            today = datetime.utcnow().date()
            start_date = today - relativedelta(months=12)
            
            revenue_data = RevenueData.query.filter(
                RevenueData.protocol_id == protocol_id,
                RevenueData.month >= start_date
            ).all()
            
            user_data = UserData.query.filter(
                UserData.protocol_id == protocol_id,
                UserData.month >= start_date
            ).all()
            
            # Convert to dictionary format for the calculator
            revenue_dict_list = [
                {
                    'month': data.month,
                    'total_fees': data.total_fees,
                    'source': data.source,
                    'mom_change': data.mom_change
                }
                for data in revenue_data
            ]
            
            user_dict_list = [
                {
                    'month': data.month,
                    'active_addresses': data.active_addresses,
                    'transaction_count': data.transaction_count,
                    'transaction_volume': data.transaction_volume,
                    'active_address_growth_rate': data.active_address_growth_rate,
                    'transaction_count_growth_rate': data.transaction_count_growth_rate,
                    'transaction_volume_growth_rate': data.transaction_volume_growth_rate,
                    'active_address_percentile': data.active_address_percentile,
                    'transaction_count_percentile': data.transaction_count_percentile,
                    'transaction_volume_percentile': data.transaction_volume_percentile
                }
                for data in user_data
            ]
            
            # Calculate scores
            eqs = ScoreCalculator.calculate_eqs(revenue_dict_list, protocol.category)
            ugs = ScoreCalculator.calculate_ugs(user_dict_list)
            fvs = ScoreCalculator.calculate_fvs(protocol.market_cap, protocol.annual_revenue, protocol.category)
            how3_score = ScoreCalculator.calculate_how3_score(eqs, ugs, fvs, security_score)
            
            # Create new score record
            new_score = Score(
                protocol_id=protocol_id,
                calculated_at=datetime.utcnow(),
                eqs=eqs,
                ugs=ugs,
                fvs=fvs,
                ss=security_score,
                how3_score=how3_score
            )
            
            db.session.add(new_score)
            db.session.commit()
            
            logger.info(f"Calculated scores for {protocol.name}: How3={how3_score}, EQS={eqs}, UGS={ugs}, FVS={fvs}, SS={security_score}")
            
        except Exception as e:
            logger.error(f"Error calculating scores: {e}")
            db.session.rollback()
