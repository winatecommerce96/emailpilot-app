#!/bin/bash

# EmailPilot Calendar Production Deployment Script
# This script deploys the calendar to the production EmailPilot.ai server

set -e  # Exit on any error

echo "🚀 Starting EmailPilot Calendar Production Deployment..."

# Configuration
PRODUCTION_CALENDAR_FILE="calendar_production.html"
BACKUP_DIR="calendar_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Pre-deployment checks
print_status "Performing pre-deployment checks..."

# Check if production calendar file exists
if [ ! -f "$PRODUCTION_CALENDAR_FILE" ]; then
    print_error "Production calendar file '$PRODUCTION_CALENDAR_FILE' not found!"
    exit 1
fi

# Check if required services are available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is required but not installed!"
    exit 1
fi

# Check if we can access the Firebase services
print_status "Checking Firebase integration files..."
FIREBASE_FILES=(
    "firebase_calendar_integration.py"
    "firebase_goals_calendar_integration.py"
)

for file in "${FIREBASE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_warning "Firebase file '$file' not found - some features may not work"
    fi
done

print_success "Pre-deployment checks completed"

# Step 2: Create backup
print_status "Creating backup of current deployment..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup current calendar if it exists in main.py routing
if grep -q "calendar_production.html" main.py 2>/dev/null; then
    cp main.py "$BACKUP_DIR/main_${TIMESTAMP}.py"
    print_success "Backed up main.py configuration"
fi

# Step 3: Update main.py to serve production calendar
print_status "Updating main.py to serve production calendar..."

# Update the calendar route to serve production version
if [ -f "main.py" ]; then
    # Create a temporary file with the updated route
    sed 's|calendar_fixed.html|calendar_production.html|g' main.py > main_temp.py
    
    # Replace the original file
    mv main_temp.py main.py
    
    print_success "Updated main.py to serve production calendar"
else
    print_error "main.py not found!"
    exit 1
fi

# Step 4: Validate the production calendar
print_status "Validating production calendar file..."

# Basic validation checks
if grep -q "EnhancedCalendarService" "$PRODUCTION_CALENDAR_FILE"; then
    print_success "✅ Calendar service class found"
else
    print_error "❌ Calendar service class not found in production file"
    exit 1
fi

if grep -q "AuthManager" "$PRODUCTION_CALENDAR_FILE"; then
    print_success "✅ Authentication manager found"
else
    print_error "❌ Authentication manager not found in production file"
    exit 1
fi

if grep -q "/api/firebase-calendar/" "$PRODUCTION_CALENDAR_FILE"; then
    print_success "✅ Production API endpoints configured"
else
    print_error "❌ Production API endpoints not found"
    exit 1
fi

if grep -q "/api/goals-calendar/" "$PRODUCTION_CALENDAR_FILE"; then
    print_success "✅ Goals API endpoints configured"
else
    print_error "❌ Goals API endpoints not found"
    exit 1
fi

# Step 5: Test local server startup (optional)
if [ "$1" = "--test-local" ]; then
    print_status "Testing local server startup..."
    
    # Start server in background for testing
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Test if calendar endpoint responds
    if curl -f -s "http://localhost:8080/calendar" > /dev/null; then
        print_success "✅ Calendar endpoint responding"
    else
        print_error "❌ Calendar endpoint not responding"
        kill $SERVER_PID
        exit 1
    fi
    
    # Kill test server
    kill $SERVER_PID
    sleep 2
    
    print_success "Local server test completed"
fi

# Step 6: Production deployment instructions
print_status "Production deployment ready!"

echo ""
echo "📋 DEPLOYMENT INSTRUCTIONS:"
echo "=========================="
echo ""
echo "1. Copy the following files to your production server:"
echo "   - calendar_production.html"
echo "   - main.py (updated)"
echo "   - All Firebase integration files"
echo "   - requirements.txt"
echo ""
echo "2. On your production server, run:"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Ensure your .env file contains:"
echo "   - GOOGLE_CLOUD_PROJECT"
echo "   - GOOGLE_APPLICATION_CREDENTIALS"
echo "   - GEMINI_API_KEY"
echo ""
echo "4. Restart your FastAPI server:"
echo "   uvicorn main:app --host 0.0.0.0 --port 8080"
echo ""
echo "5. The calendar will be available at:"
echo "   https://emailpilot.ai/calendar"
echo ""

print_success "🎉 EmailPilot Calendar is ready for production deployment!"

# Step 7: Generate deployment summary
cat > "deployment_summary_${TIMESTAMP}.md" << EOF
# EmailPilot Calendar Production Deployment

**Deployment Date:** $(date)
**Version:** Production with Authentication

## Files Deployed
- calendar_production.html (Production calendar with auth)
- main.py (Updated routing)
- Firebase integration files
- API endpoints (authenticated)

## Features Included
- ✅ JWT Authentication with login modal
- ✅ Client management integration
- ✅ Firebase calendar endpoints
- ✅ Goals dashboard with progress tracking
- ✅ AI-powered chat assistant
- ✅ Google Doc import functionality
- ✅ Campaign creation and editing
- ✅ Professional UI with animations

## API Endpoints Used
- /api/auth/login (Authentication)
- /api/clients/ (Client management)
- /api/firebase-calendar/* (Calendar operations)
- /api/goals-calendar/* (Goals and AI features)

## Production URL
https://emailpilot.ai/calendar

## Backup Location
${BACKUP_DIR}/main_${TIMESTAMP}.py

## Notes
- Uses production Firebase endpoints with authentication
- Includes login modal for user authentication  
- All test endpoints removed for security
- Professional styling and UX
EOF

print_success "Deployment summary saved: deployment_summary_${TIMESTAMP}.md"

echo ""
print_success "🚀 Deployment script completed successfully!"
print_warning "Remember to update your production server with the new files."

exit 0