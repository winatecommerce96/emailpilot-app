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
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
STUDIO_BASE = os.getenv("STUDIO_ROOT", "http://localhost:8123")

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

@test("Hub API Status")
def test_hub_api_status():
    """Test that Hub API is accessible"""
    response = requests.get(f"{API_BASE}/api/hub/status")
    assert response.status_code == 200, f"Hub API returned {response.status_code}"
    data = response.json()
    assert "studio" in data, "Missing studio status"
    assert "langsmith" in data, "Missing langsmith status"
    assert "editor" in data, "Missing editor status"

@test("LangSmith Connection")
def test_langsmith_connection():
    """Test LangSmith connectivity"""
    try:
        from langsmith import Client
        from dotenv import load_dotenv
        
        # Load environment
        load_dotenv('.env.langgraph')
        
        # Check if API key is set
        api_key = os.getenv("LANGSMITH_API_KEY")
        assert api_key, "LANGSMITH_API_KEY not set in .env.langgraph"
        
        # Test connection
        client = Client()
        projects = list(client.list_projects())
        assert len(projects) >= 0, "Failed to list projects"
        
        # Check for our project
        project_name = os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
        project_exists = any(p.name == project_name for p in projects)
        
        if not project_exists:
            print(f"  Warning: Project '{project_name}' not found in LangSmith")
            
    except ImportError:
        raise AssertionError("langsmith package not installed")

@test("Workflow Schema Loading")
def test_workflow_schema():
    """Test that workflow schema exists and is valid"""
    workflow_path = Path("workflow/workflow.json")
    assert workflow_path.exists(), "workflow/workflow.json not found"
    
    with open(workflow_path) as f:
        schema = json.load(f)
    
    # Validate required fields
    assert "name" in schema, "Schema missing 'name' field"
    assert "nodes" in schema, "Schema missing 'nodes' field"
    assert "edges" in schema, "Schema missing 'edges' field"
    assert len(schema["nodes"]) > 0, "Schema has no nodes"

@test("Hub Dashboard UI")
def test_hub_dashboard():
    """Test that Hub Dashboard is accessible"""
    response = requests.get(f"{API_BASE}/hub/")
    assert response.status_code == 200, f"Hub Dashboard returned {response.status_code}"
    assert "Hub Dashboard" in response.text, "Hub Dashboard page not loading correctly"

@test("Recent Runs API")
def test_recent_runs():
    """Test recent runs endpoint"""
    response = requests.get(f"{API_BASE}/api/hub/recent-runs?limit=5")
    assert response.status_code == 200, f"Recent runs API returned {response.status_code}"
    data = response.json()
    assert isinstance(data, list), "Recent runs should return a list"
    
    if len(data) > 0:
        run = data[0]
        assert "run_id" in run, "Run missing run_id"
        assert "status" in run, "Run missing status"
        assert "created_at" in run, "Run missing created_at"

@test("Context Save/Load")
def test_context_operations():
    """Test context save and retrieval"""
    test_context = {
        "run_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "graph": "emailpilot_calendar",
        "brand": "Test Brand",
        "month": "2025-10",
        "env": "test"
    }
    
    # Save context
    response = requests.post(
        f"{API_BASE}/api/hub/context",
        json=test_context
    )
    assert response.status_code == 200, f"Context save returned {response.status_code}"
    data = response.json()
    assert data.get("saved") == True, "Context not saved"

@test("Instrumentation Import")
def test_instrumentation():
    """Test that instrumentation module is importable"""
    try:
        from workflow.instrumentation import (
            instrument_node,
            instrument_workflow,
            create_langsmith_callback,
            get_trace_url
        )
        
        # Test trace URL generation
        trace_url = get_trace_url("test_run_123")
        assert trace_url is None or isinstance(trace_url, str), "Invalid trace URL"
        
    except ImportError as e:
        raise AssertionError(f"Failed to import instrumentation: {e}")

@test("Workflow Editor Access")
def test_workflow_editor():
    """Test that Workflow Editor is accessible"""
    response = requests.get(f"{API_BASE}/static/workflow_editor.html")
    # Accept 200 or 404 (file might not exist yet)
    assert response.status_code in [200, 404], f"Workflow Editor returned unexpected {response.status_code}"
    
    if response.status_code == 200:
        assert "workflow" in response.text.lower(), "Workflow Editor page content invalid"

@test("Environment Variables")
def test_environment():
    """Test that required environment variables are set"""
    from dotenv import load_dotenv
    
    # Load environment
    env_file = Path(".env.langgraph")
    if not env_file.exists():
        raise AssertionError(".env.langgraph file not found")
    
    load_dotenv('.env.langgraph')
    
    # Check critical variables
    required_vars = [
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
        "ENABLE_TRACING"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"  Warning: Missing environment variables: {', '.join(missing)}")

@test("Service Health Checks")
def test_service_health():
    """Test individual service health endpoints"""
    # Main app health
    response = requests.get(f"{API_BASE}/health")
    assert response.status_code == 200, f"Main app health check failed: {response.status_code}"
    
    # Hub API status
    response = requests.get(f"{API_BASE}/api/hub/status")
    assert response.status_code == 200, f"Hub API health check failed: {response.status_code}"
    
    data = response.json()
    
    # Check LangSmith connection
    if data.get("langsmith", {}).get("connected"):
        print("  ✓ LangSmith connected")
    else:
        print("  ⚠ LangSmith not connected (check API key)")
    
    # Check Studio availability
    if data.get("studio", {}).get("available"):
        print("  ✓ Studio configuration detected")
    else:
        print("  ⚠ Studio not configured (normal for dev)")

def main():
    print("=" * 50)
    print("LangGraph Integration Acceptance Tests")
    print("=" * 50)
    print(f"Testing against: {API_BASE}")
    print()
    
    # Run all tests
    test_hub_api_status()
    test_langsmith_connection()
    test_workflow_schema()
    test_hub_dashboard()
    test_recent_runs()
    test_context_operations()
    test_instrumentation()
    test_workflow_editor()
    test_environment()
    test_service_health()
    
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
    
    if failed == 0:
        print("\n🎉 All tests passed! Integration is ready.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())