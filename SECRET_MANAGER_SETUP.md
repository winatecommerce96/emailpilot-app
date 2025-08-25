# Secret Manager Setup Guide

This guide will help you configure Google Cloud Secret Manager for EmailPilot.

## Quick Start

1. **Run the diagnostic script** to check your current setup:
   ```bash
   python check_secret_manager.py
   ```

2. **Follow the recommendations** provided by the diagnostic script to fix any issues.

## Common Setup Steps

### 1. Set Environment Variables

```bash
# Set your Google Cloud project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Optional: Enable/disable Secret Manager
export SECRET_MANAGER_ENABLED=true

# For development: set environment to development
export ENVIRONMENT=development
```

### 2. Google Cloud Authentication

**For local development:**
```bash
gcloud auth application-default login
```

**For production (using service account):**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 3. Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com --project=your-project-id
```

### 4. Grant IAM Permissions

**For development (your user account):**
```bash
gcloud projects add-iam-policy-binding your-project-id \
    --member="user:your-email@domain.com" \
    --role="roles/secretmanager.admin"
```

**For production (service account):**
```bash
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.admin"
```

**Minimal permissions (if you don't want admin role):**
```bash
# Grant individual permissions
gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:your-service-account@your-project-id.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretVersionManager"
```

## Development Mode Fallbacks

EmailPilot supports several fallback mechanisms for development environments:

### 1. Environment Variables Fallback

If Secret Manager is not available, the system will look for API keys in environment variables:

```bash
# Global Klaviyo API key for development
export KLAVIYO_API_KEY=your-api-key

# Client-specific keys (replace CLIENT_SLUG with actual client slug)
export KLAVIYO_API_KEY_CLIENT_SLUG=client-specific-key
```

### 2. Disable Secret Manager

For pure local development, you can disable Secret Manager entirely:

```bash
export SECRET_MANAGER_ENABLED=false
export ENVIRONMENT=development
```

### 3. Direct Storage Mode

In development mode, API keys can be stored directly in Firestore (not recommended for production).

## Troubleshooting

### Common Error Messages

**"Failed to create secret klaviyo-api-test-client-liczju"**
- Check if GOOGLE_CLOUD_PROJECT is set
- Verify authentication: `gcloud auth list`
- Check IAM permissions
- Run diagnostic: `python check_secret_manager.py`

**"Permission denied on resource project"**
- Grant Secret Manager roles to your user/service account
- Enable Secret Manager API in your project
- Verify billing is enabled

**"GOOGLE_CLOUD_PROJECT environment variable not set"**
- Set the environment variable: `export GOOGLE_CLOUD_PROJECT=your-project-id`
- Add to your .env file for persistence

### Debug Commands

```bash
# Check current project
gcloud config get-value project

# List your authentication
gcloud auth list

# Check IAM permissions
gcloud projects get-iam-policy your-project-id

# Test Secret Manager directly
gcloud secrets list --project=your-project-id

# Create a test secret
gcloud secrets create test-secret --data-file=- <<< "test-value"
```

### API Endpoints for Status Checking

EmailPilot provides endpoints to check Secret Manager status:

- `GET /api/admin/environment` - Shows environment configuration
- `GET /api/admin/secret-manager/status` - Detailed Secret Manager diagnostics

## Production Deployment

### Google Cloud Run

```yaml
# In your Cloud Run service configuration
env:
  - name: GOOGLE_CLOUD_PROJECT
    value: your-project-id
  - name: SECRET_MANAGER_ENABLED
    value: "true"
  - name: ENVIRONMENT
    value: "production"
```

Ensure your Cloud Run service account has the `roles/secretmanager.admin` role.

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: emailpilot-config
data:
  GOOGLE_CLOUD_PROJECT: <base64-encoded-project-id>
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      serviceAccountName: emailpilot-sa  # Service account with Secret Manager permissions
      containers:
      - name: emailpilot
        env:
        - name: GOOGLE_CLOUD_PROJECT
          valueFrom:
            secretKeyRef:
              name: emailpilot-config
              key: GOOGLE_CLOUD_PROJECT
```

## Security Best Practices

1. **Never store API keys in code or environment files checked into version control**
2. **Use least-privilege IAM roles** - avoid `secretmanager.admin` in production if possible
3. **Rotate secrets regularly** using Secret Manager versioning
4. **Use development fallbacks only in development environments**
5. **Monitor secret access** using Cloud Logging

## Support

If you continue to have issues:

1. Run the full diagnostic: `python check_secret_manager.py`
2. Check the diagnostic results file: `secret_manager_diagnostic_results.json`
3. Review application logs for detailed error messages
4. Use the `/api/admin/secret-manager/status` endpoint for live diagnostics