#!/bin/bash
# MCP Rollback Script

echo "MCP Management Rollback"
echo "======================="
echo ""

echo "This will remove MCP components from the browser."
echo ""

echo "To remove MCP from the current session:"
echo "1. Open browser console (F12)"
echo "2. Run this command:"
echo ""
echo "document.getElementById('mcp-root')?.remove();"
echo "document.getElementById('mcp-toggle-button')?.remove();"
echo "document.getElementById('mcp-injected-button')?.remove();"
echo "delete window.MCPManagement;"
echo "delete window.MCP_ENDPOINTS;"
echo ""
echo "3. Refresh the page to fully clear"
echo ""

# Remove any files that were created
if [ -d "frontend/public/components" ]; then
    echo "Removing installed components..."
    rm -f frontend/public/components/MCPManagement.js
    rm -f static/js/MCPManagement.js
    rm -f public/js/MCPManagement.js
    rm -f static/js/mcp-injector.js
    rm -f public/js/mcp-injector.js
fi

echo "✅ Rollback instructions provided"
echo ""
echo "Note: Since MCP is injected via browser, it will be removed on page refresh."
echo "No permanent changes were made to the system."