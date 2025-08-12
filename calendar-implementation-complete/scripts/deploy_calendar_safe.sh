#!/bin/bash
# Safe deployment script for Calendar Tab Integration to EmailPilot.ai
# This version does NOT install dependencies to avoid conflicts

echo "🚀 Deploying Calendar Tab Integration to EmailPilot.ai (Safe Mode)"
echo "=================================================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
EMAILPILOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "📍 Script directory: $SCRIPT_DIR"
echo "📍 EmailPilot directory: $EMAILPILOT_DIR"

# Step 1: Copy frontend calendar components
echo ""
echo "📦 Copying frontend calendar components..."
if [ -d "frontend/calendar" ]; then
    # Create components directory if it doesn't exist
    mkdir -p "$EMAILPILOT_DIR/frontend/public/components"
    
    # Copy calendar components
    cp frontend/calendar/*.js "$EMAILPILOT_DIR/frontend/public/components/" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Frontend components copied successfully"
    else
        echo "⚠️  No frontend components found to copy"
    fi
else
    echo "⚠️  No frontend/calendar directory found"
fi

# Step 2: Copy API endpoints (but don't overwrite main.py)
echo ""
echo "📦 Preparing API endpoints for manual integration..."
if [ -d "api" ]; then
    # Create a calendar_api directory for the new endpoints
    mkdir -p "$EMAILPILOT_DIR/calendar_api"
    
    # Copy API files for reference
    cp -r api/* "$EMAILPILOT_DIR/calendar_api/" 2>/dev/null
    
    echo "✅ API endpoints copied to calendar_api/ for manual integration"
    echo "   You'll need to manually integrate these into main_firestore.py"
else
    echo "⚠️  No api directory found"
fi

# Step 3: Create integration instructions
echo ""
echo "📄 Creating integration instructions..."
cat > "$EMAILPILOT_DIR/CALENDAR_INTEGRATION_INSTRUCTIONS.md" << 'EOF'
# Calendar Tab Integration Instructions

## Frontend Integration

The calendar components have been copied to `frontend/public/components/`. 

To integrate them:

1. Update `frontend/public/index.html` to include the calendar scripts (already done)
2. In your main app.js, add the Calendar tab to your navigation

## Backend Integration

The calendar API endpoints are in `calendar_api/` directory.

To integrate them:

1. Review the endpoints in `calendar_api/`
2. Add the necessary endpoints to `main_firestore.py`
3. Ensure you're using the existing Firestore client, not creating new connections

## Important Notes

- Do NOT install the calendar package's requirements.txt
- Use the existing EmailPilot dependencies
- The calendar functionality should use the existing Firestore connection
- Test thoroughly before deploying

## Environment Variables

Make sure these are set in your Cloud Run environment:
- GOOGLE_CLOUD_PROJECT
- Any API keys for Gemini AI (if using chat features)

EOF

echo "✅ Integration instructions created"

# Step 4: List what needs manual integration
echo ""
echo "📋 MANUAL INTEGRATION REQUIRED:"
echo "================================"
echo ""
echo "1. Frontend files have been copied to: frontend/public/components/"
echo "2. API endpoints are available in: calendar_api/"
echo "3. Read CALENDAR_INTEGRATION_INSTRUCTIONS.md for detailed steps"
echo ""
echo "⚠️  IMPORTANT: Do NOT run 'pip install' from the calendar package!"
echo "⚠️  Use EmailPilot's existing dependencies to avoid conflicts"
echo ""
echo "🔧 Next Steps:"
echo "1. Manually review and integrate the calendar API endpoints"
echo "2. Test the calendar functionality locally"
echo "3. Deploy using the standard EmailPilot deployment process"
echo ""
echo "✅ Safe deployment preparation complete!"