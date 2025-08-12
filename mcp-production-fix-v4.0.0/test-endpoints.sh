#!/bin/bash
# Test MCP Cloud Function Endpoints

echo "Testing MCP Cloud Function Endpoints..."
echo "========================================"
echo ""

# Define endpoints
MODELS_URL="https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-models"
CLIENTS_URL="https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-clients"
HEALTH_URL="https://us-central1-emailpilot-438321.cloudfunctions.net/mcp-health"

# Test each endpoint
test_endpoint() {
    local url=$1
    local name=$2
    
    echo -n "Testing $name: "
    
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        if [ "$response" = "200" ]; then
            echo "✅ OK (HTTP $response)"
            # Show sample data
            echo "  Sample response:"
            curl -s "$url" | head -c 200
            echo ""
            echo ""
        else
            echo "❌ FAILED (HTTP $response)"
        fi
    else
        echo "⚠️  curl not installed, skipping test"
    fi
}

test_endpoint "$HEALTH_URL" "Health Check"
test_endpoint "$MODELS_URL" "Models API"
test_endpoint "$CLIENTS_URL" "Clients API"

echo ""
echo "Test complete!"
echo ""
echo "If all endpoints show ✅ OK, the Cloud Functions are working correctly."
echo "If any show ❌ FAILED, check the Cloud Functions deployment."