#!/bin/bash
# Start Klaviyo MCP Enhanced Server
# This runs the Node.js MCP server with enhanced capabilities

echo "🚀 Starting Klaviyo MCP Enhanced Server..."

# Change to the MCP Enhanced directory
cd services/klaviyo_mcp_enhanced

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Export environment variables
export PORT=9095
export NODE_ENV=development
export LOG_LEVEL=info

# Start the server
echo "✅ Starting MCP Enhanced on port 9095..."
npm start