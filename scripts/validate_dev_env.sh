#!/bin/bash

# EmailPilot Development Environment Validator
# Checks that all required tools and configurations are present

set -e

echo "🔍 EmailPilot Development Environment Validator"
echo "=============================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track issues
ISSUES_FOUND=0

# Function to check command availability
check_command() {
    local cmd=$1
    local desc=$2
    local install_hint=$3
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "✅ ${GREEN}$desc${NC} - Found: $(command -v $cmd)"
    else
        echo -e "❌ ${RED}$desc${NC} - Not found"
        if [ -n "$install_hint" ]; then
            echo -e "   💡 Install with: ${YELLOW}$install_hint${NC}"
        fi
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
}

# Function to check file existence
check_file() {
    local file=$1
    local desc=$2
    local optional=$3
    
    if [ -f "$file" ]; then
        echo -e "✅ ${GREEN}$desc${NC} - Found: $file"
    else
        if [ "$optional" = "optional" ]; then
            echo -e "⚠️  ${YELLOW}$desc${NC} - Not found (optional): $file"
        else
            echo -e "❌ ${RED}$desc${NC} - Not found: $file"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    fi
}

# Function to check directory existence
check_directory() {
    local dir=$1
    local desc=$2
    
    if [ -d "$dir" ]; then
        echo -e "✅ ${GREEN}$desc${NC} - Found: $dir"
    else
        echo -e "❌ ${RED}$desc${NC} - Not found: $dir"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
}

# Check if we're in the right directory
echo "📍 Checking project structure..."
check_file "main_firestore.py" "Main application file"
check_file "requirements.txt" "Python requirements"
check_file "Makefile" "Development Makefile"
check_directory "app" "Application directory"
check_directory "frontend/public" "Frontend directory"
echo ""

# Check Python and dependencies
echo "🐍 Checking Python environment..."
check_command "python3" "Python 3" "brew install python3"
check_command "pip" "pip package manager" "python3 -m ensurepip"

# Check if virtual environment is active
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "✅ ${GREEN}Virtual environment${NC} - Active: $VIRTUAL_ENV"
else
    echo -e "⚠️  ${YELLOW}Virtual environment${NC} - Not active (recommended for development)"
    echo -e "   💡 Create and activate with: ${YELLOW}python3 -m venv venv && source venv/bin/activate${NC}"
fi

# Check if required Python packages are available
echo ""
echo "📦 Checking Python dependencies..."
if python3 -c "import fastapi" 2>/dev/null; then
    echo -e "✅ ${GREEN}FastAPI${NC} - Available"
else
    echo -e "❌ ${RED}FastAPI${NC} - Not available"
    echo -e "   💡 Install with: ${YELLOW}make install${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

if python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "✅ ${GREEN}Uvicorn${NC} - Available"
else
    echo -e "❌ ${RED}Uvicorn${NC} - Not available"
    echo -e "   💡 Install with: ${YELLOW}make install${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi
echo ""

# Check Google Cloud tools (optional)
echo "☁️  Checking Google Cloud tools..."
check_command "gcloud" "Google Cloud CLI" "brew install google-cloud-sdk" "optional"

if command -v gcloud &> /dev/null; then
    # Check if logged in
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "✅ ${GREEN}gcloud authentication${NC} - Logged in"
    else
        echo -e "⚠️  ${YELLOW}gcloud authentication${NC} - Not logged in"
        echo -e "   💡 Login with: ${YELLOW}gcloud auth login${NC}"
    fi
    
    # Check project
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -n "$PROJECT_ID" ]; then
        echo -e "✅ ${GREEN}gcloud project${NC} - Set: $PROJECT_ID"
    else
        echo -e "⚠️  ${YELLOW}gcloud project${NC} - Not set"
        echo -e "   💡 Set with: ${YELLOW}gcloud config set project YOUR_PROJECT_ID${NC}"
    fi
fi
echo ""

# Check Node.js tools (for frontend building)
echo "📦 Checking Node.js tools..."
check_command "node" "Node.js" "brew install node"
check_command "npm" "npm package manager" "brew install node"
echo ""

# Check configuration files
echo "⚙️  Checking configuration files..."
check_file ".env" "Environment variables" "optional"
check_file ".env.template" "Environment template"
check_file "frontend/public/index.html" "Frontend HTML"
echo ""

# Check port availability
echo "🔌 Checking port availability..."
if lsof -i :8000 &> /dev/null; then
    echo -e "⚠️  ${YELLOW}Port 8000${NC} - In use (may need to stop existing server)"
    echo -e "   💡 Stop with: ${YELLOW}make kill-port${NC}"
else
    echo -e "✅ ${GREEN}Port 8000${NC} - Available"
fi

if lsof -i :8080 &> /dev/null; then
    echo -e "⚠️  ${YELLOW}Port 8080${NC} - In use (Firestore emulator port)"
else
    echo -e "✅ ${GREEN}Port 8080${NC} - Available for Firestore emulator"
fi
echo ""

# Summary
echo "📋 Summary"
echo "=========="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "🎉 ${GREEN}All checks passed!${NC} Your development environment is ready."
    echo ""
    echo "🚀 Quick start commands:"
    echo -e "   ${YELLOW}make setup${NC}      - Install dependencies and start development server"
    echo -e "   ${YELLOW}make setup-emu${NC}  - Install dependencies and start with Firestore emulator"
    echo -e "   ${YELLOW}make help${NC}       - Show all available commands"
else
    echo -e "⚠️  ${YELLOW}Found $ISSUES_FOUND issue(s)${NC} that should be resolved for optimal development."
    echo ""
    echo "🔧 Recommended fixes:"
    echo -e "   ${YELLOW}make install${NC}    - Install Python dependencies"
    echo -e "   ${YELLOW}make install-dev${NC} - Install development dependencies"
fi

echo ""
echo "📖 For more help, run: make help"