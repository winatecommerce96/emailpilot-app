#!/bin/bash

# Email/SMS Multi-Agent MCP Server - Cloud Build Deployment Script
# Uses Google Cloud Build to build and deploy without local Docker

set -e

# Configuration
PROJECT_ID="emailpilot-438321"
SERVICE_NAME="email-sms-mcp-server"
REGION="us-central1"

echo "🚀 Deploying Email/SMS Multi-Agent MCP Server via Cloud Build"
echo "============================================================="
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""

# Ensure we're in the right project
echo "📋 Setting up Google Cloud configuration..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Submit build to Cloud Build
echo "🔨 Submitting build to Google Cloud Build..."
gcloud builds submit --config=cloudbuild.yaml .

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo ""
echo "✅ Deployment Complete!"
echo "============================================================="
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
echo ""
echo "🔍 Run comprehensive tests:"
echo "python test_cloud_deployment.py ${SERVICE_URL}"