#!/usr/bin/env python3
"""
Deep investigation of ALL campaigns in Firestore without filters.
"""
import os
from google.cloud import firestore
from collections import defaultdict
import json

# Initialize Firestore
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
db = firestore.Client()

print("\n" + "="*80)
print("DEEP INVESTIGATION - ALL CAMPAIGNS (NO FILTERS)")
print("="*80 + "\n")

# Check specifically for Buca di Beppo
client_id = 'buca-di-beppo'
print(f"Checking ALL campaigns for: {client_id}\n")

# Get ALL campaigns without any filters
campaigns_ref = db.collection('clients').document(client_id).collection('campaigns')
all_campaigns = list(campaigns_ref.stream())

print(f"Total campaigns found: {len(all_campaigns)}\n")

if len(all_campaigns) > 0:
    print("First 10 campaigns (showing all fields):\n")

    for i, campaign_doc in enumerate(all_campaigns[:10]):
        print(f"--- Campaign {i+1} ---")
        print(f"ID: {campaign_doc.id}")
        campaign_data = campaign_doc.to_dict()
        for key, value in sorted(campaign_data.items()):
            print(f"  {key}: {value}")
        print()

    # Analyze field patterns
    print("\n" + "-"*80)
    print("FIELD ANALYSIS")
    print("-"*80 + "\n")

    field_types = defaultdict(set)
    field_samples = defaultdict(list)

    for campaign_doc in all_campaigns:
        campaign_data = campaign_doc.to_dict()
        for key, value in campaign_data.items():
            field_types[key].add(type(value).__name__)
            if len(field_samples[key]) < 3:
                field_samples[key].append(str(value)[:50])

    for field_name in sorted(field_types.keys()):
        types_str = ", ".join(sorted(field_types[field_name]))
        samples_str = " | ".join(field_samples[field_name])
        print(f"{field_name}:")
        print(f"  Types: {types_str}")
        print(f"  Samples: {samples_str}")
        print()

    # Check for duplicates by different keys
    print("\n" + "-"*80)
    print("DUPLICATE ANALYSIS")
    print("-"*80 + "\n")

    # Try different grouping strategies
    grouping_strategies = [
        ('title', lambda c: c.get('title', 'unknown')),
        ('event_date', lambda c: c.get('event_date', 'unknown')),
        ('title+date', lambda c: f"{c.get('title', '')}|{c.get('event_date', '')}"),
    ]

    for strategy_name, key_func in grouping_strategies:
        groups = defaultdict(list)
        for campaign_doc in all_campaigns:
            campaign_data = campaign_doc.to_dict()
            key = key_func(campaign_data)
            groups[key].append(campaign_doc.id)

        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}

        if duplicate_groups:
            print(f"Strategy: {strategy_name}")
            print(f"  Duplicate groups: {len(duplicate_groups)}")
            print(f"  Total duplicates: {sum(len(v) - 1 for v in duplicate_groups.values())}")

            # Show top 3 groups
            sorted_groups = sorted(duplicate_groups.items(), key=lambda x: len(x[1]), reverse=True)
            for key, ids in sorted_groups[:3]:
                print(f"    {key}: {len(ids)} campaigns")
            print()
        else:
            print(f"Strategy: {strategy_name} - No duplicates found\n")

else:
    print("No campaigns found. Checking if the collection exists...")

    # Try to see if collection exists but is empty
    try:
        # Get client document
        client_doc = db.collection('clients').document(client_id).get()
        if client_doc.exists:
            print(f"✓ Client document exists: {client_doc.to_dict().get('name', 'Unknown')}")
            print("✗ But campaigns subcollection is empty")
        else:
            print(f"✗ Client document does not exist")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*80)
print("Investigation complete!")
print("="*80 + "\n")
