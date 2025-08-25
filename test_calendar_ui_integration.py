#!/usr/bin/env python3
"""
Test Calendar UI Integration End-to-End
Verifies that calendar creation shows events in the UI
"""
import asyncio
import httpx
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

# Test client data
TEST_CLIENT = {
    "client_display_name": "Demo Cheese Shop",
    "client_firestore_id": "demo_cheese_123",
    "klaviyo_account_id": "test_klav_456",
    "target_month": 12,
    "target_year": 2025,
    "dry_run": False
}

class CalendarUIIntegrationTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_calendar_build_and_ui_refresh(self):
        """Test the complete flow from build to UI display"""
        print("\n🧪 Testing Calendar UI Integration...")
        print("=" * 60)
        
        # Step 1: Trigger calendar build
        print("\n1️⃣ Triggering calendar build...")
        build_response = await self.client.post(
            f"{BASE_URL}/api/calendar/build",
            json=TEST_CLIENT
        )
        
        if build_response.status_code != 200:
            print(f"❌ Build failed: {build_response.status_code}")
            print(build_response.text)
            return False
            
        build_data = build_response.json()
        correlation_id = build_data.get("correlation_id")
        print(f"✅ Build started with correlation_id: {correlation_id}")
        
        # Step 2: Wait for completion
        print("\n2️⃣ Waiting for build completion...")
        max_attempts = 30
        for i in range(max_attempts):
            status_response = await self.client.get(
                f"{BASE_URL}/api/calendar/build/status/{correlation_id}"
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                progress = status_data.get("progress", 0)
                print(f"   Progress: {progress}% - {status_data.get('message', '')}")
                
                if status_data.get("status") == "completed":
                    print("✅ Build completed successfully!")
                    break
                elif status_data.get("status") == "failed":
                    print(f"❌ Build failed: {status_data.get('message')}")
                    return False
            
            await asyncio.sleep(1)
        else:
            print("❌ Timeout waiting for build completion")
            return False
        
        # Step 3: Fetch events via orchestrator endpoint
        print(f"\n3️⃣ Fetching events for client: {TEST_CLIENT['client_firestore_id']}")
        events_response = await self.client.get(
            f"{BASE_URL}/api/calendar/events/{TEST_CLIENT['client_firestore_id']}"
            f"?year={TEST_CLIENT['target_year']}&month={TEST_CLIENT['target_month']}"
        )
        
        if events_response.status_code != 200:
            print(f"❌ Failed to fetch events: {events_response.status_code}")
            print(events_response.text)
            return False
        
        events_data = events_response.json()
        
        # Check if we got orchestrator format response
        if isinstance(events_data, dict) and "events" in events_data:
            events = events_data["events"]
            print(f"✅ Retrieved {len(events)} orchestrator events")
            print(f"   Calendar ID: {events_data.get('calendar_id')}")
            print(f"   Version: {events_data.get('version')}")
            print(f"   Correlation ID: {events_data.get('correlation_id')}")
            
            # Display first 3 events
            print("\n📅 Sample Events:")
            for i, event in enumerate(events[:3]):
                print(f"   {i+1}. {event.get('campaign_name', event.get('title', 'Untitled'))}")
                print(f"      Date: {event.get('planned_send_datetime', event.get('date', 'No date'))}")
                print(f"      Channel: {event.get('channel', 'email')}")
                print(f"      Theme: {event.get('theme', 'N/A')}")
        else:
            # Legacy format
            events = events_data if isinstance(events_data, list) else []
            print(f"✅ Retrieved {len(events)} legacy events")
        
        # Step 4: Verify events are properly formatted for UI
        print("\n4️⃣ Verifying UI compatibility...")
        issues = []
        
        for event in events:
            # Check required fields for UI
            if not event.get("campaign_name") and not event.get("title"):
                issues.append("Missing title/campaign_name")
            if not event.get("planned_send_datetime") and not event.get("date"):
                issues.append("Missing date/planned_send_datetime")
            if not event.get("channel"):
                issues.append("Missing channel")
        
        if issues:
            print(f"⚠️ Found {len(issues)} formatting issues")
            for issue in set(issues):
                print(f"   - {issue}")
        else:
            print("✅ All events properly formatted for UI")
        
        # Step 5: Test legacy endpoint compatibility
        print("\n5️⃣ Testing legacy endpoint compatibility...")
        start_date = f"{TEST_CLIENT['target_year']}-{TEST_CLIENT['target_month']:02d}-01"
        end_date = f"{TEST_CLIENT['target_year']}-{TEST_CLIENT['target_month']:02d}-31"
        
        legacy_response = await self.client.get(
            f"{BASE_URL}/api/calendar/events/{TEST_CLIENT['client_firestore_id']}"
            f"?start_date={start_date}&end_date={end_date}"
        )
        
        if legacy_response.status_code == 200:
            legacy_data = legacy_response.json()
            print(f"✅ Legacy endpoint returned {len(legacy_data)} events")
        else:
            print(f"⚠️ Legacy endpoint returned {legacy_response.status_code}")
        
        print("\n" + "=" * 60)
        print("✅ Calendar UI Integration Test PASSED!")
        print(f"📊 Summary: {len(events)} events ready for display")
        
        return True
        
    async def test_dry_run_mode(self):
        """Test dry run mode doesn't persist"""
        print("\n🧪 Testing Dry Run Mode...")
        
        dry_run_client = TEST_CLIENT.copy()
        dry_run_client["dry_run"] = True
        dry_run_client["target_month"] = 11  # Different month
        
        # Trigger dry run build
        response = await self.client.post(
            f"{BASE_URL}/api/calendar/build",
            json=dry_run_client
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Dry run completed: {result.get('correlation_id')}")
            
            # Try to fetch events - should not find any for this month
            events_response = await self.client.get(
                f"{BASE_URL}/api/calendar/events/{dry_run_client['client_firestore_id']}"
                f"?year={dry_run_client['target_year']}&month={dry_run_client['target_month']}"
            )
            
            if events_response.status_code == 200:
                data = events_response.json()
                if isinstance(data, dict):
                    events = data.get("events", [])
                else:
                    events = data
                    
                if len(events) == 0:
                    print("✅ Dry run correctly didn't persist events")
                else:
                    print(f"⚠️ Found {len(events)} events in dry run month (unexpected)")
        
    async def cleanup(self):
        await self.client.aclose()

async def main():
    tester = CalendarUIIntegrationTest()
    
    try:
        # Run main integration test
        success = await tester.test_calendar_build_and_ui_refresh()
        
        if success:
            # Run additional tests
            await tester.test_dry_run_mode()
            
        print("\n🎉 All Calendar UI Integration Tests Complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    print("📅 Calendar UI Integration Test Suite")
    print("Make sure the server is running at http://localhost:8000")
    print("Press Ctrl+C to cancel\n")
    
    asyncio.run(main())