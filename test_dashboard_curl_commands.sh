#!/bin/bash
# EmailPilot Dashboard API Test Suite - Curl Commands
# Tests all the key endpoints that should work after fixes

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TEST_CLIENT_ID="demo_client_1"

echo "🦀 EmailPilot Dashboard API Testing"
echo "Testing against: $BASE_URL"
echo "Client ID for tests: $TEST_CLIENT_ID"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success_count=0
fail_count=0
warning_count=0

test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    local check_json="${4:-true}"
    
    echo -n "Testing $name... "
    
    # Make the request with timeout
    response=$(curl -s -w "\n%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}FAIL - Connection error${NC}"
        ((fail_count++))
        return 1
    fi
    
    # Split response and status code
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    # Check status code
    if [ "$status_code" = "$expected_status" ]; then
        # Check if it's valid JSON when expected
        if [ "$check_json" = "true" ]; then
            if echo "$body" | jq . >/dev/null 2>&1; then
                echo -e "${GREEN}PASS - HTTP $status_code with valid JSON${NC}"
                ((success_count++))
                return 0
            else
                echo -e "${RED}FAIL - HTTP $status_code but invalid JSON${NC}"
                echo "Response: ${body:0:100}..."
                ((fail_count++))
                return 1
            fi
        else
            echo -e "${GREEN}PASS - HTTP $status_code${NC}"
            ((success_count++))
            return 0
        fi
    elif [ "$expected_status" = "200" ] && [ "$status_code" = "403" ] && echo "$url" | grep -q "auth"; then
        # Auth endpoints might return 403 in demo mode - check if it's clean JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo -e "${YELLOW}WARN - HTTP $status_code (demo mode) with valid JSON${NC}"
            ((warning_count++))
            return 0
        else
            echo -e "${RED}FAIL - HTTP $status_code with invalid response${NC}"
            ((fail_count++))
            return 1
        fi
    else
        echo -e "${RED}FAIL - Expected HTTP $expected_status, got $status_code${NC}"
        echo "Response: ${body:0:100}..."
        ((fail_count++))
        return 1
    fi
}


echo "🔧 Testing Backend API Endpoints"
echo "================================"

# Core authentication endpoints
test_endpoint "Auth Session" "$BASE_URL/api/auth/session" "200"
test_endpoint "Auth Me" "$BASE_URL/api/auth/me" "200"

# Admin endpoints
test_endpoint "Admin Health" "$BASE_URL/api/admin/health" "200"
test_endpoint "Admin Environment" "$BASE_URL/api/admin/environment" "200"
test_endpoint "Admin System Status" "$BASE_URL/api/admin/system/status" "200"
test_endpoint "Admin Clients" "$BASE_URL/api/admin/clients" "200"

# Performance endpoints
test_endpoint "Performance MTD" "$BASE_URL/api/performance/mtd/$TEST_CLIENT_ID" "200"
test_endpoint "Performance Historical" "$BASE_URL/api/performance/historical/$TEST_CLIENT_ID" "200"
test_endpoint "Performance Test" "$BASE_URL/api/performance/test-endpoint" "200"

# Goals endpoints
test_endpoint "Goals Clients" "$BASE_URL/api/goals/clients" "200"

echo ""
echo "📁 Testing Static File Serving"
echo "==============================="

# Test compiled JavaScript files
test_endpoint "App Bundle" "$BASE_URL/dist/app.js" "200" "false"
test_endpoint "Component Loader" "$BASE_URL/dist/component-loader.js" "200" "false"
test_endpoint "Calendar Component" "$BASE_URL/dist/Calendar.js" "200" "false"
test_endpoint "Firebase Service" "$BASE_URL/dist/FirebaseCalendarService.js" "200" "false"

echo ""
echo "🌐 Testing CORS Headers"
echo "======================="

# Test CORS preflight
echo -n "Testing CORS Preflight... "
cors_response=$(curl -s -I \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  --connect-timeout 5 --max-time 10 \
  "$BASE_URL/api/auth/session" 2>/dev/null)

if [ $? -eq 0 ]; then
    if echo "$cors_response" | grep -i "access-control-allow-origin" >/dev/null; then
        echo -e "${GREEN}PASS - CORS headers present${NC}"
        ((success_count++))
    else
        echo -e "${YELLOW}WARN - CORS headers not found${NC}"
        ((warning_count++))
    fi
else
    echo -e "${RED}FAIL - CORS test failed${NC}"
    ((fail_count++))
fi

echo ""
echo "🧪 Testing Error Handling"
echo "========================="

# Test non-existent endpoints return proper JSON errors
test_endpoint "404 Error JSON" "$BASE_URL/api/nonexistent" "404"
test_endpoint "Performance 404" "$BASE_URL/api/performance/mtd/nonexistent_client_12345" "200" # This should return mock data

echo ""
echo "📊 Test Summary"
echo "==============="
echo -e "✅ Passed: $success_count"
echo -e "⚠️  Warnings: $warning_count"
echo -e "❌ Failed: $fail_count"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed\!${NC}"
    if [ $warning_count -gt 0 ]; then
        echo -e "${YELLOW}Some warnings noted - review recommended${NC}"
    fi
    exit 0
else
    echo -e "${RED}💥 $fail_count critical issues found - must be fixed${NC}"
    exit 1
fi
EOF < /dev/null