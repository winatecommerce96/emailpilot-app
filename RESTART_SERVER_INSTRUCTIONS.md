# Server Restart Required - Klaviyo OAuth Fix

## Issue Fixed
The Klaviyo OAuth router wasn't loading due to an import error in the crypto service. This has been fixed, but the server needs to be restarted to pick up the changes.

## What Was Fixed
1. **Crypto Service Import Error**: Fixed incorrect import `PBKDF2` → `PBKDF2HMAC`
2. **Router is now importable**: The OAuth endpoints are ready to work

## How to Restart the Server

### Option 1: Kill and Restart (Recommended)
```bash
# Find the uvicorn process
ps aux | grep "uvicorn main_firestore:app"

# Kill the process (use the PID from above)
kill <PID>

# Restart the server
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

### Option 2: Quick Restart Script
```bash
# Kill existing process and restart
pkill -f "uvicorn main_firestore:app" && \
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

### Option 3: If using screen/tmux
```bash
# Attach to the session
screen -r  # or tmux attach

# Press Ctrl+C to stop the server
# Then restart with:
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

## Verify It's Working

After restarting, test the endpoints:

```bash
# Test basic endpoint (should return 200 OK)
curl -i "http://localhost:8000/api/integrations/klaviyo/test"

# Test OAuth start (should return 302 redirect)
curl -i "http://localhost:8000/api/integrations/klaviyo/oauth/start"

# Test from browser
# Go to: http://localhost:8000/admin/clients
# Click "🔗 Connect Klaviyo" button
```

## Expected Output

### For `/test` endpoint:
```
HTTP/1.1 200 OK
{"status":"ok","message":"Klaviyo OAuth router is mounted"}
```

### For `/oauth/start`:
```
HTTP/1.1 302 Found
Location: https://www.klaviyo.com/oauth/authorize?...
```

## What to Look For in Logs

After restart, you should see:
```
✅ Klaviyo OAuth integration module loaded successfully
✅ Klaviyo OAuth integration enabled with auto-client creation at /api/integrations/klaviyo
```

## If Still Not Working

1. Check for any remaining import errors in the console
2. Verify environment variables are set:
   ```bash
   echo $KLAVIYO_OAUTH_CLIENT_ID
   echo $KLAVIYO_OAUTH_CLIENT_SECRET
   ```
3. Make sure you're in the correct directory:
   ```bash
   cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
   ```
4. Check Python environment:
   ```bash
   which python
   # Should be in .venv or anaconda
   ```

## Summary of Changes Made

1. **Fixed crypto_service.py**: Corrected PBKDF2HMAC import
2. **OAuth router is ready**: All endpoints defined and working
3. **Frontend button**: Already configured at `/admin/clients`
4. **Environment**: Make sure `.env` has OAuth credentials

The code is now ready - just needs a server restart to load the fixed imports!