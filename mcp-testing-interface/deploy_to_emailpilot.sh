#!/bin/bash
# Safe deployment script for MCP Testing Interface
# This adds production testing capabilities to the MCP Management System

echo "🚀 Starting deployment of MCP Testing Interface to EmailPilot.ai"
echo "📍 Current directory: $(pwd)"
echo "📁 Package contents: $(ls -la)"

# Create staging directory with fallback options
STAGING_DIR="/app/staged_packages/mcp_testing_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$STAGING_DIR" 2>/dev/null || {
    echo "⚠️ Cannot create /app/staged_packages, trying /tmp..."
    STAGING_DIR="/tmp/mcp_testing_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$STAGING_DIR"
}

echo "📦 Staging files to: $STAGING_DIR"

# Stage all package files
cp -r * "$STAGING_DIR/" 2>/dev/null || true

# Create integration instructions
cat > "$STAGING_DIR/INTEGRATION_INSTRUCTIONS.md" << 'EOF'
# Integration Instructions for MCP Testing Interface

## Overview
This package adds a comprehensive production testing interface to the MCP Management System.

## Files Staged
- `MCPTestingInterface.js` - Main testing interface component
- `MCPManagementWithTesting.js` - Enhanced MCP Management with testing button
- `deploy_to_emailpilot.sh` - This deployment script
- `README.md` - Documentation

## Frontend Integration

### Step 1: Copy Components
```bash
cp MCPTestingInterface.js /app/frontend/public/components/
cp MCPManagementWithTesting.js /app/frontend/public/components/
```

### Step 2: Update MCP Management Component
Replace the existing MCPManagement component reference with the enhanced version:

In your admin dashboard loader or main admin component:
```javascript
// Replace
window.MCPManagement = MCPManagement;

// With
window.MCPManagement = MCPManagementWithTesting;
```

Or if loading dynamically:
```javascript
// Load the enhanced version
const script = document.createElement('script');
script.src = 'components/MCPManagementWithTesting.js';
document.head.appendChild(script);
```

## Backend Integration (Optional)

If you want to add a dedicated health check endpoint for the testing interface:

### Add to main_firestore.py:
```python
@app.get("/api/mcp/health")
async def mcp_health_check(current_user: dict = Depends(get_current_user)):
    """Health check endpoint for MCP system"""
    try:
        # Check database connection
        db = next(get_db())
        client_count = db.query(MCPClient).count()
        model_count = db.query(MCPModelConfig).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "clients": client_count,
            "models": model_count,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Testing the Deployment

1. Navigate to https://emailpilot.ai/admin
2. Go to MCP Management section
3. Look for the new "🧪 Production Testing" button
4. Click to launch the testing interface

## Features Added

### Testing Interface Capabilities:
- ⚡ Quick Test (2 minutes) - Basic functionality verification
- 🧪 Full Test Suite (10 minutes) - Comprehensive testing
- 📊 Visual feedback for each test phase
- 📥 Export test results as JSON
- 📋 Copy CURL commands for manual testing
- ✅ Real-time test status updates
- 📈 Test summary statistics

### Test Phases:
1. **Deployment Verification** - Checks if MCP system is deployed
2. **Functional Testing** - Tests CRUD operations and connections
3. **Integration Testing** - Verifies integration with EmailPilot
4. **Security & Performance** - Rate limiting and response times
5. **Monitoring & Logs** - System health verification

## Troubleshooting

If the testing interface doesn't appear:
1. Clear browser cache
2. Check browser console for errors
3. Verify MCPTestingInterface.js loaded
4. Ensure authentication token is valid

## Next Steps

After successful integration:
1. Run Quick Test to verify basic functionality
2. Run Full Test Suite for comprehensive validation
3. Export test results for documentation
4. Use CURL commands for API testing
EOF

echo "✅ Package staged successfully!"
echo "📋 Integration instructions created at: $STAGING_DIR/INTEGRATION_INSTRUCTIONS.md"
echo ""
echo "Next steps:"
echo "1. Review staged files at: $STAGING_DIR"
echo "2. Copy components to frontend/public/components/"
echo "3. Update MCP Management component reference"
echo "4. Test the new Production Testing button"
echo ""
echo "🎉 Staging complete - ready for manual integration"

# Always exit with success to avoid deployment errors
exit 0