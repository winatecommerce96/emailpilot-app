#!/usr/bin/env python3
"""
Test script to validate Workflow Editor v1 fixes
"""

import requests
import json
import sys
from pathlib import Path

# Test configuration
API_BASE = "http://localhost:8000"
TESTS_PASSED = []
TESTS_FAILED = []

def test_endpoint(method, path, data=None, expected_status=200):
    """Test an API endpoint"""
    url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == expected_status:
            print(f"✅ {method} {path} → {response.status_code}")
            TESTS_PASSED.append(f"{method} {path}")
            return response.json() if response.content else {}
        else:
            print(f"❌ {method} {path} → {response.status_code} (expected {expected_status})")
            TESTS_FAILED.append(f"{method} {path}")
            return None
    except Exception as e:
        print(f"❌ {method} {path} → ERROR: {e}")
        TESTS_FAILED.append(f"{method} {path}")
        return None

def run_tests():
    """Run all endpoint tests"""
    print("="*60)
    print("WORKFLOW EDITOR V1 - FIX VALIDATION")
    print("="*60)
    
    # Test 1: List schemas (plural)
    print("\n1. Testing plural schema endpoints...")
    schemas = test_endpoint("GET", "/api/workflow/schemas")
    if schemas and isinstance(schemas, list):
        print(f"   Found {len(schemas)} schemas")
    
    # Test 2: Get default schema
    print("\n2. Testing get default schema...")
    schema = test_endpoint("GET", "/api/workflow/schemas/default")
    if schema and "name" in schema:
        print(f"   Schema name: {schema['name']}")
    
    # Test 3: Agent discovery with format parameter
    print("\n3. Testing agent discovery...")
    agents = test_endpoint("GET", "/api/workflow/agents?format=workflow")
    if agents and "available_nodes" in agents:
        print(f"   Found {len(agents['available_nodes'])} nodes")
    
    # Test 4: Save schema
    print("\n4. Testing schema save...")
    test_schema = {
        "name": "test_workflow",
        "state": {"test": "str"},
        "nodes": [{"id": "test", "type": "python_fn", "impl": "test:run"}],
        "edges": [],
        "checkpointer": {"type": "sqlite", "dsn": "sqlite:///test.db"}
    }
    result = test_endpoint("POST", "/api/workflow/schemas/default", test_schema)
    if result and result.get("ok"):
        print("   Schema saved successfully")
    
    # Test 5: Compile schema
    print("\n5. Testing schema compilation...")
    compile_result = test_endpoint("POST", "/api/workflow/schemas/default/compile")
    if compile_result and compile_result.get("success"):
        print("   Compilation successful")
    
    # Test 6: Run workflow (stub)
    print("\n6. Testing workflow run...")
    run_result = test_endpoint("POST", "/api/workflow/schemas/default/run", {"test": "data"})
    if run_result and "run_id" in run_result:
        print(f"   Run ID: {run_result['run_id']}")
    
    # Test 7: Validate schema
    print("\n7. Testing schema validation...")
    validate_result = test_endpoint("POST", "/api/workflow/schemas/default/validate")
    if validate_result and "valid" in validate_result:
        print(f"   Valid: {validate_result['valid']}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ PASSED: {len(TESTS_PASSED)}")
    for test in TESTS_PASSED:
        print(f"   - {test}")
    
    if TESTS_FAILED:
        print(f"\n❌ FAILED: {len(TESTS_FAILED)}")
        for test in TESTS_FAILED:
            print(f"   - {test}")
        return False
    else:
        print("\n🎉 ALL TESTS PASSED!")
        return True

def check_html_fixes():
    """Check if HTML fixes are in place"""
    print("\n" + "="*60)
    print("HTML FIX VALIDATION")
    print("="*60)
    
    editor_path = Path(__file__).parent.parent / "frontend/public/workflow_editor.html"
    if not editor_path.exists():
        print("❌ workflow_editor.html not found")
        return False
    
    with open(editor_path) as f:
        content = f.read()
    
    checks = [
        ("React loaded first", '<script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>' in content),
        ("Light theme enforced", 'color-scheme: light !important' in content),
        ("Error banner present", 'id="errorBanner"' in content),
        ("Test component present", 'id="testRoot"' in content),
        ("Defensive fetch", 'safeFetch' in content),
        ("Proper hooks access", 'const { useState, useEffect, useCallback' in content)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        if passed:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    return all_passed

def main():
    """Main test runner"""
    print("Starting Workflow Editor v1 Fix Validation...")
    
    # Check HTML fixes
    html_ok = check_html_fixes()
    
    # Run API tests
    api_ok = run_tests()
    
    # Final report
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    
    if html_ok and api_ok:
        print("✅ PASS - All fixes validated successfully!")
        print("\nThe Workflow Editor should now:")
        print("  • Load without React errors")
        print("  • Display the test counter component")
        print("  • Successfully fetch agents and schemas")
        print("  • Handle errors gracefully")
        print("  • Maintain light theme")
        return 0
    else:
        print("❌ FAIL - Some issues remain")
        if not html_ok:
            print("  • HTML fixes incomplete")
        if not api_ok:
            print("  • API endpoints not all working")
        return 1

if __name__ == "__main__":
    sys.exit(main())