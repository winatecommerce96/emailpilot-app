#!/usr/bin/env python3
"""
Test script to verify EmailPilot API with Firestore is working correctly
"""

import requests
import json
from google.cloud import firestore
import os

# Set up Firestore credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/emailpilot-firestore-key.json'

# API Configuration
API_BASE = 'https://emailpilot.ai'
LOCAL_API = 'http://localhost:8080'

def test_api_health():
    """Test if API is running"""
    print("🔍 Testing API Health...")
    try:
        response = requests.get(f"{API_BASE}/api/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy: {data}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to API: {e}")
        return False

def test_firestore_direct():
    """Test direct Firestore access"""
    print("\n🔍 Testing Direct Firestore Access...")
    try:
        db = firestore.Client(project='emailpilot-438321')
        
        # Test clients
        clients = list(db.collection('clients').where('is_active', '==', True).stream())
        print(f"✅ Found {len(clients)} active clients in Firestore")
        
        # Show sample clients
        print("Sample clients:")
        for client_doc in clients[:3]:
            data = client_doc.to_dict()
            print(f"  - {data.get('name', 'Unknown')} (ID: {client_doc.id})")
        
        # Test goals
        goals = list(db.collection('goals').stream())
        print(f"\n✅ Found {len(goals)} goals in Firestore")
        
        return True
    except Exception as e:
        print(f"❌ Firestore error: {e}")
        return False

def simulate_auth_and_test():
    """Simulate authentication and test client/goals endpoints"""
    print("\n🔍 Testing API Endpoints with Simulated Auth...")
    
    # Create a session
    session = requests.Session()
    
    # Simulate login (using mock auth for testing)
    print("Attempting to authenticate...")
    auth_data = {
        "email": "damon@winatecommerce.com",
        "name": "Test User",
        "picture": ""
    }
    
    try:
        # Try to authenticate
        auth_response = session.post(
            f"{API_BASE}/api/auth/google/callback",
            json=auth_data
        )
        
        if auth_response.status_code == 200:
            print("✅ Authentication successful")
            
            # Test clients endpoint
            print("\nTesting /api/clients/ endpoint...")
            clients_response = session.get(f"{API_BASE}/api/clients/")
            
            if clients_response.status_code == 200:
                clients_data = clients_response.json()
                print(f"✅ Clients endpoint working - returned {len(clients_data)} clients")
                for client in clients_data[:3]:
                    print(f"  - {client.get('name', 'Unknown')}")
            else:
                print(f"❌ Clients endpoint returned status {clients_response.status_code}")
                print(f"Response: {clients_response.text[:200]}")
            
            # Test goals endpoint
            print("\nTesting /api/goals/clients endpoint...")
            goals_response = session.get(f"{API_BASE}/api/goals/clients")
            
            if goals_response.status_code == 200:
                goals_data = goals_response.json()
                print(f"✅ Goals endpoint working - returned {len(goals_data)} clients with goals")
            else:
                print(f"❌ Goals endpoint returned status {goals_response.status_code}")
                
        else:
            print(f"❌ Authentication failed with status {auth_response.status_code}")
            print(f"Response: {auth_response.text[:200]}")
            
    except Exception as e:
        print(f"❌ API test error: {e}")

def main():
    print("=" * 50)
    print("EMAILPILOT FIRESTORE API TEST")
    print("=" * 50)
    
    # Test API health
    api_healthy = test_api_health()
    
    # Test direct Firestore access
    firestore_working = test_firestore_direct()
    
    # Test API endpoints with auth
    if api_healthy:
        simulate_auth_and_test()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if api_healthy and firestore_working:
        print("✅ EmailPilot is configured correctly!")
        print("✅ Firestore data is accessible")
        print("\n📝 Next steps:")
        print("1. Login to https://emailpilot.ai with an approved email")
        print("2. Check that Clients and Goals are displayed")
        print("3. If data doesn't show, check browser console for errors")
    else:
        print("❌ Issues detected - see errors above")

if __name__ == "__main__":
    main()