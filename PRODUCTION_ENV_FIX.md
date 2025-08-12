# Production Environment Variables Fix

## Issue
The Environment Variables tab in the Admin Dashboard works locally but not in production at emailpilot.ai.

## Root Cause
The production deployment wasn't properly configured to:
1. Serve the frontend from the same domain as the API
2. Handle CORS correctly for the production domain
3. Load and persist environment variables from .env file

## Solution Implemented

### 1. API URL Configuration
**File**: `frontend/public/app.js`
```javascript
// Changed from hardcoded domain to dynamic origin
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8080' 
    : window.location.origin; // Use same origin as frontend
```

### 2. CORS Configuration
**File**: `main.py`
```python
allow_origins=[
    "https://emailpilot.ai",
    "https://www.emailpilot.ai",  # Added www subdomain
    "http://localhost:8080",       # Local development
]
```

### 3. Static File Serving
**File**: `main.py`
- Added static file serving for frontend
- Created catch-all route for SPA
- Serves frontend from same domain as API

### 4. Environment Variables Persistence
**File**: `app/api/admin.py`
- Added .env file reading/writing functions
- Environment changes now persist to .env file
- Automatic .env file creation if missing

### 5. Dependencies
**File**: `requirements.txt`
- Added `python-dotenv` for .env file handling
- Added `aiofiles` for async file operations

## Deployment Steps

### 1. Deploy Updated Code
```bash
# From the emailpilot-app directory
./deploy.sh
```

### 2. Set Environment Variables in Production
```bash
# Option A: Using Google Cloud Console
gcloud run services update emailpilot-api \
  --update-env-vars SLACK_WEBHOOK_URL=your-webhook-url \
  --update-env-vars GEMINI_API_KEY=your-api-key \
  --region us-central1

# Option B: Using .env file (after deployment)
# Access Admin Dashboard and configure via UI
```

### 3. Verify Frontend Access
The frontend should now be accessible at:
- Production: `https://emailpilot.ai/`
- Admin: `https://emailpilot.ai/` (click Admin link)
- API: `https://emailpilot.ai/api/`

### 4. Test Environment Variables
1. Go to `https://emailpilot.ai/`
2. Login as admin user
3. Click "Admin" link
4. Navigate to "Environment Variables" tab
5. Variables should now load and be editable

## Troubleshooting

### If Environment Variables Still Don't Show:

1. **Check Browser Console**
   - Open Developer Tools (F12)
   - Look for error messages in Console
   - Check Network tab for failed requests

2. **Verify API Access**
   ```bash
   curl https://emailpilot.ai/api/admin/health
   curl https://emailpilot.ai/api/admin/environment
   ```

3. **Check Logs**
   ```bash
   gcloud run logs read --service emailpilot-api --region us-central1
   ```

4. **Clear Browser Cache**
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Or use Incognito/Private window

### Common Issues:

1. **404 Error on /api/admin/environment**
   - Backend not deployed with latest code
   - Run deployment script again

2. **CORS Error**
   - Production domain not in CORS whitelist
   - Check main.py CORS configuration

3. **Empty Environment Variables**
   - .env file doesn't exist in production
   - Use Admin UI to set initial values

4. **Network Error**
   - Frontend and API on different domains
   - Ensure both served from same domain

## Security Considerations

1. **Sensitive Values**: Always masked in UI (showing only first/last 4 chars)
2. **Admin Only**: Environment variables only accessible to admin users
3. **HTTPS Only**: Production must use HTTPS
4. **.env File**: Should be excluded from version control

## Next Steps

After deployment:
1. Set all required environment variables via Admin UI
2. Test Slack integration with test button
3. Verify restart functionality works
4. Monitor logs for any errors

## Support

If issues persist after following these steps:
1. Check GitHub issues: https://github.com/anthropics/claude-code/issues
2. Review logs: `gcloud run logs read`
3. Verify deployment: `gcloud run services describe emailpilot-api`