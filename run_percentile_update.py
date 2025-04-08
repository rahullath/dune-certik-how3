"""
Standalone script to update percentile rankings for user data in the database.
This script bypasses the normal app initialization to avoid starting the scheduler.
"""
import logging
import os
import pandas as pd
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up database without initializing the full app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Define database model base class
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models after setting up the database connection
from models import Protocol, UserData, Score

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
            
            logger.info("Percentile rank update completed")
            
            # Check if any percentiles were actually updated
            null_percentiles = UserData.query.filter(UserData.active_address_percentile.is_(None)).count()
            if null_percentiles > 0:
                logger.warning(f"There are still {null_percentiles} records with null percentile values")
            else:
                logger.info("All records have percentile values populated")
                
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating percentile ranks: {str(e)}")
            return False

if __name__ == "__main__":
    print("Starting standalone percentile rank update...")
    with app.app_context():
        # Print some diagnostics first
        total_user_data = UserData.query.count()
        null_percentiles = UserData.query.filter(UserData.active_address_percentile.is_(None)).count()
        print(f"Total user data records: {total_user_data}")
        print(f"Records with null percentiles: {null_percentiles}")
        
        # Run the update
        result = update_percentile_ranks()
        
        # Check results
        if result:
            print("Percentile ranks updated successfully!")
            # Print final stats
            null_percentiles_after = UserData.query.filter(UserData.active_address_percentile.is_(None)).count()
            print(f"Records with null percentiles after update: {null_percentiles_after}")
        else:
            print("Failed to update percentile ranks. Check logs for details.")