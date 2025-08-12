#\!/bin/bash
# EmailPilot Dashboard - Run All Tests
# Comprehensive testing suite for dashboard fixes

set -e

echo "🚀 EmailPilot Dashboard - Complete Test Suite"
echo "=============================================="

BASE_URL="${1:-http://localhost:8000}"
echo "Testing against: $BASE_URL"
echo ""

# Check if server is running
echo "🔍 Checking if server is running..."
if \! curl -s --connect-timeout 2 "$BASE_URL/api/admin/health" >/dev/null; then
    echo "❌ Server not running at $BASE_URL"
    echo "Please start with: python main_firestore.py"
    exit 1
fi
echo "✅ Server is responding"
echo ""

# Run build system test
echo "🔧 Testing Build System..."
if [ -f "./scripts/build_frontend.sh" ]; then
    if [ \! -x "./scripts/build_frontend.sh" ]; then
        chmod +x ./scripts/build_frontend.sh
    fi
    ./scripts/build_frontend.sh
    echo "✅ Build system working"
else
    echo "⚠️ Build script not found - frontend build may not be set up"
fi
echo ""

# Run curl tests
echo "🌐 Running API Tests..."
if [ -f "./test_dashboard_curl_commands.sh" ]; then
    ./test_dashboard_curl_commands.sh "$BASE_URL"
else
    echo "⚠️ Curl test script not found"
fi
echo ""

# Run Python comprehensive tests
echo "🐍 Running Comprehensive Python Tests..."
if [ -f "./test_dashboard_fixes.py" ]; then
    python ./test_dashboard_fixes.py "$BASE_URL"
else
    echo "⚠️ Python test script not found"
fi
echo ""

# Check index.html integration
echo "📄 Checking Index.html Integration..."
if grep -q '/dist/' frontend/public/index.html; then
    echo "✅ index.html uses compiled files"
else
    echo "⚠️ index.html still uses source files - needs update"
    echo ""
    echo "📝 ACTION REQUIRED:"
    echo "   Update frontend/public/index.html to use compiled files:"
    echo "   - Change 'components/' to 'dist/'"
    echo "   - Remove 'type=\"text/babel\"' from script tags"
    echo "   - Remove @babel/standalone script"
    echo ""
fi

echo ""
echo "🏁 Test Suite Complete\!"
echo "Check the output above for any issues that need attention."
echo ""
echo "📚 Additional Testing:"
echo "   - Open http://localhost:8000 in browser"
echo "   - Check Developer Console (F12) for errors"
echo "   - Verify all dashboard features work correctly"
echo "   - See BROWSER_CONSOLE_TESTS.md for detailed console checks"
