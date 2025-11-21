#!/usr/bin/env python3
"""
Emergency cleanup script for duplicate campaigns in Firestore.
Removes duplicate campaigns for Buca di Beppo December 2025.
"""
import os
from google.cloud import firestore
from collections import defaultdict

# Initialize Firestore
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
db = firestore.Client()

def cleanup_duplicate_campaigns(client_id: str, year: int, month: int, dry_run: bool = True):
    """
    Clean up duplicate campaigns for a specific client/month/year.

    Args:
        client_id: Client document ID (e.g., 'buca-di-beppo')
        year: Year (e.g., 2025)
        month: Month number (e.g., 12 for December)
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print(f"\n{'='*80}")
    print(f"Cleaning up campaigns for: {client_id} - {month}/{year}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete duplicates)'}")
    print(f"{'='*80}\n")

    # Query campaigns for this client/month/year
    campaigns_ref = (
        db.collection('clients')
        .document(client_id)
        .collection('campaigns')
        .where('year', '==', year)
        .where('month', '==', month)
    )

    campaigns = list(campaigns_ref.stream())
    total_count = len(campaigns)

    print(f"Found {total_count} total campaigns\n")

    if total_count == 0:
        print("No campaigns found to clean up.")
        return

    # Group campaigns by unique identifier (event_date + title)
    campaign_groups = defaultdict(list)

    for campaign_doc in campaigns:
        campaign_data = campaign_doc.to_dict()
        # Create a unique key based on date and title
        event_date = campaign_data.get('event_date', 'unknown')
        title = campaign_data.get('title', 'unknown')
        unique_key = f"{event_date}|{title}"

        campaign_groups[unique_key].append({
            'id': campaign_doc.id,
            'data': campaign_data,
            'created_at': campaign_data.get('created_at', 'unknown')
        })

    # Find duplicates
    duplicates_found = 0
    kept_count = 0
    deleted_count = 0

    for unique_key, campaigns_list in campaign_groups.items():
        if len(campaigns_list) > 1:
            duplicates_found += len(campaigns_list) - 1

            # Sort by created_at to keep the oldest one
            campaigns_list.sort(key=lambda x: x['created_at'] if x['created_at'] != 'unknown' else '')

            # Keep the first one, delete the rest
            keep = campaigns_list[0]
            to_delete = campaigns_list[1:]

            print(f"\nDuplicate group: {unique_key}")
            print(f"  KEEPING: {keep['id']} (created: {keep['created_at']})")
            kept_count += 1

            for dup in to_delete:
                print(f"  DELETING: {dup['id']} (created: {dup['created_at']})")

                if not dry_run:
                    # Actually delete the duplicate
                    db.collection('clients').document(client_id).collection('campaigns').document(dup['id']).delete()
                    print(f"    ✓ Deleted")

                deleted_count += 1
        else:
            # No duplicates, keep this one
            kept_count += 1

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total campaigns found: {total_count}")
    print(f"  Unique campaigns kept: {kept_count}")
    print(f"  Duplicates {'found' if dry_run else 'deleted'}: {deleted_count}")
    print(f"{'='*80}\n")

    if dry_run:
        print("⚠️  This was a DRY RUN. No changes were made.")
        print("   Run with dry_run=False to actually delete the duplicates.\n")
    else:
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    # First do a dry run to see what would be deleted
    print("\n🔍 DRY RUN: Showing what would be deleted...")
    cleanup_duplicate_campaigns(
        client_id='buca-di-beppo',
        year=2025,
        month=12,
        dry_run=True
    )

    # Uncomment the following to actually perform the cleanup:
    # print("\n🗑️  LIVE RUN: Actually deleting duplicates...")
    # cleanup_duplicate_campaigns(
    #     client_id='buca-di-beppo',
    #     year=2025,
    #     month=12,
    #     dry_run=False
    # )
