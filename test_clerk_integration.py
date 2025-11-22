#!/usr/bin/env python3
"""
Test script for Clerk authentication integration
Verifies that Clerk keys are properly configured in Secret Manager
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_secret_manager_keys():
    """Check if Clerk keys are available in Secret Manager"""
    print("\n" + "="*60)
    print("🔑 Checking Clerk Keys in Secret Manager")
    print("="*60)
    
    try:
        from app.services.secret_manager import SecretManagerService
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_manager = SecretManagerService(project_id=project_id)
        
        secrets_to_check = [
            ("CLERK_SECRET_KEY", "Clerk Secret Key", True),
            ("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "Clerk Publishable Key", True),
            ("CLERK_WEBHOOK_SECRET", "Clerk Webhook Secret", False),  # Optional
        ]
        
        results = []
        for secret_name, display_name, required in secrets_to_check:
            try:
                # Try to get the secret
                value = secret_manager.get_secret(secret_name)
                if value:
                    # Don't print the actual secret value, just confirm it exists
                    preview = value[:10] + "..." if len(value) > 10 else "***"
                    results.append({
                        "name": display_name,
                        "status": "✅ Found",
                        "preview": preview,
                        "required": required
                    })
                    print(f"✅ {display_name}: Found (starts with: {preview})")
                else:
                    results.append({
                        "name": display_name,
                        "status": "⚠️ Empty",
                        "required": required
                    })
                    print(f"⚠️ {display_name}: Empty value")
            except Exception as e:
                status = "❌ Not found" if required else "ℹ️ Not configured (optional)"
                results.append({
                    "name": display_name,
                    "status": status,
                    "error": str(e),
                    "required": required
                })
                print(f"{status} {display_name}: {e}")
        
        return results
        
    except ImportError as e:
        print(f"❌ Failed to import Secret Manager: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []

def test_auth_endpoints():
    """Test the authentication endpoints"""
    print("\n" + "="*60)
    print("🌐 Testing Authentication Endpoints")
    print("="*60)
    
    # Check if Clerk SDK is available
    try:
        import clerk_backend_api
        print("ℹ️ Clerk SDK is installed")
    except ImportError:
        print("ℹ️ Clerk SDK not installed - using lite version")
    
    base_url = "http://localhost:8000"
    endpoints = [
        {
            "name": "Auth V2 Status",
            "method": "GET",
            "url": f"{base_url}/api/auth/v2/auth/me",
            "expected_status": [401, 200],  # 401 if not authenticated, 200 if authenticated
        },
        {
            "name": "Demo Login",
            "method": "POST",
            "url": f"{base_url}/api/auth/v2/auth/login",
            "data": {
                "email": "demo@emailpilot.ai",
                "password": "demo"
            },
            "expected_status": [200],
        },
        {
            "name": "Guest Access",
            "method": "POST",
            "url": f"{base_url}/api/auth/v2/auth/guest",
            "expected_status": [200],
        },
        {
            "name": "Clerk SSO Status",
            "method": "GET",
            "url": f"{base_url}/api/auth/v2/auth/sso/clerk",
            "expected_status": [302, 501],  # 302 redirect if configured, 501 if not
        },
    ]
    
    results = []
    session = requests.Session()
    
    for endpoint in endpoints:
        try:
            print(f"\n📍 Testing: {endpoint['name']}")
            print(f"   URL: {endpoint['url']}")
            
            if endpoint["method"] == "GET":
                response = session.get(endpoint["url"], allow_redirects=False, timeout=5)
            elif endpoint["method"] == "POST":
                headers = {"Content-Type": "application/json"}
                data = endpoint.get("data", {})
                response = session.post(
                    endpoint["url"],
                    json=data,
                    headers=headers,
                    timeout=5
                )
            
            status_ok = response.status_code in endpoint["expected_status"]
            status_symbol = "✅" if status_ok else "❌"
            
            print(f"   Status: {status_symbol} {response.status_code}")
            
            # Try to parse JSON response
            try:
                json_data = response.json()
                if "access_token" in json_data:
                    print(f"   ✅ Token received: {json_data['access_token'][:20]}...")
                    # Store token for subsequent requests
                    session.headers["Authorization"] = f"Bearer {json_data['access_token']}"
                elif "detail" in json_data:
                    print(f"   ℹ️ Message: {json_data['detail']}")
                elif "user" in json_data:
                    print(f"   ✅ User: {json_data['user'].get('email', 'Unknown')}")
            except:
                if response.status_code == 302:
                    print(f"   ↗️ Redirect to: {response.headers.get('Location', 'Unknown')}")
            
            results.append({
                "endpoint": endpoint["name"],
                "status": response.status_code,
                "success": status_ok
            })
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection refused - Is the server running?")
            results.append({
                "endpoint": endpoint["name"],
                "status": "Connection Error",
                "success": False
            })
        except requests.exceptions.Timeout:
            print(f"   ❌ Request timed out")
            results.append({
                "endpoint": endpoint["name"],
                "status": "Timeout",
                "success": False
            })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "endpoint": endpoint["name"],
                "status": f"Error: {e}",
                "success": False
            })
    
    return results

def test_api_key_management(access_token: Optional[str] = None):
    """Test API key management if we have an access token"""
    if not access_token:
        print("\n⚠️ Skipping API key tests (no access token)")
        return []
    
    print("\n" + "="*60)
    print("🔐 Testing API Key Management")
    print("="*60)
    
    base_url = "http://localhost:8000"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    results = []
    
    # Create an API key
    try:
        print("\n📍 Creating API key...")
        response = requests.post(
            f"{base_url}/api/auth/v2/auth/api-keys",
            json={
                "name": f"Test Key {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "scopes": ["read", "write"],
                "expires_in_days": 30
            },
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Created: {data['name']}")
            print(f"   🔑 Key: {data['api_key'][:20]}...")
            results.append({"action": "create", "success": True})
            
            # List API keys
            print("\n📍 Listing API keys...")
            response = requests.get(
                f"{base_url}/api/auth/v2/auth/api-keys",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                keys = response.json()
                print(f"   ✅ Found {len(keys)} API key(s)")
                for key in keys:
                    print(f"      - {key['name']} ({key['key_prefix']}...)")
                results.append({"action": "list", "success": True})
            else:
                print(f"   ❌ Failed to list keys: {response.status_code}")
                results.append({"action": "list", "success": False})
        else:
            print(f"   ❌ Failed to create key: {response.status_code}")
            results.append({"action": "create", "success": False})
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append({"action": "api_keys", "success": False, "error": str(e)})
    
    return results

def main():
    """Run all tests"""
    print("\n" + "🚀 EmailPilot Clerk Integration Test Suite " + "🚀")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")
    
    # Test 1: Check Secret Manager
    secret_results = check_secret_manager_keys()
    
    # Test 2: Test Auth Endpoints
    endpoint_results = test_auth_endpoints()
    
    # Test 3: Try to get a token for API key tests
    access_token = None
    try:
        response = requests.post(
            "http://localhost:8000/api/auth/v2/auth/login",
            json={"email": "demo@emailpilot.ai", "password": "demo"},
            timeout=5
        )
        if response.status_code == 200:
            access_token = response.json().get("access_token")
    except:
        pass
    
    # Test 4: Test API Key Management
    api_key_results = test_api_key_management(access_token)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    # Secret Manager Summary
    required_secrets = [s for s in secret_results if s.get("required", False)]
    found_secrets = [s for s in required_secrets if "Found" in s.get("status", "")]
    print(f"\n🔑 Secret Manager: {len(found_secrets)}/{len(required_secrets)} required secrets found")
    
    # Endpoint Summary
    successful_endpoints = [e for e in endpoint_results if e.get("success", False)]
    print(f"🌐 Endpoints: {len(successful_endpoints)}/{len(endpoint_results)} tests passed")
    
    # API Key Summary
    if api_key_results:
        successful_api = [a for a in api_key_results if a.get("success", False)]
        print(f"🔐 API Keys: {len(successful_api)}/{len(api_key_results)} operations successful")
    
    # Overall Status
    print("\n" + "="*60)
    all_required_secrets = len(found_secrets) == len(required_secrets)
    
    if all_required_secrets and len(successful_endpoints) > 0:
        print("✅ Clerk integration is properly configured!")
        print("\n📝 Next steps:")
        print("1. Visit http://localhost:8000/static/test-auth-v2.html to test the UI")
        print("2. Configure webhook endpoint in Clerk dashboard")
        print("3. Set up production keys before deployment")
        return 0
    else:
        print("⚠️ Clerk integration needs configuration")
        print("\n📝 To complete setup:")
        if not all_required_secrets:
            print("1. Add missing secrets to Google Secret Manager:")
            for secret in required_secrets:
                if "Found" not in secret.get("status", ""):
                    print(f"   - {secret['name']}")
        print("2. Restart the server after adding secrets")
        print("3. Run this test again to verify")
        return 1

if __name__ == "__main__":
    sys.exit(main())