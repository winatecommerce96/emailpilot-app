#!/usr/bin/env python3
"""
Standardize Klaviyo API Key storage in Firestore.

This script:
1. Finds all Klaviyo API keys from various sources (Secret Manager, encrypted fields, etc.)
2. Stores them in a standard location in Firestore (klaviyo_api_key_secret field)
3. Ensures all clients with keys can be found by the Revenue API
"""

import os
import base64
from google.cloud import firestore
from google.cloud import secretmanager

# Set project
PROJECT_ID = "emailpilot-438321"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID

def access_secret(secret_id: str, version: str = "latest") -> str:
    """Access a secret from Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version}"
        resp = client.access_secret_version(request={"name": name})
        return resp.payload.data.decode("utf-8")
    except Exception as e:
        print(f"  ❌ Could not access secret {secret_id}: {e}")
        return None

def resolve_klaviyo_key(client_data: dict, client_slug: str) -> tuple[str, str]:
    """
    Resolve Klaviyo API key from various sources.
    Returns (api_key, source_description)
    """
    # 1. Check if already in standard location
    secret_ref = client_data.get("klaviyo_api_key_secret")
    if secret_ref:
        # Try as Secret Manager reference
        if secret_ref.startswith("klaviyo-api-"):
            api_key = access_secret(secret_ref)
            if api_key:
                return api_key, f"Secret Manager: {secret_ref}"
        
        # Try as base64 encoded
        try:
            dec = base64.b64decode(secret_ref).decode("utf-8", errors="strict").strip()
            if dec and all(32 <= ord(c) <= 126 for c in dec) and len(dec) >= 16:
                return dec, "Base64 encoded in klaviyo_api_key_secret"
        except:
            pass
    
    # 2. Check encrypted field
    encrypted = client_data.get("api_key_encrypted")
    if encrypted:
        try:
            dec = base64.b64decode(encrypted).decode("utf-8", errors="strict").strip()
            if dec and all(32 <= ord(c) <= 126 for c in dec) and len(dec) >= 16:
                return dec, "Base64 encoded in api_key_encrypted"
        except:
            pass
    
    # 3. Check raw key field
    raw = client_data.get("klaviyo_api_key")
    if raw and isinstance(raw, str):
        return raw.strip(), "Raw key in klaviyo_api_key field"
    
    # 4. Try Secret Manager by slug convention
    if client_slug:
        secret_name = f"klaviyo-api-{client_slug}"
        api_key = access_secret(secret_name)
        if api_key:
            return api_key, f"Secret Manager: {secret_name}"
    
    return None, None

def main():
    db = firestore.Client(project=PROJECT_ID)
    sm_client = secretmanager.SecretManagerServiceClient()
    
    print("🔧 Standardizing Klaviyo API Key Storage in Firestore")
    print("=" * 60)
    
    clients = list(db.collection("clients").stream())
    print(f"Found {len(clients)} clients to process\n")
    
    updated_count = 0
    found_keys = 0
    
    for client_doc in clients:
        client_id = client_doc.id
        client_data = client_doc.to_dict() or {}
        client_name = client_data.get("name", client_data.get("client_name", f"Client {client_id}"))
        client_slug = client_data.get("client_slug", "")
        
        print(f"📋 Processing: {client_name}")
        print(f"   ID: {client_id}")
        print(f"   Slug: {client_slug or '(none)'}")
        
        # Try to resolve the API key
        api_key, source = resolve_klaviyo_key(client_data, client_slug)
        
        if api_key:
            found_keys += 1
            print(f"   ✅ Found API key from: {source}")
            
            # Create or update secret in Secret Manager
            secret_name = f"klaviyo-api-{client_slug if client_slug else client_id}"
            secret_path = f"projects/{PROJECT_ID}/secrets/{secret_name}"
            
            try:
                # Try to create the secret
                parent = f"projects/{PROJECT_ID}"
                secret = {"replication": {"automatic": {}}}
                sm_client.create_secret(
                    request={"parent": parent, "secret_id": secret_name, "secret": secret}
                )
                print(f"   📝 Created new secret: {secret_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   📝 Secret already exists: {secret_name}")
                else:
                    print(f"   ⚠️ Could not create secret: {e}")
            
            # Add the secret version with the API key
            try:
                sm_client.add_secret_version(
                    request={
                        "parent": secret_path,
                        "payload": {"data": api_key.encode("utf-8")}
                    }
                )
                print(f"   📝 Updated secret version")
            except Exception as e:
                print(f"   ⚠️ Could not update secret version: {e}")
            
            # Update Firestore to use the standardized secret reference
            update_data = {
                "klaviyo_api_key_secret": secret_name,
                "has_klaviyo_key": True
            }
            
            # Ensure client_slug is set
            if not client_slug:
                # Use the document ID as slug if it looks like a slug
                if client_id and "-" in client_id and not client_id[0].isupper():
                    update_data["client_slug"] = client_id
                    print(f"   📝 Setting slug to document ID: {client_id}")
            
            # Remove old fields to avoid confusion
            if "api_key_encrypted" in client_data:
                update_data["api_key_encrypted"] = firestore.DELETE_FIELD
            if "klaviyo_api_key" in client_data:
                update_data["klaviyo_api_key"] = firestore.DELETE_FIELD
                
            client_doc.reference.update(update_data)
            updated_count += 1
            print(f"   ✅ Updated Firestore record")
            
        else:
            print(f"   🔑 No API key found")
            # Mark as not having a key
            client_doc.reference.update({"has_klaviyo_key": False})
        
        print()
    
    print("=" * 60)
    print(f"✅ Standardization Complete!")
    print(f"   - Processed: {len(clients)} clients")
    print(f"   - Found API keys: {found_keys}")
    print(f"   - Updated records: {updated_count}")

if __name__ == "__main__":
    main()