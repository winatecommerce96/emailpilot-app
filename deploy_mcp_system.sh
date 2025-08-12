#!/bin/bash

# Deploy MCP System to Google Cloud
# This script sets up the complete MCP management system

set -e

echo "🚀 Starting MCP System Deployment..."

# Configuration
PROJECT_ID="emailpilot-438321"
REGION="us-central1"
SERVICE_NAME="emailpilot-mcp"

# Check if running in the correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Must run from emailpilot-app directory"
    exit 1
fi

echo "📦 Step 1: Installing dependencies..."
pip install -r requirements.txt 2>/dev/null || true
pip install google-cloud-secret-manager anthropic openai google-generativeai 2>/dev/null || true

echo "🗄️ Step 2: Creating MCP database tables..."
python migrate_mcp_tables.py

echo "🔐 Step 3: Setting up Google Secret Manager..."
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create service account for MCP if not exists
SA_NAME="mcp-service-account"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create $SA_NAME \
        --display-name="MCP Service Account" \
        --project=$PROJECT_ID
fi

# Grant necessary permissions
echo "Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretVersionManager" \
    --quiet

echo "🐳 Step 4: Building Docker image..."
cat > Dockerfile <<EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir google-cloud-secret-manager anthropic openai google-generativeai

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_CLOUD_PROJECT=$PROJECT_ID

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# Build and push Docker image
IMAGE_URL="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
echo "Building Docker image: $IMAGE_URL"
gcloud builds submit --tag $IMAGE_URL --project=$PROJECT_ID

echo "☁️ Step 5: Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_URL \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --service-account $SA_EMAIL \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "ENVIRONMENT=production"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --format 'value(status.url)')

echo "✅ Step 6: Deployment Complete!"
echo "=========================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "🔧 Admin Panel: ${SERVICE_URL}/app"
echo "📊 MCP Management: ${SERVICE_URL}/app (Navigate to Admin > MCP Management)"
echo "=========================================="

echo ""
echo "📝 Next Steps:"
echo "1. Access the admin panel at ${SERVICE_URL}/app"
echo "2. Login with admin credentials"
echo "3. Navigate to Admin > MCP Management"
echo "4. Add your first MCP client with API keys"
echo "5. Test connections to Claude, OpenAI, and Gemini"
echo ""
echo "🔒 Security Notes:"
echo "- API keys are stored securely in Google Secret Manager"
echo "- Enable authentication for production use"
echo "- Configure custom domain if needed"
echo ""

# Optional: Run a health check
echo "🏥 Running health check..."
curl -s "${SERVICE_URL}/health" | python -m json.tool || echo "Health check failed - service may still be starting"

echo ""
echo "🎉 MCP System deployment completed successfully!"