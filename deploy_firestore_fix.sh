#!/bin/bash

echo "🚀 Deploying Firestore fixes to EmailPilot..."
echo "=========================================="

# Set the project
gcloud config set project emailpilot-438321

# Build and deploy the updated application
echo "📦 Building and deploying to Cloud Run..."

# Deploy using Cloud Build and Cloud Run
gcloud builds submit --tag gcr.io/emailpilot-438321/emailpilot \
  && gcloud run deploy emailpilot \
    --image gcr.io/emailpilot-438321/emailpilot \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Visit https://emailpilot.ai"
    echo "2. Login with your approved email"
    echo "3. Check that Clients and Goals are now displaying"
else
    echo "❌ Deployment failed. Check the errors above."
fi