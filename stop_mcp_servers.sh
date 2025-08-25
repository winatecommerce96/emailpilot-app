#!/bin/bash

# MCP Server Stop Script for EmailPilot

echo "🛑 Stopping MCP Servers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to stop server by port
stop_server() {
    local name=$1
    local port=$2
    local pid_file=".mcp_${port}.pid"
    
    echo -n "Stopping $name on port $port... "
    
    # Try to read PID from file
    if [ -f "$pid_file" ]; then
        pid=$(cat $pid_file)
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            rm $pid_file
            echo -e "${GREEN}✓ Stopped (PID: $pid)${NC}"
        else
            rm $pid_file
            echo -e "${YELLOW}Process not running, cleaning up PID file${NC}"
        fi
    fi
    
    # Also kill any process on the port (backup method)
    lsof -ti :$port | xargs kill -9 2>/dev/null
}

# Stop all servers
stop_server "Klaviyo Revenue API" 9090
stop_server "Performance API" 9091

echo ""
echo "✅ All MCP servers stopped!"