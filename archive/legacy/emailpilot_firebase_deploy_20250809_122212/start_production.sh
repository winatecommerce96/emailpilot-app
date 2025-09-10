#!/bin/bash
# Load environment variables
source .env.production

# Install dependencies
pip install -r requirements.txt

echo "🔥 Starting EmailPilot with Firebase Calendar"
echo "📍 Server will be available at https://emailpilot.ai"
echo "🎯 Calendar endpoints: /api/firebase-calendar/*"

# Start with gunicorn for production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8080 --timeout 120
