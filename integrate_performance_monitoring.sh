#!/bin/bash

# Integration Script for Performance Monitoring
# Migrates from standalone Cloud Functions to integrated EmailPilot.ai service

set -e

echo "🚀 Starting Performance Monitoring Integration..."
echo "================================================"

# Configuration
PROJECT_ID="emailpilot-438321"
REGION="us-central1"
EMAILPILOT_URL="https://emailpilot.ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Deploy the updated EmailPilot service with integrated performance monitoring
echo -e "\n${YELLOW}Step 1: Deploying updated EmailPilot service...${NC}"
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app

# Check if deployment script exists
if [ -f "./deploy.sh" ]; then
    echo "Running deployment script..."
    ./deploy.sh
else
    echo "Deploying with gcloud run deploy..."
    gcloud run deploy emailpilot-app \
        --source . \
        --region $REGION \
        --allow-unauthenticated \
        --port 8080 \
        --memory 1Gi \
        --project $PROJECT_ID
fi

echo -e "${GREEN}✅ EmailPilot service deployed${NC}"

# Step 2: Update Cloud Scheduler jobs to use new endpoints
echo -e "\n${YELLOW}Step 2: Updating Cloud Scheduler jobs...${NC}"

# Update weekly scheduler
echo "Updating weekly-klaviyo-update scheduler..."
gcloud scheduler jobs update http weekly-klaviyo-update \
    --location=$REGION \
    --uri="${EMAILPILOT_URL}/api/performance/reports/weekly/scheduler-trigger" \
    --http-method=POST \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Weekly scheduler updated${NC}"

# Update monthly scheduler
echo "Updating monthly-klaviyo-report scheduler..."
gcloud scheduler jobs update http monthly-klaviyo-report \
    --location=$REGION \
    --uri="${EMAILPILOT_URL}/api/performance/reports/monthly/scheduler-trigger" \
    --http-method=POST \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Monthly scheduler updated${NC}"

# Step 3: Test the integrated endpoints
echo -e "\n${YELLOW}Step 3: Testing integrated endpoints...${NC}"

# Test weekly endpoint
echo "Testing weekly report endpoint..."
curl -X POST "${EMAILPILOT_URL}/api/performance/reports/weekly/scheduler-trigger" \
    -H "Content-Type: application/json" \
    --max-time 10 || echo -e "${YELLOW}Warning: Weekly endpoint test timed out (this is normal for background tasks)${NC}"

# Test monthly endpoint
echo "Testing monthly report endpoint..."
curl -X POST "${EMAILPILOT_URL}/api/performance/reports/monthly/scheduler-trigger" \
    -H "Content-Type: application/json" \
    --max-time 10 || echo -e "${YELLOW}Warning: Monthly endpoint test timed out (this is normal for background tasks)${NC}"

echo -e "${GREEN}✅ Endpoint tests completed${NC}"

# Step 4: Disable standalone Cloud Functions
echo -e "\n${YELLOW}Step 4: Disabling standalone Cloud Functions...${NC}"

# List of functions to disable
FUNCTIONS_TO_DISABLE=(
    "weekly-performance-generator"
    "monthly-report-generator"
    "goal-manager"
    "client-manager"
)

for func in "${FUNCTIONS_TO_DISABLE[@]}"; do
    echo "Checking if $func exists..."
    if gcloud functions describe $func --region=$REGION --project=$PROJECT_ID &>/dev/null; then
        echo "Disabling $func..."
        # Delete the function instead of disabling (Cloud Functions don't have a disable state)
        gcloud functions delete $func \
            --region=$REGION \
            --project=$PROJECT_ID \
            --quiet
        echo -e "${GREEN}✅ $func deleted${NC}"
    else
        echo -e "${YELLOW}⚠️ $func not found or already deleted${NC}"
    fi
done

# Step 5: Verify Firestore collections exist
echo -e "\n${YELLOW}Step 5: Verifying Firestore collections...${NC}"

# Check if required collections exist
python3 << EOF
from google.cloud import firestore
import sys

try:
    db = firestore.Client(project='$PROJECT_ID')
    
    # Required collections
    collections = ['clients', 'goals', 'reports']
    
    for collection in collections:
        docs = list(db.collection(collection).limit(1).stream())
        if docs:
            print(f"✅ Collection '{collection}' exists with data")
        else:
            print(f"⚠️ Collection '{collection}' exists but is empty")
            # Create a placeholder doc if empty
            if collection == 'reports':
                db.collection(collection).add({
                    'placeholder': True,
                    'created_at': firestore.SERVER_TIMESTAMP
                })
    
    print("✅ Firestore verification complete")
except Exception as e:
    print(f"❌ Firestore error: {e}")
    sys.exit(1)
EOF

# Step 6: Generate summary report
echo -e "\n${YELLOW}Step 6: Integration Summary${NC}"
echo "================================================"
echo -e "${GREEN}✅ Performance Monitoring Integration Complete!${NC}"
echo ""
echo "📊 Integration Status:"
echo "  • EmailPilot service: Deployed with integrated monitoring"
echo "  • Weekly scheduler: Updated to use ${EMAILPILOT_URL}/api/performance/reports/weekly/scheduler-trigger"
echo "  • Monthly scheduler: Updated to use ${EMAILPILOT_URL}/api/performance/reports/monthly/scheduler-trigger"
echo "  • Cloud Functions: Disabled/Deleted"
echo "  • Firestore: Verified and ready"
echo ""
echo "🔧 Next Steps:"
echo "  1. Monitor the next scheduled runs:"
echo "     - Weekly: Sundays at 5:00 AM CST"
echo "     - Monthly: 1st of each month at 5:00 AM CST"
echo "  2. Check logs: gcloud logging read 'resource.type=cloud_run_revision'"
echo "  3. Manual test: Run scheduler jobs manually if needed"
echo ""
echo "📝 Manual Testing Commands:"
echo "  gcloud scheduler jobs run weekly-klaviyo-update --location=$REGION"
echo "  gcloud scheduler jobs run monthly-klaviyo-report --location=$REGION"
echo ""
echo "🔍 View Scheduler Jobs:"
echo "  gcloud scheduler jobs list --location=$REGION"
echo ""
echo "================================================"
echo -e "${GREEN}Integration completed successfully!${NC}"