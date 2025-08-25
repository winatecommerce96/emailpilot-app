#!/bin/bash

# EmailPilot Copywriting Module Startup Script
# Runs on port 8002 (separate from main app on 8000)

echo "Starting EmailPilot Copywriting Module..."
echo "=================================="
echo "Module will run on: http://localhost:8002"
echo "Main app expected at: http://localhost:8000"
echo ""

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Google Cloud Project if not already set
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    export GOOGLE_CLOUD_PROJECT="emailpilot-438321"
    echo "Setting GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
fi

# Check MCP_ENABLED flag
if [ -z "$MCP_ENABLED" ]; then
    export MCP_ENABLED="false"
fi
echo "MCP_ENABLED=$MCP_ENABLED"

# Check for AI provider keys
echo ""
echo "Checking AI Provider Configuration:"
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "✓ OpenAI API key found"
fi
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo "✓ Anthropic API key found"
fi
if [ ! -z "$GOOGLE_API_KEY" ] || [ ! -z "$GEMINI_API_KEY" ]; then
    echo "✓ Google/Gemini API key found"
fi
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Start the copywriting module
echo ""
echo "Starting Copywriting Module on port 8002..."
echo "Access the module at: http://localhost:8002"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Run the FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8002 --reload