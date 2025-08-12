#!/bin/bash
# Manual Fix Script for MCP Auto-Integration Deployment
# This script manually performs the integration steps that should have happened automatically

echo "🔧 Manual MCP Integration Fix Script"
echo "===================================="

# Find the most recent MCP deployment
echo "🔍 Looking for MCP deployment files..."

# Check possible staging locations
STAGING_LOCATIONS=(
    "/app/staged_packages/mcp_auto_*"
    "/app/staged_packages/mcp-auto-*" 
    "/tmp/mcp_auto_*"
    "/tmp/mcp-auto-*"
    "/app/packages/mcp*"
)

FOUND_PACKAGE=""
for location in "${STAGING_LOCATIONS[@]}"; do
    if ls $location 1> /dev/null 2>&1; then
        FOUND_PACKAGE=$(ls -td $location | head -1)
        break
    fi
done

if [ -z "$FOUND_PACKAGE" ]; then
    echo "❌ Could not find MCP package files in staging directories"
    echo "   Checked locations:"
    for location in "${STAGING_LOCATIONS[@]}"; do
        echo "   - $location"
    done
    echo ""
    echo "Please run: find /app -name '*mcp*' -type d 2>/dev/null"
    echo "Or:         find /tmp -name '*mcp*' -type d 2>/dev/null"
    exit 1
fi

echo "✅ Found MCP package at: $FOUND_PACKAGE"

# Backup main_firestore.py
echo ""
echo "💾 Creating backup of main_firestore.py..."
BACKUP_DIR="/app/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/main_firestore.backup.$(date +%Y%m%d_%H%M%S).py"

MAIN_FILE="/app/main_firestore.py"
if [ ! -f "$MAIN_FILE" ]; then
    # Try alternative locations
    for alt in "/app/main.py" "./main_firestore.py" "./main.py"; do
        if [ -f "$alt" ]; then
            MAIN_FILE="$alt"
            break
        fi
    done
fi

if [ -f "$MAIN_FILE" ]; then
    cp "$MAIN_FILE" "$BACKUP_FILE"
    echo "✅ Backup created: $BACKUP_FILE"
else
    echo "❌ Could not find main application file"
    exit 1
fi

# Check if MCP is already integrated
echo ""
echo "🔍 Checking current integration status..."
if grep -q "from app.api.mcp import router as mcp_router" "$MAIN_FILE" 2>/dev/null; then
    echo "ℹ️  MCP router import already exists"
    
    if grep -q 'app.include_router.*mcp.*prefix="/api/mcp"' "$MAIN_FILE" 2>/dev/null; then
        echo "✅ MCP routes already registered - integration may be complete"
        echo "   Checking if service restart is needed..."
        
        # Test if endpoints are working
        if curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/api/mcp/models" | grep -q "401\|200"; then
            echo "✅ MCP endpoints are responding - integration is complete!"
            echo "   No further action needed."
            exit 0
        else
            echo "⚠️  Routes registered but endpoints not responding - service restart needed"
        fi
    else
        echo "⚠️  Import exists but router not registered"
    fi
else
    echo "❌ MCP not integrated - performing full integration"
fi

# Integrate MCP routes into main_firestore.py
echo ""
echo "🔧 Integrating MCP routes into main_firestore.py..."

# Use Python to safely modify the file
python3 << EOF
import re

# Read the main file
with open('$MAIN_FILE', 'r') as f:
    content = f.read()

modified = False

# Add MCP import if not present
mcp_import = 'from app.api.mcp import router as mcp_router'
if mcp_import not in content:
    # Find the last app.api import and add after it
    import_pattern = r'(from app\.api\.[^\n]*\n)'
    matches = list(re.finditer(import_pattern, content))
    if matches:
        pos = matches[-1].end()
        content = content[:pos] + mcp_import + '\n' + content[pos:]
        print("✅ Added MCP router import")
        modified = True
    else:
        # Find any app import and add after it
        app_import = re.search(r'(from app\.[^\n]*\n)', content)
        if app_import:
            pos = app_import.end()
            content = content[:pos] + mcp_import + '\n' + content[pos:]
            print("✅ Added MCP router import after app imports")
            modified = True

# Add router registration if not present
router_reg = 'app.include_router(mcp_router, prefix="/api/mcp", tags=["mcp"])'
if router_reg not in content:
    # Find existing router registrations and add after them
    router_pattern = r'(app\.include_router\([^\n]*\n)'
    match = re.search(router_pattern, content)
    if match:
        pos = match.end()
        content = content[:pos] + router_reg + '\n' + content[pos:]
        print("✅ Added MCP router registration")
        modified = True
    else:
        print("⚠️  Could not find router registration section")
        print("    Please manually add: " + router_reg)

if modified:
    # Write the modified content back
    with open('$MAIN_FILE', 'w') as f:
        f.write(content)
    print("✅ main_firestore.py updated successfully")
else:
    print("ℹ️  No changes needed to main_firestore.py")
EOF

# Copy MCP files to correct locations
echo ""
echo "📂 Installing MCP files to application directories..."

