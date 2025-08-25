#!/usr/bin/env python3
"""
Check the exact Klaviyo API key field names in Firestore
"""
import os
from google.cloud import firestore

os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'

def check_klaviyo_fields():
    """Check all field names related to Klaviyo in client documents"""
    print("\n" + "="*70)
    print("📊 CHECKING KLAVIYO FIELDS IN FIRESTORE")
    print("="*70 + "\n")
    
    db = firestore.Client(project='emailpilot-438321')
    clients_ref = db.collection('clients')
    clients = list(clients_ref.stream())
    
    print(f"Found {len(clients)} clients\n")
    
    # Check each client's fields
    klaviyo_fields = set()
    
    for doc in clients:
        client_data = doc.to_dict()
        client_name = client_data.get('name', 'Unknown')
        
        print(f"Client: {doc.id} ({client_name})")
        print(f"  All fields: {list(client_data.keys())}")
        
        # Look for any field containing 'klaviyo' or 'api'
        for field_name, field_value in client_data.items():
            if 'klaviyo' in field_name.lower() or 'api' in field_name.lower():
                klaviyo_fields.add(field_name)
                # Show the field and whether it has a value
                if field_value:
                    if isinstance(field_value, str) and len(field_value) > 20:
                        print(f"  ✅ {field_name}: {field_value[:10]}...{field_value[-10:]}")
                    else:
                        print(f"  ✅ {field_name}: {field_value}")
                else:
                    print(f"  ❌ {field_name}: Empty/None")
        print()
    
    print("="*70)
    print("SUMMARY OF KLAVIYO-RELATED FIELDS:")
    print("="*70)
    for field in sorted(klaviyo_fields):
        print(f"  • {field}")
    
    # Check if it's "klaviyo api" with a space
    print("\n🔍 Checking for 'klaviyo api' (with space)...")
    for doc in clients[:3]:  # Check first 3 clients
        client_data = doc.to_dict()
        if 'klaviyo api' in client_data:
            print(f"  ✅ Found 'klaviyo api' field in {doc.id}")
            print(f"     Value: {client_data['klaviyo api'][:20]}..." if client_data['klaviyo api'] else "Empty")

if __name__ == "__main__":
    check_klaviyo_fields()