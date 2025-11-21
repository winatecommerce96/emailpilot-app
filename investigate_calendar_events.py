#!/usr/bin/env python3
"""
Investigation script to check the calendar_events collection (top-level).
"""
import os
from google.cloud import firestore
from collections import defaultdict

# Initialize Firestore
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
db = firestore.Client()

print("\n" + "="*80)
print("INVESTIGATING calendar_events COLLECTION (TOP-LEVEL)")
print("="*80 + "\n")

# Query calendar_events for Buca di Beppo
client_id = 'buca-di-beppo'
print(f"Checking calendar_events for client: {client_id}\n")

# Get ALL events for this client
events_ref = db.collection('calendar_events').where('client_id', '==', client_id)
all_events = list(events_ref.stream())

print(f"Total events found: {len(all_events)}\n")

if len(all_events) > 0:
    # Group by event_date to see distribution
    by_date = defaultdict(int)
    for event_doc in all_events:
        event_data = event_doc.to_dict()
        event_date = event_data.get('event_date', 'unknown')
        by_date[event_date] += 1

    print("Events by date (showing dates with most events):")
    sorted_dates = sorted(by_date.items(), key=lambda x: x[1], reverse=True)
    for date, count in sorted_dates[:20]:
        print(f"  {date}: {count} events")

    # Check for duplicates by title + date
    print("\n" + "-"*80)
    print("DUPLICATE ANALYSIS")
    print("-"*80 + "\n")

    duplicate_groups = defaultdict(list)
    for event_doc in all_events:
        event_data = event_doc.to_dict()
        event_date = event_data.get('event_date', 'unknown')
        title = event_data.get('title', 'unknown')
        unique_key = f"{event_date}|{title}"
        duplicate_groups[unique_key].append({
            'id': event_doc.id,
            'created_at': event_data.get('created_at', 'unknown')
        })

    # Find duplicates
    duplicates = {k: v for k, v in duplicate_groups.items() if len(v) > 1}

    if duplicates:
        print(f"Found {len(duplicates)} unique events with duplicates")
        print(f"Total duplicate documents: {sum(len(v) - 1 for v in duplicates.values())}\n")

        # Show top duplicates
        sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
        print("Top 10 duplicated events:")
        for key, docs in sorted_dups[:10]:
            date, title = key.split('|', 1)
            print(f"  {date} - {title[:50]}... : {len(docs)} copies")
    else:
        print("No duplicates found!")

    # Show sample event
    print("\n" + "-"*80)
    print("SAMPLE EVENT")
    print("-"*80 + "\n")

    sample = all_events[0]
    sample_data = sample.to_dict()
    print(f"Document ID: {sample.id}")
    for key, value in sorted(sample_data.items()):
        print(f"  {key}: {value}")

else:
    print("No events found in calendar_events collection for this client.")

print("\n" + "="*80)
print("Investigation complete!")
print("="*80 + "\n")
