#!/bin/bash

# LangChain & LangGraph Integration Restore Script
# Created: August 27, 2025
# Purpose: Restore all files from this backup to their original locations

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} LangChain Integration Restore Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the backup directory (where this script is located)
BACKUP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$BACKUP_DIR/../.."

echo -e "${YELLOW}Backup directory:${NC} $BACKUP_DIR"
echo -e "${YELLOW}Project root:${NC} $PROJECT_ROOT"
echo ""

# Confirm before proceeding
read -p "This will restore files from the backup. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Restore cancelled.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Creating safety backup of current files...${NC}"

# Create a safety backup of current files
SAFETY_BACKUP="$PROJECT_ROOT/backups/pre-restore-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SAFETY_BACKUP"

# Backup current files before restore
cp "$PROJECT_ROOT/frontend/public/langchain_debug.html" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/frontend/public/calendar_master.html" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/frontend/public/calendar_hub.html" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/frontend/public/calendar_creator.html" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/app/api/langchain_execute.py" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/app/core/langsmith_config.py" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/main_firestore.py" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/langgraph.json" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/graph/live_graph.py" "$SAFETY_BACKUP/" 2>/dev/null
cp "$PROJECT_ROOT/graph/calendar_orchestrator_enhanced.py" "$SAFETY_BACKUP/" 2>/dev/null

echo -e "${GREEN}Safety backup created at: $SAFETY_BACKUP${NC}"
echo ""

# Function to restore a file
restore_file() {
    local source=$1
    local dest=$2
    local description=$3
    
    if [ -f "$source" ]; then
        cp "$source" "$dest"
        echo -e "${GREEN}✓${NC} Restored: $description"
    else
        echo -e "${RED}✗${NC} Not found: $source"
    fi
}

echo -e "${YELLOW}Restoring files...${NC}"
echo ""

# Restore frontend files
echo "Frontend files:"
restore_file "$BACKUP_DIR/frontend/langchain_debug.html" \
    "$PROJECT_ROOT/frontend/public/langchain_debug.html" \
    "LangChain Debug Console"

restore_file "$BACKUP_DIR/frontend/calendar_master.html" \
    "$PROJECT_ROOT/frontend/public/calendar_master.html" \
    "Calendar Master UI"

restore_file "$BACKUP_DIR/frontend/calendar_hub.html" \
    "$PROJECT_ROOT/frontend/public/calendar_hub.html" \
    "Calendar Hub Dashboard"

restore_file "$BACKUP_DIR/frontend/calendar_creator.html" \
    "$PROJECT_ROOT/frontend/public/calendar_creator.html" \
    "Calendar Creator"

echo ""
echo "API files:"

# Restore API files
restore_file "$BACKUP_DIR/api/langchain_execute.py" \
    "$PROJECT_ROOT/app/api/langchain_execute.py" \
    "LangChain Execute API"

restore_file "$BACKUP_DIR/core/langsmith_config.py" \
    "$PROJECT_ROOT/app/core/langsmith_config.py" \
    "LangSmith Configuration"

echo ""
echo "Configuration files:"

# Restore main application file
restore_file "$BACKUP_DIR/main_firestore.py" \
    "$PROJECT_ROOT/main_firestore.py" \
    "Main Application"

# Restore config files
restore_file "$BACKUP_DIR/config/langgraph.json" \
    "$PROJECT_ROOT/langgraph.json" \
    "LangGraph Configuration"

# Restore graph files
restore_file "$BACKUP_DIR/config/live_graph.py" \
    "$PROJECT_ROOT/graph/live_graph.py" \
    "Live Graph"

restore_file "$BACKUP_DIR/config/calendar_orchestrator_enhanced.py" \
    "$PROJECT_ROOT/graph/calendar_orchestrator_enhanced.py" \
    "Calendar Orchestrator"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Restore Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart the server: uvicorn main_firestore:app --port 8000 --host localhost --reload"
echo "2. Test the debug console: http://localhost:8000/static/langchain_debug.html"
echo "3. Check LangSmith traces (if configured)"
echo ""
echo -e "${YELLOW}Note:${NC} .env file was not restored. Check config/env.example for reference."
echo -e "${YELLOW}Safety backup:${NC} $SAFETY_BACKUP"