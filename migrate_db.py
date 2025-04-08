"""
Database migration script to add new percentile columns to UserData model.
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run database migrations to add new columns"""
    try:
        # Connect to database
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        engine = create_engine(db_url)
        
        # Check if columns already exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_data' 
                AND column_name = 'active_address_percentile'
            """))
            column_exists = result.scalar() is not None
        
        # Skip if columns already exist
        if column_exists:
            logger.info("Columns already exist, skipping migration")
            return True
        
        # Add the new columns
        logger.info("Adding new percentile columns to user_data table")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE user_data
                ADD COLUMN active_address_percentile FLOAT,
                ADD COLUMN transaction_count_percentile FLOAT,
                ADD COLUMN transaction_volume_percentile FLOAT
            """))
            conn.commit()
        
        logger.info("Database migration completed successfully")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database migration error: {str(e)}")
        return False

if __name__ == "__main__":
    run_migrations()