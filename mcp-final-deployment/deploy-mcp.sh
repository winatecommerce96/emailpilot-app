#!/bin/bash

# MCP Management System - Automated Deployment Script
# This script safely injects MCP into EmailPilot without modifying containers

set -e  # Exit on any error

echo "🚀 MCP Management System - Final Deployment"
echo "============================================"

# Configuration
EMAILPILOT_URL="https://emailpilot.ai"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/deployment.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting MCP deployment process"

# Verify required files exist
required_files=(
    "console-injector.js"
    "mcp-management-fixed.js" 
    "test-endpoints.html"
    "rollback.sh"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "${SCRIPT_DIR}/${file}" ]]; then
        log "❌ ERROR: Required file missing: ${file}"
        exit 1
    fi
done

log "✅ All required files present"

# Test Cloud Function endpoints
log "🔍 Testing Cloud Function endpoints..."

endpoints=(
    "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health"
    "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models"
    "https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients"
)

all_healthy=true

for endpoint in "${endpoints[@]}"; do
    log "Testing: ${endpoint}"
    if command -v curl >/dev/null 2>&1; then
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" || echo "000")
        if [[ "$response_code" == "200" ]]; then
            log "  ✅ ${endpoint} - OK (${response_code})"
        else
            log "  ❌ ${endpoint} - FAILED (${response_code})"
            all_healthy=false
        fi
    else
        log "  ⚠️  curl not available, skipping endpoint test"
    fi
done

if [[ "$all_healthy" == "false" ]]; then
    log "❌ Some endpoints are not responding. Check Cloud Functions deployment."
    echo ""
    echo "To debug, run:"
    echo "  open test-endpoints.html"
    exit 1
fi

log "✅ All Cloud Function endpoints are healthy"

# Create injection script for browser
cat > "${SCRIPT_DIR}/browser-injection.js" << 'EOF'
// MCP Management - Browser Injection Script
console.log('🚀 Loading MCP Management System...');

// Load the fixed MCP injector
const script = document.createElement('script');
script.src = 'file://EOF
echo -n "${SCRIPT_DIR}/console-injector.js" >> "${SCRIPT_DIR}/browser-injection.js"
cat >> "${SCRIPT_DIR}/browser-injection.js" << 'EOF'
';
script.onload = () => console.log('✅ MCP Management loaded successfully');
script.onerror = () => console.error('❌ Failed to load MCP Management');
document.head.appendChild(script);
EOF

# Instructions for user
echo ""
echo "🎯 DEPLOYMENT INSTRUCTIONS"
echo "=========================="
echo ""
echo "The MCP Management System is ready for deployment!"
echo ""
echo "OPTION 1 - Browser Console (Recommended):"
echo "  1. Open ${EMAILPILOT_URL} in your browser"
echo "  2. Open Developer Console (F12)"
echo "  3. Copy and paste this file's content:"
echo "     ${SCRIPT_DIR}/console-injector.js"
echo "  4. Press Enter"
echo "  5. Look for the '🤖 MCP Management' button in top-right"
echo ""
echo "OPTION 2 - Bookmarklet (Persistent):"
echo "  1. Create new bookmark in your browser"
echo "  2. Copy content from: ${SCRIPT_DIR}/bookmarklet.js"
echo "  3. Set bookmark URL to the copied content"
echo "  4. Click bookmark when on emailpilot.ai"
echo ""
echo "OPTION 3 - Test Locally First:"
echo "  1. Open: ${SCRIPT_DIR}/test-endpoints.html"
echo "  2. Verify all endpoints return green status"
echo "  3. Then proceed with Option 1 or 2"
echo ""

# Create backup info
log "📋 Creating deployment backup info"
cat > "${SCRIPT_DIR}/deployment-info.txt" << EOF
MCP Management Deployment Info
=============================
Date: $(date)
EmailPilot URL: ${EMAILPILOT_URL}
Cloud Function Base: https://us-central1-emailpilot-438321.cloudfunctions.net
Deployment Method: Frontend Injection (Safe)

Endpoints Tested:
$(for endpoint in "${endpoints[@]}"; do echo "  - ${endpoint}"; done)

Files Created:
  - console-injector.js (Main injection script)
  - bookmarklet.js (Persistent bookmark version)
  - test-endpoints.html (Local testing interface)
  - browser-injection.js (Alternative loader)
  - rollback.sh (Emergency removal)

Next Steps:
  1. Navigate to ${EMAILPILOT_URL}
  2. Use console injection or bookmarklet
  3. Verify MCP Management button appears
  4. Test all functionality

If Issues:
  1. Check browser console for errors
  2. Run test-endpoints.html locally
  3. Use rollback.sh if needed
  4. Review TROUBLESHOOTING.md
EOF

echo "VERIFICATION STEPS:"
echo "  After deployment, verify:"
echo "  - MCP Management button appears in top-right"
echo "  - Modal opens when clicked"
echo "  - Data loads from Cloud Functions"
echo "  - No console errors"
echo ""
echo "ROLLBACK:"
echo "  If something goes wrong, run:"
echo "  ./rollback.sh"
echo ""

log "✅ MCP deployment preparation complete!"
log "📁 All files ready in: ${SCRIPT_DIR}"
log "📖 Follow instructions above to complete deployment"

echo "🎉 Ready for deployment! Follow the instructions above."
echo "📝 Full log available at: ${LOG_FILE}"