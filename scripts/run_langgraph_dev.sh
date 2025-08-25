#!/bin/bash
# Run LangGraph development server for Calendar Workflow

set -e

echo "================================================"
echo "Starting LangGraph Calendar Workflow Dev Server"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check environment variables
echo -e "${YELLOW}Checking environment...${NC}"

if [ -z "$LANGSMITH_API_KEY" ]; then
    echo -e "${RED}Warning: LANGSMITH_API_KEY not set${NC}"
    echo "LangSmith tracing will be disabled"
else
    echo -e "${GREEN}✓ LANGSMITH_API_KEY found${NC}"
fi

if [ -z "$LANGSMITH_PROJECT" ]; then
    export LANGSMITH_PROJECT="emailpilot-calendar"
    echo -e "${YELLOW}Setting LANGSMITH_PROJECT=${LANGSMITH_PROJECT}${NC}"
fi

# Enable tracing
export LANGCHAIN_TRACING_V2="true"
echo -e "${GREEN}✓ LangChain tracing enabled${NC}"

# Check if langgraph is installed
if ! command -v langgraph &> /dev/null; then
    echo -e "${RED}Error: langgraph command not found${NC}"
    echo "Install with: pip install langgraph[studio]"
    exit 1
fi

# Create var directory if it doesn't exist
mkdir -p var
echo -e "${GREEN}✓ var/ directory ready${NC}"

# Check if port is available
PORT=2024
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}Port $PORT is already in use${NC}"
    echo "Kill existing process with: lsof -ti:$PORT | xargs kill -9"
    exit 1
fi

echo ""
echo "================================================"
echo -e "${GREEN}Starting LangGraph Studio on port $PORT${NC}"
echo "================================================"
echo ""
echo "Access Studio at: http://localhost:$PORT"
echo "View traces at: https://smith.langchain.com"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
langgraph dev --port $PORT