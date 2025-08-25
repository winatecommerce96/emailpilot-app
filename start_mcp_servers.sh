#!/bin/bash

# MCP Server Auto-Start Script for EmailPilot
# This script starts all required MCP servers for LangChain integration

echo "🚀 Starting MCP Servers for LangChain Integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set environment variables
export GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-"emailpilot-438321"}
export SECRET_MANAGER_TRANSPORT="rest"
export ENVIRONMENT=${ENVIRONMENT:-"development"}

# Function to check if a port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

# Function to kill process on port
kill_port() {
    echo "Killing process on port $1..."
    lsof -ti :$1 | xargs kill -9 2>/dev/null
}

# Function to start a server
start_server() {
    local name=$1
    local command=$2
    local port=$3
    local log_file=$4
    
    echo -n "Starting $name on port $port... "
    
    # Check if port is already in use
    if check_port $port; then
        echo -e "${YELLOW}Port $port already in use. Killing existing process...${NC}"
        kill_port $port
        sleep 1
    fi
    
    # Start the server in background
    nohup $command > $log_file 2>&1 &
    local pid=$!
    
    # Wait a moment for server to start
    sleep 2
    
    # Check if server started successfully
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}✓ Started (PID: $pid)${NC}"
        echo $pid > .mcp_${port}.pid
        return 0
    else
        echo -e "${RED}✗ Failed to start${NC}"
        return 1
    fi
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Klaviyo Revenue API
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
start_server "Klaviyo Revenue API" \
    "uvicorn services.klaviyo_api.main:app --host 127.0.0.1 --port 9090" \
    9090 \
    "logs/klaviyo_revenue_mcp.log"

# Start Performance API
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
start_server "Performance API" \
    "uvicorn services.performance_api.main:app --host 127.0.0.1 --port 9091" \
    9091 \
    "logs/performance_mcp.log"

# Start Multi-Agent System (if needed)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Note: Multi-Agent System runs in stdio mode for MCP protocol"
echo "It will be started on-demand by LangChain when needed"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ MCP Servers Started!"
echo ""
echo "Server Status:"
echo "  • Klaviyo Revenue API: http://127.0.0.1:9090/healthz"
echo "  • Performance API: http://127.0.0.1:9091/healthz"
echo ""
echo "Log Files:"
echo "  • Klaviyo: logs/klaviyo_revenue_mcp.log"
echo "  • Performance: logs/performance_mcp.log"
echo ""
echo "To stop servers, run: ./stop_mcp_servers.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test health endpoints
echo ""
echo "Testing health endpoints..."
sleep 2

# Test Klaviyo Revenue API
if curl -s http://127.0.0.1:9090/healthz | grep -q "ok"; then
    echo -e "  ${GREEN}✓ Klaviyo Revenue API is healthy${NC}"
else
    echo -e "  ${RED}✗ Klaviyo Revenue API health check failed${NC}"
fi

# Test Performance API
if curl -s http://127.0.0.1:9091/healthz | grep -q "ok"; then
    echo -e "  ${GREEN}✓ Performance API is healthy${NC}"
else
    echo -e "  ${RED}✗ Performance API health check failed${NC}"
fi

echo ""
echo "MCP servers are ready for LangChain integration!"