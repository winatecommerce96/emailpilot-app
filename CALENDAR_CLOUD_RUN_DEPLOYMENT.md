# 🚀 EmailPilot Calendar Feature - Cloud Run Deployment

## Overview

This deployment bakes the calendar feature directly into the Docker image and deploys to Google Cloud Run. No manual file copying or staging required!

## What's Included

### Backend API (`app/api/calendar.py`)
- ✅ **Calendar Events** - Full CRUD operations
- ✅ **Client Management** - Multi-client support
- ✅ **Goals Integration** - Revenue tracking and progress
- ✅ **Dashboard** - Real-time achievement metrics
- ✅ **AI Endpoints** - Ready for Gemini integration
- ✅ **Firebase Integration** - Cloud Firestore persistence

### Router Registration (`main_firestore.py`)
```python
# Calendar router is automatically wired in:
from app.api.calendar import router as calendar_router
app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])
```

## Deployment Options

### Option 1: Quick Deployment (Recommended)
```bash
# Run from emailpilot-app directory
./deploy-calendar-quick.sh
```

This script:
- Checks prerequisites
- Wires calendar router if needed
- Builds Docker image
- Deploys to Cloud Run
- Shows service URL and endpoints

### Option 2: Full Deployment with Backup
```bash
# Run from emailpilot-app directory
./deploy-calendar-to-cloud-run.sh
```

This script includes:
- Comprehensive prerequisite checks
- Deployment backup creation
- Detailed verification
- Deployment report generation
- Rollback capability

### Option 3: Manual Commands
```bash
# Set environment variables
export PROJECT_ID=emailpilot-438321
export REGION=us-central1
export SERVICE=emailpilot-api

# Build and submit to Cloud Build
gcloud builds submit --project $PROJECT_ID \
  --tag gcr.io/$PROJECT_ID/$SERVICE:calendar-$(date +%Y%m%d-%H%M%S)

# Deploy to Cloud Run
gcloud run deploy $SERVICE \
  --region $REGION \
  --image gcr.io/$PROJECT_ID/$SERVICE:calendar-$(date +%Y%m%d-%H%M%S) \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8000
```

## API Endpoints

Once deployed, the calendar API is available at:

### Base URL
```
https://emailpilot-api-935786836546.us-central1.run.app
```

### Calendar Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calendar/health` | Health check |
| GET | `/api/calendar/events` | Get events for client |
| POST | `/api/calendar/events` | Create new event |
| PUT | `/api/calendar/events/{id}` | Update event |
| DELETE | `/api/calendar/events/{id}` | Delete event |
| GET | `/api/calendar/clients` | List all clients |
| POST | `/api/calendar/clients` | Create new client |
| GET | `/api/calendar/goals/{client_id}` | Get client goals |
| GET | `/api/calendar/dashboard/{client_id}` | Get dashboard metrics |
| POST | `/api/calendar/ai/chat` | AI chat assistance |
| POST | `/api/calendar/ai/summarize` | Parse document to campaigns |

## Testing the Deployment

### 1. Health Check
```bash
curl https://emailpilot-api-935786836546.us-central1.run.app/api/calendar/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "calendar",
  "timestamp": "2024-12-11T20:00:00.000000"
}
```

### 2. Get Clients
```bash
curl https://emailpilot-api-935786836546.us-central1.run.app/api/calendar/clients
```

### 3. Create Event
```bash
curl -X POST https://emailpilot-api-935786836546.us-central1.run.app/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Campaign",
    "date": "2024-12-15",
    "client_id": "demo1",
    "event_type": "campaign"
  }'
```

## Frontend Integration

Update your frontend to use the calendar API:

```javascript
// API Configuration
const API_BASE = 'https://emailpilot-api-935786836546.us-central1.run.app';

// Fetch calendar events
const response = await fetch(`${API_BASE}/api/calendar/events?client_id=${clientId}`);
const events = await response.json();

// Create new event
const response = await fetch(`${API_BASE}/api/calendar/events`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'New Campaign',
    date: '2024-12-20',
    client_id: clientId
  })
});
```

## Monitoring & Logs

### View Logs
```bash
# Recent logs
gcloud run logs read --service=emailpilot-api --region=us-central1 --limit=50

# Streaming logs
gcloud run logs tail --service=emailpilot-api --region=us-central1

# Filter calendar logs
gcloud run logs read --service=emailpilot-api --region=us-central1 \
  --filter="calendar" --limit=50
```

### Check Service Status
```bash
gcloud run services describe emailpilot-api --region=us-central1
```

### View Metrics
```bash
# In Google Cloud Console
https://console.cloud.google.com/run/detail/us-central1/emailpilot-api/metrics
```

## Rollback

If you need to rollback to a previous version:

### Using Script
```bash
./deploy-calendar-to-cloud-run.sh rollback
```

### Manual Rollback
```bash
# List revisions
gcloud run revisions list --service=emailpilot-api --region=us-central1

# Deploy specific revision
gcloud run services update-traffic emailpilot-api \
  --region=us-central1 \
  --to-revisions=<previous-revision-name>=100
```

## Troubleshooting

### Build Fails
```bash
# Check Cloud Build logs
gcloud builds list --limit=5

# View specific build log
gcloud builds log <build-id>
```

### Deployment Fails
```bash
# Check service status
gcloud run services describe emailpilot-api --region=us-central1

# Check quotas
gcloud compute project-info describe --project=emailpilot-438321
```

### API Not Responding
1. Check if service is running:
   ```bash
   gcloud run services list --region=us-central1
   ```

2. Check logs for errors:
   ```bash
   gcloud run logs read --service=emailpilot-api --region=us-central1 --limit=100
   ```

3. Verify calendar router is registered:
   ```bash
   curl https://emailpilot-api-935786836546.us-central1.run.app/docs
   ```
   Look for `/api/calendar` endpoints in API documentation

### Firebase Issues
1. Ensure Application Default Credentials are set up:
   ```bash
   gcloud auth application-default login
   ```

2. Check Firestore permissions in GCP Console

3. Verify project ID in calendar.py matches your project

## Next Steps

After successful deployment:

1. **Update Frontend**
   - Configure API base URL
   - Update fetch calls to use calendar endpoints
   - Test all calendar functionality

2. **Configure AI Features**
   - Set up Gemini API key as environment variable
   - Implement actual AI summarization
   - Test AI chat functionality

3. **Set Up Firebase Security Rules**
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /calendar_events/{document=**} {
         allow read, write: if request.auth != null;
       }
       match /clients/{document=**} {
         allow read, write: if request.auth != null;
       }
       match /goals/{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

4. **Monitor Performance**
   - Set up alerts for errors
   - Monitor response times
   - Track API usage

## Summary

The calendar feature is now fully integrated into your EmailPilot API and deployed to Cloud Run. The endpoints are live and ready to use. Simply update your frontend to point to the API endpoints and the calendar functionality will be available!

### Deployment Commands Summary
```bash
# Quick deploy (recommended)
./deploy-calendar-quick.sh

# Full deploy with backup
./deploy-calendar-to-cloud-run.sh

# Verify deployment
./deploy-calendar-to-cloud-run.sh verify

# Rollback if needed
./deploy-calendar-to-cloud-run.sh rollback
```

The calendar API is now part of your production EmailPilot service! 🎉