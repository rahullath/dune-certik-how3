import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from flask import current_app
from data_processor import DataProcessor
from score_calculator import ScoreCalculator
from config import get_config

logger = logging.getLogger(__name__)

def init_scheduler(app):
    """Initialize the scheduler for recurring data updates"""
    config = get_config()
    scheduler = BackgroundScheduler()
    
    # Create the data processing jobs
    data_processor = DataProcessor()
    score_calculator = ScoreCalculator()
    
    # Add jobs to the scheduler
    scheduler.add_job(
        func=lambda: _update_data(app, data_processor, score_calculator),
        trigger=IntervalTrigger(seconds=config.UPDATE_FREQUENCY),
        id='update_data_job',
        name='Update Protocol Data',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started with update frequency: %d seconds", config.UPDATE_FREQUENCY)
    
    # Run an initial update if desired
    with app.app_context():
        _update_data(app, data_processor, score_calculator)

def _update_data(app, data_processor, score_calculator):
    """Update data for all protocols and recalculate scores"""
    with app.app_context():
        try:
            logger.info("Starting scheduled data update at %s", datetime.now())
            
            # Update protocol data
            success_count = data_processor.update_all_protocols()
            logger.info("Updated data for %d protocols", success_count)
            
            # Recalculate scores
            score_calculator.calculate_protocol_scores()
            logger.info("Recalculated scores for all protocols")
            
        except Exception as e:
            logger.error("Error in scheduled data update: %s", str(e))
