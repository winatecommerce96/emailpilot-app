# 🔧 Calendar Tab Fix Guide

## Problem
The Calendar tab in the EmailPilot SPA doesn't work when clicked.

## Solution Applied

### 1. Created Calendar React Component
**File**: `frontend/public/components/CalendarViewLocal.js`

This component:
- Integrates with the existing SPA structure
- Connects to the local API at `http://127.0.0.1:8000`
- Provides both iframe and direct rendering options
- Handles loading states and errors

### 2. Updated HTML to Load Component
**File**: `frontend/public/index.html`
- Added: `<script src="components/CalendarViewLocal.js"></script>`

### 3. Component Registration
The calendar is now available as:
- `window.CalendarView` - Main component the SPA expects
- `window.CalendarViewLocal` - Iframe version
- `window.CalendarViewDirect` - Direct React version

## How to Test

### Step 1: Start the Server
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 2: Open the App
Navigate to: http://127.0.0.1:8000

### Step 3: Click Calendar Tab
The calendar should now load when you click the Calendar tab in the sidebar.

## What You Should See

When the Calendar tab works correctly:
1. **Loading spinner** briefly appears
2. **Calendar interface** loads with:
   - Client selector dropdown
   - Month view calendar grid
   - Revenue goals dashboard (if client has goals)
   - Navigation buttons for months

## Troubleshooting

### If Calendar Tab Still Doesn't Work

#### 1. Check Browser Console (F12)
Look for errors like:
- `CalendarView is not defined` → Component not loading
- `Failed to fetch` → API not running
- `CORS error` → API configuration issue

#### 2. Verify Files Are Loaded
In browser console, type:
```javascript
console.log(typeof window.CalendarView);  // Should be "function"
console.log(typeof window.CalendarViewLocal);  // Should be "function"
```

#### 3. Force Reload
- Clear browser cache: Ctrl+Shift+Delete
- Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

#### 4. Check API Health
```bash
curl http://127.0.0.1:8000/api/calendar/health
```
Should return:
```json
{"status":"healthy","service":"calendar"}
```

#### 5. Direct Access Test
Try accessing the calendar directly:
- http://127.0.0.1:8000/calendar
- http://127.0.0.1:8000/calendar-local

### Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "Loading Calendar components..." stuck | Refresh page, check console for errors |
| "Calendar API not available" | Start server with `uvicorn app.main:app --reload` |
| Blank calendar | Check if client is selected in dropdown |
| No events showing | Create events by clicking on calendar days |
| API errors | Check server logs in terminal |

## Alternative Solutions

### Option 1: Use Iframe Version
If the direct component has issues, the CalendarViewLocal uses an iframe which isolates the calendar:
```javascript
// In browser console:
window.CalendarView = window.CalendarViewLocal;
```
Then refresh the page.

### Option 2: Direct URL Access
Skip the SPA and go directly to:
- http://127.0.0.1:8000/calendar

### Option 3: Simple Calendar Fallback
The app has a fallback to CalendarViewSimple if the main component fails to load.

## Files Involved

1. **Frontend Components**:
   - `frontend/public/components/CalendarViewLocal.js` - Main calendar component
   - `frontend/public/app.js` - SPA that loads the calendar
   - `frontend/public/index.html` - Loads all components

2. **Backend API**:
   - `app/api/calendar.py` - Calendar API endpoints
   - `main.py` - Routes including `/calendar`

3. **Static Files**:
   - `static/calendar-local.html` - Standalone calendar HTML

## Quick Fix Script

Run this to diagnose and fix issues:
```bash
./fix_calendar_tab.sh
```

This will:
- Check if server is running
- Test API endpoints
- Provide troubleshooting steps

## Summary

The calendar tab should now work by:
1. Starting the server: `uvicorn app.main:app --reload`
2. Opening: http://127.0.0.1:8000
3. Clicking the Calendar tab

The component will:
- Load automatically when CalendarWrapper checks for it
- Connect to the local API
- Display the full calendar interface
- Handle errors gracefully

If issues persist, check the browser console and server logs for specific error messages.