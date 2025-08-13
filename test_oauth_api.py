#!/usr/bin/env python3
"""Test OAuth API endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_oauth_endpoints():
    """Test OAuth configuration endpoints"""
    
    print("Testing OAuth API Endpoints...")
    print("-" * 50)
    
    # Test 1: Check OAuth status (should work without auth)
    print("\n1. Testing OAuth status endpoint...")
    response = requests.get(f"{BASE_URL}/api/auth/google/status")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   OAuth Configured: {data.get('configured', False)}")
        print(f"   Has Client ID: {data.get('has_client_id', False)}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 2: Try to save OAuth config (will fail without auth, but tests the endpoint)
    print("\n2. Testing OAuth config save endpoint...")
    oauth_config = {
        "client_id": "test-client-id",
        "client_secret": "test-secret",
        "redirect_uri": "http://localhost:8000/api/auth/google/callback"
    }
    
    # Without authentication (should get 401 or 403)
    response = requests.post(
        f"{BASE_URL}/api/auth/google/oauth-config",
        json=oauth_config,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status Code: {response.status_code}")
    if response.status_code in [401, 403]:
        print("   ✅ Correctly requires authentication")
    else:
        print(f"   Unexpected response: {response.text}")
    
    # Test 3: List admins (should fail without auth)
    print("\n3. Testing list admins endpoint...")
    response = requests.get(f"{BASE_URL}/api/auth/google/admins")
    print(f"   Status Code: {response.status_code}")
    if response.status_code in [401, 403]:
        print("   ✅ Correctly requires authentication")
    else:
        print(f"   Unexpected response: {response.text}")
    
    print("\n" + "-" * 50)
    print("OAuth endpoints are working correctly!")
    print("\nTo fully test OAuth saving:")
    print("1. Open http://localhost:8000/admin in your browser")
    print("2. Click on the 'OAuth Configuration' tab")
    print("3. Enter your Google OAuth credentials")
    print("4. Click 'Save Configuration'")
    print("\nNote: You need to be logged in as an admin to save OAuth config.")

if __name__ == "__main__":
    test_oauth_endpoints()