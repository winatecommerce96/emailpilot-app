#!/usr/bin/env python3
"""
Quick test script to verify OAuth endpoints are accessible
"""
import requests

base_url = "http://localhost:8000"

# Test endpoints
endpoints = [
    "/api/integrations/klaviyo/test",
    "/api/integrations/klaviyo/oauth/start",
]

print("Testing Klaviyo OAuth endpoints...")
print("-" * 50)

for endpoint in endpoints:
    url = base_url + endpoint
    print(f"\nTesting: {url}")
    
    try:
        response = requests.get(url, allow_redirects=False)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 302 or response.status_code == 307:
            print(f"  Redirect to: {response.headers.get('Location', 'N/A')}")
        elif response.status_code == 200:
            print(f"  Response: {response.json()}")
        elif response.status_code == 404:
            print(f"  ❌ NOT FOUND - Endpoint not mounted properly")
        elif response.status_code == 500:
            print(f"  ⚠️ Server Error: {response.json().get('detail', 'Unknown error')}")
        else:
            print(f"  Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "-" * 50)
print("Test complete!")