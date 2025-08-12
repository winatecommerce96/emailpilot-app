#!/bin/bash
# Safe deployment script for MCP Management System Package
# Version: 1.0.1
# Created: 2025-08-11

echo "🚀 Deploying MCP Management System to EmailPilot.ai"
echo "Version: 1.0.1"
echo "=========================================="

# Check if running in EmailPilot environment
if [ "$EMAILPILOT_DEPLOYMENT" = "true" ]; then
    echo "✅ Detected EmailPilot deployment environment"
    echo "📍 Current directory: $(pwd)"
    echo "📁 Directory contents:"
    ls -la
    
    # Find EmailPilot root directory - more flexible search
    EMAILPILOT_ROOT=""
    
    # Check multiple possible locations
    if [ -f "/app/main.py" ] || [ -f "/app/main_firestore.py" ]; then
        EMAILPILOT_ROOT="/app"
    elif [ -f "../main.py" ] || [ -f "../main_firestore.py" ]; then
        EMAILPILOT_ROOT=".."
    elif [ -f "../../main.py" ] || [ -f "../../main_firestore.py" ]; then
        EMAILPILOT_ROOT="../.."
    elif [ -f "../../../main.py" ] || [ -f "../../../main_firestore.py" ]; then
        EMAILPILOT_ROOT="../../.."
    else
        echo "⚠️ Could not find EmailPilot root directory automatically"
        echo "📍 Using /app as default root"
        EMAILPILOT_ROOT="/app"
    fi
    
    echo "📍 EmailPilot root found at: $EMAILPILOT_ROOT"
    
    # Copy frontend components
    if [ -d "frontend" ]; then
        echo "📦 Copying frontend components..."
        
        # Ensure components directory exists
        mkdir -p "$EMAILPILOT_ROOT/frontend/public/components" 2>/dev/null || true
        
        # Copy MCP Management component
        if [ -f "frontend/components/MCPManagement.js" ]; then
            cp frontend/components/MCPManagement.js "$EMAILPILOT_ROOT/frontend/public/components/" 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "  ✅ MCPManagement.js copied successfully"
            else
                echo "  ⚠️ Could not copy MCPManagement.js - will be staged for manual copy"
            fi
        else
            echo "  ⚠️ MCPManagement.js not found in package"
        fi
        
        echo "✅ Frontend components processing complete"
    else
        echo "ℹ️ No frontend components in package"
    fi
    
    # Stage backend components for manual integration
    if [ -d "api" ] || [ -d "services" ] || [ -d "models" ] || [ -d "schemas" ]; then
        INTEGRATION_DIR="$EMAILPILOT_ROOT/integrations/mcp_management_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$INTEGRATION_DIR" 2>/dev/null || INTEGRATION_DIR="/tmp/mcp_management_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$INTEGRATION_DIR" 2>/dev/null || true
        
        echo "📁 Staging backend components at: $INTEGRATION_DIR"
        
        # Copy API routes
        if [ -d "api" ]; then
            cp -r api "$INTEGRATION_DIR/"
            echo "  ✅ API routes staged"
        fi
        
        # Copy services
        if [ -d "services" ]; then
            cp -r services "$INTEGRATION_DIR/"
            echo "  ✅ Services staged"
        fi
        
        # Copy models
        if [ -d "models" ]; then
            cp -r models "$INTEGRATION_DIR/"
            echo "  ✅ Models staged"
        fi
        
        # Copy schemas
        if [ -d "schemas" ]; then
            cp -r schemas "$INTEGRATION_DIR/"
            echo "  ✅ Schemas staged"
        fi
        
        # Copy auth module
        if [ -d "core" ]; then
            cp -r core "$INTEGRATION_DIR/"
            echo "  ✅ Core modules staged"
        fi
        
        echo "✅ Backend files staged at: $INTEGRATION_DIR"
        
        # Create integration instructions
        cat > "$INTEGRATION_DIR/INTEGRATION_INSTRUCTIONS.md" << 'EOF'
# MCP Management System - Integration Instructions

## Backend Integration Steps

1. **Copy Python modules to app directory:**
   ```bash
   cp -r api/mcp.py ../../app/api/
   cp -r services/mcp_service.py ../../app/services/
   cp -r services/secret_manager.py ../../app/services/
   cp -r models/mcp_client.py ../../app/models/
   cp -r schemas/mcp_client.py ../../app/schemas/
   cp -r core/auth.py ../../app/core/
   ```

2. **Update main.py to include MCP router:**
   ```python
   from app.api import mcp
   app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP Management"])
   ```

3. **Run database migration:**
   ```bash
   python migrate_mcp_only.py
   ```

4. **Update requirements.txt with new dependencies:**
   - openai>=1.0.0
   - anthropic>=0.18.0
   - google-generativeai>=0.3.0
   - httpx>=0.24.0
   - PyJWT>=2.8.0

5. **Restart the application**

## Frontend Integration

The MCPManagement.js component has been automatically copied to the frontend/public/components directory.

To enable it in the admin interface:
1. The component should auto-load when accessing Admin > MCP Management tab
2. If not visible, check that the script is included in index.html

## Testing

After integration:
1. Access /api/mcp/models to verify API is working
2. Navigate to Admin > MCP Management in the UI
3. Add a test client with API keys
4. Test connections to different providers

EOF
        echo "  ✅ Integration instructions created"
    fi
    
    # Copy migration scripts
    if [ -f "migrate_mcp_only.py" ]; then
        echo "📄 Copying database migration script..."
        cp migrate_mcp_only.py "$EMAILPILOT_ROOT/"
        echo "  ✅ Migration script copied"
    fi
    
    # Copy test scripts
    if [ -f "test_compatibility.py" ]; then
        echo "🧪 Copying test script..."
        cp test_compatibility.py "$EMAILPILOT_ROOT/"
        echo "  ✅ Test script copied"
    fi
    
    # Copy documentation
    if [ -f "README.md" ]; then
        echo "📚 Copying documentation..."
        DOCS_DIR="$EMAILPILOT_ROOT/docs/packages"
        mkdir -p "$DOCS_DIR"
        cp README.md "$DOCS_DIR/MCP_MANAGEMENT_README.md"
        echo "  ✅ Documentation copied"
    fi
    
    echo ""
    echo "=========================================="
    echo "✅ MCP Management System deployment complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Backend components staged at: $INTEGRATION_DIR"
    echo "2. Follow INTEGRATION_INSTRUCTIONS.md for manual integration"
    echo "3. Run database migration: python migrate_mcp_only.py"
    echo "4. Restart the application"
    echo "5. Test at: /admin (MCP Management tab)"
    echo ""
    echo "⚠️  Note: Backend integration requires manual steps for safety"
    
    # Exit with success code
    exit 0
    
else
    echo "⚠️  This script must be run through EmailPilot Admin Dashboard"
    echo "Please upload the package ZIP file via the admin interface at:"
    echo "https://emailpilot.ai/admin"
    exit 1
fi