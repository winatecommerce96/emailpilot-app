#!/bin/bash

# MCP Management Deployment Script for EmailPilot
# Deploys MCP Management System to Google Cloud Run

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 MCP Management - Cloud Run Deployment"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Configuration
PROJECT_ID="emailpilot-438321"
SERVICE_NAME="emailpilot-app"
REGION="us-central1"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "📋 Deployment Configuration:"
echo "  • Project: $PROJECT_ID"
echo "  • Service: $SERVICE_NAME"
echo "  • Region: $REGION"
echo "  • Timestamp: $TIMESTAMP"
echo ""

# Step 1: Check if we're in the right directory
if [ ! -f "main_firestore.py" ]; then
    echo "❌ Error: main_firestore.py not found. Please run this script from the emailpilot-app directory."
    exit 1
fi

echo "✅ Directory check passed"
echo ""

# Step 2: Ensure MCP files are in place
echo "📝 Checking MCP files..."

if [ ! -f "app/api/mcp_local.py" ]; then
    echo "❌ Error: app/api/mcp_local.py not found"
    exit 1
fi

if [ ! -f "frontend/public/components/MCPManagementLocal.js" ]; then
    echo "❌ Error: frontend/public/components/MCPManagementLocal.js not found"
    exit 1
fi

echo "✅ All MCP files present"
echo ""

# Step 3: Test local deployment first
echo "🧪 Testing local deployment..."
if curl -s http://127.0.0.1:8000/api/mcp/health > /dev/null 2>&1; then
    echo "✅ Local MCP API is working"
else
    echo "⚠️  Warning: Local MCP API not responding. Make sure the dev server is running."
fi
echo ""

# Step 4: Build and deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
echo ""

# Use Cloud Build to deploy directly from source
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 10 \
    --set-env-vars "PROJECT_ID=$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="value(status.url)")
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ MCP Management System Deployed!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📋 Deployment Summary:"
    echo "  • Service: $SERVICE_NAME"
    echo "  • Region: $REGION"
    echo "  • URL: $SERVICE_URL"
    echo ""
    echo "🌐 Access your app at: $SERVICE_URL"
    echo "   The MCP Management button will appear in the top-right corner"
    echo ""
    echo "📝 Test the MCP endpoints:"
    echo "   curl $SERVICE_URL/api/mcp/health"
    echo "   curl $SERVICE_URL/api/mcp/models"
    echo "   curl $SERVICE_URL/api/mcp/clients"
    echo ""
else
    echo ""
    echo "❌ Deployment failed. Please check the error messages above."
    echo ""
    echo "Common issues:"
    echo "  1. Authentication: Run 'gcloud auth login'"
    echo "  2. Project: Run 'gcloud config set project $PROJECT_ID'"
    echo "  3. APIs: Enable Cloud Run API and Cloud Build API"
    exit 1
fi