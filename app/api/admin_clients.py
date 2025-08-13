"""
Admin Client Management API
Comprehensive client data management for admin panel
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

# Firestore
from google.cloud import firestore
from app.services.firestore_client import get_firestore_client
from app.core.config import settings

# Import Secret Manager service and KlaviyoClient
try:
    from app.services.secret_manager import SecretManagerService, get_secret_manager
    from app.services.klaviyo_client import KlaviyoClient
    
    def get_secret(name: str) -> Optional[str]:
        try:
            service = SecretManagerService()
            return service.get_secret(name)
        except Exception:
            return None
except Exception:
    get_secret = None
    get_secret_manager = None
    KlaviyoClient = None


logger = logging.getLogger(__name__)

# All routes live under /api/admin/…
router = APIRouter(prefix="/api/admin", tags=["Admin Client Management"])


# ----------------------------
# Dependencies / helpers
# ----------------------------
def get_db():
    return get_firestore_client()


def get_current_user_from_session(request: Request):
    """Basic session check with dev bypass."""
    if os.getenv("ENVIRONMENT", "development") == "development":
        user = request.session.get("user")
        if not user:
            user = {"email": "admin@emailpilot.ai", "name": "Dev Admin"}
            request.session["user"] = user
        return user

    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class ClientCreate(BaseModel):
    name: str
    metric_id: Optional[str] = ""
    klaviyo_api_key: Optional[str] = ""
    description: Optional[str] = ""
    is_active: Optional[bool] = True
    contact_email: Optional[str] = ""
    contact_name: Optional[str] = ""
    website: Optional[str] = ""
    # Brand Manager
    client_voice: Optional[str] = ""
    client_background: Optional[str] = ""
    # PM
    asana_project_link: Optional[str] = ""
    # Affinity
    affinity_segment_1_name: Optional[str] = ""
    affinity_segment_1_definition: Optional[str] = ""
    affinity_segment_2_name: Optional[str] = ""
    affinity_segment_2_definition: Optional[str] = ""
    affinity_segment_3_name: Optional[str] = ""
    affinity_segment_3_definition: Optional[str] = ""
    # Growth
    key_growth_objective: Optional[str] = "subscriptions"


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    metric_id: Optional[str] = None
    klaviyo_api_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    website: Optional[str] = None
    # Brand Manager
    client_voice: Optional[str] = None
    client_background: Optional[str] = None
    # PM
    asana_project_link: Optional[str] = None
    # Affinity
    affinity_segment_1_name: Optional[str] = None
    affinity_segment_1_definition: Optional[str] = None
    affinity_segment_2_name: Optional[str] = None
    affinity_segment_2_definition: Optional[str] = None
    affinity_segment_3_name: Optional[str] = None
    affinity_segment_3_definition: Optional[str] = None
    # Growth
    key_growth_objective: Optional[str] = None




def _resolve_client_key(db, client_id: str) -> Optional[str]:
    """
    Resolve a per-client Klaviyo API key via:
      1) Client's klaviyo_secret_name in Secret Manager
      2) Legacy fallback to direct fields (temporary)
    """
    if not client_id:
        return None
    
    try:
        snap = db.collection("clients").document(client_id).get()
        if not snap.exists:
            logger.warning(f"Client document not found: {client_id}")
            return None
        
        data = snap.to_dict() or {}
        
        # First try secret manager with client's specified secret name
        if get_secret_manager:
            secret_name = data.get("klaviyo_secret_name") or f"klaviyo-api-key-{client_id}"
            try:
                secret_manager = get_secret_manager()
                key = secret_manager.get_secret(secret_name)
                if key:
                    return key.strip()
            except Exception as e:
                logger.debug(f"Secret Manager lookup failed for {secret_name}: {e}")
        
        # Temporary legacy fallback to direct fields
        legacy_key = data.get("klaviyo_api_key") or data.get("klaviyo_private_key")
        if legacy_key:
            logger.warning(f"Client {client_id} using legacy plaintext key - migrate to Secret Manager")
            return legacy_key.strip()
            
    except Exception as e:
        logger.error(f"Key resolution failed for client {client_id}: {e}")
    
    return None


async def _store_client_klaviyo_key(db, client_id: str, api_key: str) -> None:
    """
    Store a client's Klaviyo API key in Secret Manager and update the client document
    with the secret reference.
    """
    if not api_key or not get_secret_manager:
        return
    
    try:
        # Store in Secret Manager
        secret_name = f"klaviyo-api-key-{client_id}"
        secret_manager = get_secret_manager()
        secret_manager.create_secret(secret_name, api_key, {
            "client_id": client_id,
            "type": "klaviyo_api_key"
        })
        
        # Update client document with secret reference
        client_ref = db.collection("clients").document(client_id)
        client_ref.update({
            "klaviyo_secret_name": secret_name,
            # Remove any legacy plaintext fields
            "klaviyo_api_key": firestore.DELETE_FIELD,
            "klaviyo_private_key": firestore.DELETE_FIELD
        })
        
        logger.info(f"Stored Klaviyo API key for client {client_id} in Secret Manager")
        
    except Exception as e:
        logger.error(f"Failed to store Klaviyo key for client {client_id}: {e}")
        raise


# ----------------------------
# Admin/Utility endpoints
# ----------------------------
@router.get("/environment")
async def get_environment_info():
    try:
        demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "false").lower() == "true"
        build_version = os.getenv("BUILD_VERSION", "dev")
        commit_sha = os.getenv("COMMIT_SHA", "unknown")
        firestore_project = os.getenv("GOOGLE_CLOUD_PROJECT", getattr(settings, 'google_cloud_project', 'emailpilot-438321'))
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")

        return {
            "demoMode": demo_mode,
            "environment": environment,
            "debug": debug,
            "apiBase": api_base,
            "firestoreProject": firestore_project,
            "buildVersion": build_version,
            "commitSha": commit_sha,
            "secretManagerEnabled": getattr(settings, "secret_manager_enabled", True),
            "features": {
                "firestore": True,
                "secretManager": getattr(settings, "secret_manager_enabled", True),
                "calendar": True,
                "performance": True,
                "goals": True,
                "reports": True,
            },
        }
    except Exception as e:
        logger.error("Error getting environment info: %s", e)
        return {
            "demoMode": True,
            "environment": "development",
            "debug": False,
            "apiBase": "http://localhost:8000",
            "firestoreProject": "demo-project",
            "buildVersion": "dev",
            "commitSha": "unknown",
            "error": str(e),
        }


@router.get("/clients")
async def get_all_clients(request: Request) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        docs = list(db.collection("clients").stream())
        clients: List[Dict[str, Any]] = []

        for d in docs:
            if not d.exists:
                continue
            data = d.to_dict() or {}
            resolved_key = _resolve_client_key(db, d.id)
            info: Dict[str, Any] = {
                "id": d.id,
                "name": data.get("name", "Unknown"),
                "metric_id": data.get("metric_id", ""),
                "description": data.get("description", ""),
                "is_active": data.get("is_active", True),
                "has_klaviyo_key": bool(resolved_key),
                "contact_email": data.get("contact_email", ""),
                "contact_name": data.get("contact_name", ""),
                "website": data.get("website", ""),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "client_voice": data.get("client_voice", ""),
                "client_background": data.get("client_background", ""),
                "asana_project_link": data.get("asana_project_link", ""),
                "affinity_segment_1_name": data.get("affinity_segment_1_name", ""),
                "affinity_segment_1_definition": data.get("affinity_segment_1_definition", ""),
                "affinity_segment_2_name": data.get("affinity_segment_2_name", ""),
                "affinity_segment_2_definition": data.get("affinity_segment_2_definition", ""),
                "affinity_segment_3_name": data.get("affinity_segment_3_name", ""),
                "affinity_segment_3_definition": data.get("affinity_segment_3_definition", ""),
                "key_growth_objective": data.get("key_growth_objective", "subscriptions"),
                "klaviyo_key_preview": "",
            }
            if resolved_key:
                info["klaviyo_key_preview"] = f"{resolved_key[:6]}...{resolved_key[-4:]}" if len(resolved_key) > 10 else "***"

            # recent perf (best-effort)
            try:
                perf = (
                    db.collection("performance_history")
                    .where("client_id", "==", d.id)
                    .limit(1)
                )
                perf_docs = list(perf.stream())
                if perf_docs:
                    p = perf_docs[0].to_dict() or {}
                    info["recent_revenue"] = p.get("total_revenue", 0)
                    info["recent_orders"] = p.get("placed_order", 0)
                else:
                    info["recent_revenue"] = 0
                    info["recent_orders"] = 0
            except Exception:
                info["recent_revenue"] = 0
                info["recent_orders"] = 0

            clients.append(info)

        clients.sort(key=lambda x: x["name"])
        return {
            "status": "success",
            "total_clients": len(clients),
            "active_clients": sum(1 for c in clients if c["is_active"]),
            "clients_with_keys": sum(1 for c in clients if c["has_klaviyo_key"]),
            "clients": clients,
        }
    except Exception as e:
        logger.error("Error fetching clients: %s", e)
        return {
            "status": "success",
            "total_clients": 0,
            "active_clients": 0,
            "clients_with_keys": 0,
            "clients": [],
        }


@router.get("/clients/{client_id}")
async def get_client_details(client_id: str, request: Request) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        data = doc.to_dict() or {}
        resolved_key = _resolve_client_key(db, client_id)
        details: Dict[str, Any] = {
            "id": client_id,
            "name": data.get("name", "Unknown"),
            "metric_id": data.get("metric_id", ""),
            "description": data.get("description", ""),
            "is_active": data.get("is_active", True),
            "has_klaviyo_key": bool(resolved_key),
            "contact_email": data.get("contact_email", ""),
            "contact_name": data.get("contact_name", ""),
            "website": data.get("website", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "klaviyo_key_preview": f"{resolved_key[:6]}...{resolved_key[-4:]}" if (resolved_key and len(resolved_key) > 10) else ("***" if resolved_key else ""),
            "client_voice": data.get("client_voice", ""),
            "client_background": data.get("client_background", ""),
            "asana_project_link": data.get("asana_project_link", ""),
            "affinity_segment_1_name": data.get("affinity_segment_1_name", ""),
            "affinity_segment_1_definition": data.get("affinity_segment_1_definition", ""),
            "affinity_segment_2_name": data.get("affinity_segment_2_name", ""),
            "affinity_segment_2_definition": data.get("affinity_segment_2_definition", ""),
            "affinity_segment_3_name": data.get("affinity_segment_3_name", ""),
            "affinity_segment_3_definition": data.get("affinity_segment_3_definition", ""),
            "key_growth_objective": data.get("key_growth_objective", "subscriptions"),
        }

        goals_docs = list(db.collection("goals").where("client_id", "==", client_id).stream())
        details["goals_count"] = len(goals_docs)

        perf_docs = list(
            db.collection("performance_history").where("client_id", "==", client_id).limit(12).stream()
        )
        details["performance_records"] = len(perf_docs)
        return details

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching client details: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients")
async def create_client(client: ClientCreate, request: Request) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        existing = list(db.collection("clients").where("name", "==", client.name).limit(1).stream())
        if existing:
            raise HTTPException(status_code=400, detail="Client name already exists")

        client_data = {
            "name": client.name,
            "metric_id": client.metric_id or "",
            "description": client.description or "",
            "is_active": client.is_active,
            "contact_email": client.contact_email or "",
            "contact_name": client.contact_name or "",
            "website": client.website or "",
            "client_voice": client.client_voice or "",
            "client_background": client.client_background or "",
            "asana_project_link": client.asana_project_link or "",
            "affinity_segment_1_name": client.affinity_segment_1_name or "",
            "affinity_segment_1_definition": client.affinity_segment_1_definition or "",
            "affinity_segment_2_name": client.affinity_segment_2_name or "",
            "affinity_segment_2_definition": client.affinity_segment_2_definition or "",
            "affinity_segment_3_name": client.affinity_segment_3_name or "",
            "affinity_segment_3_definition": client.affinity_segment_3_definition or "",
            "key_growth_objective": client.key_growth_objective or "subscriptions",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        doc_ref = db.collection("clients").add(client_data)
        doc_id = doc_ref[1].id
        
        # Store Klaviyo API key in Secret Manager if provided
        if client.klaviyo_api_key:
            await _store_client_klaviyo_key(db, doc_id, client.klaviyo_api_key)
        
        return {"status": "success", "message": "Client created successfully", "client_id": doc_id, "client_name": client.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}")
async def update_client(client_id: str, update: ClientUpdate, request: Request) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        ref = db.collection("clients").document(client_id)
        doc = ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        update_data: Dict[str, Any] = {}
        if update.name is not None:
            current_name = (doc.to_dict() or {}).get("name")
            if update.name != current_name:
                exists = list(db.collection("clients").where("name", "==", update.name).limit(1).stream())
                if exists:
                    raise HTTPException(status_code=400, detail="Client name already exists")
            update_data["name"] = update.name

        if update.metric_id is not None:
            update_data["metric_id"] = update.metric_id
        # Handle Klaviyo API key update
        if update.klaviyo_api_key is not None:
            if update.klaviyo_api_key == "":
                # Remove the key by deleting the secret and clearing references
                try:
                    if get_secret_manager:
                        secret_manager = get_secret_manager()
                        secret_name = f"klaviyo-api-key-{client_id}"
                        secret_manager.delete_secret(secret_name)
                    update_data["klaviyo_secret_name"] = firestore.DELETE_FIELD
                    update_data["klaviyo_api_key"] = firestore.DELETE_FIELD
                    update_data["klaviyo_private_key"] = firestore.DELETE_FIELD
                except Exception as e:
                    logger.warning(f"Failed to delete secret for client {client_id}: {e}")
            else:
                # Store new key in Secret Manager
                await _store_client_klaviyo_key(db, client_id, update.klaviyo_api_key)
        if update.description is not None:
            update_data["description"] = update.description
        if update.is_active is not None:
            update_data["is_active"] = update.is_active
        if update.contact_email is not None:
            update_data["contact_email"] = update.contact_email
        if update.contact_name is not None:
            update_data["contact_name"] = update.contact_name
        if update.website is not None:
            update_data["website"] = update.website

        # Brand/PM/Affinity/Growth
        if update.client_voice is not None:
            update_data["client_voice"] = update.client_voice
        if update.client_background is not None:
            update_data["client_background"] = update.client_background
        if update.asana_project_link is not None:
            update_data["asana_project_link"] = update.asana_project_link
        if update.affinity_segment_1_name is not None:
            update_data["affinity_segment_1_name"] = update.affinity_segment_1_name
        if update.affinity_segment_1_definition is not None:
            update_data["affinity_segment_1_definition"] = update.affinity_segment_1_definition
        if update.affinity_segment_2_name is not None:
            update_data["affinity_segment_2_name"] = update.affinity_segment_2_name
        if update.affinity_segment_2_definition is not None:
            update_data["affinity_segment_2_definition"] = update.affinity_segment_2_definition
        if update.affinity_segment_3_name is not None:
            update_data["affinity_segment_3_name"] = update.affinity_segment_3_name
        if update.affinity_segment_3_definition is not None:
            update_data["affinity_segment_3_definition"] = update.affinity_segment_3_definition
        if update.key_growth_objective is not None:
            update_data["key_growth_objective"] = update.key_growth_objective

        update_data["updated_at"] = datetime.utcnow().isoformat()
        ref.update(update_data)
        return {"status": "success", "message": "Client updated successfully", "client_id": client_id, "updated_fields": list(update_data.keys())}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, request: Request) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        ref = db.collection("clients").document(client_id)
        doc = ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        ref.update(
            {"is_active": False, "updated_at": datetime.utcnow().isoformat(), "deleted_at": datetime.utcnow().isoformat()}
        )
        name = (doc.to_dict() or {}).get("name", "Unknown")
        return {"status": "success", "message": f"Client '{name}' has been deactivated", "client_id": client_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clients/migrate-keys")
async def migrate_legacy_keys(request: Request) -> Dict[str, Any]:
    """Migrate all legacy plaintext Klaviyo keys to Secret Manager."""
    get_current_user_from_session(request)
    
    if not get_secret_manager:
        raise HTTPException(status_code=500, detail="Secret Manager service not available")
    
    try:
        db = get_db()
        migrated = []
        errors = []
        
        # Find all clients with legacy keys
        docs = list(db.collection("clients").stream())
        
        for doc in docs:
            if not doc.exists:
                continue
                
            data = doc.to_dict() or {}
            client_id = doc.id
            
            # Check if client has legacy key but no secret reference
            legacy_key = data.get("klaviyo_api_key") or data.get("klaviyo_private_key")
            has_secret = data.get("klaviyo_secret_name")
            
            if legacy_key and not has_secret:
                try:
                    await _store_client_klaviyo_key(db, client_id, legacy_key)
                    migrated.append({
                        "client_id": client_id,
                        "client_name": data.get("name", "Unknown")
                    })
                except Exception as e:
                    errors.append({
                        "client_id": client_id,
                        "client_name": data.get("name", "Unknown"),
                        "error": str(e)
                    })
        
        return {
            "status": "success",
            "message": f"Migration completed. {len(migrated)} clients migrated, {len(errors)} errors",
            "migrated": migrated,
            "errors": errors
        }
        
    except Exception as e:
        logger.exception("Error during key migration")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/clients/{client_id}/test-klaviyo")
async def test_klaviyo_connection(client_id: str, request: Request) -> Dict[str, Any]:
    """Test Klaviyo connection using per-client API key from Secret Manager."""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        # Use the same key resolution logic as performance.py
        api_key = _resolve_client_key(db, client_id)
        if not api_key:
            return {
                "status": "error", 
                "message": "No Klaviyo API key configured for this client", 
                "client_id": client_id
            }

        # Use KlaviyoClient to test the connection
        if not KlaviyoClient:
            return {
                "status": "error", 
                "message": "KlaviyoClient not available", 
                "client_id": client_id
            }
        
        try:
            klaviyo_client = KlaviyoClient(api_key)
            result = await klaviyo_client.test_connection()
            
            if result["success"]:
                return {
                    "status": "success",
                    "message": "Klaviyo connection successful",
                    "client_id": client_id,
                    "accounts": result.get("accounts", 0)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Klaviyo connection failed: {result.get('error', 'Unknown error')}",
                    "client_id": client_id
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Klaviyo connection test failed: {str(e)}",
                "client_id": client_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error testing Klaviyo connection for %s", client_id)
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# Live Klaviyo ping endpoint (using global API key)
# ----------------------------
@router.get("/klaviyo/ping")
async def klaviyo_ping(request: Request) -> Dict[str, Any]:
    """Test endpoint for system health - removed global key support."""
    get_current_user_from_session(request)
    
    return {
        "status": "info",
        "message": "Global Klaviyo ping removed - use per-client testing instead",
        "note": "Use POST /api/admin/clients/{client_id}/test-klaviyo to test specific client connections",
        "timestamp": datetime.utcnow().isoformat()
    }