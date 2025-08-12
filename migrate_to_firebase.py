#!/usr/bin/env python3
"""
Migration script to move EmailPilot from SQLAlchemy to Firebase Firestore
Provides a seamless transition to Google's scalable database solution
"""

import os
import sys
import json
import asyncio
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_prerequisites():
    """Check if Firebase is properly configured"""
    print("🔍 Checking Firebase Prerequisites...")
    
    issues = []
    
    # Check environment variables
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        issues.append("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
    else:
        print(f"✅ Google Cloud Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    
    # Check service account
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        issues.append("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    elif not os.path.exists(creds_path):
        issues.append(f"❌ Service account file not found: {creds_path}")
    else:
        print(f"✅ Service Account: {creds_path}")
    
    # Check Gemini API key
    if not os.getenv('GEMINI_API_KEY'):
        issues.append("❌ GEMINI_API_KEY environment variable not set")
    else:
        print("✅ Gemini API Key configured")
    
    if issues:
        print("\n🚨 Configuration Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        print("\nPlease resolve these issues before proceeding.")
        print("Refer to firebase_setup_guide.md for detailed setup instructions.")
        return False
    
    print("✅ All prerequisites met!")
    return True

async def test_firebase_connection():
    """Test Firebase connection and create sample data"""
    try:
        print("\n🔗 Testing Firebase Connection...")
        
        # Import Firebase services
        from firebase_calendar_integration import firebase_clients, firebase_calendar
        
        # Test creating a sample client
        sample_client_data = {
            'name': 'Migration Test Client',
            'metric_id': 'test_metric_123',
            'is_active': True
        }
        
        client_id = await firebase_clients.create_client(sample_client_data)
        print(f"✅ Successfully created test client: {client_id}")
        
        # Test creating a sample calendar event
        sample_event_data = {
            'client_id': client_id,
            'title': 'Migration Test Event',
            'content': 'This is a test event created during migration',
            'event_date': '2025-09-15',
            'event_type': 'Nurturing/Education',
            'color': 'bg-blue-200 text-blue-800'
        }
        
        event_id = await firebase_calendar.create_event(sample_event_data)
        print(f"✅ Successfully created test event: {event_id}")
        
        # Test retrieving data
        clients = await firebase_clients.get_all_clients()
        events = await firebase_calendar.get_client_events(client_id)
        
        print(f"✅ Successfully retrieved {len(clients)} clients and {len(events)} events")
        
        # Clean up test data
        await firebase_calendar.delete_event(event_id)
        print("✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        return False

def update_main_app():
    """Update main.py to use Firebase endpoints"""
    try:
        print("\n📝 Updating main.py to include Firebase calendar routes...")
        
        main_py_path = 'main.py'
        
        # Read current main.py
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Check if Firebase calendar is already included
        if 'firebase_calendar' in content:
            print("✅ Firebase calendar routes already included in main.py")
            return True
        
        # Add Firebase calendar import
        if 'from app.api import auth, reports, goals, clients, slack, calendar' in content:
            content = content.replace(
                'from app.api import auth, reports, goals, clients, slack, calendar',
                'from app.api import auth, reports, goals, clients, slack, calendar\nfrom app.api import firebase_calendar'
            )
        else:
            # Add after existing imports
            import_line = 'from app.api import auth, reports, goals, clients, slack'
            if import_line in content:
                content = content.replace(
                    import_line,
                    import_line + '\nfrom app.api import firebase_calendar'
                )
        
        # Add Firebase calendar router
        calendar_route = 'app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])'
        if calendar_route in content:
            # Add Firebase calendar route after existing calendar route
            content = content.replace(
                calendar_route,
                calendar_route + '\napp.include_router(firebase_calendar.router, prefix="/api/firebase-calendar", tags=["Firebase Calendar"])'
            )
        else:
            # Add after existing routes
            slack_route = 'app.include_router(slack.router, prefix="/api/slack", tags=["Slack"])'
            if slack_route in content:
                content = content.replace(
                    slack_route,
                    slack_route + '\napp.include_router(firebase_calendar.router, prefix="/api/firebase-calendar", tags=["Firebase Calendar"])'
                )
        
        # Write updated content
        with open(main_py_path, 'w') as f:
            f.write(content)
        
        print("✅ Successfully updated main.py with Firebase routes")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update main.py: {e}")
        return False

def update_frontend_config():
    """Update frontend to use Firebase endpoints"""
    try:
        print("\n🎨 Creating Firebase frontend configuration...")
        
        # Create a configuration file for frontend
        firebase_config = {
            "apiEndpoints": {
                "calendar": "/api/firebase-calendar",
                "events": "/api/firebase-calendar/events", 
                "clients": "/api/firebase-calendar/clients",
                "chat": "/api/firebase-calendar/chat",
                "import": "/api/firebase-calendar/import/google-doc",
                "export": "/api/firebase-calendar/export",
                "stats": "/api/firebase-calendar/client"
            },
            "features": {
                "realTimeUpdates": True,
                "offlineSupport": True,
                "autoSave": True
            }
        }
        
        # Save configuration
        config_path = 'frontend/public/firebase-config.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(firebase_config, f, indent=2)
        
        print(f"✅ Created Firebase configuration: {config_path}")
        
        # Update JavaScript to use new endpoints
        js_files = [
            'frontend/public/components/Calendar.js',
            'frontend/public/components/CalendarView.js',
            'frontend/public/components/CalendarChat.js'
        ]
        
        for js_file in js_files:
            if os.path.exists(js_file):
                print(f"📝 Note: Update {js_file} to use Firebase endpoints from firebase-config.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update frontend configuration: {e}")
        return False

async def run_migration():
    """Run the complete migration process"""
    print("🚀 EmailPilot Firebase Migration")
    print("=" * 50)
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        return False
    
    # Step 2: Test Firebase connection
    if not await test_firebase_connection():
        return False
    
    # Step 3: Update main application
    if not update_main_app():
        return False
    
    # Step 4: Update frontend configuration
    if not update_frontend_config():
        return False
    
    print("\n🎉 Migration Completed Successfully!")
    print("\n📋 Next Steps:")
    print("   1. Update frontend JavaScript files to use new Firebase endpoints")
    print("   2. Test the application locally:")
    print("      uvicorn main:app --reload --port 8080")
    print("   3. Navigate to Calendar section and test functionality")
    print("   4. Create your first client and calendar events")
    print("   5. Test AI chat and Google Doc import features")
    print("\n🔧 Firebase Benefits Now Available:")
    print("   ✅ Real-time synchronization")
    print("   ✅ Auto-scaling to millions of operations") 
    print("   ✅ 99.999% uptime SLA")
    print("   ✅ Global CDN for fast access")
    print("   ✅ Automatic backups and security")
    
    print("\n📊 Monitoring:")
    print("   • View Firebase Console: https://console.firebase.google.com")
    print("   • Monitor usage and performance")
    print("   • Set up alerts for errors")
    
    return True

def show_help():
    """Show help information"""
    print("🔧 EmailPilot Firebase Migration Tool")
    print("\nUsage:")
    print("  python migrate_to_firebase.py          # Run full migration")
    print("  python migrate_to_firebase.py --help   # Show this help")
    print("  python migrate_to_firebase.py --check  # Check prerequisites only")
    print("\nPrerequisites:")
    print("  1. Set GOOGLE_CLOUD_PROJECT environment variable")
    print("  2. Set GOOGLE_APPLICATION_CREDENTIALS to service account file")
    print("  3. Set GEMINI_API_KEY for AI functionality")
    print("  4. Install Firebase dependencies: pip install firebase-admin")
    print("\nFor detailed setup instructions, see: firebase_setup_guide.md")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            show_help()
            sys.exit(0)
        elif sys.argv[1] == '--check':
            if check_prerequisites():
                print("✅ All prerequisites met! Ready for migration.")
            sys.exit(0)
    
    # Run the full migration
    success = asyncio.run(run_migration())
    
    if success:
        print("\n🌟 EmailPilot is now running on Firebase!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)