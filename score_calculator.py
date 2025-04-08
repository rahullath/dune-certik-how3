import logging
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from config import (
    STABILITY_WEIGHT, MAGNITUDE_WEIGHT, USER_WEIGHTS, 
    SCORE_RANGES, FVS_PS_RATIO_THRESHOLDS
)

logger = logging.getLogger(__name__)

class ScoreCalculator:
    """Calculator for protocol quality scores."""
    
    @staticmethod
    def calculate_eqs(revenue_data: List[Dict[str, Any]], category: str) -> float:
        """Calculate Earnings Quality Score.
        
        Args:
            revenue_data: List of monthly revenue data
            category: Protocol category for comparative analysis
            
        Returns:
            Earnings Quality Score (0-100)
        """
        if not revenue_data:
            logger.warning("No revenue data available for EQS calculation")
            return 0
        
        try:
            # Calculate stability component
            mom_changes = [float(data.get('mom_change', 0)) for data in revenue_data if data.get('mom_change') is not None]
            if not mom_changes:
                stability_score = 0
            else:
                # Lower volatility is better - inverse of standard deviation normalized
                volatility = np.std(mom_changes) if len(mom_changes) > 1 else 1
                # Cap volatility to avoid extreme values
                capped_volatility = min(volatility, 1.0)
                stability_score = (1 - capped_volatility) * 100
            
            # Calculate magnitude component
            total_fees = [float(data.get('total_fees', 0)) for data in revenue_data]
            if not total_fees:
                magnitude_score = 0
            else:
                avg_monthly_revenue = sum(total_fees) / len(total_fees)
                # Logarithmic scaling for revenue magnitude (adjustable based on category)
                # This assumes higher revenue is better, scaled logarithmically
                if avg_monthly_revenue <= 0:
                    magnitude_score = 0
                else:
                    # Scale based on category benchmarks
                    category_scaling = ScoreCalculator._get_category_revenue_scaling(category)
                    log_revenue = np.log10(max(1, avg_monthly_revenue))
                    magnitude_score = min(100, (log_revenue / category_scaling) * 100)
            
            # Combined score
            eqs = (STABILITY_WEIGHT * stability_score) + (MAGNITUDE_WEIGHT * magnitude_score)
            
            # Ensure score is within range
            return max(SCORE_RANGES['eqs'][0], min(SCORE_RANGES['eqs'][1], eqs))
        
        except Exception as e:
            logger.error(f"Error calculating EQS: {e}")
            return 0
    
    @staticmethod
    def calculate_ugs(user_data: List[Dict[str, Any]]) -> float:
        """Calculate User Growth Score.
        
        Args:
            user_data: List of monthly user metrics data
            
        Returns:
            User Growth Score (0-100)
        """
        if not user_data:
            logger.warning("No user data available for UGS calculation")
            return 0
        
        try:
            # Calculate scores for each component
            address_scores = []
            tx_count_scores = []
            tx_volume_scores = []
            
            for data in user_data:
                # Active addresses component
                if data.get('active_address_percentile') is not None:
                    address_score = float(data.get('active_address_percentile', 0)) * 100
                    address_scores.append(address_score)
                
                # Transaction count component
                if data.get('transaction_count_percentile') is not None:
                    tx_count_score = float(data.get('transaction_count_percentile', 0)) * 100
                    tx_count_scores.append(tx_count_score)
                
                # Transaction volume component
                if data.get('transaction_volume_percentile') is not None:
                    tx_volume_score = float(data.get('transaction_volume_percentile', 0)) * 100
                    tx_volume_scores.append(tx_volume_score)
            
            # Average the scores for each component
            avg_address_score = sum(address_scores) / len(address_scores) if address_scores else 0
            avg_tx_count_score = sum(tx_count_scores) / len(tx_count_scores) if tx_count_scores else 0
            avg_tx_volume_score = sum(tx_volume_scores) / len(tx_volume_scores) if tx_volume_scores else 0
            
            # Calculate growth rates
            growth_rates = {
                'active_addresses': [float(data.get('active_address_growth_rate', 0)) 
                                  for data in user_data if data.get('active_address_growth_rate') is not None],
                'transaction_count': [float(data.get('transaction_count_growth_rate', 0)) 
                                   for data in user_data if data.get('transaction_count_growth_rate') is not None],
                'transaction_volume': [float(data.get('transaction_volume_growth_rate', 0)) 
                                    for data in user_data if data.get('transaction_volume_growth_rate') is not None]
            }
            
            growth_scores = {}
            for metric, rates in growth_rates.items():
                if not rates:
                    growth_scores[metric] = 0
                else:
                    # Positive consistent growth is ideal
                    avg_growth = sum(rates) / len(rates)
                    # Normalize growth rate (cap at reasonable values)
                    normalized_growth = min(100, max(-100, avg_growth))
                    # Convert to 0-100 scale (50 is neutral, >50 is positive growth, <50 is negative)
                    growth_scores[metric] = 50 + (normalized_growth / 2)
            
            # Combine percentile scores and growth scores
            component_scores = {
                'active_addresses': (avg_address_score + growth_scores.get('active_addresses', 0)) / 2,
                'transaction_count': (avg_tx_count_score + growth_scores.get('transaction_count', 0)) / 2,
                'transaction_volume': (avg_tx_volume_score + growth_scores.get('transaction_volume', 0)) / 2
            }
            
            # Weighted average of component scores
            ugs = sum(score * USER_WEIGHTS[metric] for metric, score in component_scores.items())
            
            # Ensure score is within range
            return max(SCORE_RANGES['ugs'][0], min(SCORE_RANGES['ugs'][1], ugs))
        
        except Exception as e:
            logger.error(f"Error calculating UGS: {e}")
            return 0
    
    @staticmethod
    def calculate_fvs(market_cap: int, annual_revenue: int, category: str) -> float:
        """Calculate Fair Value Score.
        
        Args:
            market_cap: Current market capitalization
            annual_revenue: Annual revenue in USD
            category: Protocol category for benchmark comparison
            
        Returns:
            Fair Value Score (0-100)
        """
        try:
            if market_cap <= 0 or annual_revenue <= 0:
                logger.warning("Invalid market cap or revenue for FVS calculation")
                return 50  # Neutral score when data is missing
            
            # Calculate Price-to-Sales ratio (P/S)
            ps_ratio = market_cap / annual_revenue
            
            # Get category-specific thresholds
            thresholds = FVS_PS_RATIO_THRESHOLDS.get(category, FVS_PS_RATIO_THRESHOLDS['default'])
            undervalued_threshold = thresholds['undervalued']
            overvalued_threshold = thresholds['overvalued']
            
            # Calculate score based on P/S ratio
            if ps_ratio <= undervalued_threshold:
                # Undervalued - higher score
                fvs = 100
            elif ps_ratio >= overvalued_threshold:
                # Overvalued - lower score
                fvs = 0
            else:
                # Linear interpolation between thresholds
                fvs = 100 - ((ps_ratio - undervalued_threshold) / (overvalued_threshold - undervalued_threshold) * 100)
            
            return max(SCORE_RANGES['fvs'][0], min(SCORE_RANGES['fvs'][1], fvs))
        
        except Exception as e:
            logger.error(f"Error calculating FVS: {e}")
            return 50  # Neutral score on error
    
    @staticmethod
    def calculate_how3_score(eqs: float, ugs: float, fvs: float, ss: float) -> float:
        """Calculate combined How3 score.
        
        Args:
            eqs: Earnings Quality Score
            ugs: User Growth Score
            fvs: Fair Value Score
            ss: Safety Score
            
        Returns:
            Combined How3 Score (0-100)
        """
        try:
            # Simple average of all scores
            how3_score = (eqs + ugs + fvs + ss) / 4
            
            return round(how3_score, 1)
        
        except Exception as e:
            logger.error(f"Error calculating How3 score: {e}")
            return 0
    
    @staticmethod
    def _get_category_revenue_scaling(category: str) -> float:
        """Get the revenue scaling factor for a specific category.
        
        Args:
            category: Protocol category
            
        Returns:
            Scaling factor for revenue magnitude calculation
        """
        # Different categories have different expected revenue ranges
        # These values should be calibrated based on actual data
        category_scales = {
            'DeFi': 9,         # Expect up to $1B annual revenue
            'Layer 1': 10,     # Expect up to $10B annual revenue
            'Layer 2': 8,      # Expect up to $100M annual revenue
            'Oracle': 8,       # Expect up to $100M annual revenue
            'Infrastructure': 8,
            'Gaming': 7,
            'NFT': 7,
            'DAO': 7,
            'Privacy': 7,
            'Storage': 7,
            'Analytics': 7,
            'Exchange': 9,
            'default': 8       # Default scaling
        }
        
        return category_scales.get(category, category_scales['default'])
