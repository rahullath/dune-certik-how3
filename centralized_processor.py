"""
Centralized Protocol Processor

This module provides a unified approach to processing protocol data and calculating scores,
with protocol-specific customizations applied from a central configuration.
"""

import json
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from improved_eqs_calculator import EnhancedEQSCalculator

logger = logging.getLogger(__name__)

class CentralizedProcessor:
    """
    Centralized processor for protocol data that applies protocol-specific adjustments
    based on a configuration file.
    """
    
    def __init__(self, config_path="protocol_config.json"):
        """Initialize with the path to the configuration file."""
        self.load_config(config_path)
        self.eqs_calculator = EnhancedEQSCalculator()
        
    def load_config(self, config_path):
        """Load the protocol configuration from a JSON file."""
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration with {len(self.config['protocols'])} protocols")
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.config = {"protocols": {}, "default_settings": {}}
    
    def get_protocol_config(self, protocol_name):
        """Get configuration for a specific protocol, with defaults applied."""
        protocol_config = self.config['protocols'].get(protocol_name, {})
        return protocol_config
    
    def apply_revenue_adjustments(self, df, protocol_name):
        """Apply protocol-specific revenue mapping adjustments."""
        protocol_config = self.get_protocol_config(protocol_name)
        eqs_adjustments = protocol_config.get('queries', {}).get('eqs', {}).get('adjustments', {})
        revenue_mapping = eqs_adjustments.get('revenue_mapping', {})
        
        if not revenue_mapping:
            return df
        
        # Create a copy to avoid modifying the original
        adjusted_df = df.copy()
        
        # Apply mappings
        for source_from, source_to in revenue_mapping.items():
            if source_from in adjusted_df['source'].values and source_to in adjusted_df['source'].values:
                # For each month, add the source_from revenue to source_to
                for month in adjusted_df['month'].unique():
                    month_mask = adjusted_df['month'] == month
                    from_mask = (month_mask) & (adjusted_df['source'] == source_from)
                    to_mask = (month_mask) & (adjusted_df['source'] == source_to)
                    
                    if from_mask.any() and to_mask.any():
                        # Add the revenue from source_from to source_to
                        from_revenue = adjusted_df.loc[from_mask, 'total_fees'].values[0]
                        adjusted_df.loc[to_mask, 'total_fees'] += from_revenue
                        
                        # Set source_from revenue to zero (or optionally remove it)
                        adjusted_df.loc[from_mask, 'total_fees'] = 0
        
        return adjusted_df
    
    def calculate_eqs(self, df, protocol_name):
        """
        Calculate EQS for a protocol using its specific configuration.
        
        Args:
            df: DataFrame with revenue data
            protocol_name: Name of the protocol
            
        Returns:
            EQS score (0-100) or None if insufficient data
        """
        if df.empty:
            logger.warning(f"No data provided for {protocol_name} EQS calculation")
            return None
        
        try:
            # Apply protocol-specific revenue adjustments
            adjusted_df = self.apply_revenue_adjustments(df, protocol_name)
            
            # Get protocol-specific weights
            protocol_config = self.get_protocol_config(protocol_name)
            eqs_adjustments = protocol_config.get('queries', {}).get('eqs', {}).get('adjustments', {})
            
            # Update calculator with protocol-specific settings
            weights = eqs_adjustments.get('weights', {})
            if 'stability' in weights:
                self.eqs_calculator.stability_weight = weights['stability']
            if 'diversification' in weights:
                self.eqs_calculator.diversification_weight = weights['diversification']
            
            # Calculate EQS
            eqs_score = self.eqs_calculator.calculate_eqs(adjusted_df, protocol_name)
            
            return eqs_score
            
        except Exception as e:
            logger.error(f"Error calculating EQS for {protocol_name}: {str(e)}")
            return None
    
    def generate_protocol_report(self, df, protocol_name):
        """
        Generate a comprehensive report for a protocol based on its data.
        
        Args:
            df: DataFrame with protocol data
            protocol_name: Name of the protocol
            
        Returns:
            Dict with report information
        """
        try:
            protocol_config = self.get_protocol_config(protocol_name)
            category = protocol_config.get('category', 'Unknown')
            
            # Generate EQS report
            eqs_score = self.calculate_eqs(df, protocol_name)
            
            # Calculate component scores
            stability_score = self.eqs_calculator._calculate_stability_score(df)
            diversification_score = self.eqs_calculator._calculate_diversification_score(df)
            magnitude_score = self.eqs_calculator._calculate_magnitude_score(df)
            
            # Get revenue breakdown by source
            revenue_by_source = {}
            if 'source' in df.columns and 'total_fees' in df.columns:
                recent_month = df['month'].max()
                recent_data = df[df['month'] == recent_month]
                
                for source in recent_data['source'].unique():
                    source_total = recent_data[recent_data['source'] == source]['total_fees'].sum()
                    revenue_by_source[source] = source_total
            
            # Get volatility metrics
            volatility = {}
            if 'mom_change' in df.columns:
                mom_changes = df['mom_change'].dropna()
                volatility = {
                    'average': mom_changes.mean(),
                    'median': mom_changes.median(),
                    'std_dev': mom_changes.std(),
                    'max': mom_changes.max(),
                    'min': mom_changes.min()
                }
            
            # Create report
            report = {
                'protocol': protocol_name,
                'category': category,
                'eqs': {
                    'score': eqs_score,
                    'components': {
                        'stability': stability_score,
                        'diversification': diversification_score,
                        'magnitude': magnitude_score
                    }
                },
                'revenue': {
                    'sources': revenue_by_source,
                    'volatility': volatility
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report for {protocol_name}: {str(e)}")
            return {'protocol': protocol_name, 'error': str(e)}