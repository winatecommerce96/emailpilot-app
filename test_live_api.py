#!/usr/bin/env python3
"""
Test the live EmailPilot.ai API to diagnose display issues
"""

import requests
import json

API_BASE = 'https://emailpilot.ai'

def test_without_auth():
    """Test endpoints without authentication"""
    print("🔍 Testing API Endpoints WITHOUT Authentication")
    print("=" * 50)
    
    endpoints = [
        '/api/',
        '/api/health',
        '/api/clients/',
        '/api/goals/clients',
    ]
    
    for endpoint in endpoints:
        url = f"{API_BASE}{endpoint}"
        try:
            response = requests.get(url)
            print(f"\n{endpoint}:")
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"  Response: List with {len(data)} items")
                else:
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}")
            elif response.status_code == 401:
                print(f"  Response: Authentication required (expected)")
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")

def test_with_mock_auth():
    """Test with simulated authentication"""
    print("\n\n🔍 Testing API Endpoints WITH Mock Authentication")
    print("=" * 50)
    
    session = requests.Session()
    
    # Try to authenticate
    print("\nAttempting authentication...")
    auth_response = session.post(
        f"{API_BASE}/api/auth/google/callback",
        json={
            "email": "damon@winatecommerce.com",
            "name": "Damon",
            "picture": ""
        }
    )
    
    print(f"Auth Status: {auth_response.status_code}")
    if auth_response.status_code == 200:
        print("✅ Authentication successful")
        auth_data = auth_response.json()
        print(f"User: {auth_data.get('user', {}).get('email', 'Unknown')}")
        
        # Now test authenticated endpoints
        print("\n📊 Testing authenticated endpoints:")
        
        # Test clients
        clients_response = session.get(f"{API_BASE}/api/clients/")
        print(f"\n/api/clients/:")
        print(f"  Status: {clients_response.status_code}")
        if clients_response.status_code == 200:
            clients = clients_response.json()
            print(f"  ✅ Retrieved {len(clients)} clients")
            for client in clients[:3]:
                print(f"    - {client.get('name', 'Unknown')} (ID: {client.get('id', 'Unknown')})")
        else:
            print(f"  ❌ Error: {clients_response.text[:200]}")
        
        # Test goals
        goals_response = session.get(f"{API_BASE}/api/goals/clients")
        print(f"\n/api/goals/clients:")
        print(f"  Status: {goals_response.status_code}")
        if goals_response.status_code == 200:
            goals_data = goals_response.json()
            print(f"  ✅ Retrieved {len(goals_data)} clients with goals")
            for client in goals_data[:3]:
                print(f"    - {client.get('name', 'Unknown')}: {client.get('goals_count', 0)} goals")
        else:
            print(f"  ❌ Error: {goals_response.text[:200]}")
            
        # Test dashboard stats
        stats_response = session.get(f"{API_BASE}/api/dashboard/stats")
        print(f"\n/api/dashboard/stats:")
        print(f"  Status: {stats_response.status_code}")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"  ✅ Dashboard stats:")
            print(f"    - Total Clients: {stats.get('totalClients', 0)}")
            print(f"    - Monthly Goals: {stats.get('monthlyGoals', 0)}")
            print(f"    - Active Reports: {stats.get('activeReports', 0)}")
        else:
            print(f"  ❌ Error: {stats_response.text[:200]}")
            
    else:
        print(f"❌ Authentication failed: {auth_response.text[:200]}")

def check_frontend():
    """Check if frontend files are being served"""
    print("\n\n🔍 Checking Frontend Files")
    print("=" * 50)
    
    # Check main page
    response = requests.get(f"{API_BASE}/")
    print(f"Main page (/):")
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {response.headers.get('content-type', 'Unknown')}")
    if 'text/html' in response.headers.get('content-type', ''):
        print(f"  ✅ HTML page served")
        # Check if it contains React app
        if 'React' in response.text or 'app.js' in response.text:
            print(f"  ✅ React app detected")
    
    # Check app.js
    response = requests.get(f"{API_BASE}/app.js")
    print(f"\nJavaScript (/app.js):")
    print(f"  Status: {response.status_code}")
    print(f"  Content-Type: {response.headers.get('content-type', 'Unknown')}")
    if response.status_code == 200:
        print(f"  ✅ JavaScript file served ({len(response.text)} bytes)")
        # Check for key functions
        if 'ClientsView' in response.text and 'GoalsView' in response.text:
            print(f"  ✅ ClientsView and GoalsView components found")
        if 'API_BASE_URL' in response.text:
            # Extract API_BASE_URL configuration
            for line in response.text.split('\n'):
                if 'API_BASE_URL' in line:
                    print(f"  📍 {line.strip()[:100]}")
                    break

def main():
    print("=" * 50)
    print("EMAILPILOT.AI LIVE DIAGNOSTICS")
    print("=" * 50)
    
    test_without_auth()
    test_with_mock_auth()
    check_frontend()
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    print("\n🔍 Check browser console for any JavaScript errors")
    print("🔍 Ensure cookies are enabled for session management")
    print("🔍 Try clearing browser cache and cookies")

if __name__ == "__main__":
    main()