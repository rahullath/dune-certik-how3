"""
Centralized scoring script for running protocol-specific EQS calculations
with adjustments from the configuration file.
"""

import argparse
import logging
import pandas as pd
import json
from datetime import datetime
from dune_client import DuneClient
from centralized_processor import CentralizedProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scoring.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_protocol_scoring(protocol_name, use_real_data=False):
    """
    Run protocol-specific scoring using the centralized processor.
    
    Args:
        protocol_name: Name of the protocol to score
        use_real_data: Whether to use real data from Dune
        
    Returns:
        dict: Protocol scoring report
    """
    processor = CentralizedProcessor()
    
    # Get protocol configuration
    protocol_config = processor.get_protocol_config(protocol_name)
    if not protocol_config:
        logger.error(f"No configuration found for protocol: {protocol_name}")
        return None
    
    try:
        # Get data from Dune or use sample data
        if use_real_data:
            df = get_real_dune_data(protocol_name, protocol_config)
        else:
            df = get_sample_data(protocol_name)
        
        if df is None or df.empty:
            logger.error(f"No data available for {protocol_name}")
            return None
        
        # Generate a comprehensive report
        report = processor.generate_protocol_report(df, protocol_name)
        
        # Print a summary
        print(f"\nScoring Report for {protocol_name}:")
        print(f"Category: {report['category']}")
        print(f"EQS Score: {report['eqs']['score']:.2f}")
        print("\nComponent Scores:")
        print(f"Stability: {report['eqs']['components']['stability']:.2f}")
        print(f"Diversification: {report['eqs']['components']['diversification']:.2f}")
        print(f"Magnitude: {report['eqs']['components']['magnitude']:.2f}")
        
        # Save the report to a file
        with open(f"scores/{protocol_name}_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save adjusted data to CSV for transparency
        adjusted_df = processor.apply_revenue_adjustments(df, protocol_name)
        adjusted_df.to_csv(f"scores/{protocol_name}_adjusted_data.csv", index=False)
        
        return report
    
    except Exception as e:
        logger.error(f"Error processing {protocol_name}: {str(e)}")
        return None

def get_real_dune_data(protocol_name, protocol_config):
    """
    Get real data from Dune Analytics for a protocol.
    
    Args:
        protocol_name: Name of the protocol
        protocol_config: Protocol configuration
        
    Returns:
        DataFrame with protocol data
    """
    try:
        dune_client = DuneClient()
        
        # Get query ID from config
        query_id = protocol_config.get('queries', {}).get('eqs', {}).get('query_id')
        if not query_id:
            logger.error(f"No EQS query ID configured for {protocol_name}")
            return None
        
        # Execute query
        results = dune_client.execute_query(query_id)
        if not results:
            logger.error(f"No results returned from Dune for {protocol_name}")
            return None
        
        # Convert to DataFrame (simplified for demonstration)
        df = pd.DataFrame(results)
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data from Dune: {str(e)}")
        return None

def get_sample_data(protocol_name):
    """
    Get sample data for a protocol for testing.
    
    Args:
        protocol_name: Name of the protocol
        
    Returns:
        DataFrame with sample protocol data
    """
    if protocol_name.lower() == 'chainlink':
        # Return sample Chainlink data
        return create_chainlink_sample_data()
    else:
        logger.error(f"No sample data available for {protocol_name}")
        return None

def create_chainlink_sample_data():
    """Create a DataFrame based on the sample Chainlink data from Dune."""
    # Data based on the eqs-chainlink sampledune.txt file
    data = [
        # First month (April 2024)
        {'month': datetime(2024, 4, 1), 'source': 'automation', 'total_fees': 67939.46084758072, 'mom_change': None, 
         'avg_mom_change': -0.08008760931758903, 'stddev_mom_change': 0.5116151413977408, 'num_months': 13},
        {'month': datetime(2024, 4, 1), 'source': 'ccip', 'total_fees': 98848.54011158487, 'mom_change': None, 
         'avg_mom_change': 0.009141157048100923, 'stddev_mom_change': 0.6596989982341107, 'num_months': 13},
        {'month': datetime(2024, 4, 1), 'source': 'fm', 'total_fees': 2219711.501320376, 'mom_change': None, 
         'avg_mom_change': -0.20989551767904832, 'stddev_mom_change': 0.4108114361781297, 'num_months': 13},
        {'month': datetime(2024, 4, 1), 'source': 'ocr', 'total_fees': 3395286.256855447, 'mom_change': None, 
         'avg_mom_change': -0.22781204525964827, 'stddev_mom_change': 0.421958290453829, 'num_months': 13},
        {'month': datetime(2024, 4, 1), 'source': 'vrf', 'total_fees': 31244.752470117477, 'mom_change': None, 
         'avg_mom_change': -0.2036716821229518, 'stddev_mom_change': 0.3310369401263438, 'num_months': 13},
        
        # Second month (May 2024)
        {'month': datetime(2024, 5, 1), 'source': 'automation', 'total_fees': 65326.42687327729, 'mom_change': -0.03846121152132275, 
         'avg_mom_change': -0.08008760931758903, 'stddev_mom_change': 0.5116151413977408, 'num_months': 13},
        {'month': datetime(2024, 5, 1), 'source': 'ccip', 'total_fees': 75257.5047921389, 'mom_change': -0.23865840904494182, 
         'avg_mom_change': 0.009141157048100923, 'stddev_mom_change': 0.6596989982341107, 'num_months': 13},
        {'month': datetime(2024, 5, 1), 'source': 'fm', 'total_fees': 2199732.3881992646, 'mom_change': -0.009000770194336972, 
         'avg_mom_change': -0.20989551767904832, 'stddev_mom_change': 0.4108114361781297, 'num_months': 13},
        {'month': datetime(2024, 5, 1), 'source': 'ocr', 'total_fees': 3152587.491741491, 'mom_change': -0.0714810907692749, 
         'avg_mom_change': -0.22781204525964827, 'stddev_mom_change': 0.421958290453829, 'num_months': 13},
        {'month': datetime(2024, 5, 1), 'source': 'vrf', 'total_fees': 20580.17782983342, 'mom_change': -0.3413237038918349, 
         'avg_mom_change': -0.2036716821229518, 'stddev_mom_change': 0.3310369401263438, 'num_months': 13}
    ]
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    return df

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run centralized scoring for protocols.")
    parser.add_argument("protocol", help="Protocol name (e.g., chainlink)")
    parser.add_argument("--real-data", action="store_true", help="Use real data from Dune")
    args = parser.parse_args()
    
    # Ensure the scores directory exists
    import os
    os.makedirs("scores", exist_ok=True)
    
    # Run scoring
    report = run_protocol_scoring(args.protocol, args.real_data)
    
    if report:
        logger.info(f"Successfully generated report for {args.protocol}")
    else:
        logger.error(f"Failed to generate report for {args.protocol}")

if __name__ == "__main__":
    main()