#!/usr/bin/env python3
"""
Test OAuth Callback Environment Setup
Ensures the server has proper environment for OAuth callbacks
"""

import os
import requests
import subprocess
import sys

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = {
        'GOOGLE_CLOUD_PROJECT': 'emailpilot-438321',
        'SECRET_MANAGER_TRANSPORT': 'rest',
        'ENVIRONMENT': 'development'
    }
    
    missing = []
    for var, expected in required_vars.items():
        value = os.environ.get(var)
        if not value:
            print(f"❌ {var} is not set (should be: {expected})")
            missing.append(f"{var}={expected}")
        else:
            print(f"✅ {var} = {value}")
    
    if missing:
        print("\n⚠️  Missing environment variables!")
        print("To fix, run the server with:")
        print(f"   {' '.join(missing)} uvicorn main_firestore:app --port 8000")
        return False
    
    return True

def test_server_environment():
    """Test if the running server has proper environment"""
    print("\n🔍 Testing Server Environment...")
    
    try:
        # Test OAuth status
        response = requests.get("http://localhost:8000/api/auth/google/status")
        if response.status_code == 200:
            data = response.json()
            if data.get('configured'):
                print("✅ OAuth is configured in the server")
            else:
                print("❌ OAuth is not configured")
                return False
        else:
            print(f"❌ Failed to check OAuth status: {response.status_code}")
            return False
            
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running on http://localhost:8000")
        return False

def simulate_callback():
    """Simulate an OAuth callback to test error handling"""
    print("\n🔍 Simulating OAuth Callback...")
    
    # This simulates what happens when Google redirects back
    callback_url = (
        "http://localhost:8000/api/auth/google/callback"
        "?state=test_state"
        "&code=invalid_test_code"  # Invalid code to test error handling
        "&scope=email+profile"
    )
    
    try:
        response = requests.get(callback_url, allow_redirects=False)
        
        if response.status_code == 307:  # Redirect
            location = response.headers.get('location', '')
            if 'error=' in location:
                print(f"✅ Server handled invalid callback correctly")
                print(f"   Redirected to: {location}")
                return True
            else:
                print(f"⚠️  Unexpected redirect: {location}")
                return False
        elif response.status_code == 500:
            print("❌ Server returned 500 error - environment issue likely")
            print("   This is the error you're experiencing!")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing callback: {e}")
        return False

def main():
    print("=" * 60)
    print("OAuth Callback Environment Test")
    print("=" * 60)
    
    # Check local environment
    env_ok = check_environment()
    
    # Check server
    server_ok = test_server_environment()
    
    if not server_ok:
        print("\n❌ Server is not running or not configured properly")
        print("\n📋 To fix the OAuth callback 500 error:")
        print("1. Stop the current server (Ctrl+C or pkill uvicorn)")
        print("2. Start with proper environment:")
        print("   source .venv/bin/activate")
        print("   export GOOGLE_CLOUD_PROJECT=emailpilot-438321")
        print("   export SECRET_MANAGER_TRANSPORT=rest")
        print("   export ENVIRONMENT=development")
        print("   uvicorn main_firestore:app --port 8000 --reload")
        print("\n3. Or use the start script:")
        print("   ./start_server_oauth.sh")
        sys.exit(1)
    
    # Test callback handling
    callback_ok = simulate_callback()
    
    print("\n" + "=" * 60)
    if env_ok and server_ok and callback_ok:
        print("✅ OAuth environment is properly configured!")
        print("\nYour OAuth error was caused by missing GOOGLE_CLOUD_PROJECT")
        print("The server needs to be restarted with proper environment variables.")
    else:
        print("❌ OAuth environment needs configuration")
    print("=" * 60)

if __name__ == "__main__":
    main()