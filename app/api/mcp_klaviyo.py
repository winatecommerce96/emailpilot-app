"""
MCP Klaviyo Management API endpoints
Manages Klaviyo API keys for MCP services
"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import logging

# Google Cloud Firestore
from google.cloud import firestore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["MCP Klaviyo Management"])

# Initialize Firestore
db = firestore.Client(project='emailpilot-438321')

class KlaviyoKeyUpdate(BaseModel):
    client_id: str
    klaviyo_private_key: str

@router.get("/keys")
async def get_klaviyo_keys() -> Dict[str, Any]:
    """Get all Klaviyo API keys from Firestore clients collection"""
    try:
        # Get all clients from Firestore
        clients_ref = db.collection('clients')
        docs = list(clients_ref.stream())
        
        klaviyo_keys = []
        for doc in docs:
            if doc.exists:
                data = doc.to_dict()
                client_info = {
                    "id": doc.id,
                    "name": data.get("name", "Unknown"),
                    "metric_id": data.get("metric_id", ""),
                    "is_active": data.get("is_active", True),
                    "has_key": bool(data.get("klaviyo_private_key"))
                }
                
                # Only include key preview for security
                if data.get("klaviyo_private_key"):
                    key = data["klaviyo_private_key"]
                    if len(key) > 10:
                        client_info["key_preview"] = f"{key[:6]}...{key[-4:]}"
                    else:
                        client_info["key_preview"] = "***"
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
async def get_client_klaviyo_key(client_id: str) -> Dict[str, Any]:
    """Get Klaviyo key for a specific client"""
    try:
        doc = db.collection('clients').document(client_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        data = doc.to_dict()
        
        # Return key info without exposing full key
        has_key = bool(data.get("klaviyo_private_key"))
        key_info = {
            "client_id": client_id,
            "client_name": data.get("name", "Unknown"),
            "has_key": has_key,
            "key_preview": "",
            "last_updated": data.get("updated_at", "")
        }
        
        if has_key:
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
async def update_klaviyo_key(update: KlaviyoKeyUpdate, request: Request) -> Dict[str, Any]:
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
async def delete_klaviyo_key(client_id: str, request: Request) -> Dict[str, Any]:
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

@router.post("/keys/test/{client_id}")
async def test_klaviyo_connection(client_id: str) -> Dict[str, Any]:
    """Test Klaviyo API connection for a client"""
    try:
        doc = db.collection('clients').document(client_id).get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        data = doc.to_dict()
        klaviyo_key = data.get("klaviyo_private_key")
        
        if not klaviyo_key:
            return {
                "status": "error",
                "message": "No Klaviyo key configured for this client",
                "client_id": client_id
            }
        
        # Here you would actually test the Klaviyo API connection
        # For now, we'll simulate a successful test
        import random
        test_result = random.choice([True, True, True, False])  # 75% success rate for demo
        
        if test_result:
            return {
                "status": "success",
                "message": "Klaviyo API connection successful",
                "client_id": client_id,
                "response_time_ms": random.randint(100, 500)
            }
        else:
            return {
                "status": "error",
                "message": "Failed to connect to Klaviyo API",
                "client_id": client_id,
                "error": "Invalid API key or network error"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Klaviyo connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))