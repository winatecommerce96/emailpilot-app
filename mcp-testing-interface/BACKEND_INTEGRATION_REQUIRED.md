# ⚠️ Backend Integration Required

## Problem Identified
The MCP API endpoints are returning 404, which means the backend routes aren't registered in production. The package deployed successfully but the API routes need to be manually added to the main application.

## What's Missing
The `/api/mcp/*` routes are not registered in `main_firestore.py`. This is why:
- `/api/mcp/clients` returns 404
- `/api/mcp/models` returns 404

## Quick Fix Instructions

### Step 1: SSH into Production Server
```bash
gcloud compute ssh emailpilot-instance --zone=us-central1-a
# or use Cloud Shell
```

### Step 2: Find Staged MCP Files
```bash
# Check staged packages directory
ls -la /app/staged_packages/mcp*/

# Or check temporary directory
ls -la /tmp/mcp*/

# Find the MCP API module
find /app -name "mcp.py" 2>/dev/null
find /tmp -name "mcp.py" 2>/dev/null
```

### Step 3: Add MCP Router to main_firestore.py

You need to add these lines to `/app/main_firestore.py`:

```python
# Add this import at the top with other imports
from app.api.mcp import router as mcp_router

# Add this line where other routers are registered (look for app.include_router)
app.include_router(mcp_router, prefix="/api/mcp", tags=["mcp"])
```

### Step 4: Copy MCP Files to Correct Locations

```bash
# Copy API module
cp /app/staged_packages/mcp*/api/mcp.py /app/app/api/

# Copy service modules
cp /app/staged_packages/mcp*/services/mcp_service.py /app/app/services/
cp /app/staged_packages/mcp*/services/secret_manager.py /app/app/services/

# Copy model and schema modules
cp /app/staged_packages/mcp*/models/mcp_client.py /app/app/models/
cp /app/staged_packages/mcp*/schemas/mcp_client.py /app/app/schemas/

# Copy auth module if missing
cp /app/staged_packages/mcp*/core/auth.py /app/app/core/
```

### Step 5: Run Database Migration
```bash
cd /app
python /app/staged_packages/mcp*/migrate_mcp_only.py
```

### Step 6: Restart the Application
```bash
# Option 1: Via Cloud Run
gcloud run services update emailpilot-api --region=us-central1

# Option 2: Via admin dashboard
# Go to https://emailpilot.ai/admin and click "Restart Application"
```

## Alternative: Check via Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to Cloud Run → emailpilot-api
3. Click "Edit & Deploy New Revision"
4. Check the logs for any startup errors

## Verification After Integration

Once the backend is integrated, test with:

```bash
# Test from command line
curl -X GET https://emailpilot.ai/api/mcp/models \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return JSON array of models, not 404
```

## Current Status Summary

✅ **What's Working:**
- MCP Management UI is loaded
- Frontend components are present
- Authentication is working

❌ **What's Not Working:**
- Backend API routes not registered (404 errors)
- MCP router not included in main application
- Database tables might not be created

## Manual Test Without Backend

While the backend is being fixed, you can still test the UI functionality:

```javascript
// Mock the API responses for UI testing
window.mockMCPData = {
    models: [
        {id: 1, provider: 'claude', model_name: 'claude-3-opus', display_name: 'Claude 3 Opus'},
        {id: 2, provider: 'openai', model_name: 'gpt-4-turbo', display_name: 'GPT-4 Turbo'},
        {id: 3, provider: 'gemini', model_name: 'gemini-pro', display_name: 'Gemini Pro'}
    ],
    clients: [
        {id: 'test-1', name: 'Test Client', account_id: 'test-001', enabled: true, has_klaviyo_key: true}
    ]
};

// Override fetch to return mock data
const originalFetch = window.fetch;
window.fetch = function(url, options) {
    if (url.includes('/api/mcp/models')) {
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(window.mockMCPData.models)
        });
    }
    if (url.includes('/api/mcp/clients')) {
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(window.mockMCPData.clients)
        });
    }
    return originalFetch(url, options);
};

console.log('✅ Mock MCP data loaded. Refresh the page to see mock data in UI.');
alert('✅ Mock data loaded! Refresh the MCP Management page to see test data.');
```

## Next Steps

1. **Complete backend integration** using the instructions above
2. **Restart the application** after adding the routes
3. **Test the API endpoints** to confirm they're working
4. **Then the testing UI** will work properly

The issue is that the deployment package staged the files but didn't automatically register the API routes. This is a one-time manual step that needs to be done in production.