import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from flask import Flask

from data_processor import DataProcessor
from config import DATA_UPDATE_INTERVAL

logger = logging.getLogger(__name__)

def update_all_protocols():
    """Update data for all protocols."""
    logger.info("Scheduled job: Updating all protocols")
    data_processor = DataProcessor()
    success_count, total_count = data_processor.update_all_protocols()
    logger.info(f"Updated {success_count}/{total_count} protocols")

def start_scheduler(app: Flask):
    """Initialize and start the scheduler.
    
    Args:
        app: Flask application
    """
    try:
        # Configure job stores and executors
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        # Create scheduler
        scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Add jobs
        scheduler.add_job(
            update_all_protocols,
            'interval',
            days=DATA_UPDATE_INTERVAL.days,
            id='update_all_protocols',
            replace_existing=True
        )
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started")
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
