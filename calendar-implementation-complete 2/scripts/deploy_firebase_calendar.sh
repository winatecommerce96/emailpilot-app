#!/bin/bash
# Firebase Calendar Production Deployment Script

echo "🚀 EmailPilot Firebase Calendar Deployment"
echo "============================================"

# Check if service account exists
SERVICE_ACCOUNT_FILE="/Users/Damon/Downloads/emailpilot-438321-6335761b472e.json"
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo "❌ Service account file not found: $SERVICE_ACCOUNT_FILE"
    exit 1
fi

echo "✅ Service account file found"

# Export environment variables
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
    print(f'✅ Firebase connected successfully! Found {len(clients)} clients')
except Exception as e:
    print(f'❌ Firebase connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Firebase connection test failed"
    exit 1
fi

# Check if indexes are created
echo "📊 Checking Firebase indexes..."
echo "⚠️  Make sure you've created the required indexes:"
echo "   • calendar_events: client_id, event_date, __name__"
echo "   • calendar_chat_history: client_id, session_id, created_at, __name__"
echo ""

# Test API endpoints
echo "🧪 Testing API endpoints..."
TOKEN=$(curl -s -X POST "http://localhost:8080/api/auth/login?email=admin@emailpilot.ai&password=demo" | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get authentication token"
    exit 1
fi

echo "✅ Authentication successful"

# Test Firebase calendar endpoints
CLIENTS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/firebase-calendar/clients)
if [[ $CLIENTS_RESPONSE == *"error"* ]] || [[ $CLIENTS_RESPONSE == *"detail"* ]]; then
    echo "❌ Firebase calendar endpoints not working"
    echo "Response: $CLIENTS_RESPONSE"
    exit 1
fi

echo "✅ Firebase calendar endpoints working"

# Create deployment package
echo "📦 Creating deployment package..."
DEPLOY_DIR="emailpilot_firebase_deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR"

# Copy essential files
cp main.py "$DEPLOY_DIR/"
cp firebase_calendar_integration.py "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"
cp production_deployment_guide.md "$DEPLOY_DIR/"
cp -r app/ "$DEPLOY_DIR/"
cp -r frontend/ "$DEPLOY_DIR/"

# Copy service account to deployment package
cp "$SERVICE_ACCOUNT_FILE" "$DEPLOY_DIR/service-account.json"

# Create production .env
cat > "$DEPLOY_DIR/.env.production" << EOF
# Firebase Configuration
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# API Keys
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=change-this-secret-key-in-production-deployment

# Database
DATABASE_URL=sqlite:///./emailpilot.db

# Environment  
ENVIRONMENT=production
DEBUG=false
SECRET_MANAGER_ENABLED=false
EOF

# Create production startup script
cat > "$DEPLOY_DIR/start_production.sh" << 'EOF'
#!/bin/bash
# Load environment variables
source .env.production

# Install dependencies
pip install -r requirements.txt

echo "🔥 Starting EmailPilot with Firebase Calendar"
echo "📍 Server will be available at https://emailpilot.ai"
echo "🎯 Calendar endpoints: /api/firebase-calendar/*"

# Start with gunicorn for production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8080 --timeout 120
EOF

chmod +x "$DEPLOY_DIR/start_production.sh"

echo ""
echo "🎉 DEPLOYMENT PACKAGE READY!"
echo "============================"
echo ""
echo "📁 Package location: ./$DEPLOY_DIR"
echo ""
echo "🚀 To deploy to production:"
echo "   1. Upload the entire '$DEPLOY_DIR' folder to your server"
echo "   2. Run: cd $DEPLOY_DIR && ./start_production.sh"
echo "   3. Test at: https://emailpilot.ai/test_firebase_calendar.html"
echo ""
echo "✅ Features included:"
echo "   • Firebase Firestore backend"
echo "   • Real-time calendar with drag & drop"
echo "   • AI chat with Gemini"
echo "   • Google Doc import"
echo "   • Client management"
echo "   • Export functionality"
echo "   • Production-ready configuration"
echo ""
echo "🔐 Security:"
echo "   • Change SECRET_KEY in .env.production"
echo "   • Secure service-account.json file permissions"
echo "   • Configure HTTPS in production"
echo ""
echo "📊 Monitor at: https://console.firebase.google.com/project/emailpilot-438321"

ls -la "$DEPLOY_DIR"