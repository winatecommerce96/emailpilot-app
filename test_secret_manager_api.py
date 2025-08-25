#!/usr/bin/env python3
"""
Test Secret Manager API endpoints
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_get_secrets():
    """Test GET /api/admin/environment"""
    print("Testing GET /api/admin/environment...")
    response = requests.get(f"{BASE_URL}/api/admin/environment")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Successfully fetched {len(data.get('variables', {}))} secrets")
        # Show first 3 secrets as sample
        for i, (key, value) in enumerate(list(data.get('variables', {}).items())[:3]):
            display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"  - {key}: {display_value}")
        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False

def test_create_secret():
    """Test POST /api/admin/environment"""
    print("\nTesting POST /api/admin/environment...")
    test_secret = {
        "variables": {
            "TEST_SECRET_KEY": "test_value_123"
        }
    }
    response = requests.post(
        f"{BASE_URL}/api/admin/environment",
        json=test_secret,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Successfully created/updated secret")
        print(f"  - Message: {data.get('message', 'Success')}")
        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False

def test_delete_secret():
    """Test DELETE /api/admin/environment/{secret_id}"""
    print("\nTesting DELETE /api/admin/environment/TEST_SECRET_KEY...")
    response = requests.delete(f"{BASE_URL}/api/admin/environment/TEST_SECRET_KEY")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Successfully deleted secret")
        print(f"  - Message: {data.get('message', 'Deleted')}")
        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False

def main():
    print("=" * 60)
    print("Secret Manager API Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print("❌ Server is not running at localhost:8000")
            return 1
    except:
        print("❌ Cannot connect to server at localhost:8000")
        return 1
    
    print("✓ Server is running\n")
    
    # Run tests
    results = []
    results.append(test_get_secrets())
    results.append(test_create_secret())
    results.append(test_delete_secret())
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())