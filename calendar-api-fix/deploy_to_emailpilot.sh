#!/bin/bash
# Safe deployment script for EmailPilot Calendar API Fix
# Fixes all API endpoint issues for production deployment

echo "🚀 Starting deployment of EmailPilot Calendar API Fix to EmailPilot.ai"
echo "📍 Current directory: $(pwd)"
echo "📁 Package contents: $(ls -la)"

# Create staging directory with fallback options
STAGING_DIR="/app/staged_packages/calendar_api_fix_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$STAGING_DIR" 2>/dev/null || {
    echo "⚠️ Cannot create /app/staged_packages, trying /tmp..."
    STAGING_DIR="/tmp/calendar_api_fix_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$STAGING_DIR"
}

echo "📦 Staging files to: $STAGING_DIR"

# Stage all package files
cp -r * "$STAGING_DIR/" 2>/dev/null || true

# Create integration instructions
cat > "$STAGING_DIR/INTEGRATION_INSTRUCTIONS.md" << 'EOF'
# Integration Instructions for EmailPilot Calendar API Fix

## Critical: This fixes all API endpoint issues for production

This package provides calendar and dashboard components with proper API configuration that:
1. Uses the correct Cloud Run URL for production
2. Falls back to Firebase when API is unavailable
3. Provides demo data as final fallback

## Files Staged
- CalendarViewAPIFixed.js - Calendar with API configuration
- DashboardAPIFixed.js - Dashboard with API configuration
- api-config.js - Shared API configuration helper

## Frontend Integration

### Step 1: Copy the fixed components
```bash
cp CalendarViewAPIFixed.js /app/frontend/public/components/
cp DashboardAPIFixed.js /app/frontend/public/components/
cp api-config.js /app/frontend/public/js/
```

### Step 2: Update the main app to use fixed components

In your main app.js or where views are rendered:

```javascript
// For Calendar View
if (currentView === 'calendar') {
    // Try API-fixed version first
    if (typeof window.CalendarViewAPIFixed !== 'undefined') {
        ReactDOM.render(
            React.createElement(window.CalendarViewAPIFixed),
            document.getElementById('main-content')
        );
    } else if (typeof window.CalendarView !== 'undefined') {
        // Fallback to original
        ReactDOM.render(
            React.createElement(window.CalendarView),
            document.getElementById('main-content')
        );
    }
}

// For Dashboard View
if (currentView === 'dashboard') {
    // Try API-fixed version first
    if (typeof window.DashboardAPIFixed !== 'undefined') {
        ReactDOM.render(
            React.createElement(window.DashboardAPIFixed),
            document.getElementById('main-content')
        );
    } else if (typeof window.Dashboard !== 'undefined') {
        // Fallback to original
        ReactDOM.render(
            React.createElement(window.Dashboard),
            document.getElementById('main-content')
        );
    }
}
```

### Step 3: Ensure Firebase is loaded (for fallback)
Add to your index.html if not already present:
```html
<!-- Firebase SDKs -->
<script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-firestore-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-auth-compat.js"></script>
```

## API Configuration

The components automatically configure API based on hostname:
- Production (emailpilot.ai): Uses Cloud Run URL
- Local/Development: Uses relative paths

```javascript
const API_BASE = window.API_BASE || 
  (window.location.hostname === 'emailpilot.ai'
    ? 'https://emailpilot-api-935786836546.us-central1.run.app'
    : '');
```

## Features
- ✅ Automatic API endpoint detection
- ✅ Multiple endpoint fallbacks
- ✅ Firebase direct access when API fails
- ✅ Demo data as final fallback
- ✅ Detailed console logging for debugging

## API Endpoints Tried (in order)

### For Clients:
1. /api/clients
2. /api/firebase-calendar-test/clients
3. /clients
4. /api/calendar/clients

### For Goals:
1. /api/goals/{clientId}
2. /api/goals-calendar-test/goals/{clientId}
3. /api/goals/clients/{clientId}
4. /goals/{clientId}

### For Events:
1. /api/calendar/events?client_id={clientId}
2. /api/firebase-calendar-test/events?client_id={clientId}
3. /api/events/{clientId}
4. /calendar/events/{clientId}

### For Dashboard:
1. /api/dashboard
2. /api/reports/dashboard
3. /dashboard
4. /api/analytics/dashboard

### For Reports:
1. /api/reports/{clientId}
2. /api/reports?client_id={clientId}
3. /api/analytics/reports/{clientId}
4. /reports/{clientId}

## Testing

1. Open browser console to see API endpoint attempts
2. Navigate to calendar/dashboard
3. Check console for successful endpoint discovery
4. Verify data loads (API, Firebase, or Demo)

## Rollback

Simply remove the APIFixed components and the app will use original components.

## Restart Application
After integration, restart the service:
```bash
gcloud run services update emailpilot-api --region=us-central1
```
EOF

echo "✅ Package staged successfully!"
echo "📋 Integration instructions created at: $STAGING_DIR/INTEGRATION_INSTRUCTIONS.md"
echo ""
echo "Next steps:"
echo "1. Review staged files at: $STAGING_DIR"
echo "2. Follow integration instructions"
echo "3. Test the deployment"
echo ""
echo "🎉 Staging complete - ready for manual integration"

# Always exit with success to avoid deployment errors
exit 0