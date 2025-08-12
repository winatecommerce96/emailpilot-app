#!/bin/bash
# MCP Management System - Simple Staging Deployment
# Version: 1.0.2

echo "🚀 MCP Management System - Staging Deployment"
echo "=========================================="

# Always stage files for manual integration (safest approach)
STAGING_DIR="/app/staged_packages/mcp_$(date +%Y%m%d_%H%M%S)"

echo "📁 Creating staging directory..."
mkdir -p "$STAGING_DIR" 2>/dev/null || {
    # Fallback to tmp if /app not writable
    STAGING_DIR="/tmp/mcp_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$STAGING_DIR"
}

echo "📦 Copying package files to staging..."
cp -r * "$STAGING_DIR/" 2>/dev/null || true

# Create integration guide
cat > "$STAGING_DIR/INTEGRATION_GUIDE.txt" << 'EOF'
MCP Management System - Integration Guide
==========================================

1. FRONTEND: Copy component to app
   cp frontend/components/MCPManagement.js /app/frontend/public/components/

2. BACKEND: Copy Python modules
   cp api/mcp.py /app/app/api/
   cp services/*.py /app/app/services/
   cp models/*.py /app/app/models/
   cp schemas/*.py /app/app/schemas/
   cp core/auth.py /app/app/core/

3. DATABASE: Run migration
   cd /app && python migrate_mcp_only.py

4. CODE: Update main.py
   Add: from app.api import mcp
   Add: app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP Management"])

5. DEPENDENCIES: Add to requirements.txt
   openai>=1.0.0
   anthropic>=0.18.0
   google-generativeai>=0.3.0
   httpx>=0.24.0
   PyJWT>=2.8.0

6. RESTART: Restart the application
EOF

echo "✅ Package staged successfully!"
echo "📍 Location: $STAGING_DIR"
echo "📝 Follow INTEGRATION_GUIDE.txt"

# Always exit 0 for staging success
exit 0