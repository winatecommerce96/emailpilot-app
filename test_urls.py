#!/usr/bin/env python3
"""Test the URL naming convention to verify it's working"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# Define comprehensive test endpoints
test_urls = [
    # Agents module
    ("GET", "/api/agents/admin/dashboard", "Admin Agent Dashboard"),
    ("GET", "/api/agents/admin/agents/config", "Admin Agent Config"),
    ("GET", "/api/agents/campaigns/health", "Campaign Agents Health"),
    ("GET", "/api/agents/campaigns/agents", "List Campaign Agents"),
    
    # MCP module
    ("GET", "/api/mcp/health", "MCP Health"),
    ("GET", "/api/mcp/models", "MCP Models"),
    ("GET", "/api/mcp/clients", "MCP Clients"),
    
    # MCP Klaviyo submodule
    ("GET", "/api/mcp/klaviyo/keys", "Klaviyo Keys"),
    
    # Admin module
    ("GET", "/api/admin/health", "Admin Health"),
    ("GET", "/api/admin/system/status", "System Status"),
    ("GET", "/api/admin/environment", "Environment Variables"),
    ("GET", "/api/admin/clients", "Admin Clients List"),
    
    # Calendar module
    ("GET", "/api/calendar/health", "Calendar Health"),
    ("GET", "/api/calendar/events", "Calendar Events"),
    ("GET", "/api/calendar/clients", "Calendar Clients"),
    
    # Auth module
    ("GET", "/api/auth/me", "Current User"),
    
    # Goals module
    ("GET", "/api/goals/clients", "Goals Clients"),
    
    # Performance module
    ("GET", "/api/performance/test-endpoint", "Performance Test"),
    
    # Reports module
    ("GET", "/api/reports/", "Reports List"),
    ("GET", "/api/reports/latest/weekly", "Latest Weekly Report"),
    
    # Dashboard module
    ("GET", "/api/dashboard/quick-stats", "Dashboard Stats"),
    ("GET", "/api/dashboard/overview", "Dashboard Overview"),
    
    # Legacy clients (should these still exist?)
    ("GET", "/api/clients/", "Legacy Clients"),
]

print("=" * 80)
print("TESTING URL NAMING CONVENTION")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
print()

results = {
    "success": [],
    "auth_required": [],
    "not_found": [],
    "error": []
}

for method, endpoint, description in test_urls:
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=3)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=3)
        
        status = response.status_code
        
        # Categorize results
        if status == 200:
            results["success"].append((endpoint, description))
            print(f"✅ {status} | {endpoint:50} | {description}")
        elif status in [401, 403]:
            results["auth_required"].append((endpoint, description))
            print(f"🔒 {status} | {endpoint:50} | {description}")
        elif status == 404:
            results["not_found"].append((endpoint, description))
            print(f"❌ {status} | {endpoint:50} | {description}")
        elif status == 500:
            # Try to get error details
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', 'Server error')
            except:
                error_msg = 'Server error'
            results["error"].append((endpoint, description, error_msg))
            print(f"⚠️  {status} | {endpoint:50} | {description}")
        else:
            results["error"].append((endpoint, description, f"Status {status}"))
            print(f"📍 {status} | {endpoint:50} | {description}")
            
    except requests.exceptions.RequestException as e:
        results["error"].append((endpoint, description, str(e)))
        print(f"🔌 ERR | {endpoint:50} | Connection error")
    except Exception as e:
        results["error"].append((endpoint, description, str(e)))
        print(f"❗ ERR | {endpoint:50} | {str(e)[:30]}")

print()
print("=" * 80)
print("SUMMARY BY STATUS")
print("=" * 80)

print(f"\n✅ WORKING ({len(results['success'])} endpoints):")
if results["success"]:
    for endpoint, desc in results["success"]:
        print(f"   {endpoint:45} - {desc}")
else:
    print("   None")

print(f"\n🔒 AUTH REQUIRED ({len(results['auth_required'])} endpoints):")
if results["auth_required"]:
    for endpoint, desc in results["auth_required"]:
        print(f"   {endpoint:45} - {desc}")
else:
    print("   None")

print(f"\n❌ NOT FOUND ({len(results['not_found'])} endpoints):")
if results["not_found"]:
    for endpoint, desc in results["not_found"]:
        print(f"   {endpoint:45} - {desc}")
else:
    print("   None")

print(f"\n⚠️  ERRORS ({len(results['error'])} endpoints):")
if results["error"]:
    for endpoint, desc, error in results["error"]:
        print(f"   {endpoint:45} - {desc}")
        print(f"      Error: {error}")
else:
    print("   None")

print()
print("=" * 80)
print("VERDICT")
print("=" * 80)
total = len(test_urls)
working = len(results["success"]) + len(results["auth_required"])
print(f"Working endpoints: {working}/{total} ({working*100//total}%)")
print(f"Broken endpoints: {len(results['not_found']) + len(results['error'])}/{total}")

if len(results["not_found"]) > 5:
    print("\n⚠️  WARNING: Many endpoints returning 404. The URL naming convention may not be properly implemented!")
elif working > total * 0.7:
    print("\n✅ URL naming convention appears to be working correctly!")
else:
    print("\n⚠️  Some issues detected with the URL naming convention.")

print("=" * 80)