#!/bin/bash
# Setup script for remote-only Secret Manager integration
# Run this once to configure all required secrets in Google Secret Manager

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-emailpilot-438321}

echo "Setting up secrets for project: $PROJECT_ID"
echo "==========================================="

# Function to create or update a secret
create_or_update_secret() {
    local secret_id=$1
    local data_source=$2
    
    # Check if secret exists
    if gcloud secrets describe "$secret_id" --project="$PROJECT_ID" &>/dev/null; then
        echo "Secret '$secret_id' exists, adding new version..."
        if [ "$data_source" = "-" ]; then
            # Read from stdin
            gcloud secrets versions add "$secret_id" --project="$PROJECT_ID" --data-file=-
        else
            # Read from file
            gcloud secrets versions add "$secret_id" --project="$PROJECT_ID" --data-file="$data_source"
        fi
    else
        echo "Creating secret '$secret_id'..."
        gcloud secrets create "$secret_id" --replication-policy=automatic --project="$PROJECT_ID"
        if [ "$data_source" = "-" ]; then
            # Read from stdin
            gcloud secrets versions add "$secret_id" --project="$PROJECT_ID" --data-file=-
        else
            # Read from file
            gcloud secrets versions add "$secret_id" --project="$PROJECT_ID" --data-file="$data_source"
        fi
    fi
}

# 1. Set up emailpilot-firestore-project (contains the project ID itself)
echo ""
echo "1. Setting up emailpilot-firestore-project..."
echo "$PROJECT_ID" | create_or_update_secret "emailpilot-firestore-project" "-"

# 2. Set up emailpilot-secret-key (generate a secure random key)
echo ""
echo "2. Setting up emailpilot-secret-key..."
if gcloud secrets describe "emailpilot-secret-key" --project="$PROJECT_ID" &>/dev/null; then
    echo "Secret 'emailpilot-secret-key' already exists, skipping generation."
else
    echo "Generating secure random key..."
    openssl rand -base64 48 | tr -d '\n' | create_or_update_secret "emailpilot-secret-key" "-"
fi

# 3. Set up emailpilot-google-credentials (needs service account JSON)
echo ""
echo "3. Setting up emailpilot-google-credentials..."
echo "Please provide the path to your service account JSON file:"
echo "(This should be a service account with Firestore and Secret Manager access)"
read -p "Service account JSON path: " SA_PATH

if [ -f "$SA_PATH" ]; then
    create_or_update_secret "emailpilot-google-credentials" "$SA_PATH"
else
    echo "Error: File not found: $SA_PATH"
    echo "You'll need to manually add this secret later."
fi

# 4. Optional: Set up Slack webhook
echo ""
echo "4. Optional: emailpilot-slack-webhook-url"
read -p "Enter Slack webhook URL (or press Enter to skip): " SLACK_URL
if [ -n "$SLACK_URL" ]; then
    echo "$SLACK_URL" | create_or_update_secret "emailpilot-slack-webhook-url" "-"
else
    echo "Skipping Slack webhook setup."
fi

# 5. Optional: Set up Gemini API key
echo ""
echo "5. Optional: emailpilot-gemini-api-key"
read -p "Enter Gemini API key (or press Enter to skip): " GEMINI_KEY
if [ -n "$GEMINI_KEY" ]; then
    echo "$GEMINI_KEY" | create_or_update_secret "emailpilot-gemini-api-key" "-"
else
    echo "Skipping Gemini API key setup."
fi

# 6. Set up IAM permissions
echo ""
echo "6. Setting up IAM permissions..."
echo "Please provide the service account email that will access these secrets:"
echo "(e.g., my-app@$PROJECT_ID.iam.gserviceaccount.com)"
read -p "Service account email: " SA_EMAIL

if [ -n "$SA_EMAIL" ]; then
    echo "Granting Secret Manager access..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet

    echo "Granting Firestore access..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/datastore.user" \
        --quiet
else
    echo "Skipping IAM setup. You'll need to configure permissions manually."
fi

echo ""
echo "==========================================="
echo "Setup complete!"
echo ""
echo "To test the configuration, run:"
echo "  export GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "  export SECRET_MANAGER_TRANSPORT=rest"
echo "  python scripts/validate_remote_secrets.py"
echo ""
echo "To use with the application:"
echo "  export GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "  export SECRET_MANAGER_TRANSPORT=rest"
echo "  uvicorn main_firestore:app --host 0.0.0.0 --port 8000"