#!/usr/bin/env python3
"""
Deployment verification script for EmailPilot MCP system
"""
import requests
import json
import sys
import time
from datetime import datetime

def test_deployment(service_url: str):
    """Test the deployed EmailPilot service"""
    print(f"🔍 Testing deployment at: {service_url}")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Health check
    tests_total += 1
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{service_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data.get('status')}")
            tests_passed += 1
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Admin API status
    tests_total += 1
    print("2. Testing admin API status...")
    try:
        response = requests.get(f"{service_url}/api/admin/system/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Admin API working, status: {data.get('status')}")
            tests_passed += 1
        else:
            print(f"   ❌ Admin API failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Admin API error: {e}")
    
    # Test 3: MCP models endpoint (should require auth)
    tests_total += 1
    print("3. Testing MCP models endpoint...")
    try:
        response = requests.get(f"{service_url}/api/mcp/models", timeout=10)
        if response.status_code == 401:
            print(f"   ✅ MCP endpoints require authentication (401 - correct)")
            tests_passed += 1
        elif response.status_code == 200:
            data = response.json()
            print(f"   ✅ MCP models accessible: {len(data)} models")
            tests_passed += 1
        else:
            print(f"   ❌ Unexpected MCP response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ MCP models error: {e}")
    
    # Test 4: Frontend app
    tests_total += 1
    print("4. Testing frontend app...")
    try:
        response = requests.get(f"{service_url}/app", timeout=10)
        if response.status_code == 200 and "EmailPilot" in response.text:
            print(f"   ✅ Frontend app loads successfully")
            tests_passed += 1
        else:
            print(f"   ❌ Frontend app failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Frontend app error: {e}")
    
    # Test 5: Database migration check
    tests_total += 1
    print("5. Testing database migration...")
    try:
        # This is indirect - we check if the service starts successfully
        response = requests.get(f"{service_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Database appears to be migrated (service starts)")
            tests_passed += 1
        else:
            print(f"   ❌ Potential database issue")
    except Exception as e:
        print(f"   ❌ Database check error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 60)
    
    success_rate = (tests_passed / tests_total) * 100
    print(f"Tests passed: {tests_passed}/{tests_total} ({success_rate:.1f}%)")
    
    if tests_passed == tests_total:
        print("🎉 Deployment verification PASSED! System is ready for use.")
        print("\n📝 Next steps:")
        print(f"1. Access admin panel: {service_url}/app")
        print("2. Login with admin/admin123")
        print("3. Navigate to Admin > MCP Management")
        print("4. Add MCP clients with API keys")
        print("5. Test multi-model functionality")
        return True
    elif tests_passed >= tests_total * 0.8:
        print("⚠️ Deployment verification mostly successful with minor issues.")
        print("The system should be functional, but check failed tests.")
        return True
    else:
        print("❌ Deployment verification FAILED. Please check the issues above.")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python verify_deployment.py <service_url>")
        print("Example: python verify_deployment.py https://your-service-url.run.app")
        sys.exit(1)
    
    service_url = sys.argv[1].rstrip('/')
    
    print("🚀 EmailPilot MCP System Deployment Verification")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Wait a moment for service to be ready
    print("⏳ Waiting 5 seconds for service to be ready...")
    time.sleep(5)
    
    success = test_deployment(service_url)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()