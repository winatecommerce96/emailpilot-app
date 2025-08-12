#!/bin/bash

# EmailPilot Startup Verification Script
# Ensures we're running the correct implementation and not old calendar code

set -e

echo "🔍 EmailPilot Startup Verification"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check current directory
CURRENT_DIR=$(pwd)
EXPECTED_DIR="emailpilot-app"

if [[ ! "$CURRENT_DIR" == *"$EXPECTED_DIR"* ]]; then
    echo -e "${RED}❌ ERROR: Not in emailpilot-app directory!${NC}"
    echo -e "${RED}   Current: $CURRENT_DIR${NC}"
    echo -e "${YELLOW}   Please cd to /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/${NC}"
    exit 1
fi

# Check for correct main file
if [ ! -f "main_firestore.py" ]; then
    echo -e "${RED}❌ ERROR: main_firestore.py not found!${NC}"
    echo -e "${YELLOW}   This is the correct EmailPilot implementation file.${NC}"
    exit 1
fi

# Check for old calendar-project directory
if [ -d "calendar-project" ]; then
    echo -e "${YELLOW}⚠️  Warning: Old calendar-project directory found${NC}"
    echo -e "${YELLOW}   Run ./archive_old_calendars.sh to archive it${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if server is already running on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    echo "   Current process:"
    lsof -i:8000 | grep LISTEN
    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Killing existing process..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo -e "${RED}Cannot start: Port 8000 is occupied${NC}"
        exit 1
    fi
fi

# Verify required files exist
echo -e "${GREEN}✅ Checking required files...${NC}"

REQUIRED_FILES=(
    "main_firestore.py"
    "frontend/public/index.html"
    "app/api/calendar.py"
    "requirements.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ✓ $file"
    else
        echo -e "${YELLOW}   ⚠️  Missing: $file${NC}"
    fi
done

# Check Python environment
echo -e "${GREEN}✅ Checking Python environment...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "   ✓ $PYTHON_VERSION"
else
    echo -e "${RED}   ❌ Python 3 not found${NC}"
    exit 1
fi

# Check if uvicorn is installed
if python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "   ✓ uvicorn installed"
else
    echo -e "${YELLOW}   ⚠️  uvicorn not found, installing...${NC}"
    pip install uvicorn
fi

# All checks passed
echo ""
echo -e "${GREEN}🎉 All verification checks passed!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo "Starting EmailPilot with the correct implementation..."
echo "Using: main_firestore.py"
echo "Port: 8000"
echo ""

# Start the server
echo -e "${GREEN}🚀 Starting server...${NC}"
uvicorn main_firestore:app --reload --port 8000 --host 127.0.0.1