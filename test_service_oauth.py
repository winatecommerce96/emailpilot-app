#!/usr/bin/env python3
"""
Test script for OAuth service endpoints
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TOKEN = "your-test-jwt-token-here"  # Replace with actual test token

headers = {
    "Authorization": f"Bearer {TEST_TOKEN}",
    "Content-Type": "application/json"
}

def test_asana_endpoints():
    """Test Asana OAuth endpoints"""
    print("🔧 Testing Asana OAuth endpoints...")
    
    # Test auth initiation
    try:
        response = requests.get(f"{BASE_URL}/api/integrations/asana/auth", headers=headers)
        print(f"Asana auth: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Authorization URL: {data.get('authorization_url', 'N/A')[:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test status check
    try:
        response = requests.get(f"{BASE_URL}/api/integrations/asana/status", headers=headers)
        print(f"Asana status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Connected: {data.get('connected', False)}")
    except Exception as e:
        print(f"  Error: {e}")

def test_klaviyo_endpoints():
    """Test Klaviyo OAuth endpoints"""
    print("🔧 Testing Klaviyo OAuth endpoints...")
    
    # Test auth initiation
    try:
        response = requests.get(f"{BASE_URL}/api/integrations/klaviyo/auth", headers=headers)
        print(f"Klaviyo auth: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Authorization URL: {data.get('authorization_url', 'N/A')[:100]}...")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test status check
    try:
        response = requests.get(f"{BASE_URL}/api/integrations/klaviyo/status", headers=headers)
        print(f"Klaviyo status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Connected: {data.get('connected', False)}")
    except Exception as e:
        print(f"  Error: {e}")

def test_health():
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing OAuth service endpoints")
    print("=" * 50)
    
    if not test_health():
        print("\n❌ Server is not running. Start with:")
        print("uvicorn main_firestore:app --port 8000 --host localhost --reload")
        exit(1)
    
    print(f"\n📋 Base URL: {BASE_URL}")
    print("⚠️  Note: These tests require a valid JWT token for authentication")
    print("   Update TEST_TOKEN variable with an actual token for full testing")
    
    print("\n" + "=" * 50)
    test_asana_endpoints()
    
    print("\n" + "=" * 50)
    test_klaviyo_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ OAuth endpoint tests completed")
    print("\nNext steps:")
    print("1. Configure OAuth client credentials in Secret Manager:")
    print("   - asana-client-id")
    print("   - asana-client-secret") 
    print("   - klaviyo-client-id")
    print("   - klaviyo-client-secret")
    print("2. Test OAuth flows with actual provider authorization")