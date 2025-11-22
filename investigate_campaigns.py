#!/usr/bin/env python3
"""
Investigation script to find where the 521 duplicate campaigns are stored.
"""
import os
from google.cloud import firestore
from collections import defaultdict

# Initialize Firestore
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
db = firestore.Client()

print("\n" + "="*80)
print("INVESTIGATING CAMPAIGN STORAGE")
print("="*80 + "\n")

# 1. List all clients
print("Step 1: Listing all clients...")
clients_ref = db.collection('clients')
clients = list(clients_ref.stream())
print(f"Found {len(clients)} clients:\n")

for client_doc in clients:
    client_id = client_doc.id
    client_data = client_doc.to_dict()
    client_name = client_data.get('name', 'Unknown')
    print(f"  - {client_id} ({client_name})")

print("\n" + "-"*80 + "\n")

# 2. Check campaigns for each client
print("Step 2: Checking campaigns for each client...\n")

for client_doc in clients:
    client_id = client_doc.id
    client_data = client_doc.to_dict()
    client_name = client_data.get('name', 'Unknown')

    # Get all campaigns for this client
    campaigns_ref = db.collection('clients').document(client_id).collection('campaigns')
    campaigns = list(campaigns_ref.stream())

    if len(campaigns) > 0:
        print(f"Client: {client_name} ({client_id})")
        print(f"  Total campaigns: {len(campaigns)}")

        # Group by year/month
        by_month = defaultdict(int)
        for campaign_doc in campaigns:
            campaign_data = campaign_doc.to_dict()
            year = campaign_data.get('year', 'unknown')
            month = campaign_data.get('month', 'unknown')
            by_month[f"{year}-{month}"] += 1

        # Show breakdown
        for period, count in sorted(by_month.items(), reverse=True):
            print(f"    {period}: {count} campaigns")

        print()

print("\n" + "-"*80 + "\n")

# 3. Deep dive into Buca di Beppo December 2025
print("Step 3: Deep dive into Buca di Beppo December 2025...\n")

# Try different possible client IDs
possible_ids = ['buca-di-beppo', 'bucadibeppo', 'Buca di Beppo', 'buca_di_beppo']

for client_id in possible_ids:
    print(f"Trying client_id: {client_id}")
    try:
        client_ref = db.collection('clients').document(client_id)
        client_doc = client_ref.get()

        if client_doc.exists:
            print(f"  ✓ Client exists!")
            client_data = client_doc.to_dict()
            print(f"  Name: {client_data.get('name', 'Unknown')}")

            # Get December 2025 campaigns
            campaigns_ref = (
                db.collection('clients')
                .document(client_id)
                .collection('campaigns')
                .where('year', '==', 2025)
                .where('month', '==', 12)
            )

            dec_campaigns = list(campaigns_ref.stream())
            print(f"  December 2025 campaigns: {len(dec_campaigns)}")

            if len(dec_campaigns) > 0:
                # Show first few
                print(f"\n  First 5 campaigns:")
                for i, campaign_doc in enumerate(dec_campaigns[:5]):
                    campaign_data = campaign_doc.to_dict()
                    event_date = campaign_data.get('event_date', 'unknown')
                    title = campaign_data.get('title', 'unknown')
                    created_at = campaign_data.get('created_at', 'unknown')
                    print(f"    {i+1}. {event_date} - {title[:50]}... (created: {created_at})")

                # Check for duplicates
                print(f"\n  Checking for duplicates...")
                campaign_groups = defaultdict(list)

                for campaign_doc in dec_campaigns:
                    campaign_data = campaign_doc.to_dict()
                    event_date = campaign_data.get('event_date', 'unknown')
                    title = campaign_data.get('title', 'unknown')
                    unique_key = f"{event_date}|{title}"
                    campaign_groups[unique_key].append({
                        'id': campaign_doc.id,
                        'created_at': campaign_data.get('created_at', 'unknown')
                    })

                duplicate_count = 0
                for unique_key, campaigns_list in campaign_groups.items():
                    if len(campaigns_list) > 1:
                        duplicate_count += len(campaigns_list) - 1

                print(f"  Unique campaigns: {len(campaign_groups)}")
                print(f"  Duplicate campaigns: {duplicate_count}")

            print()
        else:
            print(f"  ✗ Client does not exist")
    except Exception as e:
        print(f"  Error: {e}")

    print()

print("="*80)
print("Investigation complete!")
print("="*80 + "\n")
