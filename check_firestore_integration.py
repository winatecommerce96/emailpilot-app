#!/usr/bin/env python3
"""Check Klaviyo integration directly in Firestore"""

import os
from google.cloud import firestore
from datetime import datetime

# Set the project
os.environ["GOOGLE_CLOUD_PROJECT"] = "emailpilot-438321"

def check_integrations():
    """Check all user integrations in Firestore"""
    
    db = firestore.Client()
    
    print("=" * 60)
    print("FIRESTORE INTEGRATION CHECK")
    print("=" * 60)
    
    # Check specific user
    user_email = "damon@winatecommerce.com"
    print(f"\nChecking integrations for: {user_email}")
    print("-" * 40)
    
    # Check Klaviyo integration
    klaviyo_doc = db.collection("users").document(user_email).collection("integrations").document("klaviyo").get()
    
    if klaviyo_doc.exists:
        data = klaviyo_doc.to_dict()
        print("\n✅ KLAVIYO INTEGRATION FOUND!")
        print(f"   Status: {data.get('status', 'unknown')}")
        
        if data.get('connected_at'):
            connected_at = data['connected_at']
            print(f"   Connected: {connected_at}")
        
        if data.get('token_secret_id'):
            print(f"   Token stored in: {data['token_secret_id']}")
        
        if data.get('scope'):
            scopes = data['scope'].split(' ')
            print(f"   Scopes ({len(scopes)}): {', '.join(scopes[:3])}...")
        
        if data.get('expires_at'):
            print(f"   Expires: {data['expires_at']}")
    else:
        print("\n⚪ No Klaviyo integration found")
    
    # Check Asana integration
    asana_doc = db.collection("users").document(user_email).collection("integrations").document("asana").get()
    
    if asana_doc.exists:
        data = asana_doc.to_dict()
        print("\n✅ ASANA INTEGRATION FOUND!")
        print(f"   Status: {data.get('status', 'unknown')}")
        
        if data.get('connected_at'):
            print(f"   Connected: {data['connected_at']}")
        
        if data.get('user_name'):
            print(f"   User: {data['user_name']}")
    else:
        print("\n⚪ No Asana integration found")
    
    # Check all users with integrations
    print("\n" + "=" * 60)
    print("ALL USERS WITH INTEGRATIONS")
    print("-" * 40)
    
    users = db.collection("users").stream()
    users_with_integrations = []
    
    for user_doc in users:
        integrations = user_doc.reference.collection("integrations").stream()
        integration_list = []
        
        for integration in integrations:
            integration_list.append(integration.id)
        
        if integration_list:
            users_with_integrations.append({
                "email": user_doc.id,
                "integrations": integration_list
            })
    
    if users_with_integrations:
        for user in users_with_integrations:
            print(f"\n📧 {user['email']}")
            for integration in user['integrations']:
                print(f"   - {integration}")
    else:
        print("\nNo users have any integrations configured")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_integrations()