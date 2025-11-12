# Clerk Authentication Setup Guide

## Overview

This guide documents how Clerk authentication is configured for the EmailPilot Calendar application. Clerk provides SSO (Single Sign-On) authentication that secures access to the calendar interface.

## Architecture

The calendar application uses Clerk's JavaScript SDK to handle authentication in the browser:

```
┌─────────────────────────────────────────────────────┐
│  calendar_master.html (Browser)                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ 1. Fetch Clerk Config from API               │  │
│  │    GET /api/auth/v2/clerk-config             │  │
│  └──────────────────┬───────────────────────────┘  │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐  │
│  │ 2. Initialize Clerk SDK with publishable key│  │
│  │    Clerk.load({ publishableKey: "pk_..." }) │  │
│  └──────────────────┬───────────────────────────┘  │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐  │
│  │ 3. Render calendar after authentication     │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Frontend Integration

**File:** `frontend/public/calendar_master.html`

The calendar HTML loads Clerk SDK and fetches configuration dynamically:

```html
<!-- Line 24: Clerk SDK loaded -->
<script
  crossorigin="anonymous"
  data-clerk-publishable-key=""
  src="https://cdn.jsdelivr.net/npm/@clerk/clerk-js@latest/dist/clerk.browser.js">
</script>
```

**Note:** The `data-clerk-publishable-key` attribute is intentionally empty. The key is fetched dynamically via JavaScript to allow environment-specific configuration.

### 2. Backend Configuration Endpoint

**File:** `app/api/auth_v2.py` (lines 631-638)

```python
@router.get("/clerk-config")
async def get_clerk_config(settings: Settings = Depends(get_settings)):
    """Get Clerk configuration for frontend"""
    return {
        "publishable_key": settings.clerk_frontend_api,
        "environment": "development",
        "configured": bool(settings.clerk_frontend_api)
    }
