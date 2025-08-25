#!/bin/bash

# Frontend Fix Script - Resolves component loading and caching issues
set -e

echo "==================================================="
echo "EmailPilot Frontend Fix Script"
echo "==================================================="
echo ""

# 1. Fix the build script to properly compile app.js
echo "1. Fixing build script to properly handle app.js..."
if [[ -f "scripts/build_frontend.sh" ]]; then
    # Backup original
    cp scripts/build_frontend.sh scripts/build_frontend.sh.backup
    
    # Fix the app.js compilation issue
    sed -i '' 's|frontend/public/components/app.js|frontend/public/app.js|g' scripts/build_frontend.sh
    echo "   ✅ Fixed app.js path in build script"
fi

# 2. Add cache busting to index.html
echo "2. Adding cache busting to prevent stale assets..."
TIMESTAMP=$(date +%s)
if [[ -f "frontend/public/index.html" ]]; then
    # Add timestamp to app.js script tag
    sed -i '' "s|/static/dist/app.js\"|/static/dist/app.js?v=${TIMESTAMP}\"|g" frontend/public/index.html
    echo "   ✅ Added cache busting to app.js (v=${TIMESTAMP})"
fi

# 3. Ensure DeveloperTools is in the component list
echo "3. Adding DeveloperTools to build components list..."
if ! grep -q "DeveloperTools" scripts/build_frontend.sh; then
    # Add DeveloperTools to the JSX_COMPONENTS array
    sed -i '' '/^JSX_COMPONENTS=/a\
    "DeveloperTools"
' scripts/build_frontend.sh
    echo "   ✅ Added DeveloperTools to build list"
else
    echo "   ✅ DeveloperTools already in build list"
fi

# 4. Rebuild everything with the fixes
echo "4. Rebuilding frontend with fixes..."
npm run build

# 5. Create a version file to track builds
echo "5. Creating version tracking..."
echo "{
  \"version\": \"${TIMESTAMP}\",
  \"buildDate\": \"$(date)\",
  \"fixes\": [
    \"Fixed app.js compilation path\",
    \"Added cache busting\",
    \"Added DeveloperTools to build\",
    \"Rebuilt all components\"
  ]
}" > frontend/public/dist/build-version.json
echo "   ✅ Created build version file"

# 6. Clear any service workers
echo "6. Creating service worker cleanup script..."
cat > frontend/public/clear-cache.js << 'EOF'
// Clear service workers and caches
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for(let registration of registrations) {
            registration.unregister();
            console.log('Service worker unregistered');
        }
    });
}

// Clear caches
if ('caches' in window) {
    caches.keys().then(function(names) {
        for (let name of names) {
            caches.delete(name);
            console.log('Cache cleared:', name);
        }
    });
}

// Force reload
setTimeout(() => {
    window.location.reload(true);
}, 100);
EOF
echo "   ✅ Created cache clearing script"

echo ""
echo "==================================================="
echo "Fix Complete! Next Steps:"
echo "==================================================="
echo ""
echo "1. Restart the server:"
echo "   pkill -f uvicorn || true"
echo "   uvicorn main_firestore:app --port 8000 --host localhost --reload"
echo ""
echo "2. Clear browser cache:"
echo "   - Open browser DevTools (F12)"
echo "   - Right-click the refresh button"
echo "   - Select 'Empty Cache and Hard Reload'"
echo ""
echo "3. Test the Developer Tools:"
echo "   - Navigate to http://localhost:8000/admin"
echo "   - Click 'Developer Tools' in Quick Actions"
echo "   - OR navigate to http://localhost:8000/test-dev-tools.html"
echo ""
echo "Build version: ${TIMESTAMP}"
echo "==================================================="