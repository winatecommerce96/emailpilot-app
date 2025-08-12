# Fix for Admin 404 Errors in Production

## Problem Identified
The production environment at emailpilot.ai was returning 404 errors for:
- `/api/admin/environment`
- `/api/admin/system/status`
- All other admin endpoints

## Root Cause
Production uses `main_firestore.py` (not `main.py`), and the admin router was not included in that file.

### Evidence from Error Logs:
```
GET https://emailpilot.ai/api/admin/environment 404 (Not Found)
GET https://emailpilot.ai/api/admin/system/status 404 (Not Found)
```

### Dockerfile Configuration:
```dockerfile
CMD ["uvicorn", "main_firestore:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Solution Implemented

### 1. Added Admin Import
**File**: `main_firestore.py` (line 19-20)
```python
# Import admin router
from app.api import admin
```

### 2. Added BackgroundTasks Import
**File**: `main_firestore.py` (line 7)
```python
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
```

### 3. Included Admin Router
**File**: `main_firestore.py` (line 123-124)
```python
# Include admin router for admin endpoints
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
```

## Files Modified
1. `main_firestore.py` - Added admin router inclusion
2. `deploy_admin_fix.sh` - Created deployment script

## Deployment Instructions

### Quick Deploy:
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
./deploy_admin_fix.sh
```

### Manual Deploy:
```bash
# Verify changes
grep "admin.router" main_firestore.py

# Deploy to Cloud Run
gcloud builds submit --config cloudbuild.yaml .

# Get service URL
gcloud run services describe emailpilot-api --region=us-central1
```

## Testing After Deployment

### 1. Test Admin Endpoints
```bash
# Replace SERVICE_URL with your actual URL
curl https://emailpilot.ai/api/admin/health
curl https://emailpilot.ai/api/admin/environment
```

### 2. Test in Browser
1. Clear browser cache (Cmd+Shift+R or Ctrl+Shift+R)
2. Visit https://emailpilot.ai
3. Login as admin
4. Click "Admin" → "Environment Variables"
5. Should now load without 404 errors

## What This Fixes
✅ Environment Variables tab loading
✅ System Status display
✅ Slack test functionality
✅ Server restart button
✅ Package upload features

## Important Notes
- Production uses Firestore (`main_firestore.py`)
- Development uses SQLite (`main.py`)
- Both now have admin endpoints included
- The .env file persistence works in both environments

## Troubleshooting
If issues persist after deployment:

1. **Check deployment logs**:
   ```bash
   gcloud run logs read --service emailpilot-api --region us-central1
   ```

2. **Verify admin router is included**:
   ```bash
   curl https://emailpilot.ai/api/admin/health
   ```
   Should return: `{"status":"healthy","service":"EmailPilot Admin API"...}`

3. **Check browser console**:
   - Should no longer show 404 errors
   - Should show successful API calls

## Success Indicators
- No 404 errors in browser console
- Environment variables load and display
- Slack test button works
- Restart server button appears
- All admin features functional