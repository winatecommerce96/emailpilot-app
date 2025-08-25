#!/bin/bash

echo "📅 Calendar Debug Harness Verification"
echo "======================================"
echo ""

# Check if server is running
echo "1️⃣ Checking if server is running..."
if curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:8000/health | grep -q "200"; then
    echo "✅ Server is running"
else
    echo "❌ Server is not running or not responding"
    echo "   Start with: uvicorn main_firestore:app --port 8000 --host localhost --reload"
    exit 1
fi

echo ""
echo "2️⃣ Checking production calendar page..."
if [ -f "frontend/public/calendar.html" ]; then
    echo "✅ Production calendar.html exists"
    lines=$(wc -l < frontend/public/calendar.html)
    echo "   File has $lines lines"
else
    echo "❌ Production calendar.html not found"
fi

echo ""
echo "3️⃣ Checking debug calendar page..."
if [ -f "frontend/public/calendar_debug.html" ]; then
    echo "✅ Debug calendar_debug.html exists"
    lines=$(wc -l < frontend/public/calendar_debug.html)
    echo "   File has $lines lines"
    
    # Check for key debug features
    if grep -q "DEBUG_STATE" frontend/public/calendar_debug.html; then
        echo "   ✅ Debug state tracking present"
    fi
    
    if grep -q "debug-overlay" frontend/public/calendar_debug.html; then
        echo "   ✅ Debug overlay present"
    fi
    
    if grep -q "Ctrl+Alt+D" frontend/public/calendar_debug.html; then
        echo "   ✅ Keyboard shortcut documented"
    fi
else
    echo "❌ Debug calendar_debug.html not found"
fi

echo ""
echo "4️⃣ Checking routes in main_firestore.py..."
if grep -q "@app.get(\"/calendar\")" main_firestore.py; then
    echo "✅ /calendar route present"
else
    echo "❌ /calendar route missing"
fi

if grep -q "@app.get(\"/calendar-debug\")" main_firestore.py; then
    echo "✅ /calendar-debug route present"
else
    echo "❌ /calendar-debug route missing"
fi

echo ""
echo "5️⃣ Comparing key elements between pages..."
if [ -f "frontend/public/calendar.html" ] && [ -f "frontend/public/calendar_debug.html" ]; then
    # Check if both use same CSS
    prod_css=$(grep -o 'href="[^"]*\.css"' frontend/public/calendar.html | sort)
    debug_css=$(grep -o 'href="[^"]*\.css"' frontend/public/calendar_debug.html | sort)
    
    if [ "$prod_css" = "$debug_css" ]; then
        echo "✅ CSS includes match"
    else
        echo "❌ CSS includes differ"
    fi
    
    # Check if both have same main structure
    for element in "nav-root" "calendar-root"; do
        if grep -q "id=\"$element\"" frontend/public/calendar.html && \
           grep -q "id=\"$element\"" frontend/public/calendar_debug.html; then
            echo "✅ Both have $element"
        else
            echo "❌ Element $element mismatch"
        fi
    done
fi

echo ""
echo "======================================"
echo "📊 Summary:"
echo ""
echo "Production URL:  http://localhost:8000/calendar"
echo "Debug URL:       http://localhost:8000/calendar-debug"
echo "Debug w/ overlay: http://localhost:8000/calendar-debug?debug=1"
echo ""
echo "To toggle debug overlay: Press Ctrl+Alt+D"
echo ""
echo "✅ Calendar Debug Harness is ready for testing!"