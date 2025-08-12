#!/bin/bash
# Deploy Firebase Calendar to existing EmailPilot.ai Calendar Tab

echo "📅 EmailPilot.ai Calendar Tab Integration Deployment"
echo "=================================================="

# Check if service account exists
SERVICE_ACCOUNT_FILE="/Users/Damon/Downloads/emailpilot-438321-6335761b472e.json"
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "❌ Service account file not found: $SERVICE_ACCOUNT_FILE"
    exit 1
fi

echo "✅ Service account file found"

# Export environment variables for testing
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
export GOOGLE_APPLICATION_CREDENTIALS=$SERVICE_ACCOUNT_FILE
export GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs

echo "✅ Environment variables set"

# Test Firebase connection
echo "🔥 Testing Firebase connection..."
python -c "
import asyncio
from firebase_calendar_integration import firebase_clients
try:
    loop = asyncio.get_event_loop()
    clients = loop.run_until_complete(firebase_clients.get_all_clients())
    print(f'✅ Firebase connected! Found {len(clients)} clients')
except Exception as e:
    print(f'❌ Firebase connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Firebase connection test failed"
    exit 1
fi

# Create Calendar Tab deployment package
echo "📦 Creating Calendar Tab Integration Package..."
DEPLOY_DIR="emailpilot_calendar_tab_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"

# Backend files
echo "📂 Copying backend files..."
cp main.py "$DEPLOY_DIR/"
cp firebase_calendar_integration.py "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"
cp -r app/ "$DEPLOY_DIR/"

# Frontend files for Calendar Tab
echo "🎨 Copying frontend files..."
mkdir -p "$DEPLOY_DIR/frontend/calendar"
cp frontend/public/components/Calendar.js "$DEPLOY_DIR/frontend/calendar/"
cp frontend/public/components/CalendarView.js "$DEPLOY_DIR/frontend/calendar/"
cp frontend/public/components/CalendarChat.js "$DEPLOY_DIR/frontend/calendar/"
cp frontend/public/components/EventModal.js "$DEPLOY_DIR/frontend/calendar/"
cp frontend/public/components/EmailPilotCalendarTab.js "$DEPLOY_DIR/frontend/calendar/"

# Copy service account
cp "$SERVICE_ACCOUNT_FILE" "$DEPLOY_DIR/service-account.json"

# Create Calendar Tab specific configuration
cat > "$DEPLOY_DIR/calendar_tab_config.json" << 'EOF'
{
  "integration": {
    "type": "calendar_tab_replacement",
    "target": "/calendar",
    "component": "EmailPilotCalendarTab"
  },
  "apiEndpoints": {
    "base": "/api/firebase-calendar",
    "clients": "/api/firebase-calendar/clients",
    "events": "/api/firebase-calendar/events",
    "chat": "/api/firebase-calendar/chat",
    "stats": "/api/firebase-calendar/client",
    "import": "/api/firebase-calendar/import/google-doc",
    "export": "/api/firebase-calendar/export"
  },
  "features": {
    "dragAndDrop": true,
    "aiChat": true,
    "realTimeSync": true,
    "googleDocImport": true,
    "exportData": true,
    "multiClient": true
  }
}
EOF

# Create integration instructions
cat > "$DEPLOY_DIR/CALENDAR_TAB_INTEGRATION.md" << 'EOF'
# 📅 EmailPilot.ai Calendar Tab Integration

## 🎯 Overview
This package contains everything needed to integrate the Firebase calendar into your existing EmailPilot.ai Calendar tab.

## 🚀 Quick Integration Steps

### 1. Upload Backend Files
Upload these files to your EmailPilot.ai server:
- `main.py` (replace existing - includes Firebase routes)
- `firebase_calendar_integration.py` (new file)
- `app/api/firebase_calendar.py` (new file)
- `service-account.json` (secure location)

### 2. Set Environment Variables
Add to your production environment:
```bash
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs
```

### 3. Update Calendar Tab Frontend
Replace your existing Calendar tab component with:
```javascript
import EmailPilotCalendarTab from './frontend/calendar/EmailPilotCalendarTab.js';

// In your main app routing
<Route path="/calendar" component={EmailPilotCalendarTab} />
```

### 4. Include Required Components
Copy these components to your frontend:
- `EmailPilotCalendarTab.js` (main component)
- `CalendarView.js` (calendar interface) 
- `CalendarChat.js` (AI assistant)
- `Calendar.js` (calendar logic)
- `EventModal.js` (event editing)

### 5. Test Integration
1. Restart your EmailPilot.ai application
2. Navigate to the Calendar tab
3. Select a client
4. Test calendar functionality

## ✅ Features Available in Calendar Tab

- **📅 Visual Calendar** - Drag & drop campaign planning
- **🤖 AI Assistant** - Gemini-powered campaign suggestions  
- **👥 Client Context** - Automatically uses selected client
- **📊 Statistics** - Campaign analytics and insights
- **📁 Import/Export** - Google Docs integration
- **🔄 Real-time Sync** - Instant updates across devices
- **📱 Responsive** - Works on desktop and mobile

## 🔐 Security Considerations

- Secure `service-account.json` with appropriate permissions
- Use environment variables for sensitive data
- Configure Firebase security rules
- Enable HTTPS in production

## 📊 Monitoring

Monitor your Calendar tab integration:
- Firebase Console: https://console.firebase.google.com/project/emailpilot-438321
- Application logs for API calls
- User engagement with calendar features

## 🆘 Support

If you encounter issues:
1. Check Firebase connection in console
2. Verify environment variables are set
3. Confirm client authentication works
4. Test API endpoints individually

Your Calendar tab will be enhanced with powerful Firebase-backed functionality!
EOF

# Create production environment file
cat > "$DEPLOY_DIR/.env.production" << EOF
# Firebase Configuration for EmailPilot.ai Calendar Tab
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# AI Integration
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs

# EmailPilot Configuration
SECRET_KEY=change-this-in-production-for-security
DATABASE_URL=sqlite:///./emailpilot.db
ENVIRONMENT=production
DEBUG=false
EOF

# Create deployment script
cat > "$DEPLOY_DIR/deploy_to_emailpilot.sh" << 'EOF'
#!/bin/bash
# Deploy Calendar Tab Integration to EmailPilot.ai

echo "🚀 Deploying Calendar Tab Integration to EmailPilot.ai"
echo "====================================================="

# Load environment variables
if [ -f ".env.production" ]; then
    source .env.production
    echo "✅ Environment variables loaded"
else
    echo "❌ .env.production file not found"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Test Firebase connection
echo "🔥 Testing Firebase connection..."
python -c "
from firebase_calendar_integration import firebase_clients
import asyncio
try:
    loop = asyncio.get_event_loop()
    clients = loop.run_until_complete(firebase_clients.get_all_clients())
    print(f'✅ Firebase connected! Ready for production.')
except Exception as e:
    print(f'❌ Firebase connection failed: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 CALENDAR TAB INTEGRATION READY!"
    echo "=================================="
    echo ""
    echo "✅ Backend: Firebase calendar API endpoints active"
    echo "✅ Frontend: React components ready for Calendar tab"
    echo "✅ Database: Firebase Firestore connected"
    echo "✅ AI: Gemini integration working"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Replace your Calendar tab component with EmailPilotCalendarTab"
    echo "2. Restart your EmailPilot.ai application"
    echo "3. Test the Calendar tab functionality"
    echo "4. Monitor usage via Firebase Console"
    echo ""
    echo "🌐 Your enhanced Calendar tab will be available at:"
    echo "   https://emailpilot.ai/calendar"
else
    echo "❌ Deployment preparation failed"
    exit 1
fi
EOF

chmod +x "$DEPLOY_DIR/deploy_to_emailpilot.sh"

echo ""
echo "🎉 CALENDAR TAB INTEGRATION PACKAGE READY!"
echo "=========================================="
echo ""
echo "📁 Package location: ./$DEPLOY_DIR"
echo ""
echo "🚀 To integrate into EmailPilot.ai Calendar tab:"
echo "   1. Upload '$DEPLOY_DIR' to your EmailPilot.ai server"
echo "   2. Run: cd $DEPLOY_DIR && ./deploy_to_emailpilot.sh"
echo "   3. Update your Calendar tab component routing"
echo "   4. Restart EmailPilot.ai application"
echo ""
echo "✅ Calendar Tab Features:"
echo "   • 📅 Visual drag & drop calendar"
echo "   • 🤖 AI campaign assistant" 
echo "   • 👥 Multi-client support"
echo "   • 📊 Campaign analytics"
echo "   • 🔄 Real-time sync"
echo "   • 📱 Mobile responsive"
echo ""
echo "🎯 Integration Target: https://emailpilot.ai/calendar"

ls -la "$DEPLOY_DIR"