#!/usr/bin/env python3
"""Check integration status directly via API"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def check_klaviyo_integration():
    """Check Klaviyo integration status for a user"""
    
    print("=" * 60)
    print("KLAVIYO INTEGRATION STATUS CHECK")
    print("=" * 60)
    
    # First, get a guest token for testing
    print("\n1. Getting authentication token...")
    auth_response = requests.post(f"{API_BASE}/api/auth/google/guest")
    
    if auth_response.status_code == 200:
        token = auth_response.json()["access_token"]
        print("   ✅ Got auth token")
    else:
        print(f"   ❌ Failed to get token: {auth_response.status_code}")
        return
    
    # Check user info
    print("\n2. Checking authenticated user...")
    headers = {"Authorization": f"Bearer {token}"}
    me_response = requests.get(f"{API_BASE}/api/auth/google/me", headers=headers)
    
    if me_response.status_code == 200:
        user_data = me_response.json()
        user_email = user_data.get("email", user_data.get("sub", "Unknown"))
        print(f"   ✅ Authenticated as: {user_email}")
    else:
        print(f"   ❌ Failed to get user info: {me_response.status_code}")
        return
    
    # Check Klaviyo status
    print("\n3. Checking Klaviyo connection status...")
    klaviyo_response = requests.get(f"{API_BASE}/api/integrations/klaviyo/status", headers=headers)
    
    if klaviyo_response.status_code == 200:
        klaviyo_data = klaviyo_response.json()
        
        if klaviyo_data.get("connected"):
            print("   ✅ KLAVIYO IS CONNECTED!")
            print(f"\n   Connection Details:")
            
            if klaviyo_data.get("connected_at"):
                connected_at = datetime.fromisoformat(klaviyo_data["connected_at"].replace("Z", "+00:00"))
                print(f"   - Connected: {connected_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if klaviyo_data.get("scope"):
                scopes = klaviyo_data["scope"].split(" ")
                print(f"   - Permissions: {len(scopes)} scopes granted")
                print("   - Scopes:")
                for scope in scopes:
                    print(f"     • {scope}")
        else:
            print("   ⚪ Klaviyo is NOT connected")
            print("   - No active connection found")
    else:
        print(f"   ❌ Failed to check status: {klaviyo_response.status_code}")
        print(f"   Response: {klaviyo_response.text}")
    
    # Check Asana status
    print("\n4. Checking Asana connection status...")
    asana_response = requests.get(f"{API_BASE}/api/integrations/asana/status", headers=headers)
    
    if asana_response.status_code == 200:
        asana_data = asana_response.json()
        
        if asana_data.get("connected"):
            print("   ✅ ASANA IS CONNECTED!")
            print(f"\n   Connection Details:")
            
            if asana_data.get("connected_at"):
                connected_at = datetime.fromisoformat(asana_data["connected_at"].replace("Z", "+00:00"))
                print(f"   - Connected: {connected_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if asana_data.get("user_name"):
                print(f"   - Account: {asana_data['user_name']}")
            
            if asana_data.get("user_email"):
                print(f"   - Email: {asana_data['user_email']}")
        else:
            print("   ⚪ Asana is NOT connected")
            print("   - No active connection found")
    else:
        print(f"   ❌ Failed to check status: {asana_response.status_code}")
    
    print("\n" + "=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    check_klaviyo_integration()