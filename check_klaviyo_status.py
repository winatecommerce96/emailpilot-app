#!/usr/bin/env python3
"""
Check Klaviyo OAuth status in Firestore
"""

import os
import sys
from google.cloud import firestore

# Set project
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"

def check_klaviyo_status(user_email):
    db = firestore.Client()
    
    print(f"\n🔍 Checking Klaviyo status for {user_email}...")
    print("=" * 60)
    
    # Check user integrations
    try:
        integration_doc = db.collection("users").document(user_email).collection("integrations").document("klaviyo").get()
        
        if integration_doc.exists:
            data = integration_doc.to_dict()
            print("✅ Klaviyo integration found in Firestore!")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Connected at: {data.get('connected_at', 'unknown')}")
            print(f"   Token secret ID: {data.get('token_secret_id', 'not found')}")
            print(f"   Scope: {data.get('scope', 'unknown')}")
            
            # Check if we can get the secret
            if data.get('token_secret_id'):
                print(f"\n📦 Token is stored in Secret Manager as: {data['token_secret_id']}")
                print("   Use this secret ID to retrieve the OAuth token")
            
            return True
        else:
            print("❌ No Klaviyo integration found in Firestore")
            print("   You need to connect Klaviyo through the EmailPilot UI first")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Firestore: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_klaviyo_status.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    success = check_klaviyo_status(user_email)
    
    if success:
        print("\n✅ Next steps:")
        print("1. The OAuth token is connected and stored")
        print("2. Open http://localhost:8000/static/klaviyo_cors_fixed.html")
        print("3. Click 'Check Status' to verify the connection")
        print("4. Click 'Discover Accounts' to find your Klaviyo accounts")
        print("5. Click 'Link to Clients' to connect accounts with EmailPilot clients")
    else:
        print("\n❌ Action required:")
        print("1. Open http://localhost:8000")
        print("2. Log in with your account")
        print("3. Go to Settings or look for an Integrations section")
        print("4. Click 'Connect Klaviyo'")
        print("5. Complete the OAuth flow")
        print("6. You should see 'Mission Accomplished! Connection made.' when done")
    
    sys.exit(0 if success else 1)