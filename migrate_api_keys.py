#!/usr/bin/env python3
"""
Migrate API keys from account_configs.json to Firestore
"""

import os
import json
from google.cloud import firestore

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/emailpilot-firestore-key.json'
db = firestore.Client(project='emailpilot-438321')

def migrate_api_keys():
    """Migrate API keys from account_configs.json to Firestore clients"""
    
    # Read account configs
    config_file = "/Users/Damon/klaviyo/klaviyo-audit-automation/account_configs.json"
    with open(config_file, 'r') as f:
        configs = json.load(f)
    
    print(f"Found {len(configs)} account configurations")
    
    # Get existing clients from Firestore
    clients = list(db.collection('clients').stream())
    
    updated_count = 0
    
    for client_doc in clients:
        client_data = client_doc.to_dict()
        client_name = client_data.get('name', '')
        
        # Skip test/placeholder clients
        if client_data.get('placeholder', False) or 'test' in client_name.lower():
            continue
        
        # Find matching config
        matching_config = None
        for config in configs:
            if config['account_name'].lower() == client_name.lower():
                matching_config = config
                break
        
        if matching_config:
            print(f"Updating {client_name}...")
            
            # Update client with API key and metric info
            update_data = {
                'klaviyo_private_key': matching_config['api_key'],
                'placed_order_metric_id': matching_config['metric_id'],
                'is_active': matching_config.get('active', True),
                'description': matching_config.get('description', ''),
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            client_doc.reference.update(update_data)
            updated_count += 1
            print(f"  ✅ Updated with API key and metric ID {matching_config['metric_id']}")
        else:
            print(f"  ❌ No matching config for {client_name}")
    
    print(f"\n✅ Migration complete! Updated {updated_count} clients")

if __name__ == "__main__":
    migrate_api_keys()