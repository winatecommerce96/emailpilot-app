#!/usr/bin/env python3
"""Debug the natural language API issue"""
import asyncio
from google.cloud import firestore
from app.deps import get_db
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver

async def test_client_fetch():
    """Test fetching client data"""
    db = firestore.Client()
    
    try:
        # Test synchronous get
        client_doc = db.collection('clients').document('christopher-bean-coffee').get()
        print(f"Client exists: {client_doc.exists}")
        
        if client_doc.exists:
            data = client_doc.to_dict()
            print(f"Client data keys: {list(data.keys())[:5]}")
            print(f"Placed order metric ID: {data.get('placed_order_metric_id', 'NOT FOUND')}")
        
        # Test key resolver
        resolver = ClientKeyResolver(db)
        api_key = await resolver.get_client_klaviyo_key('christopher-bean-coffee')
        if api_key:
            print(f"API Key found: {api_key[:6]}...{api_key[-4:]}")
        else:
            print("No API key found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_client_fetch())