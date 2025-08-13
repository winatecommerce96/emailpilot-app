#!/bin/bash
# Start EmailPilot server with OAuth configuration

echo "Starting EmailPilot server with OAuth..."

# Set required environment variables
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
export SECRET_MANAGER_TRANSPORT=rest
export ENVIRONMENT=development

# Activate virtual environment
source .venv/bin/activate

# Start the server
echo "Starting server on http://localhost:8000"
echo "OAuth login will be available at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""
uvicorn main_firestore:app --port 8000 --reload --log-level info