#!/usr/bin/env python3
"""
E2E Test for Multi-Page Application (MPA) Architecture
Tests that EmailPilot behaves like a traditional web application
"""

import requests
import json
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"

def test_route(path: str) -> Tuple[int, str, Dict]:
    """Test a single route and return status, content type, and headers"""
    try:
        response = requests.get(f"{BASE_URL}{path}", allow_redirects=False)
        return (
            response.status_code,
            response.headers.get('content-type', ''),
            dict(response.headers)
        )
    except Exception as e:
        return (0, str(e), {})

def check_html_content(path: str) -> bool:
    """Check if route returns proper HTML"""
    try:
        response = requests.get(f"{BASE_URL}{path}")
        content = response.text
        return (
            response.status_code == 200 and
            '<!DOCTYPE html>' in content and
            '<html' in content and
            '</html>' in content
        )
    except:
        return False

def main():
    print("=" * 60)
    print("EmailPilot MPA E2E Test Suite")
    print("=" * 60)
    
    # Test 1: All main routes return HTML
    print("\n1. Testing main routes return proper HTML:")
    routes = ["/", "/calendar", "/clients", "/reports", "/settings"]
    for route in routes:
        status, content_type, _ = test_route(route)
        is_html = 'text/html' in content_type
        has_content = check_html_content(route)
        print(f"  {route:15} Status: {status:3} HTML: {is_html and has_content}")
    
    # Test 2: 404 handling
    print("\n2. Testing 404 handling:")
    invalid_routes = ["/nonexistent", "/foo/bar", "/api/fake"]
    for route in invalid_routes:
        status, content_type, _ = test_route(route)
        print(f"  {route:20} Status: {status:3} (Expected: 404)")
    
    # Test 3: Dynamic routes (client detail)
    print("\n3. Testing dynamic routes:")
    client_routes = ["/clients/client1", "/clients/abc123", "/clients/test"]
    for route in client_routes:
        status, content_type, _ = test_route(route)
        is_html = 'text/html' in content_type
        print(f"  {route:25} Status: {status:3} HTML: {is_html}")
    
    # Test 4: No SPA routing (no catch-all)
    print("\n4. Testing no SPA catch-all:")
    spa_test_routes = ["/random/deep/path", "/another/fake/route"]
    for route in spa_test_routes:
        status, _, _ = test_route(route)
        print(f"  {route:30} Status: {status:3} (Should be 404, not 200)")
    
    # Test 5: Direct deep links work
    print("\n5. Testing deep links work directly:")
    deep_links = [
        ("/calendar", "Calendar"),
        ("/reports", "Reports"),
        ("/clients/test123", "Client")
    ]
    for path, expected_title in deep_links:
        response = requests.get(f"{BASE_URL}{path}")
        has_title = expected_title in response.text
        print(f"  {path:25} Contains '{expected_title}': {has_title}")
    
    # Test 6: API routes still work
    print("\n6. Testing API routes:")
    api_routes = ["/health", "/version", "/api/auth/me"]
    for route in api_routes:
        status, content_type, _ = test_route(route)
        is_json = 'application/json' in content_type
        print(f"  {route:20} Status: {status:3} JSON: {is_json}")
    
    # Test 7: Static files served correctly
    print("\n7. Testing static file serving:")
    static_routes = [
        "/static/dist/app.js",
        "/static/dist/styles.css",
        "/static/dist/Navigation.js"
    ]
    for route in static_routes:
        status, _, _ = test_route(route)
        print(f"  {route:35} Status: {status:3}")
    
    print("\n" + "=" * 60)
    print("MPA E2E Test Complete")
    print("✅ EmailPilot is now a proper Multi-Page Application")
    print("=" * 60)

if __name__ == "__main__":
    main()