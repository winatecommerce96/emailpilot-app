# 📅 EmailPilot Calendar - Local Development Guide

## Quick Start

### 1. Start the FastAPI server
```bash
# From the emailpilot-app directory
uvicorn app.main:app --reload --port 8000
```

### 2. Open the calendar
Navigate to: http://127.0.0.1:8000/calendar

## What's Available

### Frontend
- **Location**: `static/calendar-local.html`
- **Features**:
  - Full calendar UI with month view
  - Client selector and management
  - Event creation/editing/deletion
  - Revenue goals dashboard
  - AI chat assistant
  - Real-time calculations

### API Endpoints (Local)
All endpoints are available at `http://127.0.0.1:8000/api/calendar/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calendar/health` | Health check |
| GET | `/api/calendar/events?client_id={id}` | Get events |
| POST | `/api/calendar/events` | Create event |
| PUT | `/api/calendar/events/{id}` | Update event |
| DELETE | `/api/calendar/events/{id}` | Delete event |
| GET | `/api/calendar/clients` | List clients |
| POST | `/api/calendar/clients` | Create client |
| GET | `/api/calendar/goals/{client_id}` | Get goals |
| GET | `/api/calendar/dashboard/{client_id}` | Dashboard data |
| POST | `/api/calendar/ai/chat` | AI chat |

## Testing the Calendar

### 1. Check API Health
```bash
curl http://127.0.0.1:8000/api/calendar/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "calendar",
  "timestamp": "2024-12-11T..."
}
```

### 2. Test Client Creation
```bash
curl -X POST http://127.0.0.1:8000/api/calendar/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Client"}'
```

### 3. Test Event Creation
```bash
curl -X POST http://127.0.0.1:8000/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Holiday Campaign",
    "date": "2024-12-25",
    "client_id": "demo1",
    "event_type": "cheese-club"
  }'
```

### 4. Test Dashboard
```bash
curl http://127.0.0.1:8000/api/calendar/dashboard/demo1
```

## Development Workflow

### Making Changes

#### Frontend Changes
1. Edit `static/calendar-local.html`
2. Refresh browser (no restart needed)

#### Backend Changes
1. Edit `app/api/calendar.py`
2. Server auto-reloads with `--reload` flag
3. Test API endpoints

### Firebase Integration

The calendar can work in two modes:

1. **API Mode** (Default)
   - Uses FastAPI backend at `http://127.0.0.1:8000`
   - Data stored in Firestore via backend

2. **Direct Firebase Mode** (Fallback)
   - If API fails, falls back to direct Firebase access
   - Requires Firebase configuration in HTML

### Debugging

#### Check Console Logs
Open browser developer tools (F12) and check:
- Network tab for API calls
- Console for JavaScript errors
- Application tab for local storage

#### API Logs
Watch server logs in terminal:
```bash
# You'll see requests like:
INFO:     127.0.0.1:52341 - "GET /calendar HTTP/1.1" 200 OK
INFO:     127.0.0.1:52341 - "GET /api/calendar/clients HTTP/1.1" 200 OK
INFO:     127.0.0.1:52341 - "GET /api/calendar/events?client_id=demo1 HTTP/1.1" 200 OK
```

## Features Overview

### 📊 Revenue Goals Dashboard
- Monthly revenue targets
- Current progress tracking
- Achievement percentage
- Strategic recommendations

### 📅 Calendar Grid
- Month view with navigation
- Click to create events
- Click events to edit/delete
- Color-coded by campaign type

### 🎯 Campaign Types & Multipliers
- **Cheese Club** (Green) - 2.0x revenue
- **RRB Promotion** (Red) - 1.5x revenue
- **SMS Alert** (Orange) - 1.3x revenue
- **Re-engagement** (Yellow) - 1.2x revenue
- **Nurturing** (Blue) - 0.8x revenue
- **Community** (Purple) - 0.7x revenue
- **General** (Gray) - 1.0x revenue

### 🤖 AI Chat Assistant
- Campaign planning suggestions
- Goal achievement strategies
- Currently returns mock responses
- Ready for Gemini integration

## Common Issues & Solutions

### Calendar Not Loading
1. Check server is running: `uvicorn app.main:app --reload`
2. Verify URL: http://127.0.0.1:8000/calendar
3. Check browser console for errors

### API Errors
1. Check Firestore credentials are set up
2. Verify `app/api/calendar.py` exists
3. Check import in `main.py`: `from app.api import calendar`

### No Clients Showing
- Calendar will show demo clients if API fails
- Create a client using the "+ New Client" button
- Check API endpoint: http://127.0.0.1:8000/api/calendar/clients

### Events Not Saving
1. Ensure client is selected
2. Check date format (YYYY-MM-DD)
3. Verify API endpoint is responding

## Customization

### Change API Base URL
Edit `static/calendar-local.html`:
```javascript
const API_BASE = 'http://127.0.0.1:8000';  // Change this
```

### Modify Campaign Types
Edit revenue multipliers in `app/api/calendar.py`:
```python
campaign_multipliers = {
    'cheese-club': 2.0,
    'rrb': 1.5,
    # Add or modify types here
}
```

### Update UI Styling
The calendar uses Tailwind CSS via CDN. Modify classes in `static/calendar-local.html`.

## Deployment

After testing locally:

1. **Test thoroughly** with local server
2. **Deploy to Cloud Run**:
   ```bash
   ./deploy-calendar-quick.sh
   ```
3. **Update frontend** to use production API:
   ```javascript
   const API_BASE = 'https://emailpilot-api-935786836546.us-central1.run.app';
   ```

## API Documentation

View interactive API docs:
http://127.0.0.1:8000/docs#/Calendar

This shows all calendar endpoints with:
- Request/response schemas
- Try-it-out functionality
- Parameter descriptions

## Summary

The calendar is now running locally with:
- ✅ Full UI at http://127.0.0.1:8000/calendar
- ✅ API endpoints at http://127.0.0.1:8000/api/calendar/*
- ✅ Firebase integration for data persistence
- ✅ Hot reload for development
- ✅ Mock AI responses for testing

Start developing with:
```bash
uvicorn app.main:app --reload
```

Then open: http://127.0.0.1:8000/calendar