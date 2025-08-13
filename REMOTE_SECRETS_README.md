# Remote-Only Secret Manager Integration

This document describes the Firestore-only remote Secret Manager integration for EmailPilot.

## Overview

The application now uses Google Secret Manager exclusively for all configuration values. There are **no local fallbacks** - if secrets cannot be loaded from Secret Manager, the application will fail to start with clear error messages.

## Architecture

### Components

1. **app/services/secret_manager.py**
   - Strict remote-only secret loading
   - No local fallbacks
   - Clear error messages on failure
   - Support for JSON secrets

2. **app/services/firestore.py**
   - Builds Firestore client with service account credentials
   - In-memory credentials (no files written to disk)
   - Lightweight connectivity check

3. **app/core/config.py**
   - Loads all configuration from Secret Manager
   - Required secrets: project ID, credentials, secret key
   - Optional secrets: Slack webhook, Gemini API key
   - Validates configuration and tests connectivity

## Required Secrets

| Secret ID | Description | Required |
|-----------|-------------|----------|
| `emailpilot-firestore-project` | GCP project ID for Firestore | ✅ Yes |
| `emailpilot-google-credentials` | Service Account JSON with Firestore + Secret Manager access | ✅ Yes |
| `emailpilot-secret-key` | Application crypto key (min 16 chars) | ✅ Yes |
| `emailpilot-slack-webhook-url` | Slack webhook for notifications | ❌ Optional |
| `emailpilot-gemini-api-key` | Gemini API key for AI features | ❌ Optional |

## Setup Instructions

### 1. Initial Setup

Run the setup script to configure all secrets:

```bash
cd emailpilot-app
./scripts/setup_remote_secrets.sh
```

This script will:
- Create all required secrets in Secret Manager
- Generate a secure random key for `emailpilot-secret-key`
- Prompt for service account JSON and optional secrets
- Configure IAM permissions

### 2. Manual Secret Creation (Alternative)

If you prefer to set up secrets manually:

```bash
PROJECT_ID=emailpilot-438321

# Create the project ID secret
printf "%s" "$PROJECT_ID" | gcloud secrets create emailpilot-firestore-project \
    --data-file=- --replication-policy=automatic --project="$PROJECT_ID"

# Create the secret key
openssl rand -base64 48 | tr -d '\n' | gcloud secrets create emailpilot-secret-key \
    --data-file=- --replication-policy=automatic --project="$PROJECT_ID"

# Create the service account credentials
gcloud secrets create emailpilot-google-credentials \
    --data-file=path/to/service-account.json \
    --replication-policy=automatic --project="$PROJECT_ID"

# Optional: Slack webhook
gcloud secrets create emailpilot-slack-webhook-url \
    --data-file=- --replication-policy=automatic --project="$PROJECT_ID"

# Optional: Gemini API key
gcloud secrets create emailpilot-gemini-api-key \
    --data-file=- --replication-policy=automatic --project="$PROJECT_ID"
```

### 3. IAM Configuration

The service account needs these roles:

```bash
SA_EMAIL=your-service-account@$PROJECT_ID.iam.gserviceaccount.com

# Secret Manager access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

# Firestore access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/datastore.user"
```

## Testing

### Quick Test Scripts

```bash
# Test secret loading only
python scripts/smoke_secrets.py

# Test Firestore connectivity
python scripts/fs_probe.py

# Comprehensive validation
python scripts/validate_remote_secrets.py
```

### Local Development Testing

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
export SECRET_MANAGER_TRANSPORT=rest  # Use REST to avoid DNS issues

# Authenticate with ADC for local development
gcloud auth application-default login
gcloud auth application-default set-quota-project "$GOOGLE_CLOUD_PROJECT"

# Run validation
python scripts/validate_remote_secrets.py

# Start the application
uvicorn main_firestore:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID for bootstrap | (from ADC) |
| `SECRET_MANAGER_TRANSPORT` | Transport protocol (rest/grpc) | rest |
| `ENVIRONMENT` | Environment name | production |
| `DEBUG` | Enable debug mode | false |

## Error Handling

The system will fail fast with clear error messages if:

1. **No Project ID**: "No project ID found."
2. **Missing Required Secret**: "Failed to load Secret 'xxx' from project 'yyy'"
3. **Invalid Credentials**: "Could not build Firestore client: xxx"
4. **Connectivity Issues**: "Firestore connectivity check failed: xxx"
5. **Invalid Secret Key**: "Invalid SECRET_KEY length."

## Production Deployment

For production (Cloud Run), ensure:

1. Service account has necessary IAM roles
2. All required secrets exist in Secret Manager
3. `GOOGLE_CLOUD_PROJECT` is set in environment
4. No local credential files are needed

## Troubleshooting

### Common Issues

1. **404 Secret Not Found**
   - Verify secret exists: `gcloud secrets list --project=$PROJECT_ID`
   - Check secret name spelling

2. **Permission Denied**
   - Verify IAM roles: `gcloud projects get-iam-policy $PROJECT_ID`
   - Ensure service account has `secretmanager.secretAccessor` role

3. **DNS/Network Issues**
   - Use `SECRET_MANAGER_TRANSPORT=rest` to avoid DNS SRV lookups
   - Check network connectivity to Google APIs

4. **Invalid Credentials**
   - Verify service account JSON is valid
   - Check project ID matches the service account's project

### Debug Commands

```bash
# List all secrets
gcloud secrets list --project=$PROJECT_ID

# View secret versions
gcloud secrets versions list emailpilot-secret-key --project=$PROJECT_ID

# Test secret access
gcloud secrets versions access latest --secret=emailpilot-secret-key --project=$PROJECT_ID

# Check IAM policy
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" \
    --filter="bindings.role:roles/secretmanager.secretAccessor"
```

## Migration from Local Config

If migrating from local configuration:

1. Extract current values from `.env` or config files
2. Create secrets in Secret Manager using setup script
3. Remove all local config files
4. Update deployment to use new config module
5. Test thoroughly with validation script

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use separate projects** for dev/staging/prod
3. **Rotate secrets regularly** (especially secret keys)
4. **Limit IAM permissions** to minimum required
5. **Audit secret access** via Cloud Logging
6. **Use service accounts** (not user credentials) in production