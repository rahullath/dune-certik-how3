"""
Test script for integrating our improved EQS calculator with the Dune processor.
This uses the EQS sample data and performs a direct integration test.
"""

import pandas as pd
import logging
from improved_eqs_calculator import EnhancedEQSCalculator, integrate_with_dune_processor
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDuneProcessor:
    """A simplified version of the DuneProcessor for testing."""
    
    def __init__(self):
        self.protocols = {'chainlink': {'name': 'chainlink', 'category': 'Oracle'}}
        
    def register_protocol(self, name, config):
        """Register a protocol for testing."""
        self.protocols[name] = {'name': name, **config}
        
    def calculate_eqs(self, df):
        """Calculate EQS score using our improved calculator."""
        try:
            # Use improved EQS calculator directly
            calculator = EnhancedEQSCalculator()
            protocol_name = "chainlink"  # For testing
            score = calculator.calculate_eqs(df, protocol_name)
            return score
        except Exception as e:
            logger.error(f"Error in EQS calculation: {e}")
            return None
            
    def calculate_eqs_with_integration(self, df):
        """Use the integration function to calculate EQS."""
        try:
            protocol_name = "chainlink"  # For testing
            data = {'eqs': df}
            score = integrate_with_dune_processor(self, protocol_name, data)
            return score
        except Exception as e:
            logger.error(f"Error in EQS integration: {e}")
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

def test_eqs_integration():
    """Test the integration of our improved EQS calculator with the Dune processor."""
    try:
        # Load sample data
        df = create_chainlink_sample_data()
        
        # Create a simplified Dune processor
        processor = SimpleDuneProcessor()
        
        # Calculate EQS directly
        direct_score = processor.calculate_eqs(df)
        
        # Calculate EQS using integration function
        integration_score = processor.calculate_eqs_with_integration(df)
        
        # Print results
        print("\nEQS Calculation Results:")
        print(f"Direct calculation: {direct_score:.2f}")
        print(f"Integration function: {integration_score:.2f}")
        
        # Calculate detailed scores for analysis
        calculator = EnhancedEQSCalculator()
        stability_score = calculator._calculate_stability_score(df)
        diversification_score = calculator._calculate_diversification_score(df)
        magnitude_score = calculator._calculate_magnitude_score(df)
        
        print("\nComponent Scores:")
        print(f"Stability Score: {stability_score:.2f}")
        print(f"Diversification Score: {diversification_score:.2f}")
        print(f"Magnitude Score: {magnitude_score:.2f}")
        
        # Calculate revenue distribution to verify diversification
        recent_month = df[df['month'] == df['month'].max()]
        total_revenue = recent_month['total_fees'].sum()
        
        print("\nRevenue Distribution for Most Recent Month:")
        for _, row in recent_month.iterrows():
            source = row['source']
            fees = row['total_fees']
            percentage = (fees / total_revenue) * 100
            print(f"{source}: ${fees:,.2f} ({percentage:.2f}%)")
        
        print(f"\nTotal Monthly Revenue: ${total_revenue:,.2f}")
        
        # Verify our implementation matches the expected EQS formula
        # Formula: When both stability and diversification exist: 0.7 * stability_score + 0.3 * diversification_score
        # When combined with magnitude: (quality_score * magnitude_score) / 100
        quality_score = 0.7 * stability_score + 0.3 * diversification_score
        expected_score = (quality_score * magnitude_score) / 100
        
        print("\nVerification:")
        print(f"Quality Score (0.7 * stability + 0.3 * diversification): {quality_score:.2f}")
        print(f"Expected EQS ((quality_score * magnitude_score) / 100): {expected_score:.2f}")
        print(f"Actual EQS: {direct_score:.2f}")
        print(f"Difference: {abs(expected_score - direct_score):.4f}")
        
        # Test successful if scores match
        return abs(expected_score - direct_score) < 0.01
        
    except Exception as e:
        logger.error(f"Error testing EQS integration: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing EQS Integration...")
    success = test_eqs_integration()
    if success:
        print("\nIntegration test completed successfully!")
        sys.exit(0)
    else:
        print("\nIntegration test failed.")
        sys.exit(1)