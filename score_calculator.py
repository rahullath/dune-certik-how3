import numpy as np
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import Protocol, RevenueData, UserData, Score, Category
from config import get_config
from utils import normalize_score, calculate_percentile_rank
from certik_client import CertikClient

logger = logging.getLogger(__name__)

class ScoreCalculator:
    """Class for calculating standardized scores for protocols"""
    
    def __init__(self):
        self.config = get_config()
        self.certik_client = CertikClient()
        
        # Weighting factors from config
        self.rev_stability_weight = self.config.REVENUE_STABILITY_WEIGHT
        self.rev_magnitude_weight = self.config.REVENUE_MAGNITUDE_WEIGHT
        
        self.active_addr_weight = self.config.ACTIVE_ADDRESSES_WEIGHT
        self.tx_count_weight = self.config.TRANSACTION_COUNT_WEIGHT
        self.tx_volume_weight = self.config.TRANSACTION_VOLUME_WEIGHT
        
        self.eqs_weight = self.config.EQS_WEIGHT
        self.ugs_weight = self.config.UGS_WEIGHT
        self.fvs_weight = self.config.FVS_WEIGHT
        self.ss_weight = self.config.SS_WEIGHT
    
    def calculate_protocol_scores(self, protocol_id=None):
        """Calculate scores for a specific protocol or all protocols"""
        try:
            if protocol_id:
                protocols = [Protocol.query.get(protocol_id)]
                if not protocols[0]:
                    logger.error(f"Protocol with ID {protocol_id} not found")
                    return False
            else:
                protocols = Protocol.query.all()
            
            for protocol in protocols:
                eqs = self._calculate_eqs(protocol)
                ugs = self._calculate_ugs(protocol)
                fvs = self._calculate_fvs(protocol)
                ss = self._get_safety_score(protocol)
                
                # Calculate combined How3 score
                how3_score = float(
                    self.eqs_weight * eqs + 
                    self.ugs_weight * ugs + 
                    self.fvs_weight * fvs + 
                    self.ss_weight * ss
                )
                
                # Create or update score record
                existing_score = Score.query.filter_by(protocol_id=protocol.id).first()
                
                if existing_score:
                    existing_score.earnings_quality_score = float(eqs)
                    existing_score.user_growth_score = float(ugs)
                    existing_score.fair_value_score = float(fvs)
                    existing_score.safety_score = float(ss)
                    existing_score.how3_score = float(how3_score)
                    existing_score.timestamp = datetime.utcnow()
                else:
                    new_score = Score(
                        protocol_id=protocol.id,
                        earnings_quality_score=float(eqs),
                        user_growth_score=float(ugs),
                        fair_value_score=float(fvs),
                        safety_score=float(ss),
                        how3_score=float(how3_score),
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(new_score)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error calculating scores: {str(e)}")
            return False
    
    def _calculate_eqs(self, protocol):
        """Calculate Earnings Quality Score for a protocol"""
        try:
            # Get last 6 months of revenue data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=180)
            
            revenue_data = RevenueData.query.filter(
                RevenueData.protocol_id == protocol.id,
                RevenueData.month >= start_date,
                RevenueData.month <= end_date
            ).order_by(RevenueData.month).all()
            
            if not revenue_data or len(revenue_data) < 2:
                logger.warning(f"Insufficient revenue data for {protocol.name}")
                return 0
            
            # Calculate stability metric (lower variance is better)
            mom_changes = [rd.stability_score for rd in revenue_data if rd.stability_score is not None]
            if mom_changes:
                # Convert to numpy array for calculations
                mom_changes = np.array(mom_changes)
                
                # Calculate stability score (inverse of standard deviation, normalized)
                stability_raw = 1 / (1 + np.std(mom_changes))
                stability_score = normalize_score(stability_raw, 0, 1)
            else:
                stability_score = 0
            
            # Get magnitude score (already calculated relative to category peers)
            latest_data = revenue_data[-1] if revenue_data else None
            magnitude_score = latest_data.magnitude_score if latest_data and latest_data.magnitude_score else 0
            
            # Combined EQS using weighted average
            eqs = (
                self.rev_stability_weight * stability_score + 
                self.rev_magnitude_weight * magnitude_score
            )
            
            return min(max(eqs, 0), 100)  # Ensure score is between 0 and 100
            
        except Exception as e:
            logger.error(f"Error calculating EQS for {protocol.name}: {str(e)}")
            return 0
    
    def _calculate_ugs(self, protocol):
        """Calculate User Growth Score for a protocol"""
        try:
            # Get last 6 months of user data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=180)
            
            user_data = UserData.query.filter(
                UserData.protocol_id == protocol.id,
                UserData.month >= start_date,
                UserData.month <= end_date
            ).order_by(UserData.month).all()
            
            if not user_data:
                logger.warning(f"No user data found for {protocol.name}")
                return 0
            
            # Get the latest user data metrics
            latest_data = user_data[-1]
            
            # Get protocols in the same category
            category_protocols = Protocol.query.filter_by(category=protocol.category).all()
            protocol_ids = [p.id for p in category_protocols]
            
            # Get the latest user data for all protocols in the category
            latest_month = db.session.query(func.max(UserData.month)).scalar()
            category_data = UserData.query.filter(
                UserData.protocol_id.in_(protocol_ids),
                UserData.month == latest_month
            ).all()
            
            if not category_data:
                logger.warning(f"No category data found for {protocol.category}")
                return 0
            
            # Calculate percentile ranks for each metric
            active_addr_rank = calculate_percentile_rank(
                [data.active_addresses for data in category_data],
                latest_data.active_addresses
            )
            
            tx_count_rank = calculate_percentile_rank(
                [data.transaction_count for data in category_data],
                latest_data.transaction_count
            )
            
            tx_volume_rank = calculate_percentile_rank(
                [data.transaction_volume for data in category_data],
                latest_data.transaction_volume
            )
            
            # Calculate growth trend factor (positive growth rates are better)
            growth_factors = []
            if latest_data.active_address_growth is not None:
                growth_factors.append(normalize_score(latest_data.active_address_growth, -100, 100))
            if latest_data.transaction_count_growth is not None:
                growth_factors.append(normalize_score(latest_data.transaction_count_growth, -100, 100))
            if latest_data.transaction_volume_growth is not None:
                growth_factors.append(normalize_score(latest_data.transaction_volume_growth, -100, 100))
            
            growth_factor = np.mean(growth_factors) if growth_factors else 0
            
            # Combined UGS using weighted average of metrics and growth trend
            ugs = (
                0.7 * (
                    self.active_addr_weight * active_addr_rank +
                    self.tx_count_weight * tx_count_rank +
                    self.tx_volume_weight * tx_volume_rank
                ) +
                0.3 * growth_factor
            )
            
            return min(max(ugs * 100, 0), 100)  # Ensure score is between 0 and 100
            
        except Exception as e:
            logger.error(f"Error calculating UGS for {protocol.name}: {str(e)}")
            return 0
    
    def _calculate_fvs(self, protocol):
        """Calculate Fair Value Score for a protocol"""
        try:
            if not protocol.market_cap or not protocol.annual_revenue or protocol.annual_revenue <= 0:
                logger.warning(f"Missing market cap or revenue data for {protocol.name}")
                return 0
            
            # Calculate P/S ratio (Price to Sales, or Market Cap to Annual Revenue)
            ps_ratio = protocol.market_cap / protocol.annual_revenue
            
            # Get category average P/S ratio
            category = Category.query.filter_by(name=protocol.category).first()
            category_avg_ps = category.avg_revenue_multiple if category else None
            
            if not category_avg_ps or category_avg_ps <= 0:
                # If no category average, calculate it from all protocols in the category
                category_protocols = Protocol.query.filter_by(category=protocol.category).all()
                
                valid_protocols = [p for p in category_protocols 
                                   if p.market_cap and p.annual_revenue and p.annual_revenue > 0]
                
                if valid_protocols:
                    ratios = [p.market_cap / p.annual_revenue for p in valid_protocols]
                    category_avg_ps = np.median(ratios)  # Using median to avoid outlier influence
                    
                    # Update category average
                    if category:
                        category.avg_revenue_multiple = category_avg_ps
                        db.session.commit()
                else:
                    # Fallback to a reasonable default if no data is available
                    category_avg_ps = 30
            
            # Calculate how undervalued/overvalued the protocol is compared to category average
            # Lower P/S ratio is better (undervalued)
            if ps_ratio <= category_avg_ps:
                # Undervalued or fairly valued
                value_factor = 1 - (ps_ratio / category_avg_ps)
            else:
                # Overvalued
                overvalued_factor = min((ps_ratio / category_avg_ps) - 1, 10)  # Cap at 10x overvaluation
                value_factor = -overvalued_factor
            
            # Normalize to 0-100 scale
            fvs = normalize_score(value_factor, -10, 1) * 100
            
            return min(max(fvs, 0), 100)  # Ensure score is between 0 and 100
            
        except Exception as e:
            logger.error(f"Error calculating FVS for {protocol.name}: {str(e)}")
            return 0
    
    def _get_safety_score(self, protocol):
        """Get Safety Score from Certik Skynet"""
        try:
            # This could be replaced with actual API call to Certik when available
            safety_score = self.certik_client.get_security_score(protocol.name)
            
            # Normalize to 0-100 scale if needed
            if safety_score is not None:
                return min(max(safety_score, 0), 100)
            else:
                # Default to a moderate score if data is unavailable
                return 50
            
        except Exception as e:
            logger.error(f"Error getting safety score for {protocol.name}: {str(e)}")
            return 50
