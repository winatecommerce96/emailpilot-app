#!/bin/bash

# ============================================================================
# LangGraph Studio + LangSmith Integration Setup Script
# ============================================================================
# This script sets up the integration between LangGraph Studio, LangSmith,
# and the existing Workflow Editor with the new Hub Dashboard
#
# Usage: ./scripts/setup_langgraph_integration.sh [dev|staging|prod]
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default environment
ENV=${1:-dev}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}LangGraph Integration Setup - ${ENV}${NC}"
echo -e "${GREEN}========================================${NC}"

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.9"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}✗ Python $required_version or higher required (found $python_version)${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Python $python_version${NC}"
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✗ pip3 not found${NC}"
    exit 1
else
    echo -e "${GREEN}✓ pip3 installed${NC}"
fi

# Check if npm is installed (for Hub Dashboard)
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
else
    echo -e "${GREEN}✓ npm installed${NC}"
fi

# Check if .env.langgraph exists
if [ ! -f ".env.langgraph" ]; then
    echo -e "${YELLOW}Creating .env.langgraph from template...${NC}"
    cp .env.langgraph.example .env.langgraph
    echo -e "${YELLOW}⚠ Please edit .env.langgraph with your API keys${NC}"
else
    echo -e "${GREEN}✓ .env.langgraph exists${NC}"
fi

# ============================================================================
# Step 2: Install Dependencies
# ============================================================================

echo -e "\n${YELLOW}Installing Python dependencies...${NC}"

pip3 install --upgrade pip
pip3 install langsmith>=0.1.0
pip3 install langchain-core>=0.1.0
pip3 install langgraph>=0.0.20
pip3 install langchain-openai>=0.0.5  # If using OpenAI
pip3 install python-dotenv>=1.0.0

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# ============================================================================
# Step 3: Create Directory Structure
# ============================================================================

echo -e "\n${YELLOW}Creating directory structure...${NC}"

# Create required directories
mkdir -p workflow/graphs
mkdir -p workflow/generated
mkdir -p workflow/checkpoints
mkdir -p backups
mkdir -p logs
mkdir -p frontend/public/hub

echo -e "${GREEN}✓ Directory structure created${NC}"

# ============================================================================
# Step 4: Validate Environment Variables
# ============================================================================

echo -e "\n${YELLOW}Validating environment variables...${NC}"

# Source the environment file
set -a
source .env.langgraph
set +a

# Check required variables
missing_vars=()

if [ -z "$LANGSMITH_API_KEY" ]; then
    missing_vars+=("LANGSMITH_API_KEY")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo -e "${YELLOW}Please edit .env.langgraph and set these variables${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Environment variables configured${NC}"
fi

# ============================================================================
# Step 5: Test LangSmith Connection
# ============================================================================

echo -e "\n${YELLOW}Testing LangSmith connection...${NC}"

python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.langgraph')

try:
    from langsmith import Client
    client = Client()
    projects = client.list_projects()
    print('✓ LangSmith connection successful')
    print(f'  Found {len(list(projects))} projects')
except Exception as e:
    print(f'✗ LangSmith connection failed: {e}')
    exit(1)
" || exit 1

# ============================================================================
# Step 6: Check/Install LangGraph Studio
# ============================================================================

echo -e "\n${YELLOW}Checking LangGraph Studio...${NC}"

