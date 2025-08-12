#!/bin/bash

# EmailPilot Enhanced Calendar Deployment Script
# Deploys the deep Firebase-integrated calendar components

echo "🚀 Deploying Enhanced Firebase Calendar Components..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend/public"

echo "📁 Current working directory: $SCRIPT_DIR"

# Check if components exist
if [ ! -f "$FRONTEND_DIR/components/CalendarViewEnhanced.js" ]; then
    echo "❌ Error: CalendarViewEnhanced.js not found"
    exit 1
fi

# Backup existing CalendarView if it exists
if [ -f "$FRONTEND_DIR/components/CalendarView.js" ]; then
    echo "📦 Backing up existing CalendarView.js..."
    cp "$FRONTEND_DIR/components/CalendarView.js" "$FRONTEND_DIR/components/CalendarView.js.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Replace CalendarView with Enhanced version
echo "🔧 Updating CalendarView component..."
cp "$FRONTEND_DIR/components/CalendarViewEnhanced.js" "$FRONTEND_DIR/components/CalendarView.js"

echo "✅ Enhanced Calendar deployment complete!"
echo ""
echo "📌 Integration Instructions:"
echo ""
echo "🔹 Calendar Route Available:"
echo "   • Direct HTML: http://localhost:8080/calendar"
echo "   • React Component: Use updated CalendarView.js in your React app"
echo ""
echo "🔹 React Integration:"
echo "   1. The CalendarView component now connects directly to Firebase"
echo "   2. No API calls to your backend - works independently"
echo "   3. Firebase configuration is built-in for emailpilot-438321 project"
echo ""
echo "🔹 Features Included:"
echo "   ✓ Direct Firebase Firestore integration"
echo "   ✓ Client management (create/read from Firebase 'clients' collection)"
echo "   ✓ Goals integration (reads from Firebase 'goals' collection)"
echo "   ✓ Campaign storage (stores in client documents)"
echo "   ✓ Real-time revenue goal progress tracking"
echo "   ✓ Campaign type color coding"
echo "   ✓ Month navigation"
echo "   ✓ Drag and drop (basic implementation)"
echo ""
echo "🔹 Firebase Collections Expected:"
echo "   • clients: { id, name, campaignData: {...}, lastModified }"
echo "   • goals: { client_id, revenue_goal, year, month, created_at }"
echo ""
echo "🔹 To use in your existing React app:"
echo "   1. Ensure Firebase is loaded in your main HTML"
echo "   2. The CalendarView component is now Firebase-native"
echo "   3. No backend API dependencies for calendar operations"
echo ""
echo "🔹 Test URLs:"
echo "   • Standalone: http://localhost:8080/calendar"
echo "   • In React: Import the updated CalendarView component"
echo ""
echo "🔐 Security Note: Firebase authentication is set to anonymous for testing"
echo "    Consider implementing proper auth for production use"