#!/bin/bash

# Fix Calendar Tab for Local Development
echo "🔧 Fixing Calendar Tab for Local Development"
echo "============================================"

# Check if server is running
if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "⚠️  Server not running. Starting it now..."
    uvicorn app.main:app --reload --port 8000 &
    sleep 3
fi

# Test calendar API
echo "✅ Testing Calendar API..."
if curl -s http://127.0.0.1:8000/api/calendar/health | grep -q "healthy"; then
    echo "   Calendar API is working!"
else
    echo "   ⚠️ Calendar API not responding"
fi

# Test calendar routes
echo "✅ Testing Calendar Routes..."
if curl -s http://127.0.0.1:8000/calendar > /dev/null; then
    echo "   /calendar route is working!"
else
    echo "   ⚠️ /calendar route not found"
fi

echo ""
echo "📋 Instructions to test the Calendar tab:"
echo "============================================"
echo "1. Open: http://127.0.0.1:8000"
echo "2. Login if needed (use any email)"
echo "3. Click on the 'Calendar' tab in the sidebar"
echo ""
echo "If the calendar doesn't load:"
echo "  - Check browser console (F12) for errors"
echo "  - Try refreshing the page (Ctrl+F5)"
echo "  - Make sure all files are saved"
echo ""
echo "Alternative URLs to test:"
echo "  - Direct calendar: http://127.0.0.1:8000/calendar"
echo "  - Local calendar: http://127.0.0.1:8000/calendar-local"
echo "  - API docs: http://127.0.0.1:8000/docs#/Calendar"