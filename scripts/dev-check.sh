#!/bin/bash

# EmailPilot SPA Development Check Script
# Ensures the SPA is working correctly with no errors

set -e

echo "================================"
echo "EmailPilot SPA Development Check"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
check_server() {
    echo -n "Checking if server is running on port 8000... "
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        echo "Server is not running. Please start it with: uvicorn main_firestore:app --port 8000 --host localhost --reload"
        return 1
    fi
}

# Check SPA routes
check_spa_routes() {
    echo "Checking SPA routes..."
    
    routes=("/" "/calendar" "/clients" "/reports" "/settings" "/login")
    
    for route in "${routes[@]}"; do
        echo -n "  Testing $route... "
        status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$route)
        if [ "$status" = "200" ]; then
            echo -e "${GREEN}✓ (200)${NC}"
        else
            echo -e "${RED}✗ ($status)${NC}"
        fi
    done
}

# Check API endpoints
check_api_endpoints() {
    echo "Checking API endpoints..."
    
    echo -n "  /api/auth/me... "
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/auth/me)
    if [ "$status" = "401" ]; then
        echo -e "${GREEN}✓ (401 - Expected for unauthenticated)${NC}"
    else
        echo -e "${YELLOW}! ($status)${NC}"
    fi
    
    echo -n "  /health... "
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$status" = "200" ]; then
        echo -e "${GREEN}✓ (200)${NC}"
    else
        echo -e "${RED}✗ ($status)${NC}"
    fi
}

# Check static files
check_static_files() {
    echo "Checking static files..."
    
    files=("/static/dist/SPAApp.js" "/static/dist/CalendarChat.js" "/static/dist/CalendarView.js")
    
    for file in "${files[@]}"; do
        echo -n "  $file... "
        status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$file)
        if [ "$status" = "200" ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗ ($status)${NC}"
        fi
    done
}

# Run Playwright tests if available
run_tests() {
    echo "Running Playwright tests..."
    
    if command -v npx &> /dev/null && [ -f "playwright.config.js" ]; then
        echo "  Running authenticated user tests..."
        npx playwright test tests/e2e/authenticated.spec.js --reporter=list || true
        
        echo "  Running unauthenticated user tests..."
        npx playwright test tests/e2e/unauthenticated.spec.js --reporter=list || true
    else
        echo -e "${YELLOW}  Playwright not installed. Run: npm install @playwright/test${NC}"
    fi
}

# Main execution
main() {
    echo ""
    
    if ! check_server; then
        exit 1
    fi
    
    echo ""
    check_spa_routes
    
    echo ""
    check_api_endpoints
    
    echo ""
    check_static_files
    
    echo ""
    run_tests
    
    echo ""
    echo "================================"
    echo "Development Check Complete"
    echo "================================"
    echo ""
    echo "To test the SPA manually:"
    echo "  1. Open http://localhost:8000 in your browser"
    echo "  2. Check the browser console for errors"
    echo "  3. Navigate through all routes"
    echo "  4. Verify no 401 errors for authenticated users"
    echo ""
}

main