declare -A FILE_MAP=(
    ["api/mcp.py"]="/app/app/api/mcp.py"
    ["services/mcp_service.py"]="/app/app/services/mcp_service.py"
    ["services/secret_manager.py"]="/app/app/services/secret_manager.py"
    ["models/mcp_client.py"]="/app/app/models/mcp_client.py"
    ["schemas/mcp_client.py"]="/app/app/schemas/mcp_client.py"
    ["core/auth.py"]="/app/app/core/auth.py"
)

for src_file in "${!FILE_MAP[@]}"; do
    dest_file="${FILE_MAP[$src_file]}"
    src_path="$FOUND_PACKAGE/$src_file"
    
    if [ -f "$src_path" ]; then
        # Create destination directory if needed
        dest_dir=$(dirname "$dest_file")
        mkdir -p "$dest_dir"
        
        # Copy file
        cp "$src_path" "$dest_file"
        echo "  ✅ $src_file -> $dest_file"
    else
        echo "  ⚠️  Source file not found: $src_path"
    fi
done

# Run database migration
echo ""
echo "🗄️  Running MCP database migration..."
if [ -f "$FOUND_PACKAGE/migrate_mcp_only.py" ]; then
    cd "$FOUND_PACKAGE"
    if python3 migrate_mcp_only.py; then
        echo "✅ Database migration completed successfully"
    else
        echo "⚠️  Database migration encountered issues - check logs"
    fi
    cd - > /dev/null
else
    echo "⚠️  Migration script not found - database setup may be incomplete"
fi

# Restart Cloud Run service
echo ""
echo "🔄 Restarting Cloud Run service..."
SERVICE_NAME="emailpilot-api"
REGION="us-central1"

if command -v gcloud &> /dev/null; then
    echo "📡 Updating service to trigger restart..."
    
    # Add timestamp to trigger new revision
    ENV_VAR="MCP_INTEGRATION_COMPLETE=$(date +%s)"
    
    if gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --set-env-vars="$ENV_VAR" \
        --quiet 2>/dev/null; then
        
        echo "✅ Service restart initiated"
        echo "⏱️  Waiting 30 seconds for service to become ready..."
        sleep 30
        
    else
        echo "⚠️  gcloud update failed - trying alternative method..."
        
        if gcloud run services update-traffic "$SERVICE_NAME" \
            --region="$REGION" \
            --to-latest \
            --quiet 2>/dev/null; then
            echo "✅ Service restart via traffic update"
            sleep 30
        else
            echo "❌ Could not restart service via gcloud"
            echo "   Please manually restart via Google Cloud Console"
        fi
    fi
else
    echo "❌ gcloud not available - manual restart required"
    echo "   Please restart via Google Cloud Console or:"
    echo "   gcloud run services update $SERVICE_NAME --region=$REGION"
fi

# Verify integration
echo ""
echo "🧪 Verifying MCP integration..."
echo "  Testing /api/mcp/models endpoint..."

# Wait a bit more for service to be ready
sleep 15

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/api/mcp/models")
if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "200" ]]; then
    echo "  ✅ MCP models endpoint responding (HTTP $HTTP_CODE)"
    MODELS_OK=true
else
    echo "  ❌ MCP models endpoint failed (HTTP $HTTP_CODE)"
    MODELS_OK=false
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://emailpilot.ai/api/mcp/clients")
if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "200" ]]; then
    echo "  ✅ MCP clients endpoint responding (HTTP $HTTP_CODE)"
    CLIENTS_OK=true
else
    echo "  ❌ MCP clients endpoint failed (HTTP $HTTP_CODE)"
    CLIENTS_OK=false
fi

# Overall result
echo ""
echo "🎯 INTEGRATION COMPLETE"
echo "======================"

if [[ "$MODELS_OK" == true && "$CLIENTS_OK" == true ]]; then
    echo "✅ SUCCESS: MCP integration is fully functional!"
    echo ""
    echo "🧪 Next Steps:"
    echo "  1. Go to https://emailpilot.ai/admin → MCP Management"
    echo "  2. The interface should now work without 404 errors"
    echo "  3. Create your first MCP client configuration"
    echo "  4. Run the production testing interface"
else
    echo "⚠️  PARTIAL SUCCESS: Integration completed but some endpoints not responding"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  1. Check service logs: gcloud run logs read --service=$SERVICE_NAME"
    echo "  2. Verify service is running: curl https://emailpilot.ai/health"
    echo "  3. Allow more time for service startup (may take 1-2 minutes)"
fi

echo ""
echo "📄 Backup available for rollback: $BACKUP_FILE"
echo "🔗 Service URL: https://emailpilot.ai"

# Create rollback script
cat > "$BACKUP_DIR/rollback_mcp.sh" << EOF
#!/bin/bash
echo "🔄 Rolling back MCP integration..."
cp "$BACKUP_FILE" "$MAIN_FILE"
echo "✅ main_firestore.py restored from backup"
echo "Please restart the service manually:"
echo "gcloud run services update $SERVICE_NAME --region=$REGION"
EOF

chmod +x "$BACKUP_DIR/rollback_mcp.sh"
echo "📜 Rollback script: $BACKUP_DIR/rollback_mcp.sh"