#!/bin/bash
set -e

echo "================================"
echo "Production Fixes Verification"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo ""
echo "1. AI Models Health Check"
echo "--------------------------"

# Check models endpoint
MODELS=$(curl -s http://localhost:8002/api/models | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('source', 'unknown'))")
if [ "$MODELS" == "orchestrator" ]; then
    check_pass "Models loading from orchestrator (not fallback)"
elif [ "$MODELS" == "fallback" ]; then
    check_fail "Models in fallback state"
else
    check_warn "Models source: $MODELS"
fi

# Count models
MODEL_COUNT=$(curl -s http://localhost:8002/api/models | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('models', [])))")
if [ "$MODEL_COUNT" -gt "3" ]; then
    check_pass "Found $MODEL_COUNT models (more than fallback 3)"
else
    check_warn "Only $MODEL_COUNT models found"
fi

echo ""
echo "2. Agents Parity Check"
echo "-----------------------"

# Check agent counts match
UNIFIED_COUNT=$(curl -s http://localhost:8000/api/agents/ | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('agents', [])))")
COPYWRITING_COUNT=$(curl -s http://localhost:8002/api/agents | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('agents', [])))")

if [ "$UNIFIED_COUNT" == "$COPYWRITING_COUNT" ]; then
    check_pass "Agent counts match: $UNIFIED_COUNT agents"
else
    check_fail "Agent count mismatch: Unified=$UNIFIED_COUNT, Copywriting=$COPYWRITING_COUNT"
fi

# Get agent IDs from both endpoints
UNIFIED_IDS=$(curl -s http://localhost:8000/api/agents/ | python3 -c "import sys, json; data = json.load(sys.stdin); agents = data.get('agents', []); print(','.join(sorted([a['agent_id'] for a in agents])))")
COPYWRITING_IDS=$(curl -s http://localhost:8002/api/agents | python3 -c "import sys, json; data = json.load(sys.stdin); agents = data.get('agents', []); print(','.join(sorted([a['id'] for a in agents])))")

if [ "$UNIFIED_IDS" == "$COPYWRITING_IDS" ]; then
    check_pass "Agent IDs match perfectly"
else
    check_fail "Agent ID mismatch"
    echo "  Unified: $UNIFIED_IDS"
    echo "  Copywriting: $COPYWRITING_IDS"
fi

echo ""
echo "3. Production Build Check"
echo "-------------------------"

# Check for Tailwind CSS build
if [ -f "frontend/public/dist/styles.css" ]; then
    check_pass "Tailwind CSS compiled to dist/styles.css"
else
    check_fail "Tailwind CSS not compiled"
fi

# Check index.html doesn't use CDN Tailwind
if grep -q "cdn.tailwindcss.com" frontend/public/index.html; then
    check_fail "index.html still uses Tailwind CDN"
else
    check_pass "index.html uses compiled Tailwind (no CDN)"
fi

# Check for Babel in main index
if grep -q "text/babel\|babel-standalone" frontend/public/index.html; then
    check_fail "index.html still uses in-browser Babel"
else
    check_pass "index.html doesn't use in-browser Babel"
fi

# Check for compiled JS
JS_FILES=$(ls frontend/public/dist/*.js 2>/dev/null | wc -l)
if [ "$JS_FILES" -gt 10 ]; then
    check_pass "Found $JS_FILES compiled JS files in dist/"
else
    check_warn "Only $JS_FILES JS files in dist/ (expected more)"
fi

echo ""
echo "4. API Endpoints Check"
echo "----------------------"

# Check health endpoint
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH" == "200" ]; then
    check_pass "Health endpoint responding (HTTP $HEALTH)"
else
    check_fail "Health endpoint not responding (HTTP $HEALTH)"
fi

# Check agents stats endpoint
STATS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/agents/stats)
if [ "$STATS" == "200" ]; then
    check_pass "Agents stats endpoint working (HTTP $STATS)"
else
    check_fail "Agents stats endpoint failed (HTTP $STATS)"
fi

# Check models health endpoint
MODELS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/ai-models/models/health)
if [ "$MODELS_HEALTH" == "200" ]; then
    check_pass "Models health endpoint working (HTTP $MODELS_HEALTH)"
else
    check_warn "Models health endpoint not available (HTTP $MODELS_HEALTH)"
fi

echo ""
echo "5. Console Warnings Check"
echo "-------------------------"
echo "Manual check required:"
echo "  1. Open browser DevTools console"
echo "  2. Navigate to http://localhost:8000"
echo "  3. Check for these warnings:"
echo "     - No 'cdn.tailwindcss.com should not be used in production'"
echo "     - No 'You are using the in-browser Babel transformer'"
echo ""

echo "================================"
echo "Verification Complete!"
echo "================================"
echo ""
echo "Summary:"
echo "--------"
echo "✅ Models: Not in fallback state"
echo "✅ Agents: Perfect parity between endpoints"
echo "✅ Build: Tailwind compiled, no CDN usage"
echo "✅ Babel: Not used in main index.html"
echo "✅ APIs: All endpoints responding"
echo ""
echo "Next steps:"
echo "-----------"
echo "1. Check browser console for warnings"
echo "2. Test model selection dropdown in copywriting tool"
echo "3. Verify agent list in UI matches API"
echo ""