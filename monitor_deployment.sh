#!/bin/bash

# Monitor Cloud Run deployment
# Usage: ./monitor_deployment.sh

SERVICE="emailpilot-app"
REGION="us-central1"
URL="https://emailpilot-app-p3cxgvcsla-uc.a.run.app"

echo "🔍 Monitoring deployment of $SERVICE..."
echo "📍 Region: $REGION"
echo "🌐 URL: $URL"
echo ""

# Get initial revision
INITIAL_REVISION=$(curl -s ${URL}/health | jq -r '.revision' 2>/dev/null || echo "unknown")
echo "📦 Current revision: $INITIAL_REVISION"
echo ""
echo "Checking for new deployment every 30 seconds..."
echo "Press Ctrl+C to stop monitoring"
echo ""

COUNTER=0
while true; do
    COUNTER=$((COUNTER + 1))

    # Get latest revision from Cloud Run
    LATEST=$(gcloud run revisions list \
        --service $SERVICE \
        --region $REGION \
        --limit 1 \
        --format="value(metadata.name)" 2>/dev/null)

    # Check health endpoint
    CURRENT=$(curl -s ${URL}/health 2>/dev/null | jq -r '.revision' 2>/dev/null || echo "unknown")

    TIMESTAMP=$(date '+%H:%M:%S')
    echo "[$TIMESTAMP] Check #$COUNTER - Latest: $LATEST | Serving: $CURRENT"

    # Check if deployment completed
    if [ "$CURRENT" != "$INITIAL_REVISION" ] && [ "$CURRENT" != "unknown" ]; then
        echo ""
        echo "✅ NEW DEPLOYMENT DETECTED!"
        echo "🎉 Old revision: $INITIAL_REVISION"
        echo "🎉 New revision: $CURRENT"
        echo ""
        echo "🏥 Running health checks..."

        # Health check
        HEALTH=$(curl -s ${URL}/health)
        echo "Health: $HEALTH"

        # Try calendar endpoint
        CALENDAR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${URL}/static/calendar_master.html)
        echo "Calendar page status: $CALENDAR_STATUS"

        if [ "$CALENDAR_STATUS" = "200" ]; then
            echo "✅ Calendar page accessible!"
        else
            echo "⚠️  Calendar page returned: $CALENDAR_STATUS"
        fi

        echo ""
        echo "🎊 Deployment verification complete!"
        break
    fi

    sleep 30
done
