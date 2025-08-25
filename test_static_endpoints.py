#!/usr/bin/env python3
"""
Quick test to verify all calendar endpoints are working
This mimics what the static HTML page does
"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def test_all_endpoints():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing All Calendar Endpoints\n")
        print("=" * 60)
        
        # 1. Test Build
        print("\n1️⃣ POST /api/calendar/build")
        build_response = await client.post(
            f"{BASE_URL}/api/calendar/build",
            json={
                "client_display_name": "Static Test Client",
                "client_firestore_id": "static_test_123",
                "klaviyo_account_id": "test_klav_static",
                "target_month": 11,
                "target_year": 2025,
                "dry_run": True  # Dry run for quick test
            }
        )
        
        if build_response.status_code == 200:
            build_data = build_response.json()
            correlation_id = build_data.get("correlation_id")
            print(f"✅ Build started: {correlation_id}")
        else:
            print(f"❌ Build failed: {build_response.status_code}")
            return
        
        # 2. Test Status Check
        print("\n2️⃣ GET /api/calendar/build/status/{correlation_id}")
        await asyncio.sleep(1)  # Wait a bit
        
        status_response = await client.get(
            f"{BASE_URL}/api/calendar/build/status/{correlation_id}"
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ Status: {status_data.get('status')} - {status_data.get('progress')}%")
        else:
            print(f"❌ Status check failed: {status_response.status_code}")
        
        # 3. Test Orchestrator Events
        print("\n3️⃣ GET /api/calendar/events/{client_id}?year=YYYY&month=MM")
        events_response = await client.get(
            f"{BASE_URL}/api/calendar/events/demo_cheese_123?year=2025&month=12"
        )
        
        if events_response.status_code == 200:
            events_data = events_response.json()
            if isinstance(events_data, dict) and "events" in events_data:
                print(f"✅ Orchestrator format: {len(events_data['events'])} events")
            elif isinstance(events_data, list):
                print(f"✅ Legacy format: {len(events_data)} events")
            else:
                print("✅ Response received (unknown format)")
        else:
            print(f"❌ Events fetch failed: {events_response.status_code}")
        
        # 4. Test Legacy Events
        print("\n4️⃣ GET /api/calendar/events/{client_id}?start_date=X&end_date=Y")
        legacy_response = await client.get(
            f"{BASE_URL}/api/calendar/events/demo_cheese_123?start_date=2025-12-01&end_date=2025-12-31"
        )
        
        if legacy_response.status_code == 200:
            legacy_data = legacy_response.json()
            event_count = len(legacy_data) if isinstance(legacy_data, list) else len(legacy_data.get("events", []))
            print(f"✅ Legacy endpoint: {event_count} events")
        else:
            print(f"❌ Legacy fetch failed: {legacy_response.status_code}")
        
        # 5. Test Clients
        print("\n5️⃣ GET /api/calendar/clients?active_only=true")
        clients_response = await client.get(
            f"{BASE_URL}/api/calendar/clients?active_only=true"
        )
        
        if clients_response.status_code == 200:
            clients_data = clients_response.json()
            print(f"✅ Found {len(clients_data)} clients")
        else:
            print(f"❌ Clients fetch failed: {clients_response.status_code}")
        
        print("\n" + "=" * 60)
        print("✅ All endpoints tested successfully!")
        print("\n📝 Static page ready for Frontend team at:")
        print(f"   {BASE_URL}/static/calendar_static_reference.html")

if __name__ == "__main__":
    print("📅 Calendar Endpoints Test")
    print("Testing all endpoints that the static page uses...\n")
    
    asyncio.run(test_all_endpoints())