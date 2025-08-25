#!/usr/bin/env python3
"""
Test script for local calendar development
Run this after starting the server to verify all endpoints work
"""

import requests
import json
from datetime import datetime, date
from typing import Dict, Any

# Configuration
API_BASE = "http://localhost:8000"
CALENDAR_API = f"{API_BASE}/api/calendar"

def test_endpoint(method: str, endpoint: str, data: Dict[Any, Any] = None, expected_status: int = 200) -> Dict:
    """Test an API endpoint"""
    url = f"{CALENDAR_API}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        print(f"✓ {method:6} {endpoint:40} Status: {response.status_code}")
        
        if response.status_code != expected_status:
            print(f"  ⚠️  Expected {expected_status}, got {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        
        if response.status_code == 200:
            return response.json()
        return {}
        
    except requests.exceptions.ConnectionError:
        print(f"✗ {method:6} {endpoint:40} Connection failed - is server running?")
        return {}
    except Exception as e:
        print(f"✗ {method:6} {endpoint:40} Error: {str(e)}")
        return {}

def main():
    """Run all calendar tests"""
    print("=" * 70)
    print("EmailPilot Calendar - Local Development Test")
    print("=" * 70)
    print(f"Testing API at: {CALENDAR_API}")
    print()
    
    # Test health endpoint
    print("1. Testing Health Check")
    print("-" * 40)
    health = test_endpoint("GET", "/health")
    if health:
        print(f"  Service: {health.get('service')}")
        print(f"  Status: {health.get('status')}")
    print()
    
    # Test clients
    print("2. Testing Client Management")
    print("-" * 40)
    clients = test_endpoint("GET", "/clients")
    print(f"  Found {len(clients) if isinstance(clients, list) else 0} clients")
    
    # Create a test client
    test_client = test_endpoint("POST", "/clients", {
        "name": f"Test Client {datetime.now().strftime('%H%M%S')}"
    })
    
    if test_client and 'id' in test_client:
        client_id = test_client['id']
        print(f"  Created client: {client_id}")
    else:
        # Use demo client if creation failed
        client_id = "demo1"
        print(f"  Using demo client: {client_id}")
    print()
    
    # Test events
    print("3. Testing Event Management")
    print("-" * 40)
    
    # Get events
    events = test_endpoint("GET", f"/events?client_id={client_id}")
    print(f"  Found {len(events) if isinstance(events, list) else 0} events")
    
    # Create test event
    test_event = test_endpoint("POST", "/events", {
        "title": "Test Campaign",
        "date": date.today().isoformat(),
        "client_id": client_id,
        "event_type": "cheese-club",
        "content": "Test campaign created by test script"
    })
    
    if test_event and 'id' in test_event:
        event_id = test_event['id']
        print(f"  Created event: {event_id}")
        
        # Update event
        test_endpoint("PUT", f"/events/{event_id}", {
            "title": "Updated Test Campaign"
        })
        
        # Delete event
        test_endpoint("DELETE", f"/events/{event_id}")
    print()
    
    # Test goals
    print("4. Testing Goals Integration")
    print("-" * 40)
    goals = test_endpoint("GET", f"/goals/{client_id}")
    if goals and isinstance(goals, list) and len(goals) > 0:
        goal = goals[0]
        print(f"  Monthly revenue goal: ${goal.get('monthly_revenue', 0):,}")
    print()
    
    # Test dashboard
    print("5. Testing Dashboard")
    print("-" * 40)
    dashboard = test_endpoint("GET", f"/dashboard/{client_id}")
    if dashboard:
        print(f"  Goal: ${dashboard.get('goal', 0):,}")
        print(f"  Current: ${dashboard.get('current_revenue', 0):,}")
        print(f"  Achievement: {dashboard.get('achievement_percentage', 0):.1f}%")
        print(f"  Status: {dashboard.get('status', {}).get('label', 'Unknown')}")
    print()
    
    # Test AI chat
    print("6. Testing AI Chat")
    print("-" * 40)
    chat_response = test_endpoint("POST", "/ai/chat", {
        "message": "What campaigns should I run this month?",
        "client_id": client_id
    })
    if chat_response:
        print(f"  Response: {chat_response.get('response', 'No response')[:100]}...")
        suggestions = chat_response.get('suggestions', [])
        if suggestions:
            print(f"  Suggestions: {len(suggestions)} provided")
    print()
    
    # Test calendar page
    print("7. Testing Calendar UI")
    print("-" * 40)
    try:
        response = requests.get(f"{API_BASE}/calendar")
        if response.status_code == 200:
            print(f"✓ Calendar UI available at: {API_BASE}/calendar")
            print(f"  Page size: {len(response.text)} bytes")
        else:
            print(f"✗ Calendar UI not found (status: {response.status_code})")
    except:
        print(f"✗ Could not reach calendar UI")
    print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"✅ Calendar API is {'running' if health else 'not responding'}")
    print(f"📊 Access the calendar at: {API_BASE}/calendar")
    print(f"📚 View API docs at: {API_BASE}/docs#/Calendar")
    print()
    print("Next steps:")
    print("1. Open http://localhost:8000/calendar in your browser")
    print("2. Select or create a client")
    print("3. Add some campaign events")
    print("4. Check the revenue dashboard")
    print("5. Try the AI chat assistant")

if __name__ == "__main__":
    main()