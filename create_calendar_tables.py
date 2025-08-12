#!/usr/bin/env python3
"""
Database migration script to create calendar tables
Run this script to set up the calendar functionality in your existing EmailPilot database
"""

from app.core.database import engine, Base
from app.models.calendar import CalendarEvent, CalendarImportLog, CalendarChatHistory
from app.models.client import Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_calendar_tables():
    """Create calendar tables in the database"""
    try:
        logger.info("Creating calendar tables...")
        
        # Import all models to ensure they're registered with SQLAlchemy
        from app.models import client, calendar  # This ensures all models are loaded
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Calendar tables created successfully!")
        logger.info("Tables created: calendar_events, calendar_import_logs, calendar_chat_history")
        
    except Exception as e:
        logger.error(f"Error creating calendar tables: {e}")
        raise

if __name__ == "__main__":
    create_calendar_tables()
    print("\n✅ Calendar integration is ready!")
    print("\nNext steps:")
    print("1. Start the FastAPI server: uvicorn main:app --reload --host 0.0.0.0 --port 8080")
    print("2. Open your browser to http://localhost:8080")
    print("3. Navigate to the Calendar section")
    print("4. Add a client and start creating campaigns!")