#!/bin/bash

# EmailPilot Integrated Calendar Deployment Script
# Deploys the new Firebase-integrated calendar with goals support

echo "🚀 Deploying Integrated Calendar to EmailPilot..."

# Set directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend/public"

# Check if calendar file exists
if [ ! -f "$FRONTEND_DIR/calendar_integrated.html" ]; then
    echo "❌ Error: calendar_integrated.html not found in $FRONTEND_DIR"
    exit 1
fi

# Backup existing calendar files if they exist
if [ -f "$FRONTEND_DIR/calendar.html" ]; then
    echo "📦 Backing up existing calendar.html..."
    cp "$FRONTEND_DIR/calendar.html" "$FRONTEND_DIR/calendar.html.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Deploy the integrated calendar
echo "📝 Deploying integrated calendar..."
cp "$FRONTEND_DIR/calendar_integrated.html" "$FRONTEND_DIR/calendar.html"

# Update index.html to use the new calendar
echo "🔧 Updating index.html to use integrated calendar..."
if [ -f "$FRONTEND_DIR/index.html" ]; then
    # Check if calendar.html is already referenced
    if grep -q "calendar.html" "$FRONTEND_DIR/index.html"; then
        echo "✅ index.html already references calendar.html"
    else
        echo "⚠️ index.html doesn't reference calendar.html - manual update may be needed"
    fi
fi

# Create a configuration file for Firebase settings
echo "📝 Creating Firebase configuration..."
cat > "$FRONTEND_DIR/firebase_config.js" << 'EOF'
// EmailPilot Firebase Configuration
window.FIREBASE_CONFIG = {
    apiKey: "AIzaSyB0RrH7hbER2R-SzXfNmFe0O32HhH7HBEM",
    authDomain: "emailpilot-438321.firebaseapp.com",
    projectId: "emailpilot-438321",
    storageBucket: "emailpilot-438321.appspot.com",
    messagingSenderId: "104067375141",
    appId: "1:104067375141:web:2b65c86eec8e8c8b4c9f3a"
};

window.GEMINI_API_KEY = "AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs";
window.GOOGLE_API_KEY = "AIzaSyAMeP8IjAfqmHAh7MeN5lpu2OpHhfRTTEg";
window.GOOGLE_CLIENT_ID = "1058910766003-pqu4avth8ltclpbtpk81k0ln21dl8jue.apps.googleusercontent.com";
EOF

echo "✅ Calendar deployment complete!"
echo ""
echo "📌 Next steps:"
echo "1. Test the calendar at: http://localhost:8080/calendar.html"
echo "2. Ensure Firebase Firestore has the following collections:"
echo "   - clients (for calendar data)"
echo "   - goals (for revenue goals)"
echo "3. Update your Calendar Tab component to use calendar.html"
echo ""
echo "🎯 Features included:"
echo "   ✓ Full drag-and-drop calendar functionality"
echo "   ✓ Client management"
echo "   ✓ Google Doc import"
echo "   ✓ Goals integration with revenue tracking"
echo "   ✓ AI chat with goal awareness"
echo "   ✓ Campaign type revenue multipliers"
echo ""
echo "🔐 Security note: Ensure proper authentication is configured for production use"