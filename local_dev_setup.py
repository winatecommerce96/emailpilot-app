#!/usr/bin/env python3
"""
Local Development Setup for Calendar Integration
This script ONLY works with local development databases - safe to run locally
"""

import os
import sys

def setup_local_development():
    """Set up calendar integration for local development only"""
    
    print("🔧 EmailPilot Calendar - Local Development Setup")
    print("=" * 50)
    
    # Force local development database
    local_db_url = "sqlite:///./emailpilot_dev.db"
    os.environ["DATABASE_URL"] = local_db_url
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DEBUG"] = "true"
    
    print(f"📁 Using local database: {local_db_url}")
    print("✅ This will NOT affect production emailpilot.ai")
    
    # Import after setting environment variables
    from app.core.database import engine, Base
    from app.models.calendar import CalendarEvent, CalendarImportLog, CalendarChatHistory
    from app.models.client import Client
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        print("\n📊 Creating local development tables...")
        
        # Import models to register with SQLAlchemy
        from app.models import client, calendar
        
        # Create all tables (including existing ones)
        Base.metadata.create_all(bind=engine)
        
        print("✅ Local development database ready!")
        
        # Create a demo client for testing
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if demo client exists
        demo_client = session.query(Client).filter(Client.name == "Demo Client").first()
        
        if not demo_client:
            demo_client = Client(
                name="Demo Client",
                metric_id="demo_metric_123",
                is_active=True
            )
            session.add(demo_client)
            session.commit()
            print("✅ Demo client created for testing")
        else:
            print("✅ Demo client already exists")
        
        session.close()
        
        print("\n🎉 Local Development Setup Complete!")
        print("\n🚀 To start developing:")
        print("   1. uvicorn main:app --reload --port 8000")
        print("   2. Open http://localhost:8000")
        print("   3. Login with demo credentials")
        print("   4. Navigate to Calendar")
        print("   5. Select 'Demo Client' to test")
        
        print("\n📋 What you can test locally:")
        print("   ✅ Calendar drag-and-drop functionality")
        print("   ✅ Event creation and editing")
        print("   ✅ AI chat (if GEMINI_API_KEY is set)")
        print("   ✅ Client switching")
        print("   ✅ Export functionality")
        
        print("\n🔒 Production Safety:")
        print("   • This setup uses a separate local database")
        print("   • No impact on live emailpilot.ai")
        print("   • Safe for development and testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Local setup failed: {e}")
        return False

if __name__ == "__main__":
    setup_local_development()