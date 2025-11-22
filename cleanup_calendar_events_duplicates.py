#!/usr/bin/env python3
"""
Emergency cleanup script for duplicate calendar events in Firestore.
Removes duplicate events from the calendar_events collection.
"""
import argparse
import os
from collections import defaultdict

from google.cloud import firestore

# Initialize Firestore
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
db = firestore.Client()

def cleanup_duplicate_events(client_id: str, dry_run: bool = True):
    """
    Clean up duplicate events for a specific client in calendar_events collection.

    Args:
        client_id: Client ID (e.g., 'buca-di-beppo')
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print(f"\n{'='*80}")
    print(f"Cleaning up calendar_events for: {client_id}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete duplicates)'}")
    print(f"{'='*80}\n")

    # Query all events for this client
    events_ref = db.collection('calendar_events').where('client_id', '==', client_id)
    events = list(events_ref.stream())
    total_count = len(events)

    print(f"Found {total_count} total events\n")

    if total_count == 0:
        print("No events found to clean up.")
        return

    # Group events by unique identifier (event_date + title)
    event_groups = defaultdict(list)

    for event_doc in events:
        event_data = event_doc.to_dict()
        # Create a unique key based on date and title
        event_date = event_data.get('event_date', 'unknown')
        title = event_data.get('title', 'unknown')
        unique_key = f"{event_date}|{title}"

        event_groups[unique_key].append({
            'id': event_doc.id,
            'data': event_data,
            'created_at': event_data.get('created_at', 'unknown')
        })

    # Find duplicates
    duplicates_found = 0
    kept_count = 0
    deleted_count = 0

    for unique_key, events_list in event_groups.items():
        if len(events_list) > 1:
            duplicates_found += len(events_list) - 1

            # Sort by created_at to keep the oldest one
            events_list.sort(key=lambda x: x['created_at'] if x['created_at'] != 'unknown' else '')

            # Keep the first one, delete the rest
            keep = events_list[0]
            to_delete = events_list[1:]

            print(f"\nDuplicate group: {unique_key}")
            print(f"  KEEPING: {keep['id']} (created: {keep['created_at']})")
            kept_count += 1

            for dup in to_delete:
                print(f"  DELETING: {dup['id']} (created: {dup['created_at']})")

                if not dry_run:
                    # Actually delete the duplicate
                    db.collection('calendar_events').document(dup['id']).delete()
                    print(f"    ✓ Deleted")

                deleted_count += 1
        else:
            # No duplicates, keep this one
            kept_count += 1

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total events found: {total_count}")
    print(f"  Unique events kept: {kept_count}")
    print(f"  Duplicates {'found' if dry_run else 'deleted'}: {deleted_count}")
    print(f"{'='*80}\n")

    if dry_run:
        print("⚠️  This was a DRY RUN. No changes were made.")
        print("   Run with dry_run=False to actually delete the duplicates.\n")
    else:
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Remove duplicate calendar events for a client."
    )
    parser.add_argument(
        "--client-id",
        required=True,
        help="Client ID (e.g., 'buca-di-beppo')",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Set to run in live mode (dry_run=False) and actually delete duplicates.",
    )

    args = parser.parse_args()

    # dry_run defaults to True unless --live is provided
    cleanup_duplicate_events(
        client_id=args.client_id,
        dry_run=not args.live,
    )
