"""
MCP Klaviyo Management API endpoints
Manages Klaviyo API keys for MCP services
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import logging

# Google Cloud Firestore
from google.cloud import firestore
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver
from app.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MCP Klaviyo Management"])

class KlaviyoKeyUpdate(BaseModel):
    client_id: str
    klaviyo_private_key: str

@router.get("/keys")
async def get_klaviyo_keys(
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get all Klaviyo API keys from Firestore clients collection"""
    try:
        # Get all clients from Firestore
        clients_ref = db.collection('clients')
        docs = list(clients_ref.stream())
        
        klaviyo_keys = []
        for doc in docs:
            if doc.exists:
                data = doc.to_dict()
                
                # Check for keys in Secret Manager or legacy fields
                # Check both new and old field names for backward compatibility
                has_secret_key = bool(data.get("klaviyo_api_key_secret") or data.get("klaviyo_secret_name"))
                has_legacy_key = bool(data.get("klaviyo_private_key") or data.get("klaviyo_api_key"))
                has_any_key = has_secret_key or has_legacy_key
                
                client_info = {
                    "id": doc.id,
                    "name": data.get("name", "Unknown"),
                    "metric_id": data.get("metric_id", ""),
                    "placed_order_metric_id": data.get("placed_order_metric_id", ""),
                    "is_active": data.get("is_active", True),
                    "has_key": has_any_key,
                    "uses_secret_manager": has_secret_key
                }
                
                # Try to get key preview
                if has_secret_key or has_legacy_key:
                    try:
                        # Try to get key from Secret Manager or legacy for preview
                        actual_key = await key_resolver.get_client_klaviyo_key(doc.id)
                        if actual_key and len(actual_key) > 10:
                            client_info["key_preview"] = f"{actual_key[:6]}...{actual_key[-4:]}"
                            client_info["has_key"] = True  # Confirm key exists
                        else:
                            client_info["key_preview"] = "***" if actual_key else "[No key]"
                    except Exception as e:
                        logger.debug(f"Could not get key preview for {doc.id}: {e}")
                        client_info["key_preview"] = "[Check Secret Manager]"
                else:
                    client_info["key_preview"] = ""
                
                klaviyo_keys.append(client_info)
        
        # Sort by name
        klaviyo_keys.sort(key=lambda x: x["name"])
        
        return {
            "status": "success",
            "total_clients": len(klaviyo_keys),
            "clients_with_keys": sum(1 for k in klaviyo_keys if k["has_key"]),
            "clients": klaviyo_keys
        }
        
    except Exception as e:
        logger.error(f"Error fetching Klaviyo keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keys/{client_id}")
async def get_client_klaviyo_key(
    client_id: str,
    db: firestore.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Get Klaviyo key for a specific client"""
    try:
        doc = db.collection('clients').document(client_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        data = doc.to_dict()
        
        # Check for key in both Secret Manager and legacy fields  
        has_secret_key = bool(data.get("klaviyo_api_key_secret") or data.get("klaviyo_secret_name"))
        has_legacy_key = bool(data.get("klaviyo_private_key") or data.get("klaviyo_api_key"))
        has_key = has_secret_key or has_legacy_key
        
        key_info = {
            "client_id": client_id,
            "client_name": data.get("name", "Unknown"),
            "has_key": has_key,
            "uses_secret_manager": has_secret_key,
            "key_preview": "",
            "last_updated": data.get("updated_at", "")
        }
        
        # Get preview from Secret Manager or legacy field
        if has_key:
            try:
                # Try to get key using resolver for preview
                actual_key = await key_resolver.get_client_klaviyo_key(client_id)
                if actual_key and len(actual_key) > 10:
                    key_info["key_preview"] = f"{actual_key[:6]}...{actual_key[-4:]}"
                else:
                    key_info["key_preview"] = "***"
            except Exception:
                key_info["key_preview"] = "[Secret Manager]"
        elif has_legacy_key:
            key = data["klaviyo_private_key"]
            if len(key) > 10:
                key_info["key_preview"] = f"{key[:6]}...{key[-4:]}"
            else:
                key_info["key_preview"] = "***"
        
        return key_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client Klaviyo key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys")
async def update_klaviyo_key(
    update: KlaviyoKeyUpdate, 
    request: Request,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Update or set a Klaviyo API key for a client"""
    try:
        # Update the client document
        client_ref = db.collection('clients').document(update.client_id)
        doc = client_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Update with new key
        client_ref.update({
            "klaviyo_private_key": update.klaviyo_private_key,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        return {
            "status": "success",
            "message": f"Klaviyo key updated for client {update.client_id}",
            "client_id": update.client_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Klaviyo key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/keys/{client_id}")
async def delete_klaviyo_key(
    client_id: str, 
    request: Request,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Remove a Klaviyo API key from a client"""
    try:
        client_ref = db.collection('clients').document(client_id)
        doc = client_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Remove the key
        client_ref.update({
            "klaviyo_private_key": firestore.DELETE_FIELD,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        return {
            "status": "success",
            "message": f"Klaviyo key removed for client {client_id}",
            "client_id": client_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting Klaviyo key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import httpx

@router.get("/keys/{client_id}/actual")
async def get_client_actual_klaviyo_key(
    client_id: str,
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get the actual Klaviyo API key for MCP usage (from Secret Manager)"""
    try:
        # Get the actual key using resolver (handles all fallback logic)
        klaviyo_key = await key_resolver.get_client_klaviyo_key(client_id)
        
        if not klaviyo_key:
            raise HTTPException(status_code=404, detail="No API key found for this client")
        
        # Get client info
        doc = db.collection('clients').document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
            
        data = doc.to_dict()
        client_name = data.get("name", "Unknown")
        
        # Determine source
        has_secret = bool(data.get("klaviyo_api_key_secret") or data.get("klaviyo_secret_name"))
        
        return {
            "client_id": client_id,
            "client_name": client_name,
            "api_key": klaviyo_key,
            "source": "secret_manager" if has_secret else "legacy"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting actual Klaviyo key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/test/{client_id}")
async def test_klaviyo_connection(
    client_id: str,
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Test Klaviyo API connection for a client"""
    try:
        # Get client Klaviyo key using resolver
        klaviyo_key = await key_resolver.get_client_klaviyo_key(client_id)
        
        if not klaviyo_key:
            return {
                "status": "error",
                "message": "No Klaviyo key configured for this client",
                "client_id": client_id
            }
        
        # Test the Klaviyo API connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://a.klaviyo.com/api/v2/campaigns",
                    params={"api_key": klaviyo_key}
                )
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                
            return {
                "status": "success",
                "message": "Klaviyo API connection successful",
                "client_id": client_id,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "message": f"Failed to connect to Klaviyo API: {e.response.status_code} {e.response.reason_phrase}",
                "client_id": client_id,
                "error": str(e)
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "message": "Failed to connect to Klaviyo API",
                "client_id": client_id,
                "error": str(e)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Klaviyo connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))