#!/bin/bash

# EmailPilot Deployment Script
# Run this to deploy EmailPilot to Google Cloud Run

set -e

echo "🚀 Deploying EmailPilot to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged into gcloud. Run: gcloud auth login"
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

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy using Cloud Build
echo "🏗️  Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Get the service URL
SERVICE_URL=$(gcloud run services describe emailpilot-api --region=us-central1 --format='value(status.url)')

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📋 API Documentation: $SERVICE_URL/docs"
echo "🩺 Health Check: $SERVICE_URL/health"
echo ""
echo "🔧 Next Steps:"
echo "1. Set up your domain: gcloud run domain-mappings create --service emailpilot-api --domain emailpilot.ai"
echo "2. Configure environment variables for production"
echo "3. Set up Cloud SQL database"
echo "4. Configure Slack webhooks to point to: $SERVICE_URL/api/slack/"
echo ""
echo "🎉 EmailPilot is now live!"