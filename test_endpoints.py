#!/usr/bin/env python3
"""Test key endpoints from each module"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8001"

# Define test endpoints - one from each module
test_endpoints = [
    ("Root", "GET", "/"),
    ("Authentication", "GET", "/api/auth/me"),
    ("Admin System", "GET", "/api/admin/health"),
    ("Admin Agent Management", "GET", "/api/agents/admin/agents/config"),
    ("Admin Client Management", "GET", "/api/admin/clients"),
    ("Email/SMS Campaign Agents", "GET", "/api/agents/campaigns/health"),
    ("Calendar", "GET", "/api/calendar/health"),
    ("Dashboard", "GET", "/api/dashboard/quick-stats"),
    ("Goals Management", "GET", "/api/goals/clients"),
    ("MCP Management", "GET", "/api/mcp/health"),
    ("MCP Management", "GET", "/api/mcp/models"),
    ("MCP Klaviyo", "GET", "/api/mcp/klaviyo/keys"),
    ("Performance", "GET", "/api/performance/test-endpoint"),
    ("Reports", "GET", "/api/reports/"),
]

print("=" * 80)
print("TESTING EMAILPILOT API ENDPOINTS")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

results = []

for module, method, endpoint in test_endpoints:
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=5)
        
        status = response.status_code
        
        # Determine result
        if status == 200:
            result = "✅ Success"
            # Try to get a sample of the response
            try:
                data = response.json()
                if isinstance(data, dict) and len(str(data)) < 100:
                    sample = str(data)
                elif isinstance(data, list):
                    sample = f"List with {len(data)} items"
                else:
                    sample = f"{type(data).__name__} response"
            except:
                sample = response.text[:50]
        elif status == 401:
            result = "🔒 Auth Required"
            sample = "Requires authentication"
        elif status == 404:
            result = "❌ Not Found"
            sample = "Endpoint not found"
        elif status == 500:
            result = "⚠️  Server Error"
            sample = "Internal server error"
        else:
            result = f"📍 Status {status}"
            sample = response.text[:50] if response.text else "No response"
            
        results.append((module, endpoint, result, sample))
        print(f"{module:30} {endpoint:45} {result}")
        
    except requests.exceptions.Timeout:
        results.append((module, endpoint, "⏱️ Timeout", "Request timed out"))
        print(f"{module:30} {endpoint:45} ⏱️ Timeout")
    except requests.exceptions.ConnectionError:
        results.append((module, endpoint, "🔌 Connection Error", "Could not connect"))
        print(f"{module:30} {endpoint:45} 🔌 Connection Error")
    except Exception as e:
        results.append((module, endpoint, "❗ Error", str(e)[:50]))
        print(f"{module:30} {endpoint:45} ❗ Error")

print()
print("=" * 80)
print("DETAILED RESULTS")
print("=" * 80)

for module, endpoint, result, sample in results:
    if "Success" in result:
        print(f"\n{module} - {endpoint}")
        print(f"  Status: {result}")
        print(f"  Response: {sample[:100]}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
success_count = sum(1 for _, _, result, _ in results if "Success" in result)
auth_count = sum(1 for _, _, result, _ in results if "Auth" in result)
error_count = sum(1 for _, _, result, _ in results if "Error" in result or "Not Found" in result)

print(f"✅ Successful: {success_count}/{len(results)}")
print(f"🔒 Auth Required: {auth_count}/{len(results)}")
print(f"❌ Errors: {error_count}/{len(results)}")
print("=" * 80)