#!/bin/bash
# Rollback script for MCP Cloud Function Frontend Update
# Use this if the Cloud Function update causes issues

echo "🔄 Starting MCP Cloud Function Frontend Update Rollback..."

# Check if backup directory exists
BACKUP_BASE="/app/frontend/public/components/backups"
if [ ! -d "$BACKUP_BASE" ]; then
    echo "❌ No backup directory found at $BACKUP_BASE"
    echo "Cannot perform automatic rollback."
    exit 1
fi

# Find the most recent backup
LATEST_BACKUP=$(find "$BACKUP_BASE" -type d -name "20*" | sort -r | head -n1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup directories found"
    echo "Cannot perform automatic rollback."
    exit 1
fi

echo "📦 Found backup directory: $LATEST_BACKUP"

# Components directory
COMPONENTS_DIR="/app/frontend/public/components"

# Restore backed up components
echo "🔄 Restoring original components..."

if [ -f "$LATEST_BACKUP/MCPManagement.js.backup" ]; then
    cp "$LATEST_BACKUP/MCPManagement.js.backup" "$COMPONENTS_DIR/MCPManagement.js"
    echo "✅ Restored MCPManagement.js"
else
    echo "⚠️ MCPManagement.js backup not found"
fi

if [ -f "$LATEST_BACKUP/MCPTestingInterface.js.backup" ]; then
    cp "$LATEST_BACKUP/MCPTestingInterface.js.backup" "$COMPONENTS_DIR/MCPTestingInterface.js"
    echo "✅ Restored MCPTestingInterface.js"
else
    echo "⚠️ MCPTestingInterface.js backup not found"
fi

# Remove the mcp-config.js file that was added
if [ -f "$COMPONENTS_DIR/mcp-config.js" ]; then
    rm "$COMPONENTS_DIR/mcp-config.js"
    echo "✅ Removed mcp-config.js"
fi

echo ""
echo "✅ Rollback completed successfully!"
echo "📋 Summary:"
echo "   • Restored components from: $LATEST_BACKUP"
echo "   • Removed Cloud Function configuration"
echo "   • System should now use original /api/mcp/* endpoints"
echo ""
echo "⚠️ Note: You may need to restart the EmailPilot application for changes to take effect"
echo ""
echo "🔍 To verify rollback:"
echo "1. Check EmailPilot Admin Dashboard → MCP Management"
echo "2. Verify components are using /api/mcp/* endpoints again"
echo "3. Test MCP functionality"

exit 0