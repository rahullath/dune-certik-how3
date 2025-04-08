"""
Test script to calculate EQS for Chainlink using the sample data from Dune.
This uses a simplified version of the Dune output to test our EQS calculator.
"""

import pandas as pd
import logging
from improved_eqs_calculator import EnhancedEQSCalculator
from datetime import datetime

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

def test_chainlink_sample():
    """Test the EQS calculator with the Chainlink sample data."""
    try:
        # Load the sample data
        df = create_chainlink_sample_data()
        
        # Print data summary
        print(f"Chainlink sample data with {len(df)} rows")
        print(f"Columns: {df.columns.tolist()}")
        print("\nSample data (first 5 rows):")
        print(df.head(5).to_string())
        
        # Calculate EQS
        calculator = EnhancedEQSCalculator()
        eqs_score = calculator.calculate_eqs(df, "chainlink")
        
        # Display component scores
        stability_score = calculator._calculate_stability_score(df)
        diversification_score = calculator._calculate_diversification_score(df)
        magnitude_score = calculator._calculate_magnitude_score(df)
        
        print("\nChainlink EQS Component Scores:")
        print(f"Stability Score: {stability_score:.2f}")
        print(f"Diversification Score: {diversification_score:.2f}")
        print(f"Magnitude Score: {magnitude_score:.2f}")
        print(f"Overall EQS: {eqs_score:.2f}")
        
        # Analyze the diversification of revenue sources
        recent_month = df[df['month'] == df['month'].max()]
        print("\nRevenue Distribution for Most Recent Month:")
        for _, row in recent_month.iterrows():
            source = row['source']
            fees = row['total_fees']
            percentage = (fees / recent_month['total_fees'].sum()) * 100
            print(f"{source}: ${fees:,.2f} ({percentage:.2f}%)")
        
        # Calculate total monthly revenue
        monthly_total = recent_month['total_fees'].sum()
        print(f"\nTotal Monthly Revenue: ${monthly_total:,.2f}")
        
        # Calculate average volatility
        volatility = df['mom_change'].dropna().abs().mean() * 100
        print(f"Average Month-over-Month Volatility: {volatility:.2f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing Chainlink EQS calculation: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing EQS Calculator with Chainlink Sample Data...")
    success = test_chainlink_sample()
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed due to errors.")