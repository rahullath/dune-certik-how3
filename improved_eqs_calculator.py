"""
Enhanced Earnings Quality Score (EQS) calculator for crypto protocols.
This module uses Dune Analytics data to calculate EQS based on revenue stability and diversification.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class EnhancedEQSCalculator:
    """
    Enhanced Earnings Quality Score calculator that works with Dune Analytics data.
    Calculates revenue stability, diversification, and magnitude scores.
    """
    
    def __init__(self):
        # Define weights for scoring components
        self.stability_weight = 0.7  # 70% weight for stability
        self.diversification_weight = 0.3  # 30% weight for diversification
        self.log_base = 10  # Base for logarithmic scaling in magnitude calculation
        
    def calculate_eqs(self, df: pd.DataFrame, protocol_name: str) -> Optional[float]:
        """
        Calculate the Earnings Quality Score for a protocol based on revenue data.
        
        Args:
            df: DataFrame with revenue data from Dune Analytics
            protocol_name: Name of the protocol
            
        Returns:
            EQS score (0-100) or None if insufficient data
        """
        if df.empty:
            logger.warning(f"No revenue data available for {protocol_name}")
            return None
            
        try:
            # Ensure we have required columns for the data format seen in the Dune sample
            # Format from Dune sample: month, source, total_fees, mom_change, avg_mom_change, stddev_mom_change, num_months
            expected_columns = ['month', 'source', 'total_fees', 'mom_change']
            missing_columns = [col for col in expected_columns if col not in df.columns]
            
            if missing_columns:
                logger.warning(f"Missing required columns for {protocol_name}: {missing_columns}. Available: {df.columns.tolist()}")
                return None
                
            # Calculate stability score based on revenue trend volatility
            stability_score = self._calculate_stability_score(df)
            logger.info(f"{protocol_name} stability score: {stability_score:.2f}")
            
            # Calculate diversification score based on revenue distribution across sources
            diversification_score = self._calculate_diversification_score(df)
            logger.info(f"{protocol_name} diversification score: {diversification_score:.2f}")
            
            # Calculate magnitude score for weighting
            magnitude_score = self._calculate_magnitude_score(df)
            logger.info(f"{protocol_name} magnitude score: {magnitude_score:.2f}")
            
            # Combine scores using weights
            # First combine stability and diversification with their weights
            if pd.notna(stability_score) and pd.notna(diversification_score):
                quality_score = (self.stability_weight * stability_score) + (self.diversification_weight * diversification_score)
            elif pd.notna(stability_score):
                quality_score = stability_score  # Only stability data available
            elif pd.notna(diversification_score):
                quality_score = diversification_score  # Only diversification data available
            else:
                logger.warning(f"Insufficient data to calculate EQS for {protocol_name}")
                return None
                
            # Apply magnitude adjustment - this scales the quality score based on revenue magnitude
            # Using the formula from your description: (stability_score * magnitude_score) / 100
            adjusted_score = (quality_score * magnitude_score) / 100
            
            logger.info(f"Calculated EQS for {protocol_name}: {adjusted_score:.2f}")
            return round(adjusted_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating EQS for {protocol_name}: {str(e)}")
            return None
            
    def _calculate_stability_score(self, df: pd.DataFrame) -> float:
        """
        Calculate stability score (0-100) based on mom_change volatility.
        
        Args:
            df: DataFrame with revenue data
            
        Returns:
            Stability score (0-100)
        """
        # Filter out rows with null month-over-month changes
        valid_data = df[pd.notna(df['mom_change'])]
        
        if valid_data.empty:
            logger.warning("No valid month-over-month change data for stability calculation")
            return 50.0  # Default neutral score
            
        # Use absolute values of mom_change to measure volatility
        # Larger absolute changes indicate higher volatility
        mom_change_abs = valid_data['mom_change'].abs()
        
        # Calculate average month-over-month volatility
        avg_trend = mom_change_abs.mean()
        
        # Using the formula: stability_score = max(0, 100 - (avg_trend * 100))
        # Lower volatility (lower avg_trend) gives higher stability score
        stability_score = max(0, 100 - (avg_trend * 100))
        
        # Cap at 100 in case volatility is extremely low
        return min(100, stability_score)
        
    def _calculate_magnitude_score(self, df: pd.DataFrame) -> float:
        """
        Calculate magnitude score (0-100) based on total revenue.
        Used for weighting the overall score.
        
        Args:
            df: DataFrame with revenue data
            
        Returns:
            Magnitude score (0-100)
        """
        # Get the most recent month
        latest_month = df['month'].max()
        recent_data = df[df['month'] == latest_month]
        
        # Sum total revenue across all sources for the most recent month
        total_revenue = recent_data['total_fees'].sum()
        
        if total_revenue <= 0:
            return 10.0  # Minimum score instead of zero
            
        # Use a reference value for "large revenue" based on industry standards
        # This could be adjusted based on protocol category
        reference_revenue = 5000000  # $5M monthly revenue as a reference point
        
        # Using logarithmic scaling: magnitude_score = 100 * log(revenue_sum + 1) / log(max_revenue_sum + 1)
        magnitude_score = 100 * np.log(total_revenue + 1) / np.log(reference_revenue + 1)
        
        # Ensure score is within 0-100 range
        return min(100, max(0, magnitude_score))
        
    def _calculate_diversification_score(self, df: pd.DataFrame) -> float:
        """
        Calculate diversification score (0-100) based on distribution of revenue sources.
        
        Args:
            df: DataFrame with revenue data
            
        Returns:
            Diversification score (0-100)
        """
        # Get the most recent month
        latest_month = df['month'].max()
        recent_data = df[df['month'] == latest_month]
        
        # Count number of revenue sources
        sources = recent_data['source'].unique()
        
        if len(sources) <= 1:
            logger.warning("Insufficient source diversity for diversification calculation")
            return 0.0  # Minimum diversification
            
        # Get revenue by source
        revenue_by_source = recent_data.groupby('source')['total_fees'].sum()
        
        # Calculate standard deviation and mean for diversification
        diversification_std = revenue_by_source.std()
        diversification_mean = revenue_by_source.mean()
        
        if diversification_mean <= 0:
            return 0.0  # Avoid division by zero
            
        # Using the formula: diversification_score = 100 * (diversification_std / diversification_mean)
        # Higher coefficient of variation indicates more diversification
        cv = diversification_std / diversification_mean
        
        # Normalize to a 0-100 score
        # Typical CV values are in 0-1.5 range for crypto protocols, but can go higher
        # We're using a scaling factor based on observed data
        diversification_score = min(100, 50 * cv)
        
        return diversification_score


def integrate_with_dune_processor(processor, protocol_name: str, data: Dict[str, pd.DataFrame]) -> Optional[float]:
    """
    Integration function to calculate EQS from Dune processor data.
    
    Args:
        processor: DuneProcessor instance
        protocol_name: Name of the protocol
        data: Dictionary with query types as keys and DataFrames as values
        
    Returns:
        EQS score (0-100) or None if insufficient data
    """
    if 'eqs' not in data or data['eqs'].empty:
        logger.warning(f"No EQS data available for {protocol_name}")
        return None
        
    try:
        calculator = EnhancedEQSCalculator()
        eqs_score = calculator.calculate_eqs(data['eqs'], protocol_name)
        
        # Log detailed information about the calculation
        if eqs_score is not None:
            logger.info(f"Successfully calculated EQS for {protocol_name}: {eqs_score:.2f}")
            
            # Save detailed component scores for reference
            # This could be expanded to store these in the database
            stability_score = calculator._calculate_stability_score(data['eqs'])
            diversification_score = calculator._calculate_diversification_score(data['eqs'])
            magnitude_score = calculator._calculate_magnitude_score(data['eqs'])
            
            logger.info(f"{protocol_name} component scores - "
                       f"Stability: {stability_score:.2f}, "
                       f"Diversification: {diversification_score:.2f}, "
                       f"Magnitude: {magnitude_score:.2f}")
        
        return eqs_score
        
    except Exception as e:
        logger.error(f"Error in EQS calculation for {protocol_name}: {str(e)}")
        return None


# Constants for EQS components
EQS_WEIGHTS = {
    "stability": 0.7,  # 70% weight for stability
    "diversification": 0.3,  # 30% weight for diversification
}