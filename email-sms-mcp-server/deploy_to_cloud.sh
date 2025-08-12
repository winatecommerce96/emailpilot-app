#!/bin/bash

# Email/SMS Multi-Agent MCP Server - Cloud Deployment Script
# Deploys to Google Cloud Run in EmailPilot.ai project

set -e

# Configuration
PROJECT_ID="emailpilot-438321"
SERVICE_NAME="email-sms-mcp-server"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Email/SMS Multi-Agent MCP Server to Cloud Run"
echo "=================================================="
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""

# Ensure we're in the right project
echo "📋 Setting up Google Cloud configuration..."
gcloud config set project ${PROJECT_ID}

# Build and push Docker image
echo "🔨 Building Docker image..."
docker build -t ${IMAGE_NAME}:latest .

echo "📤 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 1000 \
    --timeout 300 \
    --port 8080 \
    --set-env-vars="ENVIRONMENT=production"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "=================================================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "MCP Server Endpoints:"
echo "- Health Check: ${SERVICE_URL}/health"
echo "- List Tools: ${SERVICE_URL}/mcp/list_tools"
echo "- List Resources: ${SERVICE_URL}/mcp/list_resources"
echo ""
echo "EmailPilot API Endpoints:"
echo "- Create Email Campaign: ${SERVICE_URL}/api/campaign/email"
echo "- Create SMS Campaign: ${SERVICE_URL}/api/campaign/sms" 
echo "- List Agents: ${SERVICE_URL}/api/agents"
echo ""
echo "📋 To configure in Claude Code:"
echo "claude mcp add email-sms-agents --transport http ${SERVICE_URL}"
echo ""
echo "🧪 Test the deployment:"
echo "curl ${SERVICE_URL}/health"