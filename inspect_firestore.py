#!/usr/bin/env python3
"""
Inspect Firestore to dump a representative client document
"""

import os
import json
from google.cloud import firestore
from datetime import datetime

def get_db():
    """Get Firestore client"""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT") or "emailpilot-ai"
    return firestore.Client(project=project_id)

def inspect_clients_collection():
    """Inspect the clients collection and dump a representative document"""
    db = get_db()
    
    print("=" * 60)
    print("FIRESTORE INSPECTION - CLIENTS COLLECTION")
    print("=" * 60)
    
    try:
        # Get the clients collection
        clients_ref = db.collection('clients')
        
        # Get all documents (limit to first 5 for inspection)
        docs = clients_ref.limit(5).stream()
        
        client_docs = []
        for doc in docs:
            client_docs.append({
                'id': doc.id,
                'data': doc.to_dict()
            })
        
        if client_docs:
            print(f"\nFound {len(client_docs)} client document(s)")
            print("\n" + "-" * 40)
            print("REPRESENTATIVE CLIENT DOCUMENT:")
            print("-" * 40)
            
            # Display the first client document
            first_client = client_docs[0]
            print(f"\nDocument ID: {first_client['id']}")
            print(f"Document Data:")
            print(json.dumps(first_client['data'], indent=2, default=str))
            
            # Show field types
            print("\n" + "-" * 40)
            print("FIELD TYPES:")
            print("-" * 40)
            if first_client['data']:
                for key, value in first_client['data'].items():
                    value_type = type(value).__name__
                    if value_type == 'Timestamp':
                        value_type = 'Firestore Timestamp'
                    print(f"  {key}: {value_type}")
            
            # Show all client IDs
            if len(client_docs) > 1:
                print("\n" + "-" * 40)
                print("ALL CLIENT IDs FOUND:")
                print("-" * 40)
                for client in client_docs:
                    name = client['data'].get('name', 'No name') if client['data'] else 'No data'
                    print(f"  - {client['id']}: {name}")
        else:
            print("\nNo client documents found in Firestore.")
            print("\nTrying to create a sample client document...")
            
            # Create a sample client document
            sample_client = {
                'name': 'Sample Client Co.',
                'email': 'contact@sampleclient.com',
                'klaviyo_api_key': 'pk_sample_key_123',
                'status': 'active',
                'is_active': True,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'settings': {
                    'send_weekly_reports': True,
                    'send_monthly_reports': True,
                    'timezone': 'America/New_York'
                }
            }
            
            # Add the sample document
            doc_ref = clients_ref.add(sample_client)
            print(f"Created sample client with ID: {doc_ref[1].id}")
            
            # Read it back
            created_doc = doc_ref[1].get()
            print("\nCreated document:")
            print(json.dumps(created_doc.to_dict(), indent=2, default=str))
            
    except Exception as e:
        print(f"\nError accessing Firestore: {e}")
        print("\nPossible reasons:")
        print("1. Firestore not initialized")
        print("2. Missing authentication")
        print("3. Collection doesn't exist yet")
        
        # Try to check if we can at least connect
        try:
            collections = db.collections()
            collection_names = [c.id for c in collections]
            print(f"\nAvailable collections: {collection_names if collection_names else 'None'}")
        except Exception as e2:
            print(f"Cannot list collections: {e2}")

def inspect_goals_collection():
    """Also inspect goals collection structure"""
    db = get_db()
    
    print("\n" + "=" * 60)
    print("GOALS COLLECTION INSPECTION")
    print("=" * 60)
    
    try:
        goals_ref = db.collection('goals')
        goals = goals_ref.limit(3).stream()
        
        goal_docs = []
        for doc in goals:
            goal_docs.append({
                'id': doc.id,
                'data': doc.to_dict()
            })
        
        if goal_docs:
            print(f"\nFound {len(goal_docs)} goal document(s)")
            print("\nSample goal document:")
            print(json.dumps(goal_docs[0], indent=2, default=str))
        else:
            print("\nNo goal documents found.")
            
    except Exception as e:
        print(f"Error accessing goals collection: {e}")

if __name__ == "__main__":
    print(f"Using project: {os.getenv('GOOGLE_CLOUD_PROJECT') or 'emailpilot-ai'}")
    print(f"Firestore emulator: {os.getenv('FIRESTORE_EMULATOR_HOST') or 'Not set (using production)'}")
    
    inspect_clients_collection()
    inspect_goals_collection()
    
    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)