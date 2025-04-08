"""
Script to update percentile rankings for existing user data.
"""
import logging
import pandas as pd
from datetime import datetime
from app import app, db
from models import Protocol, UserData, Score
from score_calculator import ScoreCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_percentile_ranks():
    """Calculate and update percentile ranks for existing user data"""
    with app.app_context():
        try:
            # Get all protocols
            protocols = Protocol.query.all()
            logger.info(f"Found {len(protocols)} protocols")
            
            # Process each category separately to make percentile rankings comparable
            # First, group protocols by category
            category_protocols = {}
            for protocol in protocols:
                if protocol.category not in category_protocols:
                    category_protocols[protocol.category] = []
                category_protocols[protocol.category].append(protocol)
            
            # For each category, calculate percentiles
            for category, protocols_in_category in category_protocols.items():
                logger.info(f"Processing category: {category} with {len(protocols_in_category)} protocols")
                
                # For each month, calculate percentiles across all protocols in this category
                # First, get a list of all unique months
                all_months = set()
                for protocol in protocols_in_category:
                    months = [ud.month for ud in UserData.query.filter_by(protocol_id=protocol.id).all()]
                    all_months.update(months)
                
                sorted_months = sorted(all_months)
                logger.info(f"Found {len(sorted_months)} unique months of data")
                
                # For each month, calculate percentiles
                for month in sorted_months:
                    logger.info(f"Processing month: {month}")
                    
                    # Collect data for all protocols in this category for this month
                    month_data = []
                    for protocol in protocols_in_category:
                        user_data = UserData.query.filter_by(protocol_id=protocol.id, month=month).first()
                        if user_data:
                            month_data.append({
                                'id': user_data.id,
                                'protocol_id': protocol.id,
                                'protocol_name': protocol.name,
                                'active_addresses': user_data.active_addresses,
                                'transaction_count': user_data.transaction_count,
                                'transaction_volume': user_data.transaction_volume
                            })
                    
                    if not month_data:
                        logger.warning(f"No data found for {month} in category {category}")
                        continue
                    
                    # Convert to DataFrame for easier percentile calculation
                    df = pd.DataFrame(month_data)
                    
                    # Calculate percentile ranks within this category and month
                    df['active_address_percentile'] = df['active_addresses'].rank(pct=True)
                    df['transaction_count_percentile'] = df['transaction_count'].rank(pct=True)
                    df['transaction_volume_percentile'] = df['transaction_volume'].rank(pct=True)
                    
                    # Update database records
                    for _, row in df.iterrows():
                        user_data_record = UserData.query.get(row['id'])
                        if user_data_record:
                            user_data_record.active_address_percentile = row['active_address_percentile']
                            user_data_record.transaction_count_percentile = row['transaction_count_percentile']
                            user_data_record.transaction_volume_percentile = row['transaction_volume_percentile']
                    
                    db.session.commit()
                    logger.info(f"Successfully updated percentile ranks for {month} in category {category}")
            
            # Recalculate scores based on new percentile data
            logger.info("Recalculating scores with new percentile data")
            score_calculator = ScoreCalculator()
            score_calculator.calculate_protocol_scores()
            
            logger.info("Percentile rank update and score recalculation completed")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating percentile ranks: {str(e)}")
            return False

def run_update():
    """Run the update process with proper error handling"""
    try:
        print("Starting percentile ranks update...")
        result = update_percentile_ranks()
        if result:
            print("Percentile ranks updated successfully!")
        else:
            print("Failed to update percentile ranks. Check logs for details.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Disable scheduler to speed up execution and avoid double updates
    import os
    os.environ['DISABLE_SCHEDULER'] = 'True'
    # Run the update only
    run_update()