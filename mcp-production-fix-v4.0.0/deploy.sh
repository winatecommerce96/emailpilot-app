#!/bin/bash
# MCP Production Fix Deployment Script
# Version: 4.0.0 - With all lessons learned

set -e

echo "==========================================="
echo "MCP Management System - Production Fix v4.0"
echo "==========================================="
echo ""
echo "This deployment fixes the proxy dependency issue"
echo "by using direct Cloud Function URLs"
echo ""

# Create timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups/mcp-backup-$TIMESTAMP"

# Create backup directory
mkdir -p $BACKUP_DIR

echo "1. Creating backup of existing files..."
# Backup any existing MCP files
if [ -d "frontend/public/components" ]; then
    cp -r frontend/public/components $BACKUP_DIR/ 2>/dev/null || true
fi

echo "2. Installing fixed MCP components..."

# Create directories if they don't exist
mkdir -p frontend/public/components
mkdir -p static/js
mkdir -p public/js

# Copy fixed components to multiple locations to ensure they're found
cp frontend/MCPManagement-fixed.js frontend/public/components/MCPManagement.js
cp frontend/MCPManagement-fixed.js static/js/MCPManagement.js
cp frontend/MCPManagement-fixed.js public/js/MCPManagement.js

# Copy injection scripts
cp injection/console-injector-fixed.js static/js/mcp-injector.js
cp injection/console-injector-fixed.js public/js/mcp-injector.js

echo "3. Testing Cloud Function endpoints..."
bash test-endpoints.sh

echo "4. Creating browser injection helper..."
cat > browser-inject.txt << 'EOF'
INSTRUCTIONS FOR BROWSER INJECTION:
====================================
1. Go to https://emailpilot.ai
2. Open Developer Console (F12)
3. Copy and paste the contents of: injection/console-injector-fixed.js
4. Press Enter
5. Look for the "🤖 MCP Management" button in top-right corner

The button should appear immediately and clicking it will open the MCP interface.
All data will load from the Cloud Functions directly.
EOF

echo "5. Creating environment configuration..."
cat > .env.production << 'EOF'
# MCP Production Configuration
REACT_APP_MCP_MODELS_URL=https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models
REACT_APP_MCP_CLIENTS_URL=https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients
REACT_APP_MCP_HEALTH_URL=https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health
REACT_APP_MCP_ENABLED=true
EOF

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "The fixed MCP components have been installed."
echo ""
echo "IMPORTANT: Since we cannot modify the running container,"
echo "you need to inject MCP via the browser console:"
echo ""
echo "1. Open https://emailpilot.ai"
echo "2. Open browser console (F12)"
echo "3. Paste the contents of: injection/console-injector-fixed.js"
echo "4. The MCP button will appear in the top-right corner"
echo ""
echo "For persistent access, use the bookmarklet in: injection/bookmarklet.js"
echo ""
echo "Backup created at: $BACKUP_DIR"
echo ""
echo "To rollback: bash rollback.sh"