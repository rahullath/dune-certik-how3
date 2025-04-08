"""
A flexible data processor for fetching and processing Dune Analytics data for crypto protocol scoring.
This module handles query execution, data standardization, and score calculation.
"""
import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta

from dune_client import DuneClient
from protocol_config import PROTOCOL_CONFIGS, CATEGORY_SETTINGS, SCORE_WEIGHTS, EQS_WEIGHTS, UGS_WEIGHTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuneProcessor:
    """
    Centralized processor for Dune Analytics data, handling multiple protocols and query types.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the DuneProcessor with an API key.
        
        Args:
            api_key: Dune Analytics API key (fallback to environment variable if None)
        """
        self.api_key = api_key or os.environ.get("DUNE_API_KEY")
        if not self.api_key:
            logger.warning("No Dune API key provided. Set DUNE_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize with our custom DuneClient
        self.client = DuneClient()
        
        # Dictionary to store protocol configurations
        self.protocol_configs = {}
        
        # Dictionary to hold cached query results
        self.query_cache = {}
        
        # Initialize from protocol_config if available
        if PROTOCOL_CONFIGS:
            for protocol, config in PROTOCOL_CONFIGS.items():
                self.register_protocol(protocol, config)
    
    def register_protocol(self, protocol_name: str, query_config: Dict[str, Any]):
        """
        Register a protocol with its query IDs and processor functions.
        
        Args:
            protocol_name: Name of the protocol (e.g., 'chainlink', 'uniswap')
            query_config: Dict containing query IDs and optional processor functions,
                as well as metadata like 'category'
                Example: {
                    'eqs': {
                        'query_id': 4953227,
                        'processor': custom_processor_func  # Optional
                    },
                    'category': 'Oracle'  # Metadata field
                }
        """
        self.protocol_configs[protocol_name] = query_config
        logger.info(f"Registered protocol: {protocol_name}")
    
    def fetch_all_protocol_data(self, protocol_name: str) -> Dict[str, pd.DataFrame]:
        """
        Fetch all registered query data for a specific protocol.
        
        Args:
            protocol_name: Name of the protocol to fetch data for
        
        Returns:
            Dictionary with query types as keys and DataFrames as values
        """
        if protocol_name not in self.protocol_configs:
            logger.error(f"Protocol '{protocol_name}' not registered")
            return {}
        
        config = self.protocol_configs[protocol_name]
        results = {}
        
        # Fetch data for each query type
        for query_type, query_info in config.items():
            # Skip non-query config items (like 'category')
            if not isinstance(query_info, dict) or 'query_id' not in query_info:
                continue
                
            query_id = query_info.get('query_id')
            if not query_id:
                logger.warning(f"No query ID for {protocol_name} {query_type}")
                results[query_type] = pd.DataFrame()
                continue
            
            try:
                # Fetch data from Dune
                logger.info(f"Fetching {query_type} data for {protocol_name} (Query ID: {query_id})")
                
                # Use cache if available
                cache_key = f"{protocol_name}_{query_type}_{query_id}"
                if cache_key in self.query_cache:
                    logger.info(f"Using cached data for {cache_key}")
                    raw_data = self.query_cache[cache_key]
                else:
                    raw_data = self.fetch_query_data(query_id)
                    self.query_cache[cache_key] = raw_data
                
                # Process the data
                processor = query_info.get('processor', lambda d, qt: self._default_processor(d, qt))
                df = processor(raw_data, query_type)
                
                # Apply specific post-processing based on query type
                if query_type == 'eqs':
                    df = self._process_eqs_data(df)
                elif query_type == 'ugs':
                    df = self._process_ugs_data(df)
                elif query_type == 'fvs':
                    df = self._process_fvs_data(df)
                
                results[query_type] = df
                logger.info(f"Processed {len(df)} rows of {query_type} data for {protocol_name}")
                
            except Exception as e:
                logger.error(f"Error fetching {query_type} data for {protocol_name}: {str(e)}")
                results[query_type] = pd.DataFrame()
        
        return results
    
    def fetch_query_data(self, query_id: int) -> Dict[str, Any]:
        """
        Fetch data for a specific query ID from Dune Analytics.
        
        Args:
            query_id: Dune Analytics query ID
        
        Returns:
            Raw query result in DataFrame format (converted to Dict for compatibility)
        """
        try:
            logger.info(f"Fetching data for query ID {query_id}")
            df_result = self.client.execute_query(query_id)
            
            if df_result is None or df_result.empty:
                logger.warning(f"No data returned for query ID {query_id}")
                return {'result': {'rows': []}}
            
            # Convert DataFrame to expected dict format
            result_dict = {
                'result': {
                    'rows': df_result.to_dict(orient='records')
                }
            }
            
            logger.info(f"Successfully fetched {len(df_result)} rows for query ID {query_id}")
            return result_dict
            
        except Exception as e:
            logger.error(f"Error fetching data for query ID {query_id}: {str(e)}")
            return {'result': {'rows': []}}
    
    def _default_processor(self, raw_data: Dict[str, Any], query_type: str) -> pd.DataFrame:
        """
        Default processor for Dune Analytics data.
        
        Args:
            raw_data: Raw data from Dune
            query_type: Type of query data (eqs, ugs, fvs)
        
        Returns:
            Processed DataFrame
        """
        if not raw_data or 'result' not in raw_data or 'rows' not in raw_data['result']:
            logger.warning(f"No data to process for {query_type}")
            return pd.DataFrame()
        
        # Create DataFrame from query result
        df = pd.DataFrame(raw_data['result']['rows'])
        
        if df.empty:
            logger.warning(f"Empty DataFrame for {query_type}")
            return df
        
        # Convert month column to datetime if present
        if 'month' in df.columns:
            df['month'] = pd.to_datetime(df['month'])
        
        # Sort by month or date column if present
        date_cols = ['month', 'date', 'day', 'timestamp', 'block_time']
        for col in date_cols:
            if col in df.columns:
                df = df.sort_values(col, ascending=False)
                break
        
        return df
    
    def _process_eqs_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process Earnings Quality Score data"""
        if df.empty:
            return df
        
        # Ensure required columns exist
        required_cols = ['month', 'total_fees', 'mom_change']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns in EQS data: {missing_cols}")
            # Try to calculate missing columns if possible
            if 'total_fees' in df.columns and 'month' in df.columns and 'mom_change' not in df.columns:
                try:
                    # Sort by month
                    df = df.sort_values('month')
                    # Calculate month-over-month change
                    df['mom_change'] = df['total_fees'].pct_change()
                except Exception as e:
                    logger.error(f"Error calculating mom_change: {str(e)}")
        
        # Calculate additional metrics if needed
        if 'mom_change' in df.columns and 'avg_mom_change' not in df.columns:
            df['avg_mom_change'] = df['mom_change'].mean()
        
        if 'mom_change' in df.columns and 'stddev_mom_change' not in df.columns:
            df['stddev_mom_change'] = df['mom_change'].std()
        
        return df
    
    def _process_ugs_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process User Growth Score data"""
        if df.empty:
            return df
        
        # Ensure required columns exist
        required_cols = ['month', 'active_addresses', 'transaction_count', 'transaction_volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns in UGS data: {missing_cols}")
            # We can't easily derive these metrics, so we'll have to work with what we have
        
        # Calculate growth rates if not present
        growth_rate_cols = [
            'active_address_growth_rate', 
            'transaction_count_growth_rate', 
            'transaction_volume_growth_rate'
        ]
        
        missing_growth_cols = [col for col in growth_rate_cols if col not in df.columns]
        
        if missing_growth_cols and 'month' in df.columns:
            try:
                # Sort by month
                df = df.sort_values('month')
                
                # Calculate growth rates
                if 'active_addresses' in df.columns and 'active_address_growth_rate' not in df.columns:
                    df['active_address_growth_rate'] = df['active_addresses'].pct_change() * 100
                
                if 'transaction_count' in df.columns and 'transaction_count_growth_rate' not in df.columns:
                    df['transaction_count_growth_rate'] = df['transaction_count'].pct_change() * 100
                
                if 'transaction_volume' in df.columns and 'transaction_volume_growth_rate' not in df.columns:
                    df['transaction_volume_growth_rate'] = df['transaction_volume'].pct_change() * 100
            except Exception as e:
                logger.error(f"Error calculating growth rates: {str(e)}")
        
        # Calculate percentiles if not present
        percentile_cols = [
            'active_address_percentile',
            'transaction_count_percentile',
            'transaction_volume_percentile'
        ]
        
        missing_percentile_cols = [col for col in percentile_cols if col not in df.columns]
        
        if missing_percentile_cols:
            try:
                if 'active_addresses' in df.columns and 'active_address_percentile' not in df.columns:
                    df['active_address_percentile'] = df['active_addresses'].rank(pct=True)
                
                if 'transaction_count' in df.columns and 'transaction_count_percentile' not in df.columns:
                    df['transaction_count_percentile'] = df['transaction_count'].rank(pct=True)
                
                if 'transaction_volume' in df.columns and 'transaction_volume_percentile' not in df.columns:
                    df['transaction_volume_percentile'] = df['transaction_volume'].rank(pct=True)
            except Exception as e:
                logger.error(f"Error calculating percentiles: {str(e)}")
        
        return df
    
    def _process_fvs_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process Fair Value Score data"""
        if df.empty:
            return df
        
        # Ensure required columns exist
        required_cols = ['month', 'market_cap', 'annual_revenue']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns in FVS data: {missing_cols}")
        
        # Calculate P/S ratio if not present
        if 'market_cap' in df.columns and 'annual_revenue' in df.columns and 'ps_ratio' not in df.columns:
            try:
                df['ps_ratio'] = df.apply(
                    lambda row: row['market_cap'] / row['annual_revenue'] if row['annual_revenue'] > 0 else None,
                    axis=1
                )
            except Exception as e:
                logger.error(f"Error calculating P/S ratio: {str(e)}")
        
        return df
    
    def calculate_scores(self, protocol_name: str, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Calculate scores for a protocol based on fetched data.
        
        Args:
            protocol_name: Name of the protocol
            data: Dictionary with query types as keys and DataFrames as values
        
        Returns:
            Dictionary with score types and values
        """
        scores = {}
        
        # Calculate EQS if data available
        if 'eqs' in data and not data['eqs'].empty:
            scores['eqs'] = self._calculate_eqs(data['eqs'])
        else:
            logger.warning(f"No EQS data available for {protocol_name}")
            scores['eqs'] = None
        
        # Calculate UGS if data available
        if 'ugs' in data and not data['ugs'].empty:
            scores['ugs'] = self._calculate_ugs(data['ugs'])
        else:
            logger.warning(f"No UGS data available for {protocol_name}")
            scores['ugs'] = None
        
        # Calculate FVS if data available
        if 'fvs' in data and not data['fvs'].empty:
            scores['fvs'] = self._calculate_fvs(data['fvs'])
        elif 'eqs' in data and not data['eqs'].empty:
            # Try to estimate FVS from EQS data if we have it
            protocol_config = self.protocol_configs.get(protocol_name, {})
            category = protocol_config.get('category')
            
            if category and category in CATEGORY_SETTINGS:
                logger.info(f"Estimating FVS for {protocol_name} based on EQS data and category settings")
                scores['fvs'] = self._estimate_fvs_from_eqs(data['eqs'], category)
            else:
                logger.warning(f"No FVS data or category settings available for {protocol_name}")
                scores['fvs'] = None
        else:
            logger.warning(f"No FVS or EQS data available for {protocol_name}")
            scores['fvs'] = None
        
        # Calculate SS from security data (or use a default placeholder)
        scores['ss'] = self._calculate_default_ss(protocol_name)
        
        # Calculate combined score
        valid_scores = {k: v for k, v in scores.items() if v is not None}
        
        if valid_scores:
            # Use configured weights for available scores
            weighted_scores = []
            total_weight = 0
            
            for score_type, weight in SCORE_WEIGHTS.items():
                if score_type in valid_scores:
                    weighted_scores.append(valid_scores[score_type] * weight)
                    total_weight += weight
            
            if total_weight > 0:
                # Normalize by the total weight of available scores
                combined_score = sum(weighted_scores) / total_weight
            else:
                combined_score = None
            
            scores['combined'] = combined_score
        else:
            scores['combined'] = None
        
        return scores
    
    def _calculate_eqs(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate Earnings Quality Score from revenue data.
        
        Args:
            df: DataFrame with revenue data
        
        Returns:
            EQS score (0-100)
        """
        try:
            # Import the improved EQS calculator
            from improved_eqs_calculator import EnhancedEQSCalculator, integrate_with_dune_processor
            
            # Check if we have necessary data
            if df.empty or 'mom_change' not in df.columns:
                logger.warning("Insufficient data for EQS calculation")
                return None
                
            # Use our enhanced calculator through the integration function
            # Try to get protocol name from registered protocols or use a default
            current_protocol = next(iter(self.protocols.keys()), 'current_protocol') if hasattr(self, 'protocols') else 'current_protocol'
            data = {'eqs': df}
            eqs_score = integrate_with_dune_processor(self, current_protocol, data)
            
            if eqs_score is not None:
                logger.info(f"Using improved EQS calculator: score = {eqs_score:.2f}")
                return eqs_score
                
            # If integration function failed, fall back to direct calculator
            logger.warning("Integration function failed, trying direct calculator")
            calculator = EnhancedEQSCalculator()
            eqs_score = calculator.calculate_eqs(df, current_protocol)
            
            if eqs_score is not None:
                logger.info(f"Using direct EQS calculator: score = {eqs_score:.2f}")
                return eqs_score
                
            # Fall back to basic calculation if enhanced calculator fails
            logger.warning("Enhanced EQS calculator failed, using fallback method")
            
            # Calculate stability score based on revenue trend volatility
            stability_score = 0
            if 'mom_change' in df.columns:
                # Filter out NaN values and take absolute values
                mom_changes = df['mom_change'].dropna().abs()
                
                if not mom_changes.empty:
                    # Calculate average volatility
                    avg_trend = mom_changes.mean()
                    
                    # Using the formula: stability_score = max(0, 100 - (avg_trend * 100))
                    stability_score = max(0, 100 - (avg_trend * 100))
            
            # Calculate magnitude score
            magnitude_score = 0
            if 'total_fees' in df.columns:
                # Get most recent month
                recent_month = df['month'].max()
                recent_data = df[df['month'] == recent_month]
                total_revenue = recent_data['total_fees'].sum()
                
                # Use a reference value for "large revenue"
                reference_revenue = 5000000  # $5M monthly revenue as reference
                
                # Log scale for better distribution
                if total_revenue > 0:
                    magnitude_score = min(100, 100 * np.log(total_revenue + 1) / np.log(reference_revenue + 1))
            
            # Calculate diversification score if possible
            diversification_score = None
            sources = df['source'].unique() if 'source' in df.columns else []
            
            if len(sources) > 1:
                # Get recent month's data
                recent_month = df['month'].max()
                recent_data = df[df['month'] == recent_month]
                
                # Get revenue by source
                revenue_by_source = recent_data.groupby('source')['total_fees'].sum()
                
                # Calculate standard deviation and mean for diversification
                diversification_std = revenue_by_source.std()
                diversification_mean = revenue_by_source.mean()
                
                if diversification_mean > 0:
                    # Higher coefficient of variation indicates more diversification
                    cv = diversification_std / diversification_mean
                    diversification_score = min(100, 50 * cv)
            
            # Combine scores using weights
            if diversification_score is not None:
                # When both stability and diversification exist: 0.7 * stability_score + 0.3 * diversification_score
                quality_score = 0.7 * stability_score + 0.3 * diversification_score
            else:
                quality_score = stability_score
            
            # Apply magnitude adjustment - (stability_score * magnitude_score) / 100
            eqs_score = (quality_score * magnitude_score) / 100
            
            return round(eqs_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating EQS: {str(e)}")
            return None
    
    def _calculate_ugs(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate User Growth Score from user metrics data.
        
        Args:
            df: DataFrame with user metrics data
        
        Returns:
            UGS score (0-100)
        """
        try:
            # Check if we have necessary data
            required_cols = ['active_addresses', 'transaction_count', 'transaction_volume']
            if df.empty or not any(col in df.columns for col in required_cols):
                logger.warning("Insufficient data for UGS calculation")
                return None
            
            # Get most recent month's data
            recent_data = df.sort_values('month', ascending=False).iloc[0]
            
            scores = {}
            
            # Calculate active addresses score
            if 'active_addresses' in df.columns and 'active_address_percentile' in df.columns:
                scores['active_addresses'] = recent_data['active_address_percentile'] * 100
            elif 'active_addresses' in df.columns:
                # Estimate score based on absolute value (logarithmic scale)
                # 100 users -> ~25 points
                # 1,000 users -> ~50 points
                # 10,000 users -> ~75 points
                # 100,000+ users -> 100 points
                active_addresses = recent_data['active_addresses']
                if active_addresses > 0:
                    scores['active_addresses'] = min(100, max(0, 25 * np.log10(active_addresses)))
                else:
                    scores['active_addresses'] = 0
            
            # Calculate transaction count score
            if 'transaction_count' in df.columns and 'transaction_count_percentile' in df.columns:
                scores['transaction_count'] = recent_data['transaction_count_percentile'] * 100
            elif 'transaction_count' in df.columns:
                # Estimate score based on absolute value (logarithmic scale)
                tx_count = recent_data['transaction_count']
                if tx_count > 0:
                    scores['transaction_count'] = min(100, max(0, 25 * np.log10(tx_count)))
                else:
                    scores['transaction_count'] = 0
            
            # Calculate transaction volume score
            if 'transaction_volume' in df.columns and 'transaction_volume_percentile' in df.columns:
                scores['transaction_volume'] = recent_data['transaction_volume_percentile'] * 100
            elif 'transaction_volume' in df.columns:
                # Estimate score based on absolute value (logarithmic scale)
                # $10k volume -> ~25 points
                # $100k volume -> ~50 points
                # $1M volume -> ~75 points
                # $10M+ volume -> 100 points
                tx_volume = recent_data['transaction_volume']
                if tx_volume > 0:
                    scores['transaction_volume'] = min(100, max(0, 25 * (np.log10(tx_volume) - 3)))
                else:
                    scores['transaction_volume'] = 0
            
            # Combine scores using weights from config
            total_score = 0
            total_weight = 0
            
            for metric, weight in UGS_WEIGHTS.items():
                if metric in scores:
                    total_score += scores[metric] * weight
                    total_weight += weight
            
            if total_weight > 0:
                ugs_score = total_score / total_weight
                return round(ugs_score, 2)
            else:
                logger.warning("No metrics available for UGS calculation")
                return None
            
        except Exception as e:
            logger.error(f"Error calculating UGS: {str(e)}")
            return None
    
    def _calculate_fvs(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate Fair Value Score from market/revenue data.
        
        Args:
            df: DataFrame with market and revenue metrics
        
        Returns:
            FVS score (0-100)
        """
        try:
            # Check if we have necessary data
            if df.empty or 'ps_ratio' not in df.columns:
                logger.warning("Insufficient data for FVS calculation")
                return None
            
            # Get most recent data
            recent_data = df.iloc[0]
            ps_ratio = recent_data['ps_ratio']
            
            if pd.isna(ps_ratio) or ps_ratio <= 0:
                logger.warning("Invalid P/S ratio for FVS calculation")
                return None
            
            # Calculate FVS based on P/S ratio
            # Lower P/S ratio is generally better (more revenue relative to market cap)
            # We'll use a logarithmic scale to avoid extreme scores
            
            # Typical P/S ratios for crypto protocols range from 1 to 100+
            # P/S ratio of 5 -> ~80 points (excellent value)
            # P/S ratio of 20 -> ~60 points (good value)
            # P/S ratio of 50 -> ~40 points (fair value)
            # P/S ratio of 100 -> ~20 points (overvalued)
            
            # Normalize score (0-100, higher is better value)
            if ps_ratio < 1:
                fvs_score = 100  # Extremely undervalued
            else:
                # Logarithmic scale
                log_ps = np.log10(ps_ratio)
                normalized_score = max(0, 100 - (log_ps * 40))
                fvs_score = normalized_score
            
            return round(fvs_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating FVS: {str(e)}")
            return None
    
    def _estimate_fvs_from_eqs(self, eqs_df: pd.DataFrame, category: str) -> Optional[float]:
        """
        Estimate Fair Value Score based on EQS data and category averages.
        
        Args:
            eqs_df: DataFrame with revenue data
            category: Protocol category (DEX, Lending, etc.)
        
        Returns:
            Estimated FVS score (0-100)
        """
        try:
            # Get category settings
            avg_revenue_multiple = CATEGORY_SETTINGS.get(category, {}).get('avg_revenue_multiple', 30)
            
            # Calculate annual revenue
            if eqs_df.empty or 'total_fees' not in eqs_df.columns:
                logger.warning("Insufficient revenue data for FVS estimation")
                return None
            
            # Get most recent 12 months if available
            recent_df = eqs_df.sort_values('month', ascending=False).head(12)
            annual_revenue = recent_df['total_fees'].sum()
            
            if annual_revenue <= 0:
                logger.warning("Zero or negative annual revenue for FVS estimation")
                return None
            
            # Estimate market cap based on category average multiple
            estimated_market_cap = annual_revenue * avg_revenue_multiple
            
            # Calculate PS ratio
            ps_ratio = avg_revenue_multiple  # By definition
            
            # Calculate FVS score (same logic as _calculate_fvs)
            if ps_ratio < 1:
                fvs_score = 100  # Extremely undervalued
            else:
                # Logarithmic scale
                log_ps = np.log10(ps_ratio)
                normalized_score = max(0, 100 - (log_ps * 40))
                fvs_score = normalized_score
            
            return round(fvs_score, 2)
            
        except Exception as e:
            logger.error(f"Error estimating FVS from EQS: {str(e)}")
            return None
    
    def _calculate_ss(self, df: pd.DataFrame) -> Optional[float]:
        """
        Calculate Safety Score from security data.
        
        Args:
            df: DataFrame with security metrics
        
        Returns:
            Safety Score (0-100)
        """
        try:
            # Implementation depends on security data structure
            # Since we don't have an actual Certik security query yet,
            # we'll use placeholder logic
            if df.empty:
                logger.warning("No security data available for SS calculation")
                return None
            
            # Placeholder calculation based on security metrics
            # This should be replaced with actual calculation based on real security data
            security_score = df['security_score'].mean() if 'security_score' in df.columns else 50
            
            return round(security_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating SS: {str(e)}")
            return None
    
    def _calculate_default_ss(self, protocol_name: str) -> float:
        """Generate a default safety score for a protocol"""
        # This is a placeholder - in production, we should use real security data
        # For now, we'll use a simple deterministic value based on protocol name
        # This ensures consistent scoring for testing purposes
        
        # Generate a hash of the protocol name
        name_hash = sum(ord(c) for c in protocol_name)
        
        # Create a score between 50 and 90
        default_score = 50 + (name_hash % 41)
        
        logger.warning(f"Using default Safety Score for {protocol_name}: {default_score}")
        return default_score
    
    def export_scores_to_csv(self, scores_dict: Dict[str, Dict[str, float]], filepath: str = 'protocol_scores.csv'):
        """
        Export calculated scores to a CSV file.
        
        Args:
            scores_dict: Dictionary with protocol names as keys and score dictionaries as values
            filepath: Path to output CSV file
        """
        try:
            # Create list of dictionaries for DataFrame
            rows = []
            for protocol, scores in scores_dict.items():
                # Create a new dictionary with protocol name and all scores
                row = {'protocol': protocol}
                # Safely copy values from scores dict to row
                for k, v in scores.items():
                    if v is not None:
                        row[k] = v
                    else:
                        row[k] = None
                rows.append(row)
            
            # Convert to DataFrame and export
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported scores to {filepath}")
            
            return True
        except Exception as e:
            logger.error(f"Error exporting scores: {str(e)}")
            return False


if __name__ == "__main__":
    # Example usage
    api_key = os.environ.get("DUNE_API_KEY")
    processor = DuneProcessor(api_key)
    
    # Register a protocol with query IDs
    processor.register_protocol('chainlink', {
        'eqs': {'query_id': 4953227},
        'ugs': {'query_id': 4953009},
        'category': 'Oracle'
    })
    
    # Fetch data for the protocol
    data = processor.fetch_all_protocol_data('chainlink')
    
    # Calculate scores
    scores = processor.calculate_scores('chainlink', data)
    
    print(f"Chainlink scores: {scores}")