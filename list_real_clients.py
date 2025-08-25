#!/usr/bin/env python3
"""
List REAL clients from Firestore
No mock data - actual production clients
"""
import os
from google.cloud import firestore

# Set project
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'

def list_real_clients():
    """List all real clients from Firestore"""
    print("\n" + "="*70)
    print("📊 REAL CLIENTS IN FIRESTORE")
    print("="*70 + "\n")
    
    # Connect to Firestore
    db = firestore.Client(project='emailpilot-438321')
    
    # Get all clients
    clients_ref = db.collection('clients')
    clients = clients_ref.stream()
    
    client_list = []
    for doc in clients:
        client_data = doc.to_dict()
        client_list.append({
            'id': doc.id,
            'name': client_data.get('name', 'Unknown'),
            'klaviyo_account_id': client_data.get('klaviyo_account_id'),
            'klaviyo_api_key': 'Present' if client_data.get('klaviyo_api_key') else 'Missing',
            'industry': client_data.get('industry', 'Not specified'),
            'status': client_data.get('status', 'active')
        })
    
    if client_list:
        print(f"Found {len(client_list)} real clients:\n")
        for i, client in enumerate(client_list, 1):
            print(f"{i}. Client ID: {client['id']}")
            print(f"   Name: {client['name']}")
            print(f"   Klaviyo Account: {client['klaviyo_account_id'] or 'Not linked'}")
            print(f"   API Key: {client['klaviyo_api_key']}")
            print(f"   Industry: {client['industry']}")
            print(f"   Status: {client['status']}")
            print()
        
        # Return first active client with Klaviyo connection
        for client in client_list:
            if client['klaviyo_api_key'] == 'Present' and client['status'] == 'active':
                print(f"✅ Recommended client for calendar: {client['id']} ({client['name']})")
                return client['id']
    else:
        print("❌ No clients found in Firestore")
        print("\nMake sure you're connected to the right project:")
        print("  export GOOGLE_CLOUD_PROJECT=emailpilot-438321")
    
    return None

if __name__ == "__main__":
    recommended_client = list_real_clients()
    
    if recommended_client:
        print("\n" + "="*70)
        print("🚀 NEXT STEP")
        print("="*70)
        print(f"\nUse this client ID in your calendar creation:")
        print(f"  python create_calendar_now.py --client {recommended_client}")
        print(f"\nOr in LangGraph Studio, use:")
        print(f'  {{"client_id": "{recommended_client}", "month": "2025-03"}}')