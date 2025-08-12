# EmailPilot Calendar Implementation Guide

## ⚠️ IMPORTANT: Correct Implementation

This guide ensures you're using the correct calendar implementation and avoiding conflicts with old versions.

## ✅ Current Working Implementation

The **ONLY** correct calendar implementation is integrated into the main EmailPilot application:

- **Main Application File**: `main_firestore.py`
- **Frontend Components**: `frontend/public/components/`
- **API Endpoints**: `app/api/calendar.py`
- **Database**: Google Firestore (cloud-based)

## 🚫 Old Implementations to Avoid

The following directories contain OLD implementations that should NOT be used:

- `calendar-project/` - Old standalone calendar app
- `calendar-implementation-complete/` - Previous attempt
- `emailpilot_calendar_tab_*/` - Old tab implementations
- Any ZIP files with "calendar" in the name

## 🚀 Starting the Server Correctly

### Method 1: Using Verification Script (Recommended)
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
./verify_and_start.sh
```

### Method 2: Using Makefile
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
make dev
```

### Method 3: Direct uvicorn Command
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
uvicorn main_firestore:app --reload --port 8000
```

## 🗄️ Archiving Old Implementations

If you still have old calendar directories, archive them:

```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
./archive_old_calendars.sh
```

This will move all old implementations to an archive folder with a timestamp.

## 📁 Directory Structure

```
emailpilot-app/
├── main_firestore.py          # ✅ MAIN APPLICATION (use this!)
├── main.py                     # Alternative simple version
├── app/
│   ├── api/
│   │   ├── calendar.py        # Calendar API endpoints
│   │   ├── goals.py           # Goals API endpoints
│   │   └── auth.py            # Authentication
│   ├── services/
│   │   └── mcp_service.py     # MCP integration
│   └── models/
│       └── calendar.py        # Calendar data models
├── frontend/
│   └── public/
│       ├── index.html         # Main HTML
│       ├── app.js             # Main React app
│       └── components/
│           ├── CalendarView.js         # Main calendar component
│           ├── Calendar.js             # Calendar grid
│           ├── EventModal.js          # Event editor
│           └── CalendarChat.js        # AI chat
└── Makefile                   # Development commands
```

## ❌ Common Mistakes to Avoid

1. **DO NOT** run any `main.py` from `calendar-project/` directory
2. **DO NOT** import or reference old calendar implementations
3. **DO NOT** use standalone calendar HTML files
4. **DO NOT** run multiple calendar servers simultaneously

## ✅ Verification Checklist

Before starting development, verify:

- [ ] You're in `/emailpilot-app/` directory
- [ ] You're using `main_firestore.py`
- [ ] Port 8000 is available
- [ ] No old calendar processes are running
- [ ] Frontend loads from `frontend/public/`

## 🔍 Troubleshooting

### "Old calendar-project detected in path" Error
- You're running from the wrong directory
- Solution: `cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app`

### Port 8000 Already in Use
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Restart
uvicorn main_firestore:app --reload --port 8000
```

### Calendar Not Loading
1. Check browser console for errors
2. Verify API is responding: `curl http://localhost:8000/api/calendar/health`
3. Check that all components are loaded in `index.html`

## 📞 Quick Commands Reference

```bash
# Start server with verification
./verify_and_start.sh

# Archive old calendars
./archive_old_calendars.sh

# Quick restart
make restart

# Check health
make health

# View logs
make logs
```

## 🎯 Key Points to Remember

1. **One Implementation**: Only use the integrated EmailPilot calendar
2. **Correct File**: Always start with `main_firestore.py`
3. **Right Directory**: Work from `/emailpilot-app/`
4. **Archive Old Code**: Keep workspace clean by archiving old implementations
5. **Use Scripts**: Leverage verification and startup scripts for safety

---

Last Updated: December 2024
Current Working Implementation: main_firestore.py with integrated calendar