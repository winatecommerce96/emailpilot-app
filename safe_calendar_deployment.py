#!/usr/bin/env python3
"""
Safe Calendar Deployment Script
This script helps you deploy calendar tables safely based on your environment
"""

import os
import sys
from app.core.config import settings
from app.core.database import engine, Base
from app.models.calendar import CalendarEvent, CalendarImportLog, CalendarChatHistory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check current environment and database configuration"""
    print("🔍 Environment Check:")
    print(f"   Environment: {settings.environment}")
    print(f"   Database URL: {settings.database_url}")
    print(f"   Google Cloud Project: {settings.google_cloud_project}")
    print(f"   Debug Mode: {settings.debug}")
    
    # Determine if this is production
    is_production = (
        settings.environment.lower() == "production" or
        "emailpilot.ai" in settings.database_url or
        "prod" in settings.google_cloud_project.lower() or
        not settings.debug
    )
    
    return is_production

def create_calendar_tables_safe():
    """Safely create calendar tables with environment checks"""
    
    print("🚀 EmailPilot Calendar Integration Deployment")
    print("=" * 50)
    
    # Environment check
    is_production = check_environment()
    
    if is_production:
        print("⚠️  PRODUCTION ENVIRONMENT DETECTED!")
        print("   This will affect the live emailpilot.ai database.")
        print("   Recommendations:")
        print("   1. Test in development environment first")
        print("   2. Backup production database before proceeding")
        print("   3. Deploy during maintenance window")
        print("   4. Have rollback plan ready")
        
        confirm = input("\n❓ Are you sure you want to proceed with PRODUCTION deployment? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Deployment cancelled for safety.")
            sys.exit(0)
    else:
        print("✅ Development/Local environment detected - safe to proceed")
    
    try:
        print("\n📊 Creating calendar tables...")
        
        # Import models to register with SQLAlchemy
        from app.models import client, calendar
        
        # Show what tables will be created
        print("   Tables to create:")
        print("   - calendar_events (main calendar data)")
        print("   - calendar_import_logs (Google Doc import tracking)")
        print("   - calendar_chat_history (AI chat logs)")
        
        # Create tables (additive operation - won't affect existing data)
        Base.metadata.create_all(bind=engine)
        
        print("✅ Calendar tables created successfully!")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        calendar_tables = [
            'calendar_events',
            'calendar_import_logs', 
            'calendar_chat_history'
        ]
        
        print("\n🔍 Verification:")
        for table in calendar_tables:
            if table in inspector.get_table_names():
                print(f"   ✅ {table} - Created successfully")
            else:
                print(f"   ❌ {table} - Missing!")
                
        print("\n🎉 Calendar Integration Ready!")
        
        if is_production:
            print("\n📋 Post-Deployment Checklist:")
            print("   □ Verify emailpilot.ai loads correctly")
            print("   □ Test calendar navigation")
            print("   □ Test client selection")
            print("   □ Verify existing functionality unchanged")
            print("   □ Monitor error logs")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during deployment: {e}")
        logger.error(f"Deployment failed: {e}")
        
        if is_production:
            print("🚨 PRODUCTION DEPLOYMENT FAILED!")
            print("   Immediate actions:")
            print("   1. Check application logs")
            print("   2. Verify site accessibility") 
            print("   3. Consider rollback if needed")
            print("   4. Contact system administrator")
        
        return False

def show_next_steps(is_production=False):
    """Show next steps after successful deployment"""
    print("\n🚀 Next Steps:")
    
    if is_production:
        print("   1. Monitor emailpilot.ai for any issues")
        print("   2. Test calendar functionality with real users")
        print("   3. Update documentation")
        print("   4. Announce new calendar feature")
    else:
        print("   1. Start development server:")
        print("      uvicorn main:app --reload --host 0.0.0.0 --port 8080")
        print("   2. Open http://localhost:8080")
        print("   3. Login and navigate to Calendar")
        print("   4. Test all calendar functionality")
        print("   5. Deploy to production when ready")

if __name__ == "__main__":
    success = create_calendar_tables_safe()
    
    if success:
        is_prod = check_environment()
        show_next_steps(is_prod)
    else:
        sys.exit(1)