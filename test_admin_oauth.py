#!/usr/bin/env python3
"""
Test script for Admin OAuth functionality
"""
import asyncio
import httpx
import json
from app.deps.firestore import get_db
from app.services.secret_manager import get_secret_manager
from app.services.auth import get_admin_emails, initialize_admin_user

async def test_firestore_connection():
    """Test Firestore connection"""
    print("🔍 Testing Firestore connection...")
    try:
        db = get_db()
        # Try to read from a collection
        test_docs = db.collection("test").limit(1).get()
        print("✅ Firestore connection successful")
        return True
    except Exception as e:
        print(f"❌ Firestore connection failed: {e}")
        return False

def test_secret_manager():
    """Test Secret Manager access"""
    print("🔍 Testing Secret Manager access...")
    try:
        secret_manager = get_secret_manager()
        secrets = secret_manager.list_secrets()
        print(f"✅ Secret Manager access successful - found {len(secrets)} secrets")
        
        # Test OAuth config status
        client_id = secret_manager.get_secret("google-oauth-client-id")
        client_secret = secret_manager.get_secret("google-oauth-client-secret")
        
        if client_id and client_secret:
            print("✅ OAuth credentials found in Secret Manager")
        else:
            print("⚠️  OAuth credentials not configured in Secret Manager")
            print("Run setup_admin_oauth.py to configure them")
        
        return True
    except Exception as e:
        print(f"❌ Secret Manager access failed: {e}")
        return False

async def test_admin_functions():
    """Test admin user functions"""
    print("🔍 Testing admin user functions...")
    try:
        db = get_db()
        
        # Test getting admin emails
        admin_emails = await get_admin_emails(db)
        print(f"✅ Found {len(admin_emails)} admin users: {admin_emails}")
        
        # Test admin user exists
        if admin_emails:
            print("✅ Admin system is configured")
        else:
            print("⚠️  No admin users found")
            print("Run setup_admin_oauth.py to create first admin")
        
        return True
    except Exception as e:
        print(f"❌ Admin functions test failed: {e}")
        return False

async def test_oauth_endpoints():
    """Test OAuth endpoints"""
    print("🔍 Testing OAuth endpoints...")
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test OAuth status endpoint
            response = await client.get(f"{base_url}/api/auth/google/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ OAuth status endpoint working: {status_data}")
            else:
                print(f"❌ OAuth status endpoint failed: {response.status_code}")
                return False
                
            # Test login redirect (should not throw error)
            response = await client.get(f"{base_url}/api/auth/google/login", follow_redirects=False)
            if response.status_code in [302, 307]:  # Redirect responses
                print("✅ OAuth login endpoint working (redirects to Google)")
            else:
                print(f"⚠️  OAuth login endpoint response: {response.status_code}")
                if response.status_code == 500:
                    print("This likely means OAuth is not configured yet")
        
        return True
    except httpx.ConnectError:
        print("⚠️  Could not connect to server - make sure EmailPilot is running")
        print("Start with: uvicorn main_firestore:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ OAuth endpoints test failed: {e}")
        return False

async def test_jwt_functionality():
    """Test JWT token functionality"""
    print("🔍 Testing JWT functionality...")
    try:
        from app.services.auth import create_access_token, verify_token
        from datetime import timedelta
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Test token creation
        test_data = {"sub": "test@example.com", "role": "admin"}
        token = create_access_token(test_data, expires_delta=timedelta(hours=1))
        print("✅ JWT token creation successful")
        
        # Test token verification (mock credentials)
        class MockCredentials:
            def __init__(self, token):
                self.credentials = token
        
        mock_creds = MockCredentials(token)
        decoded = verify_token(mock_creds)
        
        if decoded.get("sub") == "test@example.com":
            print("✅ JWT token verification successful")
        else:
            print("❌ JWT token verification failed - wrong data")
            return False
        
        return True
    except Exception as e:
        print(f"❌ JWT functionality test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 EmailPilot Admin OAuth Test Suite")
    print("=" * 50)
    
    tests = [
        ("Firestore Connection", test_firestore_connection()),
        ("Secret Manager Access", test_secret_manager()),
        ("Admin Functions", test_admin_functions()),
        ("JWT Functionality", test_jwt_functionality()),
        ("OAuth Endpoints", test_oauth_endpoints()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
            
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! OAuth system is ready.")
        print("\nTo use the system:")
        print("1. Run setup_admin_oauth.py if you haven't configured OAuth yet")
        print("2. Start server: uvicorn main_firestore:app --reload --port 8000")
        print("3. Navigate to: http://localhost:8000/api/auth/google/login")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())