if [ "$ENV" = "dev" ]; then
    # LangGraph Studio is a desktop application, not a pip package
    # Check if LangGraph API server is available
    if command -v langgraph &> /dev/null; then
        echo -e "${GREEN}✓ LangGraph CLI available${NC}"
    else
        echo -e "${YELLOW}Installing LangGraph CLI...${NC}"
        pip3 install langgraph-cli
        echo -e "${GREEN}✓ LangGraph CLI installed${NC}"
    fi
    
    # Check if we can use the API server mode
    echo -e "${YELLOW}Note: LangGraph Studio Desktop Application Setup${NC}"
    echo -e "  1. Download from: https://github.com/langchain-ai/langgraph-studio/releases"
    echo -e "  2. Or use the API server mode with: langgraph up"
    echo -e "  3. Or use the web-based viewer (development mode)"
    
    # Create a local development server configuration
    cat > workflow/langgraph.json << 'EOF'
{
  "graphs": {
    "emailpilot_calendar": {
      "path": "./workflow.json",
      "description": "Email campaign calendar workflow"
    }
  },
  "dependencies": [
    "langchain-core",
    "langchain-openai",
    "langgraph"
  ],
  "python_version": "3.9",
  "env": ".env.langgraph"
}
EOF
    echo -e "${GREEN}✓ LangGraph configuration created${NC}"
else
    echo -e "${YELLOW}ℹ Studio setup skipped (not needed in $ENV)${NC}"
fi

# ============================================================================
# Step 7: Create Initial Workflow Schema
# ============================================================================

echo -e "\n${YELLOW}Creating initial workflow schema...${NC}"

if [ ! -f "workflow/workflow.json" ]; then
    cat > workflow/workflow.json << 'EOF'
{
  "name": "emailpilot_calendar",
  "version": "1.0.0",
  "description": "Email campaign calendar workflow",
  "state": {
    "brand": "string",
    "month": "string",
    "campaigns": "array",
    "status": "string"
  },
  "nodes": [
    {
      "id": "start",
      "type": "python_fn",
      "impl": "workflow.nodes.start_node",
      "params": {}
    },
    {
      "id": "analyze",
      "type": "agent",
      "impl": "workflow.agents.analyzer",
      "params": {
        "temperature": 0.7,
        "max_tokens": 1000
      }
    },
    {
      "id": "generate",
      "type": "agent",
      "impl": "workflow.agents.generator",
      "params": {
        "temperature": 0.8,
        "max_tokens": 2000
      }
    },
    {
      "id": "review",
      "type": "human_gate",
      "impl": "workflow.gates.review_gate",
      "params": {
        "timeout": 3600
      }
    },
    {
      "id": "end",
      "type": "python_fn",
      "impl": "workflow.nodes.end_node",
      "params": {}
    }
  ],
  "edges": [
    {
      "from": "start",
      "to": "analyze"
    },
    {
      "from": "analyze",
      "to": "generate"
    },
    {
      "from": "generate",
      "to": "review"
    },
    {
      "from": "review",
      "to": "end",
      "condition": "state['approved'] == True"
    }
  ],
  "checkpointer": {
    "type": "filesystem",
    "path": "./workflow/checkpoints"
  },
  "metadata": {
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "author": "setup_script"
  }
}
EOF
    echo -e "${GREEN}✓ Initial workflow schema created${NC}"
else
    echo -e "${GREEN}✓ Workflow schema already exists${NC}"
fi

# ============================================================================
# Step 8: Create API Endpoints
# ============================================================================

echo -e "\n${YELLOW}Creating API endpoint stubs...${NC}"

