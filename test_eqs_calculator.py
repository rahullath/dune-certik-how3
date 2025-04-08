"""
Test script for the improved EQS calculator.
This script simulates data from Dune Analytics and tests the calculator functionality.
"""

import pandas as pd
import numpy as np
import logging
from improved_eqs_calculator import EnhancedEQSCalculator
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_data(num_months=12, num_sources=5):
    """
    Create a sample dataset similar to what we'd get from Dune Analytics.
    Based on the Chainlink sample data structure.
    
    Returns:
        DataFrame with simulated revenue data
    """
    # Initialize data structure
    data = []
    
    # Generate dates for the past 'num_months' months
    end_date = datetime.now()
    
    sources = ['vrf', 'automation', 'fm', 'ocr', 'ccip'][:num_sources]
    
    # Generate data for each month and source
    for i in range(num_months):
        # Calculate month date
        month_date = end_date - timedelta(days=30 * i)
        
        for source in sources:
            # Generate revenue for this source (more recent months have higher revenue)
            base_revenue = 100000 * (1 + (num_months - i) / 10)
            # Add randomness to make it realistic
            revenue = base_revenue * (0.7 + 0.6 * np.random.random())
            
            # Calculate month-over-month change (except for the first month)
            mom_change = np.nan  # Default for most recent month
            
            if i > 0:
                # Find previous month's data for this source
                prev_month_data = [item for item in data 
                                  if item['source'] == source and 
                                     item['month'] == end_date - timedelta(days=30 * (i-1))]
                
                if prev_month_data:
                    prev_revenue = prev_month_data[0]['total_fees']
                    mom_change = (revenue - prev_revenue) / prev_revenue
            
            # Create data point
            data_point = {
                'month': month_date,
                'source': source,
                'total_fees': revenue,
                'mom_change': mom_change,
                'avg_mom_change': -0.1,  # Average MoM change (historical)
                'stddev_mom_change': 0.4,  # Standard deviation of MoM changes
                'num_months': num_months  # Number of months in the dataset
            }
            
            data.append(data_point)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    return df

def test_calculator():
    """Test the EQS calculator with sample data."""
    try:
        # Create sample data
        df = create_sample_data()
        
        # Print data summary
        print(f"Generated sample data with {len(df)} rows")
        print(f"Columns: {df.columns.tolist()}")
        print("\nSample data (first 5 rows):")
        print(df.head(5).to_string())
        
        # Calculate EQS
        calculator = EnhancedEQSCalculator()
        eqs_score = calculator.calculate_eqs(df, "test_protocol")
        
        # Display component scores
        stability_score = calculator._calculate_stability_score(df)
        diversification_score = calculator._calculate_diversification_score(df)
        magnitude_score = calculator._calculate_magnitude_score(df)
        
        print("\nEQS Component Scores:")
        print(f"Stability Score: {stability_score:.2f}")
        print(f"Diversification Score: {diversification_score:.2f}")
        print(f"Magnitude Score: {magnitude_score:.2f}")
        print(f"Overall EQS: {eqs_score:.2f}")
        
        # Test with different data scenarios
        print("\nTesting different data scenarios:")
        
        # Scenario 1: High stability (low volatility)
        df_stable = df.copy()
        df_stable['mom_change'] = df_stable['mom_change'] * 0.2  # Reduce volatility
        eqs_stable = calculator.calculate_eqs(df_stable, "stable_protocol")
        print(f"High Stability Scenario EQS: {eqs_stable:.2f}")
        
        # Scenario 2: High diversification (more evenly distributed revenue)
        df_diverse = df.copy()
        # Make revenue more evenly distributed across sources
        sources = df_diverse['source'].unique()
        for i, source in enumerate(sources):
            multiplier = 0.8 + 0.4 * (i / len(sources))  # Creates more even distribution
            df_diverse.loc[df_diverse['source'] == source, 'total_fees'] *= multiplier
        eqs_diverse = calculator.calculate_eqs(df_diverse, "diverse_protocol")
        print(f"High Diversification Scenario EQS: {eqs_diverse:.2f}")
        
        # Scenario 3: High magnitude (higher revenue)
        df_high_rev = df.copy()
        df_high_rev['total_fees'] = df_high_rev['total_fees'] * 10  # 10x revenue
        eqs_high_rev = calculator.calculate_eqs(df_high_rev, "high_revenue_protocol")
        print(f"High Revenue Scenario EQS: {eqs_high_rev:.2f}")
        
        # Compare scenarios
        print("\nScenario comparison:")
        print(f"Baseline EQS: {eqs_score:.2f}")
        print(f"High Stability EQS: {eqs_stable:.2f} ({(eqs_stable-eqs_score):.2f} change)")
        print(f"High Diversification EQS: {eqs_diverse:.2f} ({(eqs_diverse-eqs_score):.2f} change)")
        print(f"High Revenue EQS: {eqs_high_rev:.2f} ({(eqs_high_rev-eqs_score):.2f} change)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing EQS calculator: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Enhanced EQS Calculator...")
    success = test_calculator()
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest failed due to errors.")