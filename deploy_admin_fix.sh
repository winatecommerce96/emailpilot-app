#!/bin/bash

# Deploy Admin Fix for EmailPilot
# This script deploys the updated main_firestore.py with admin endpoints

set -e

echo "🚀 Deploying Admin Fix for EmailPilot..."
echo "======================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Project: $PROJECT_ID"
echo "📍 Region: us-central1"
echo ""

# Verify the admin router is included
echo "🔍 Verifying admin router inclusion..."
if grep -q "app.include_router(admin.router" main_firestore.py; then
    echo "✅ Admin router is included in main_firestore.py"
else
    echo "❌ Admin router not found in main_firestore.py"
    exit 1
fi

if grep -q "from app.api import admin" main_firestore.py; then
    echo "✅ Admin module is imported"
else
    echo "❌ Admin module import not found"
    exit 1
fi

echo ""
echo "📦 Building and deploying to Cloud Run..."
echo ""

# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml . || {
    echo "❌ Cloud Build failed"
    exit 1
}

# Get the service URL
SERVICE_URL=$(gcloud run services describe emailpilot-api --region=us-central1 --format='value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    echo "⚠️  Could not retrieve service URL. Checking alternate service name..."
    SERVICE_URL=$(gcloud run services describe emailpilot --region=us-central1 --format='value(status.url)' 2>/dev/null)
fi

echo ""
echo "✅ Deployment completed!"
echo "======================================"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📋 Test the admin endpoints:"
echo "  curl $SERVICE_URL/api/admin/health"
echo "  curl $SERVICE_URL/api/admin/environment"
echo ""
echo "🔧 Next Steps:"
echo "1. Clear browser cache or use incognito mode"
echo "2. Visit $SERVICE_URL"
echo "3. Login as admin user"
echo "4. Navigate to Admin → Environment Variables"
echo "5. Variables should now load correctly"
echo ""
echo "🎉 Admin endpoints have been deployed!"