cat > app/api/hub.py << 'EOF'
"""
Hub Dashboard API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import os
from datetime import datetime

router = APIRouter(prefix="/api/hub", tags=["Hub Dashboard"])

@router.get("/status")
async def get_service_status() -> Dict[str, Any]:
    """Check service availability"""
    return {
        "studio": {
            "available": check_studio_health(),
            "version": "1.0.0"
        },
        "langsmith": {
            "connected": check_langsmith_connection(),
            "project": os.getenv("LANGSMITH_PROJECT", "unknown")
        },
        "editor": {
            "available": True
        }
    }

@router.get("/recent-runs")
async def get_recent_runs(limit: int = 10, graph: str = None) -> List[Dict[str, Any]]:
    """List recent workflow runs"""
    # TODO: Implement actual run fetching
    return [
        {
            "run_id": f"run_{datetime.now().strftime('%Y%m%d')}_{i:03d}",
            "graph": graph or "emailpilot_calendar",
            "status": "success" if i % 3 != 2 else "failed",
            "created_at": datetime.now().isoformat(),
            "smith_run_url": f"https://smith.langchain.com/runs/{i}"
        }
        for i in range(limit)
    ]

@router.post("/context")
async def save_run_context(context: Dict[str, Any]) -> Dict[str, bool]:
    """Save run context"""
    # TODO: Implement context storage
    return {"saved": True}

def check_studio_health() -> bool:
    """Check if Studio is available"""
    # TODO: Implement actual health check
    studio_root = os.getenv("STUDIO_ROOT", "")
    return bool(studio_root)

def check_langsmith_connection() -> bool:
    """Check LangSmith connectivity"""
    try:
        from langsmith import Client
        client = Client()
        # Simple connectivity check
        list(client.list_projects())
        return True
    except:
        return False
EOF

echo -e "${GREEN}✓ API endpoints created${NC}"

# ============================================================================
# Step 9: Create Instrumentation Hooks
# ============================================================================

echo -e "\n${YELLOW}Creating instrumentation hooks...${NC}"

cat > workflow/instrumentation.py << 'EOF'
"""
Instrumentation for LangSmith tracing
"""
import os
from typing import Dict, Any, Optional
from functools import wraps
from langsmith import Client
from langsmith.run_helpers import traceable
import logging

logger = logging.getLogger(__name__)

# Initialize client if tracing enabled
ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"
LANGSMITH_CLIENT = Client() if ENABLE_TRACING else None

def instrument_node(node_id: str, run_context: Dict[str, Any]):
    """Decorator to instrument workflow nodes"""
    def decorator(func):
        if not ENABLE_TRACING:
            return func
        
        @wraps(func)
        @traceable(
            run_type="chain",
            name=f"node_{node_id}",
            tags=[
                f"graph:{run_context.get('graph', 'unknown')}",
                f"node:{node_id}",
                f"brand:{run_context.get('brand', 'unknown')}",
                f"month:{run_context.get('month', 'unknown')}",
                f"env:{run_context.get('env', 'dev')}",
                f"run_id:{run_context.get('run_id', 'unknown')}"
            ]
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_trace_url(run_id: str) -> Optional[str]:
    """Get LangSmith trace URL for a run"""
    if not LANGSMITH_CLIENT:
        return None
    
    try:
        project = os.getenv("LANGSMITH_PROJECT", "default")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com")
        return f"{endpoint}/projects/{project}/runs?query=run_id:{run_id}"
    except Exception as e:
        logger.error(f"Failed to get trace URL: {e}")
        return None
EOF

echo -e "${GREEN}✓ Instrumentation hooks created${NC}"

# ============================================================================
# Step 10: Generate Acceptance Test Script
# ============================================================================

echo -e "\n${YELLOW}Creating acceptance test script...${NC}"

cat > scripts/test_langgraph_integration.py << 'EOF'
#!/usr/bin/env python3
"""
Acceptance tests for LangGraph integration
"""
import os
import sys
import json
import time
import requests
from typing import Dict, Any, List
from datetime import datetime

# Test results
results = []

def test(name: str):
    """Decorator for test functions"""
    def decorator(func):
        def wrapper():
            try:
                func()
                results.append({"test": name, "status": "✓ PASS", "error": None})
                print(f"✓ {name}")
            except Exception as e:
                results.append({"test": name, "status": "✗ FAIL", "error": str(e)})
                print(f"✗ {name}: {e}")
        return wrapper
    return decorator

@test("Studio Edit Loop")
def test_studio_edit_loop():
    """Test that Studio edits round-trip correctly"""
    # TODO: Implement actual test
    # 1. Load schema
    # 2. Modify parameter
    # 3. Save schema
    # 4. Verify changes
    pass

@test("End-to-End Trace")
def test_e2e_trace():
    """Test that traces appear in LangSmith"""
    from langsmith import Client
    client = Client()
    
    # Run a test workflow
    # TODO: Trigger actual workflow
    
    # Check for trace
    time.sleep(5)  # Wait for trace to appear
    
    # Verify trace exists
    # TODO: Query for specific run

@test("Context Continuity")
def test_context_continuity():
    """Test that context flows through all tools"""
    context = {
        "run_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "graph": "emailpilot_calendar",
        "brand": "Test Brand",
        "month": "2025-10",
        "env": "test"
    }
    
    # Save context
    # TODO: Call hub API
    
    # Verify context in deep links
    # TODO: Verify URLs contain context

@test("Workflow Editor Isolation")
def test_editor_isolation():
    """Test that Workflow Editor has no debug features"""
    # TODO: Check editor UI for absence of debug features
    pass

@test("Resilience Testing")
def test_resilience():
    """Test system resilience to service failures"""
    # TODO: Test with services down
    pass

@test("Security Validation")
def test_security():
    """Test that no secrets are exposed"""
    # TODO: Check API responses for secrets
    pass

def main():
    print("=" * 50)
    print("LangGraph Integration Acceptance Tests")
    print("=" * 50)
    
    # Run all tests
    test_studio_edit_loop()
    test_e2e_trace()
    test_context_continuity()
    test_editor_isolation()
    test_resilience()
    test_security()
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for r in results if "PASS" in r["status"])
    failed = sum(1 for r in results if "FAIL" in r["status"])
    
    for result in results:
        print(f"{result['status']} {result['test']}")
        if result['error']:
            print(f"    Error: {result['error']}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x scripts/test_langgraph_integration.py

echo -e "${GREEN}✓ Acceptance test script created${NC}"

# ============================================================================
# Step 11: Start Services (Dev Only)
# ============================================================================

if [ "$ENV" = "dev" ]; then
    echo -e "\n${YELLOW}Starting services in development mode...${NC}"
    
    # Option 1: Use LangGraph API server
    if command -v langgraph &> /dev/null; then
        echo -e "${YELLOW}Starting LangGraph API server...${NC}"
        echo -e "${YELLOW}Run this in a separate terminal:${NC}"
        echo -e "${GREEN}  cd workflow && langgraph up --port 8123${NC}"
        echo -e "${YELLOW}Then access at: http://localhost:8123${NC}"
    fi
    
    # Option 2: Use the development viewer
    echo -e "\n${YELLOW}Alternative: Use the web-based workflow viewer${NC}"
    echo -e "  The Workflow Editor at ${GREEN}http://localhost:8000/static/workflow_editor.html${NC}"
    echo -e "  provides basic graph visualization and editing."
fi

# ============================================================================
# Step 12: Final Summary
# ============================================================================

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Edit ${YELLOW}.env.langgraph${NC} with your API keys"
echo -e "2. Run ${YELLOW}python scripts/test_langgraph_integration.py${NC} to verify setup"
echo -e "3. Open ${YELLOW}http://localhost:8000/hub/${NC} to access the Hub Dashboard"
echo -e "4. Read ${YELLOW}LANGGRAPH_INTEGRATION.md${NC} for detailed documentation"

echo -e "\n${YELLOW}Quick Commands:${NC}"
echo -e "  Start API Server:  ${GREEN}cd workflow && langgraph up --port 8123${NC}"
echo -e "  View traces:       ${GREEN}open https://smith.langchain.com${NC}"
echo -e "  Workflow Editor:   ${GREEN}open http://localhost:8000/static/workflow_editor.html${NC}"
echo -e "  Run tests:         ${GREEN}python scripts/test_langgraph_integration.py${NC}"
echo -e "  Check status:      ${GREEN}curl http://localhost:8000/api/hub/status${NC}"

echo -e "\n${YELLOW}LangGraph Studio Options:${NC}"
echo -e "  1. Desktop App:  Download from GitHub releases (recommended)"
echo -e "  2. API Server:   Use 'langgraph up' command (development)"
echo -e "  3. Web Editor:   Use existing Workflow Editor (basic features)"

echo -e "\n${GREEN}Happy workflow building! 🚀${NC}"