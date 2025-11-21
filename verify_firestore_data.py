#!/usr/bin/env python3
"""
Verify Firestore data integrity for strategy summaries and calendar events.
"""
import os
import sys
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client()

print("=" * 80)
print("FIRESTORE DATA INTEGRITY VERIFICATION")
print("=" * 80)

# 1. Verify strategy_summaries collection
print("\n1. Checking strategy_summaries collection...")
strategy_summaries = list(db.collection("strategy_summaries").stream())
print(f"   Found {len(strategy_summaries)} strategy summaries")

for doc in strategy_summaries:
    data = doc.to_dict()
    print(f"\n   Strategy ID: {doc.id}")
    print(f"   - client_id: {data.get('client_id')}")
    print(f"   - start_date: {data.get('start_date')}")
    print(f"   - end_date: {data.get('end_date')}")
    print(f"   - event_count: {data.get('event_count')}")
    print(f"   - key_insights: {len(data.get('key_insights', []))} items")
    print(f"   - generated_by: {data.get('generated_by')}")

    # Validate required fields
    required_fields = ['client_id', 'start_date', 'end_date', 'key_insights',
                      'targeting_approach', 'timing_strategy', 'content_strategy']
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"   ⚠️  MISSING FIELDS: {missing}")
    else:
        print(f"   ✅ All required fields present")

# 2. Verify calendar_events for test clients
print("\n2. Checking calendar_events for test clients...")
test_clients = ['test-client-strategy', 'test-client-no-strategy']

for client_id in test_clients:
    events = list(db.collection("calendar_events")
                   .where("client_id", "==", client_id)
                   .stream())
    print(f"\n   Client: {client_id}")
    print(f"   - Events found: {len(events)}")

    for event in events[:2]:  # Show first 2 events per client
        data = event.to_dict()
        print(f"     • {data.get('title')} ({data.get('event_date')})")

# 3. Verify composite indexes are working
print("\n3. Testing composite index queries...")

# Test query using client_id + start_date index
try:
    results = list(db.collection("strategy_summaries")
                    .where("client_id", "==", "test-client-strategy")
                    .where("start_date", ">=", "2026-02-01")
                    .limit(1)
                    .stream())
    print(f"   ✅ client_id + start_date index: WORKING ({len(results)} results)")
except Exception as e:
    print(f"   ❌ client_id + start_date index: FAILED - {e}")

# Test query using client_id + created_at index
try:
    results = list(db.collection("strategy_summaries")
                    .where("client_id", "==", "test-client-strategy")
                    .order_by("created_at", direction=firestore.Query.DESCENDING)
                    .limit(1)
                    .stream())
    print(f"   ✅ client_id + created_at index: WORKING ({len(results)} results)")
except Exception as e:
    print(f"   ❌ client_id + created_at index: FAILED - {e}")

print("\n" + "=" * 80)
print("DATA INTEGRITY VERIFICATION COMPLETE")
print("=" * 80)
