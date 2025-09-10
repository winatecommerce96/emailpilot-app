#!/usr/bin/env python3
"""Quick test to verify auth endpoints are working"""

import requests
import json

print("Testing Auth V2 Endpoints...")
print("="*50)

base_url = "http://localhost:8000"

# Test endpoints
endpoints = [
    ("GET", "/test-auth-v2.html", None),
    ("GET", "/api/auth/v2/auth/me", None),
    ("POST", "/api/auth/v2/auth/login", {"email": "demo@emailpilot.ai", "password": "demo"}),
    ("GET", "/api/auth/v2/auth/clerk", None),
]

for method, path, data in endpoints:
    url = base_url + path
    print(f"\n{method} {path}")
    try:
        if method == "GET":
            response = requests.get(url, timeout=2)
        else:
            response = requests.post(url, json=data, timeout=2)
        
        if response.status_code == 200:
            print(f"  ✅ Status: {response.status_code}")
            if path.endswith('.html'):
                print(f"  HTML page loaded ({len(response.text)} bytes)")
            elif 'access_token' in response.text:
                data = response.json()
                print(f"  Token: {data['access_token'][:20]}...")
        elif response.status_code == 401:
            print(f"  🔒 Status: {response.status_code} (Authentication required)")
        else:
            print(f"  ❌ Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"  Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connection refused - Is the server running?")
        print(f"     Run: uvicorn main_firestore:app --port 8000 --host localhost --reload")
    except requests.exceptions.Timeout:
        print(f"  ❌ Request timed out")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*50)
print("IMPORTANT: Restart the server for changes to take effect!")
print("Run: uvicorn main_firestore:app --port 8000 --host localhost --reload")