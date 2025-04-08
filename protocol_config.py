"""
Configuration file for protocol query IDs and custom processors.
Add protocols and their corresponding Dune Analytics query IDs here.
"""

# Configuration for each protocol: query IDs and optional custom processors
PROTOCOL_CONFIGS = {
    "chainlink": {
        "eqs": {"query_id": 4953227},
        "ugs": {"query_id": 4953009},
        "category": "Oracle"
    },
    "aave": {
        "eqs": {"query_id": None},  # Replace with actual query ID
        "ugs": {"query_id": None},  # Replace with actual query ID
        "category": "Lending"
    },
    "gmx": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "DEX"
    },
    "lido": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Staking"
    },
    "bitcoin": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Currency"
    },
    "uniswap": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "DEX"
    },
    "bnb": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Exchange"
    },
    "optimism": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "L2"
    },
    "pendle": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Yield"
    },
    "curve": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "DEX"
    },
    "maple": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Lending"
    },
    "compound": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "Lending"
    },
    "ethereum": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "L1"
    },
    "avalanche": {
        "eqs": {"query_id": None},
        "ugs": {"query_id": None},
        "category": "L1"
    }
}

# Custom processors for specific protocols
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def custom_chainlink_ugs_processor(raw_data):
    """
    Custom processor for Chainlink UGS data to handle very large transaction volumes.
    
    Args:
        raw_data: Raw data from Dune query
        
    Returns:
        Processed DataFrame
    """
    try:
        # Convert to DataFrame if not already
        if not isinstance(raw_data, pd.DataFrame):
            if 'rows' in raw_data:
                df = pd.DataFrame(raw_data['rows'])
                
                # Map column names if needed
                if 'meta' in raw_data and 'column_names' in raw_data['meta']:
                    column_names = raw_data['meta']['column_names']
                    df.columns = column_names
            else:
                logger.error("Expected 'rows' in raw_data but not found")
                return pd.DataFrame()
        else:
            df = raw_data.copy()
        
        if df.empty:
            return df
            
        # Handle very large transaction volumes (divide by 10^18 if needed for token normalization)
        if 'transaction_volume' in df.columns:
            # Check if values are unusually large (indicating they're in raw token units)
            if df['transaction_volume'].max() > 1e18:
                logger.info("Normalizing large transaction volumes (dividing by 10^18)")
                df['transaction_volume'] = df['transaction_volume'] / 1e18
        
        # Sort by month to ensure proper time-series handling
        if 'month' in df.columns:
            df = df.sort_values('month')
            
            # Calculate growth rates if missing
            for metric in ['active_addresses', 'transaction_count', 'transaction_volume']:
                growth_col = f"{metric}_growth_rate"
                if metric in df.columns and growth_col not in df.columns:
                    df[growth_col] = df[metric].pct_change() * 100
            
            # Calculate percentiles across the time series
            for metric in ['active_addresses', 'transaction_count', 'transaction_volume']:
                percentile_col = f"{metric}_percentile"
                if metric in df.columns and percentile_col not in df.columns:
                    df[percentile_col] = df[metric].rank(pct=True)
        
        return df
    
    except Exception as e:
        logger.error(f"Error in custom Chainlink UGS processor: {str(e)}")
        return pd.DataFrame()

# Register the custom processor
PROTOCOL_CONFIGS["chainlink"]["ugs"]["processor"] = custom_chainlink_ugs_processor

# Category-specific settings
CATEGORY_SETTINGS = {
    "DEX": {
        "avg_revenue_multiple": 25,
    },
    "Lending": {
        "avg_revenue_multiple": 30,
    },
    "Oracle": {
        "avg_revenue_multiple": 40,
    },
    "L1": {
        "avg_revenue_multiple": 50,
    },
    "L2": {
        "avg_revenue_multiple": 45,
    },
    "Staking": {
        "avg_revenue_multiple": 35,
    },
    "Currency": {
        "avg_revenue_multiple": 60,
    },
    "Exchange": {
        "avg_revenue_multiple": 20,
    },
    "Yield": {
        "avg_revenue_multiple": 28,
    }
}

# Weight configurations for score calculation
SCORE_WEIGHTS = {
    "eqs": 0.25,  # Earnings Quality Score weight
    "ugs": 0.25,  # User Growth Score weight
    "fvs": 0.25,  # Fair Value Score weight
    "ss": 0.25    # Safety Score weight
}

# EQS component weights
EQS_WEIGHTS = {
    "stability": 0.5,
    "magnitude": 0.5
}

# UGS component weights
UGS_WEIGHTS = {
    "active_addresses": 0.4,
    "transaction_count": 0.3,
    "transaction_volume": 0.3
}