#!/bin/bash
# Restart EmailPilot application on Cloud Run

echo "🔄 Restarting EmailPilot Application..."
echo "===================================="

# Method 1: Update with a dummy environment variable to force new revision
TIMESTAMP=$(date +%s)
echo "📍 Creating new Cloud Run revision..."

gcloud run services update emailpilot-api \
    --region=us-central1 \
    --update-env-vars="RESTART_TIME=$TIMESTAMP" \
    --quiet

if [ $? -eq 0 ]; then
    echo "✅ Restart successful!"
    echo "🌐 The application is restarting at https://emailpilot.ai"
    echo "⏱️  Wait 30-60 seconds for the new revision to be ready"
else
    echo "❌ Restart failed"
    echo ""
    echo "Alternative methods:"
    echo "1. Deploy a new version: ./deploy.sh"
    echo "2. Use Cloud Console: https://console.cloud.google.com/run"
fi