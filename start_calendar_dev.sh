#!/bin/bash

# EmailPilot Calendar - Local Development Startup Script
# This script starts the FastAPI server and opens the calendar

echo "🚀 Starting EmailPilot Calendar Development Environment"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo -e "${YELLOW}⚠️  uvicorn not found. Installing...${NC}"
    pip install uvicorn
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import fastapi" 2>/dev/null || pip install fastapi
python -c "import firebase_admin" 2>/dev/null || pip install firebase-admin
python -c "import google.cloud.firestore" 2>/dev/null || pip install google-cloud-firestore

# Kill any existing uvicorn process on port 8000
echo "🔄 Checking for existing server..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "Stopped existing server" || echo "No existing server found"

# Start the server in background
echo -e "${BLUE}🖥️  Starting FastAPI server...${NC}"
uvicorn app.main:app --reload --port 8000 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 3

# Check if server is running
if curl -s http://127.0.0.1:8000/api/calendar/health > /dev/null; then
    echo -e "${GREEN}✅ Server started successfully!${NC}"
    
    # Run tests
    echo ""
    echo "🧪 Running API tests..."
    python test_calendar_local.py
    
    echo ""
    echo "=================================================="
    echo -e "${GREEN}✨ Calendar Development Environment Ready!${NC}"
    echo "=================================================="
    echo ""
    echo "📅 Calendar UI: http://127.0.0.1:8000/calendar"
    echo "📚 API Docs: http://127.0.0.1:8000/docs#/Calendar"
    echo "🔍 Health Check: http://127.0.0.1:8000/api/calendar/health"
    echo ""
    echo "Server PID: $SERVER_PID"
    echo "To stop: kill $SERVER_PID or press Ctrl+C"
    echo ""
    
    # Open browser (works on macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "🌐 Opening calendar in browser..."
        open http://127.0.0.1:8000/calendar
    else
        echo "🌐 Open in browser: http://127.0.0.1:8000/calendar"
    fi
    
    # Keep script running and show logs
    echo ""
    echo "📋 Server logs:"
    echo "=================================================="
    
    # Bring uvicorn to foreground
    wait $SERVER_PID
else
    echo -e "${YELLOW}⚠️  Server failed to start${NC}"
    echo "Check the error messages above"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi