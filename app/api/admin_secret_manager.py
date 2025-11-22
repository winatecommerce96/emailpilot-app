"""
Admin Secret Manager API for managing client Klaviyo keys via Secret Manager
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
from app.services.client_key_resolver import get_client_key_resolver
from app.services.secret_manager import SecretManagerService
from app.deps import get_secret_manager_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/secret-manager", tags=["Admin Secret Manager"])

# Pydantic models
class ClientKeyMapping(BaseModel):
    client_id: str
    client_name: str
    klaviyo_secret_name: Optional[str] = None
    has_legacy_key: bool = False
    suggested_secret_name: Optional[str] = None
    key_status: str  # "configured", "missing", "legacy_only"

class SetClientKeyRequest(BaseModel):
    client_id: str = Field(..., description="Client ID")
    api_key: str = Field(..., description="Klaviyo API key")

class MigrateClientRequest(BaseModel):
    client_id: str = Field(..., description="Client ID to migrate")

class BulkMigrateRequest(BaseModel):
    client_ids: List[str] = Field(..., description="List of client IDs to migrate")

class SecretManagerStatus(BaseModel):
    available: bool
    project_id: Optional[str] = None
    total_secrets: int = 0
    klaviyo_secrets: int = 0
    error: Optional[str] = None

# Get dependencies
key_resolver = get_client_key_resolver()

@router.get("/status", response_model=SecretManagerStatus)
async def get_secret_manager_status(secret_manager: SecretManagerService = Depends(get_secret_manager_service)):
    """Get Secret Manager status and basic statistics"""
    try:
        # Get basic info
        project_id = secret_manager.project_id
        
        # List secrets
        try:
            all_secrets = secret_manager.list_secrets()
            klaviyo_secrets = [s for s in all_secrets if s.startswith("klaviyo-api-")]
            
            return SecretManagerStatus(
                available=True,
                project_id=project_id,
                total_secrets=len(all_secrets),
                klaviyo_secrets=len(klaviyo_secrets)
            )
        except Exception as e:
            return SecretManagerStatus(
                available=True,
                project_id=project_id,
                total_secrets=0,
                klaviyo_secrets=0,
                error=f"Failed to list secrets: {e}"
            )
            
    except Exception as e:
        return SecretManagerStatus(
            available=False,
            error=str(e)
        )

@router.get("/client-mappings", response_model=List[ClientKeyMapping])
async def get_client_key_mappings():
    """Get all client key mappings and their status"""
    try:
        mappings = key_resolver.list_client_secret_mappings()
        results = []
        
        for client_id, mapping in mappings.items():
            # Determine key status
            if mapping.get('klaviyo_secret_name'):
                key_status = "configured"
            elif mapping.get('has_legacy_key'):
                key_status = "legacy_only"
            else:
                key_status = "missing"
            
            results.append(ClientKeyMapping(
                client_id=client_id,
                client_name=mapping.get('name', ''),
                klaviyo_secret_name=mapping.get('klaviyo_secret_name'),
                has_legacy_key=mapping.get('has_legacy_key', False),
                suggested_secret_name=mapping.get('suggested_secret_name'),
                key_status=key_status
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to get client key mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get client key mappings: {e}")

@router.get("/client/{client_id}/key-status")
async def get_client_key_status(client_id: str):
    """Get detailed key status for a specific client"""
    try:
        mappings = key_resolver.list_client_secret_mappings()
        client_mapping = mappings.get(client_id)
        
        if not client_mapping:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Test if key is actually accessible
        try:
            actual_key = await key_resolver.get_client_klaviyo_key(client_id)
            key_accessible = bool(actual_key)
        except Exception as e:
            key_accessible = False
        
        return {
            "client_id": client_id,
            "client_name": client_mapping.get('name', ''),
            "klaviyo_secret_name": client_mapping.get('klaviyo_secret_name'),
            "has_legacy_key": client_mapping.get('has_legacy_key', False),
            "suggested_secret_name": client_mapping.get('suggested_secret_name'),
            "key_accessible": key_accessible,
            "key_status": "configured" if key_accessible else ("legacy_only" if client_mapping.get('has_legacy_key') else "missing")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get client key status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get client key status: {e}")

@router.post("/client/set-key")
async def set_client_klaviyo_key(request: SetClientKeyRequest):
    """Set Klaviyo API key for a client in Secret Manager"""
    try:
        success = await key_resolver.set_client_klaviyo_key(request.client_id, request.api_key)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully stored Klaviyo key for client {request.client_id}",
                "client_id": request.client_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store Klaviyo key")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set client Klaviyo key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set client Klaviyo key: {e}")

@router.post("/client/{client_id}/migrate")
async def migrate_client_to_secret_manager(client_id: str):
    """Migrate a client's legacy key to Secret Manager"""
    try:
        # Get current key (this will trigger migration if legacy key exists)
        key = await key_resolver.get_client_klaviyo_key(client_id)
        
        if key:
            return {
                "success": True,
                "message": f"Successfully migrated client {client_id} to Secret Manager",
                "client_id": client_id
            }
        else:
            raise HTTPException(status_code=400, detail="No key found to migrate")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to migrate client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to migrate client: {e}")

