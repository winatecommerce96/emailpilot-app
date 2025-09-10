#!/usr/bin/env python3
"""Check all available clients in the system"""

import json
import os
from google.cloud import firestore

def check_klaviyo_clients():
    """Check Klaviyo clients from account_configs.json"""
    config_file = '/Users/Damon/klaviyo/klaviyo-audit-automation/account_configs.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            configs = json.load(f)
            print("Klaviyo Clients from account_configs.json:")
            for config in configs:
                if config.get('active'):
                    name = config['account_name']
                    # Generate client ID (lowercase, hyphenated)
                    client_id = name.lower().replace(' ', '-')
                    print(f"  - {client_id}: {name}")
    else:
        print("account_configs.json not found")

def check_firestore_clients():
    """Check clients in Firestore"""
    try:
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
        db = firestore.Client()
        clients_ref = db.collection('clients')
        clients = clients_ref.stream()
        
        print("\nFirestore clients:")
        for client in clients:
            data = client.to_dict()
            print(f"  - {client.id}: {data.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Could not check Firestore: {e}")

if __name__ == "__main__":
    check_klaviyo_clients()
    check_firestore_clients()