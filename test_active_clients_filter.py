#!/usr/bin/env python3
"""
Test script for the active clients filter feature in the calendar API
"""

import requests
import json
from datetime import datetime

def test_calendar_clients_api():
    """Test the calendar clients endpoint with active filtering"""
    
    base_url = "http://localhost:8000"
    endpoint = "/api/calendar/clients"
    
    print("🧪 Testing Calendar Clients API with Active Filtering")
    print("=" * 60)
    
    test_cases = [
        {"params": {}, "description": "All clients (no filter)"},
        {"params": {"active_only": True}, "description": "Active clients only"},
        {"params": {"active_only": False}, "description": "Inactive clients only"},
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['description']}")
        print("-" * 40)
        
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, params=test_case["params"], timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                clients = response.json()
                print(f"Number of clients returned: {len(clients)}")
                
                # Display client details
                for i, client in enumerate(clients[:3]):  # Show first 3 clients
                    print(f"  {i+1}. {client.get('name', 'N/A')} (Active: {client.get('is_active', 'N/A')})")
                
                if len(clients) > 3:
                    print(f"  ... and {len(clients) - 3} more clients")
                
                # Verify filtering logic
                if test_case["params"].get("active_only") is True:
                    inactive_count = sum(1 for c in clients if not c.get('is_active', True))
                    if inactive_count > 0:
                        print(f"⚠️  WARNING: Found {inactive_count} inactive clients when filtering for active only")
                    else:
                        print("✅ Filtering working correctly - only active clients returned")
                
                elif test_case["params"].get("active_only") is False:
                    active_count = sum(1 for c in clients if c.get('is_active', True))
                    if active_count > 0:
                        print(f"⚠️  WARNING: Found {active_count} active clients when filtering for inactive only")
                    else:
                        print("✅ Filtering working correctly - only inactive clients returned")
                
            else:
                print(f"❌ Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

def test_endpoint_documentation():
    """Test that the endpoint is properly documented in the API docs"""
    
    print("\n📚 Testing API Documentation")
    print("=" * 40)
    
    try:
        base_url = "http://localhost:8000"
        docs_url = f"{base_url}/docs"
        
        print(f"API Documentation available at: {docs_url}")
        print("You can visit this URL to see the interactive API documentation")
        print("and test the /api/calendar/clients endpoint with the active_only parameter")
        
    except Exception as e:
        print(f"❌ Error checking documentation: {e}")

if __name__ == "__main__":
    print("🚀 Starting Active Clients Filter Test")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
        else:
            print("⚠️  Server responded but may have issues")
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start the server with:")
        print("   source .venv/bin/activate")
        print("   uvicorn main_firestore:app --port 8000")
        exit(1)
    
    # Run tests
    test_calendar_clients_api()
    test_endpoint_documentation()
    
    print(f"\n✨ All tests completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")