@router.post("/bulk-migrate")
async def bulk_migrate_clients(request: BulkMigrateRequest):
    """Migrate multiple clients to Secret Manager"""
    try:
        results = []
        
        for client_id in request.client_ids:
            try:
                # Get current key (this will trigger migration if legacy key exists)
                key = await key_resolver.get_client_klaviyo_key(client_id)
                
                if key:
                    results.append({
                        "client_id": client_id,
                        "success": True,
                        "message": "Migrated successfully"
                    })
                else:
                    results.append({
                        "client_id": client_id,
                        "success": False,
                        "message": "No key found to migrate"
                    })
                    
            except Exception as e:
                logger.error(f"Failed to migrate client {client_id}: {e}")
                results.append({
                    "client_id": client_id,
                    "success": False,
                    "message": f"Migration failed: {e}"
                })
        
        successful_migrations = sum(1 for r in results if r["success"])
        
        return {
            "total_clients": len(request.client_ids),
            "successful_migrations": successful_migrations,
            "failed_migrations": len(request.client_ids) - successful_migrations,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed bulk migration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed bulk migration: {e}")

@router.delete("/client/{client_id}/secret")
async def delete_client_secret(client_id: str, secret_manager: SecretManagerService = Depends(get_secret_manager_service)):
    """Delete a client's secret from Secret Manager (admin only)"""
    try:
        # Get client's secret name
        mappings = key_resolver.list_client_secret_mappings()
        client_mapping = mappings.get(client_id)
        
        if not client_mapping or not client_mapping.get('klaviyo_secret_name'):
            raise HTTPException(status_code=404, detail="No secret found for client")
        
        secret_name = client_mapping['klaviyo_secret_name']
        
        # Delete the secret from Secret Manager
        secret_manager.delete_secret(secret_name)
        
        # Update the client document in Firestore
        from google.cloud import firestore
        db = firestore.Client(project=secret_manager.project_id)
        client_ref = db.collection('clients').document(client_id)
        client_ref.update({
            'klaviyo_secret_name': firestore.DELETE_FIELD,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return {
            "success": True,
            "message": f"Deleted secret {secret_name} and removed reference for client {client_id}",
            "secret_name": secret_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete client secret: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete client secret: {e}")

@router.get("/secrets/klaviyo")
async def list_klaviyo_secrets(secret_manager: SecretManagerService = Depends(get_secret_manager_service)):
    """List all Klaviyo secrets in Secret Manager"""
    try:
        all_secrets = secret_manager.list_secrets()
        klaviyo_secrets = [s for s in all_secrets if s.startswith("klaviyo-api-")]
        
        return {
            "total_secrets": len(all_secrets),
            "klaviyo_secrets": klaviyo_secrets,
            "count": len(klaviyo_secrets)
        }
        
    except Exception as e:
        logger.error(f"Failed to list Klaviyo secrets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Klaviyo secrets: {e}")