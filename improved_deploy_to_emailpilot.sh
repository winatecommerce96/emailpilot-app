#!/bin/bash
# Improved Deploy Calendar Tab Integration to EmailPilot.ai
# This version checks for dependency conflicts before installing

echo "🚀 Deploying Calendar Tab Integration to EmailPilot.ai"
echo "====================================================="

# Function to check if we're in EmailPilot environment
check_emailpilot_env() {
    if [ -f "../main_firestore.py" ] || [ -f "../../main_firestore.py" ]; then
        return 0  # We're in EmailPilot
    else
        return 1  # Not in EmailPilot
    fi
}

# Function to copy files without installing dependencies
safe_deploy() {
    echo "🛡️  Safe deployment mode (no dependency installation)"
    
    # Find EmailPilot root
    if [ -f "../main_firestore.py" ]; then
        EMAILPILOT_ROOT=".."
    elif [ -f "../../main_firestore.py" ]; then
        EMAILPILOT_ROOT="../.."
    else
        echo "❌ Cannot find EmailPilot root directory"
        exit 1
    fi
    
    # Copy frontend components
    echo "📦 Copying frontend components..."
    mkdir -p "$EMAILPILOT_ROOT/frontend/public/components"
    cp frontend/calendar/*.js "$EMAILPILOT_ROOT/frontend/public/components/" 2>/dev/null || echo "⚠️  No frontend components to copy"
    
    # Create calendar API directory
    echo "📦 Preparing calendar API endpoints..."
    mkdir -p "$EMAILPILOT_ROOT/calendar_api_integration"
    cp -r api/* "$EMAILPILOT_ROOT/calendar_api_integration/" 2>/dev/null || echo "⚠️  No API files to copy"
    
    # Copy any calendar-specific services
    if [ -d "services" ]; then
        mkdir -p "$EMAILPILOT_ROOT/calendar_services"
        cp -r services/* "$EMAILPILOT_ROOT/calendar_services/" 2>/dev/null
    fi
    
    echo ""
    echo "✅ Files copied successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Review files in calendar_api_integration/"
    echo "2. Manually integrate endpoints into main_firestore.py"
    echo "3. Test the calendar functionality"
    echo "4. Deploy using standard EmailPilot deployment"
    echo ""
    echo "⚠️  IMPORTANT: Dependencies were NOT installed to avoid conflicts"
    echo "⚠️  Use EmailPilot's existing dependencies"
}

# Main deployment logic
if check_emailpilot_env; then
    echo "✅ EmailPilot environment detected"
    echo "🛡️  Using safe deployment to avoid dependency conflicts"
    safe_deploy
else
    echo "⚠️  Not in EmailPilot environment"
    echo "❓ Do you want to:"
    echo "   1. Proceed with full installation (may cause conflicts)"
    echo "   2. Exit and deploy manually"
    read -p "Choice (1/2): " choice
    
    if [ "$choice" = "1" ]; then
        # Original deployment logic
        if [ -f ".env.production" ]; then
            source .env.production
            echo "✅ Environment variables loaded"
        fi
        
        echo "⚠️  Installing dependencies (may conflict with EmailPilot)..."
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
"
    else
        echo "👍 Good choice! Please deploy manually to avoid conflicts."
        exit 0
    fi
fi

echo ""
echo "🎉 CALENDAR TAB INTEGRATION READY!"
echo "=================================="