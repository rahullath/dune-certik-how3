import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import routes after db initialization to avoid circular imports
from routes import *  # noqa

# Create database tables
with app.app_context():
    # Import models here to ensure tables are created
    import models  # noqa
    
    # Check which tables need to be created
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    # We'll only create tables that don't already exist
    try:
        # Use create_all with bind parameter to control table creation
        # This will skip tables that already exist
        db.create_all()
        logger.info("Database tables verified and created if necessary")
    except Exception as e:
        logger.error(f"Error managing database tables: {e}")
        
    # Log existing tables for debugging
    logger.info(f"Existing database tables: {existing_tables}")

# Import and start scheduler after app initialization
from scheduler import start_scheduler

with app.app_context():
    start_scheduler(app)
