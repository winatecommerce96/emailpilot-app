#!/bin/bash

# EmailPilot Deployment Script with Secret Manager Integration
# This script migrates secrets to Google Secret Manager and deploys to Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="emailpilot-438321"
REGION="us-central1"
SERVICE_NAME="emailpilot-api"

echo -e "${GREEN}EmailPilot Secret Manager Migration & Deployment Script${NC}"
echo "======================================================="

# Check if gcloud is configured
if ! gcloud config get-value project > /dev/null 2>&1; then
    echo -e "${RED}Error: gcloud is not configured. Please run 'gcloud init' first.${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable secretmanager.googleapis.com cloudbuild.googleapis.com run.googleapis.com

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    # Check if secret exists
    if gcloud secrets describe ${secret_name} --project=${PROJECT_ID} > /dev/null 2>&1; then
        echo -e "${YELLOW}Updating secret: ${secret_name}${NC}"
        echo -n "${secret_value}" | gcloud secrets versions add ${secret_name} --data-file=- --project=${PROJECT_ID}
    else
        echo -e "${GREEN}Creating secret: ${secret_name}${NC}"
        echo -n "${secret_value}" | gcloud secrets create ${secret_name} \
            --data-file=- \
            --replication-policy="automatic" \
            --labels="app=emailpilot,type=config" \
            --project=${PROJECT_ID}
    fi
}

# Check if .env file exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Found .env file. Reading configuration...${NC}"
    
    # Load .env file
    set -a
    source .env
    set +a
    
    # Migrate secrets to Secret Manager
    echo -e "${GREEN}Migrating secrets to Google Secret Manager...${NC}"
    
    # Database URL
    if [ ! -z "$DATABASE_URL" ]; then
        create_or_update_secret "emailpilot-database-url" "$DATABASE_URL"
    fi
    
    # Secret Key
    if [ ! -z "$SECRET_KEY" ]; then
        create_or_update_secret "emailpilot-secret-key" "$SECRET_KEY"
    else
        # Generate a new secret key if not provided
        echo -e "${YELLOW}Generating new SECRET_KEY...${NC}"
        SECRET_KEY=$(openssl rand -hex 32)
        create_or_update_secret "emailpilot-secret-key" "$SECRET_KEY"
    fi
    
    # Klaviyo API Key
    if [ ! -z "$KLAVIYO_API_KEY" ]; then
        create_or_update_secret "emailpilot-klaviyo-api-key" "$KLAVIYO_API_KEY"
    fi
    
    # Slack Webhook URL
    if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
        create_or_update_secret "emailpilot-slack-webhook-url" "$SLACK_WEBHOOK_URL"
    fi
    
    # Gemini API Key
    if [ ! -z "$GEMINI_API_KEY" ]; then
        create_or_update_secret "emailpilot-gemini-api-key" "$GEMINI_API_KEY"
    fi
    
    echo -e "${GREEN}Secrets migration completed!${NC}"
else
    echo -e "${YELLOW}No .env file found. Checking if secrets already exist in Secret Manager...${NC}"
    
    # Check if critical secrets exist
    if ! gcloud secrets describe emailpilot-secret-key --project=${PROJECT_ID} > /dev/null 2>&1; then
        echo -e "${YELLOW}Creating default SECRET_KEY...${NC}"
        SECRET_KEY=$(openssl rand -hex 32)
        create_or_update_secret "emailpilot-secret-key" "$SECRET_KEY"
    fi
    
    if ! gcloud secrets describe emailpilot-database-url --project=${PROJECT_ID} > /dev/null 2>&1; then
        echo -e "${YELLOW}Creating default DATABASE_URL for SQLite...${NC}"
        create_or_update_secret "emailpilot-database-url" "sqlite:///./emailpilot.db"
    fi
fi

# Grant Cloud Run service account access to secrets
echo -e "${YELLOW}Granting Cloud Run access to secrets...${NC}"
SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

for secret in emailpilot-database-url emailpilot-secret-key emailpilot-klaviyo-api-key emailpilot-slack-webhook-url emailpilot-gemini-api-key; do
    if gcloud secrets describe ${secret} --project=${PROJECT_ID} > /dev/null 2>&1; then
        gcloud secrets add-iam-policy-binding ${secret} \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="roles/secretmanager.secretAccessor" \
            --project=${PROJECT_ID} > /dev/null 2>&1
        echo -e "${GREEN}✓ Granted access to ${secret}${NC}"
    fi
done

# Update .env file to enable Secret Manager
echo -e "${YELLOW}Updating .env file to enable Secret Manager...${NC}"
if [ -f ".env" ]; then
    # Remove sensitive values and add SECRET_MANAGER_ENABLED
    grep -v "^DATABASE_URL=" .env | \
    grep -v "^SECRET_KEY=" .env | \
    grep -v "^KLAVIYO_API_KEY=" .env | \
    grep -v "^SLACK_WEBHOOK_URL=" .env | \
    grep -v "^GEMINI_API_KEY=" .env | \
    grep -v "^SECRET_MANAGER_ENABLED=" .env > .env.tmp
    
    echo "SECRET_MANAGER_ENABLED=true" >> .env.tmp
    echo "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" >> .env.tmp
    
    mv .env.tmp .env
    echo -e "${GREEN}✓ Updated .env file${NC}"
else
    echo "SECRET_MANAGER_ENABLED=true" > .env
    echo "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" >> .env
    echo "ENVIRONMENT=production" >> .env
    echo -e "${GREEN}✓ Created .env file with Secret Manager enabled${NC}"
fi

# Deploy to Cloud Run
echo -e "${GREEN}Starting deployment to Cloud Run...${NC}"

# Check if cloudbuild.yaml exists
if [ -f "cloudbuild.yaml" ]; then
    echo -e "${YELLOW}Using Cloud Build for deployment...${NC}"
    gcloud builds submit --config=cloudbuild.yaml --project=${PROJECT_ID}
else
    echo -e "${YELLOW}Building and deploying directly...${NC}"
    
    # Build the container
    docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest .
    
    # Push to Container Registry
    docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest
    
    # Deploy to Cloud Run
    gcloud run deploy ${SERVICE_NAME} \
        --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --port 8080 \
        --memory 2Gi \
        --cpu 1 \
        --max-instances 10 \
        --set-env-vars "ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},SECRET_MANAGER_ENABLED=true,DEBUG=false" \
        --set-secrets "DATABASE_URL=emailpilot-database-url:latest,SECRET_KEY=emailpilot-secret-key:latest,KLAVIYO_API_KEY=emailpilot-klaviyo-api-key:latest,SLACK_WEBHOOK_URL=emailpilot-slack-webhook-url:latest,GEMINI_API_KEY=emailpilot-gemini-api-key:latest" \
        --project=${PROJECT_ID}
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)' --project=${PROJECT_ID})

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Service URL: ${YELLOW}${SERVICE_URL}${NC}"
echo -e "Admin Panel: ${YELLOW}${SERVICE_URL}/admin${NC}"
echo ""
echo -e "${GREEN}Secret Manager Status:${NC}"
echo -e "  • Secrets are now stored in Google Secret Manager"
echo -e "  • Sensitive values have been removed from .env file"
echo -e "  • Cloud Run is configured to use secrets directly"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Visit the Admin Panel to verify configuration"
echo -e "  2. Test the Slack webhook using the Admin interface"
echo -e "  3. Verify all integrations are working correctly"
echo ""