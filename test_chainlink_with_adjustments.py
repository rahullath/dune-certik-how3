"""
Test script for calculating Chainlink EQS with the centralized processor
and protocol-specific adjustments.
"""

import pandas as pd
import logging
from datetime import datetime
from centralized_processor import CentralizedProcessor
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def print_revenue_distribution(df, title):
    """Print revenue distribution for a DataFrame."""
    recent_month = df[df['month'] == df['month'].max()]
    total_revenue = recent_month['total_fees'].sum()
    
    print(f"\n{title} (Total: ${total_revenue:,.2f}):")
    for _, row in recent_month.iterrows():
        source = row['source']
        fees = row['total_fees']
        percentage = (fees / total_revenue) * 100
        print(f"  {source}: ${fees:,.2f} ({percentage:.2f}%)")

def test_chainlink_adjustments():
    """Test the centralized processor with Chainlink data and adjustments."""
    try:
        # Load the sample data
        df = create_chainlink_sample_data()
        
        # Print the original revenue distribution
        print_revenue_distribution(df, "Original Revenue Distribution")
        
        # Create the centralized processor
        processor = CentralizedProcessor()
        
        # Calculate EQS before adjustments
        eqs_before = processor.eqs_calculator.calculate_eqs(df, "chainlink")
        print(f"\nEQS Before Adjustments: {eqs_before:.2f}")
        
        # Generate a report with adjustments
        report = processor.generate_protocol_report(df, "chainlink")
        
        # Get the adjusted DataFrame
        adjusted_df = processor.apply_revenue_adjustments(df, "chainlink")
        
        # Print the adjusted revenue distribution
        print_revenue_distribution(adjusted_df, "Adjusted Revenue Distribution")
        
        # Calculate EQS after adjustments
        eqs_after = processor.calculate_eqs(df, "chainlink")
        print(f"\nEQS After Adjustments: {eqs_after:.2f}")
        
        # Print the full report
        print("\nFull Protocol Report:")
        print(json.dumps(report, indent=2, default=str))
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing Chainlink adjustments: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Chainlink with Protocol-Specific Adjustments...")
    success = test_chainlink_adjustments()
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed due to errors.")