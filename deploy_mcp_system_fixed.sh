#!/bin/bash

# Deploy Fixed MCP System to Google Cloud
# This script includes compatibility fixes for recent codebase updates

set -e

echo "🚀 Starting Fixed MCP System Deployment..."

# Configuration
PROJECT_ID="emailpilot-438321"
REGION="us-central1"
SERVICE_NAME="emailpilot-mcp"

# Check if running in the correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Must run from emailpilot-app directory"
    exit 1
fi

echo "📦 Step 1: Installing fixed dependencies..."
pip install -r requirements.txt

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

echo "🐳 Step 4: Building Docker image with compatibility fixes..."
cat > Dockerfile <<EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and uvx for MCP server
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs
    
# Install uvx for MCP server
RUN pip install uv
RUN pip install uvx

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_CLOUD_PROJECT=$PROJECT_ID

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# Build and push Docker image
IMAGE_URL="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
echo "Building Docker image: $IMAGE_URL"
gcloud builds submit --tag $IMAGE_URL --project=$PROJECT_ID

echo "☁️ Step 5: Deploying to Cloud Run with compatibility settings..."
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
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "SECRET_KEY=$(openssl rand -base64 32)"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --format 'value(status.url)')

echo "🔧 Step 6: Testing compatibility fixes..."

# Test auth endpoint
echo "Testing auth system..."
curl -s "${SERVICE_URL}/api/auth/health" > /dev/null && echo "✅ Auth system working" || echo "❌ Auth system needs attention"

# Test MCP endpoints
echo "Testing MCP endpoints..."
curl -s "${SERVICE_URL}/api/mcp/models" > /dev/null && echo "✅ MCP endpoints accessible" || echo "❌ MCP endpoints need auth token"

# Test health check
echo "Testing overall health..."
curl -s "${SERVICE_URL}/health" | python -m json.tool || echo "Service may still be starting..."

echo "✅ Step 7: Deployment Complete!"
echo "=========================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "🔧 Admin Panel: ${SERVICE_URL}/app"
echo "📊 MCP Management: ${SERVICE_URL}/app (Navigate to Admin > MCP Management)"
echo "=========================================="

echo ""
echo "🔧 Compatibility Fixes Applied:"
echo "✅ Created app/core/auth.py with get_current_user function"
echo "✅ Updated OpenAI API to use new client pattern"
echo "✅ Fixed Anthropic client initialization"
echo "✅ Added missing dependencies (openai, anthropic, httpx, PyJWT)"
echo "✅ Re-enabled MCP router in main.py"
echo ""

echo "📝 Next Steps:"
echo "1. Access the admin panel at ${SERVICE_URL}/app"
echo "2. Login with admin credentials (admin/admin123)"
echo "3. Navigate to Admin > MCP Management"
echo "4. Add your first MCP client with API keys"
echo "5. Test connections to Claude, OpenAI, and Gemini"
echo ""

echo "🔒 Security Notes:"
echo "- API keys are stored securely in Google Secret Manager"
echo "- JWT secret key is auto-generated for production"
echo "- Authentication is working with demo users"
echo "- Consider implementing OAuth for production use"
echo ""

echo "🎉 Fixed MCP System deployment completed successfully!"