```

This endpoint returns the Clerk publishable key to the frontend.

### 3. Settings Configuration

**File:** `app/core/settings.py` (lines 137-143)

```python
clerk_frontend_api = secret_manager.get_secret("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
if not clerk_frontend_api:
    logger.warning("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY not found in Secret Manager")
    try:
        clerk_frontend_api = secret_manager.get_secret("clerk-frontend-api")
    except Exception:
        clerk_frontend_api = None
```

The application attempts to load the Clerk key from Google Secret Manager with fallback options.

## Google Cloud Configuration

### Secret Manager Setup

The Clerk publishable key is stored in Google Secret Manager:

**Secret Name:** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

**Current Value:** `pk_test_Y3VycmVudC1zdG9yay05OS5jbGVyay5hY2NvdW50cy5kZXYk`

### Cloud Run Environment

The secret is mounted to the Cloud Run service as an environment variable:

```bash
gcloud run services update emailpilot-app \
  --region=us-central1 \
  --update-secrets=NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:latest \
  --project=emailpilot-438321
```

**Revision:** `emailpilot-app-00036-v5j` (latest)

## Testing the Configuration

### 1. Verify Clerk Config Endpoint

```bash
# Via direct Cloud Run URL
curl https://emailpilot-app-p3cxgvcsla-uc.a.run.app/api/auth/v2/clerk-config

# Via load balancer
curl https://app.emailpilot.ai/api/auth/v2/clerk-config
```

**Expected Response:**
```json
{
  "publishable_key": "pk_test_Y3VycmVudC1zdG9yay05OS5jbGVyay5hY2NvdW50cy5kZXYk",
  "environment": "development",
  "configured": true
}
```

### 2. Test Calendar Access

**Production URL:** https://app.emailpilot.ai/calendar

**Direct URL:** https://emailpilot-app-p3cxgvcsla-uc.a.run.app/calendar

The calendar should:
1. Load successfully (200 OK)
2. Initialize Clerk SDK
3. Prompt for authentication
4. Display calendar events after successful login

## Load Balancer Configuration

The load balancer routes the following paths to `emailpilot-app`:

```yaml
pathRules:
  - paths:
    - /calendar
    - /calendar/*
    - /api/calendar
    - /api/calendar/*
    - /api/auth/v2/clerk-config
    service: emailpilot-app-backend
```

This ensures all calendar-related requests (page, API, and auth config) route to the same service.

## Clerk Dashboard Configuration

### Required Clerk Settings

In your Clerk dashboard (https://dashboard.clerk.com/), configure:

1. **Allowed Redirect URLs:**
   - `https://app.emailpilot.ai/calendar`
   - `https://emailpilot-app-p3cxgvcsla-uc.a.run.app/calendar`
   - `http://localhost:8000/calendar` (for local development)

2. **Allowed Origins:**
   - `https://app.emailpilot.ai`
   - `https://emailpilot-app-p3cxgvcsla-uc.a.run.app`
   - `http://localhost:8000` (for local development)

3. **Application Settings:**
   - Application Name: EmailPilot Calendar
   - Environment: Development (currently)

## Troubleshooting

### Issue: "Clerk SDK failed to load"

**Symptoms:** Browser console shows 404 error for Clerk script

**Solution:** Verify the Clerk CDN URL is accessible and the publishable key is correctly formatted

**Verification:**
```bash
curl https://app.emailpilot.ai/api/auth/v2/clerk-config
```

### Issue: "Authentication required" errors

**Symptoms:** API calls return 401/403 errors after Clerk initialization

**Solution:** Ensure the calendar is using relative URLs for API calls (not absolute URLs to a different origin)

**Current Implementation:** Calendar uses relative URLs like `/api/calendar/events` which automatically resolve to the same origin

### Issue: Redirect loop or "Invalid redirect URL"

**Symptoms:** After Clerk login, page keeps redirecting

**Solution:**
1. Check Clerk dashboard has correct redirect URLs configured
2. Verify the `redirect_url` parameter in Clerk callbacks matches allowed URLs

### Issue: Callback redirect error / "Could not establish connection"

**Symptoms:**
- Browser console shows "Uncaught (in promise) Error: Could not establish connection. Receiving end does not exist"
- Page redirects to Clerk's sign-in page with callback URL like `/api/auth/v2/auth/clerk/callback`
- Error occurs after 3 seconds of loading the calendar

**Root Cause:** Calendar code was attempting to redirect to non-existent server-side OAuth endpoints (`/api/auth/v2/auth/sso/clerk`) instead of using Clerk's browser-based authentication methods.

**Solution:** Use Clerk's built-in browser methods for authentication redirects:

**Fixed in:** `calendar_master.html` lines 4552-4559 (commit da5443da)

**Before (incorrect):**
```javascript
window.location.href = '/api/auth/v2/auth/sso/clerk';
```

**After (correct):**
```javascript
clerkInstance.redirectToSignIn();
```

This uses Clerk's proper browser-based authentication flow that handles all the OAuth complexity internally.

### Issue: Clerk key not loading from Secret Manager

**Symptoms:** `/clerk-config` returns `configured: false`

**Solution:**
```bash
# Check if secret exists
gcloud secrets describe NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY --project=emailpilot-438321

# Check if Cloud Run service has access
gcloud run services describe emailpilot-app --region=us-central1 --format=yaml | grep -A 5 "secretEnvVar"

# Update Cloud Run service with secret
gcloud run services update emailpilot-app \
  --region=us-central1 \
  --update-secrets=NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:latest \
  --project=emailpilot-438321
```

## Security Considerations

1. **Publishable Key is Safe to Expose:** The Clerk publishable key (starting with `pk_`) is designed to be used in browser-side code and does not need to be kept secret.

2. **Secret Key Must Remain Private:** The Clerk secret key (stored as `CLERK_SECRET_KEY` in Secret Manager) should NEVER be exposed to the browser or included in frontend code.

3. **HTTPS Only in Production:** Clerk authentication should only be used over HTTPS in production to prevent man-in-the-middle attacks.

4. **CORS Configuration:** The load balancer and Cloud Run service must have proper CORS headers configured to allow Clerk callbacks to function correctly.

## Updating Clerk Configuration

### To Update the Publishable Key

1. Get the new key from Clerk dashboard
2. Update the secret in Secret Manager:
   ```bash
   echo -n "NEW_PUBLISHABLE_KEY" | gcloud secrets versions add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY --data-file=- --project=emailpilot-438321
   ```
3. Restart the Cloud Run service to pick up the new secret:
   ```bash
   gcloud run services update-traffic emailpilot-app --to-latest --region=us-central1 --project=emailpilot-438321
   ```

### To Switch Clerk Environments

Update the `environment` field in `app/api/auth_v2.py`:

```python
return {
    "publishable_key": settings.clerk_frontend_api,
    "environment": "production",  # Change from "development"
    "configured": bool(settings.clerk_frontend_api)
}
```

Redeploy the application after making this change.

## Related Files

- `frontend/public/calendar_master.html` - Frontend Clerk integration (lines 24, 4472-4674)
- `app/api/auth_v2.py` - Clerk config endpoint (lines 631-638)
- `app/core/settings.py` - Settings loader (lines 137-143)
- `app/main.py` - Main application setup (includes auth router)

## Support

For issues with Clerk configuration:
- Clerk Documentation: https://clerk.com/docs
- Clerk Support: support@clerk.com
- EmailPilot GitHub Issues: https://github.com/anthropics/emailpilot/issues

---

**Last Updated:** 2025-11-11
**Clerk Version:** Latest (CDN)
**Application:** emailpilot-app
**Environment:** Development
