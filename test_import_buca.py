#!/usr/bin/env python3
"""
QA Test Script: Buca di Beppo December Campaign Import
Tests the complete import workflow and verifies persistence.
"""

import json
import requests
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
CLIENT_ID = "buca-di-beppo"
JSON_FILE = "/Users/Damon/Downloads/buca_dec_4.json"

def log_test(message, status="INFO"):
    """Log test messages with timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
    print(f"[{timestamp}] {symbols.get(status, 'ℹ️')} {message}")

def read_import_file():
    """Read and parse the JSON import file"""
    log_test("Reading import file...", "INFO")
    with open(JSON_FILE, 'r') as f:
        events = json.load(f)
    log_test(f"Loaded {len(events)} events from file", "PASS")
    return events

def transform_event(event):
    """Transform JSON event to API format"""
    # Map JSON fields to API fields
    return {
        "client_id": CLIENT_ID,  # Each event needs client_id!
        "title": event.get("title", "Untitled"),
        "event_date": event.get("date"),  # CRITICAL: Use event_date, not date
        "time": event.get("time", "10:00 AM"),  # Default to 10:00 AM with AM/PM
        "description": event.get("content", ""),
        "event_type": event.get("event_type", "email"),
        "channel": event.get("channel", "email"),  # Include channel at top level
        "segment": event.get("segment", ""),
        "color": get_event_color(event.get("event_type", "email")),
        "metadata": {
            "channel": event.get("channel", "email"),
            "offer": event.get("offer", ""),
            "original_event_type": event.get("event_type", "")
        }
    }

def get_event_color(event_type):
    """Get color based on event type"""
    colors = {
        "email": "bg-blue-100 text-blue-800",
        "sms": "bg-green-100 text-green-800",
        "resend": "bg-yellow-100 text-yellow-800",
        "new": "bg-purple-100 text-purple-800",
        "changed": "bg-orange-100 text-orange-800"
    }
    return colors.get(event_type, "bg-gray-100 text-gray-800")

def test_1_clear_existing_events():
    """Test 1: Clear any existing events for clean slate"""
    log_test("TEST 1: Clearing existing events", "INFO")

    # Get existing events for December 2025
    response = requests.get(
        f"{API_BASE}/api/calendar/events",
        params={
            "client_id": CLIENT_ID,
            "start_date": "2025-12-01",
            "end_date": "2025-12-31"
        }
    )

    if response.status_code == 200:
        existing = response.json().get("events", [])
        log_test(f"Found {len(existing)} existing events", "INFO")

        # Delete each event
        deleted_count = 0
        for event in existing:
            delete_response = requests.delete(
                f"{API_BASE}/api/calendar/events/{event['id']}"
            )
            if delete_response.status_code == 200:
                deleted_count += 1

        log_test(f"Deleted {deleted_count} events", "PASS" if deleted_count == len(existing) else "WARN")
    else:
        log_test(f"Failed to get existing events: {response.status_code}", "FAIL")

def test_2_bulk_import():
    """Test 2: Bulk import events from JSON file"""
    log_test("TEST 2: Bulk importing events", "INFO")

    # Read and transform events
    source_events = read_import_file()
    transformed_events = [transform_event(e) for e in source_events]

    # Prepare bulk create request
    bulk_data = {
        "client_id": CLIENT_ID,
        "events": transformed_events
    }

    # Send bulk create request
    response = requests.post(
        f"{API_BASE}/api/calendar/create-bulk-events",
        json=bulk_data
    )

    if response.status_code == 200:
        result = response.json()
        created_count = result.get("count", 0)
        log_test(f"Successfully created {created_count} events", "PASS")
        return created_count
    else:
        log_test(f"Bulk import failed: {response.status_code} - {response.text}", "FAIL")
        return 0

def test_3_verify_retrieval(expected_count):
    """Test 3: Verify events can be retrieved"""
    log_test("TEST 3: Verifying event retrieval", "INFO")

    # Wait a moment for Firestore to index
    time.sleep(2)

    # Get events for December 2025
    response = requests.get(
        f"{API_BASE}/api/calendar/events",
        params={
            "client_id": CLIENT_ID,
            "start_date": "2025-12-01",
            "end_date": "2025-12-31"
        }
    )

    if response.status_code == 200:
        events = response.json().get("events", [])
        retrieved_count = len(events)
        log_test(f"Retrieved {retrieved_count} events", "INFO")

        if retrieved_count == expected_count:
            log_test(f"Count matches expected: {expected_count}", "PASS")
            return True, events
        else:
            log_test(f"Count mismatch! Expected {expected_count}, got {retrieved_count}", "FAIL")
            return False, events
    else:
        log_test(f"Retrieval failed: {response.status_code}", "FAIL")
        return False, []

def test_4_verify_persistence():
    """Test 4: Verify events persist after reload"""
    log_test("TEST 4: Testing persistence (waiting 10 seconds)", "INFO")

    time.sleep(10)

    response = requests.get(
        f"{API_BASE}/api/calendar/events",
        params={
            "client_id": CLIENT_ID,
            "start_date": "2025-12-01",
            "end_date": "2025-12-31"
        }
    )

    if response.status_code == 200:
        events = response.json().get("events", [])
        log_test(f"Events still present after 10s: {len(events)}", "PASS" if len(events) > 0 else "FAIL")
        return len(events) > 0
    else:
        log_test(f"Persistence check failed: {response.status_code}", "FAIL")
        return False

def test_5_verify_event_details(events):
    """Test 5: Verify event details are correct"""
    log_test("TEST 5: Verifying event details", "INFO")

    if not events:
        log_test("No events to verify", "FAIL")
        return False

    # Check a few sample events
    sample_checks = [
        ("E#0: Cyber Monday", "2025-12-01"),
        ("SMS #1: Weekend Only Deal", "2025-12-06"),
        ("E#9: $20 OFF $40 (Jan Offer)", "2025-12-27")
    ]

    all_passed = True
    for title, expected_date in sample_checks:
        matching = [e for e in events if title in e.get("title", "")]
        if matching:
            event = matching[0]
            actual_date = event.get("event_date", "N/A")
            if actual_date == expected_date:
                log_test(f"✓ '{title}' has correct date: {expected_date}", "PASS")
            else:
                log_test(f"✗ '{title}' date mismatch: expected {expected_date}, got {actual_date}", "FAIL")
                all_passed = False
        else:
            log_test(f"✗ Event not found: '{title}'", "FAIL")
            all_passed = False

    return all_passed

def generate_report(test_results):
    """Generate final QA report"""
    print("\n" + "="*60)
    print("QA TEST REPORT: Buca di Beppo Import")
    print("="*60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client: {CLIENT_ID}")
    print(f"Import File: {JSON_FILE}")
    print("-"*60)

    passed = sum(1 for r in test_results.values() if r)
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    print("-"*60)
    print(f"Results: {passed}/{total} tests passed")
    print(f"Status: {'🎉 ALL TESTS PASSED' if passed == total else '⚠️ SOME TESTS FAILED'}")
    print("="*60)

def main():
    """Run all QA tests"""
    print("\n🔬 Starting QA Test Suite for Buca di Beppo Import\n")

    test_results = {}

    try:
        # Test 1: Clear existing
        test_1_clear_existing_events()
        test_results["Test 1: Clear Existing"] = True

        # Test 2: Bulk import
        created_count = test_2_bulk_import()
        test_results["Test 2: Bulk Import"] = created_count == 22

        # Test 3: Verify retrieval
        retrieval_ok, events = test_3_verify_retrieval(created_count)
        test_results["Test 3: Verify Retrieval"] = retrieval_ok

        # Test 4: Verify persistence
        persistence_ok = test_4_verify_persistence()
        test_results["Test 4: Verify Persistence"] = persistence_ok

        # Test 5: Verify details
        details_ok = test_5_verify_event_details(events)
        test_results["Test 5: Verify Event Details"] = details_ok

    except Exception as e:
        log_test(f"Test suite error: {str(e)}", "FAIL")
        test_results["Test Suite Execution"] = False

    # Generate final report
    generate_report(test_results)

if __name__ == "__main__":
    main()
