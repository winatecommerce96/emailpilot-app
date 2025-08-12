#!/bin/bash

# Quick deployment script for EmailPilot Calendar Feature
# Run this from the emailpilot-app directory where Dockerfile exists

echo "🚀 Deploying EmailPilot Calendar Feature to Cloud Run..."

# Set variables
export PROJECT_ID=emailpilot-438321
export REGION=us-central1
export SERVICE=emailpilot-api
export TAG=calendar-$(date +%Y%m%d-%H%M%S)

# Ensure we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found. Please run from emailpilot-app directory"
    exit 1
fi

# Check if calendar.py exists
if [ ! -f "app/api/calendar.py" ]; then
    echo "❌ Error: app/api/calendar.py not found"
    exit 1
fi

# Check if calendar router is wired in main_firestore.py
if ! grep -q "calendar_router" main_firestore.py; then
    echo "⚠️  Warning: Calendar router not found in main_firestore.py"
    echo "Adding calendar router..."
    
    # Add import if not present
    if ! grep -q "from app.api.calendar import router as calendar_router" main_firestore.py; then
        sed -i '25a\\n# Import calendar router\nfrom app.api.calendar import router as calendar_router' main_firestore.py
    fi
    
    # Add router registration if not present
    if ! grep -q 'app.include_router(calendar_router' main_firestore.py; then
        sed -i '/# Include admin router/a\\n# Include calendar router\napp.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])' main_firestore.py
    fi
    
    echo "✅ Calendar router added to main_firestore.py"
fi

echo "📦 Building and submitting to Cloud Build..."

# Build and submit
gcloud builds submit \
    --project $PROJECT_ID \
    --tag gcr.io/$PROJECT_ID/$SERVICE:$TAG \
    --timeout=20m

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "🚢 Deploying to Cloud Run..."

# Deploy
gcloud run deploy $SERVICE \
    --region $REGION \
    --image gcr.io/$PROJECT_ID/$SERVICE:$TAG \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --port 8000

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE \
    --region=$REGION \
    --format="value(status.url)")

echo ""
echo "✅ Calendar Feature Deployed Successfully!"
echo "=================================================="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Calendar API Endpoints:"
echo "  • Health: $SERVICE_URL/api/calendar/health"
echo "  • Events: $SERVICE_URL/api/calendar/events"
echo "  • Clients: $SERVICE_URL/api/calendar/clients"
echo "  • Goals: $SERVICE_URL/api/calendar/goals/{client_id}"
echo "  • Dashboard: $SERVICE_URL/api/calendar/dashboard/{client_id}"
echo ""
echo "Test with:"
echo "  curl $SERVICE_URL/api/calendar/health"
echo ""
echo "View logs:"
echo "  gcloud run logs read --service=$SERVICE --region=$REGION --limit=50"