import logging
from datetime import datetime, timedelta
from app import db
from models import Protocol, Category, Score, RevenueData, UserData
from config import get_config

logger = logging.getLogger(__name__)

def seed_database():
    """Seed the database with initial data for testing"""
    logger.info("Starting database seeding process")
    
    try:
        # Only seed if the database is empty
        if Protocol.query.count() > 0:
            logger.info("Database already has protocols, skipping seed")
            return
        
        config = get_config()
        protocols_config = config.PROTOCOLS
        
        # Add categories
        categories = {
            "Oracle": "Protocols that provide off-chain data to blockchain applications",
            "DEX": "Decentralized exchanges for trading tokens",
            "Lending": "Protocols that enable lending and borrowing of crypto assets",
            "Infrastructure": "Base layer protocols that support blockchain applications",
            "Derivatives": "Protocols for trading derivative financial products",
            "Asset Management": "Protocols for managing and optimizing crypto assets"
        }
        
        for name, description in categories.items():
            category = Category(
                name=name,
                description=description,
                avg_revenue_multiple=30.0,  # Default multiplier
                avg_annual_revenue=10000000.0  # Default annual revenue
            )
            db.session.add(category)
        
        db.session.commit()
        logger.info(f"Added {len(categories)} categories")
        
        # Add protocols from config
        added_protocols = []
        for name, details in protocols_config.items():
            protocol = Protocol(
                name=name.capitalize(),
                symbol=details['symbol'],
                category=details['category'],
                description=details['description'],
                market_cap=10000000000.0,  # Default market cap
                price=100.0,  # Default price
                annual_revenue=100000000.0  # Default annual revenue
            )
            db.session.add(protocol)
            added_protocols.append(protocol)
        
        db.session.commit()
        logger.info(f"Added {len(added_protocols)} protocols")
        
        # Add sample scores for each protocol
        for protocol in added_protocols:
            score = Score(
                protocol_id=protocol.id,
                earnings_quality_score=75.0,
                user_growth_score=80.0,
                fair_value_score=65.0,
                safety_score=90.0,
                how3_score=77.5,  # Average of the four scores
                timestamp=datetime.utcnow()
            )
            db.session.add(score)
        
        db.session.commit()
        logger.info(f"Added scores for {len(added_protocols)} protocols")
        
        # Add sample historical data for each protocol
        today = datetime.utcnow().date()
        
        for protocol in added_protocols:
            # Add 12 months of revenue data
            for i in range(12):
                month_date = today.replace(day=1) - timedelta(days=i*30)
                
                # Slight variation in revenue each month
                base_revenue = 10000000.0  # $10M base monthly revenue
                variation = (0.8 + 0.4 * (i % 3)) # Creates a pattern in the data
                monthly_revenue = base_revenue * variation
                
                revenue_data = RevenueData(
                    protocol_id=protocol.id,
                    month=month_date,
                    revenue=monthly_revenue,
                    revenue_source="total",
                    stability_score=0.0 if i == 0 else (monthly_revenue / base_revenue) - 1,
                    magnitude_score=0.8  # Relative to category peers
                )
                db.session.add(revenue_data)
            
            # Add 12 months of user data
            for i in range(12):
                month_date = today.replace(day=1) - timedelta(days=i*30)
                
                # Base metrics with some variation
                base_addresses = 100000
                base_txns = 1000000
                base_volume = 500000000.0
                
                variation = 1.0 + 0.1 * ((12 - i) / 12)  # Growth trend
                
                user_data = UserData(
                    protocol_id=protocol.id,
                    month=month_date,
                    active_addresses=int(base_addresses * variation),
                    transaction_count=int(base_txns * variation),
                    transaction_volume=base_volume * variation,
                    active_address_growth=5.0 if i > 0 else None,
                    transaction_count_growth=8.0 if i > 0 else None,
                    transaction_volume_growth=10.0 if i > 0 else None
                )
                db.session.add(user_data)
        
        db.session.commit()
        logger.info(f"Added historical data for {len(added_protocols)} protocols")
        
        logger.info("Database seeding completed successfully")
        return True
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding database: {str(e)}")
        return False

if __name__ == "__main__":
    # This allows running the script directly
    from app import app
    with app.app_context():
        seed_database()