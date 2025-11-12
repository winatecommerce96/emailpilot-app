"""
Admin Client Management API
Comprehensive client data management for admin panel
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel

# Firestore
from google.cloud import firestore
from app.deps import get_db, get_secret_manager_service
from app.core.settings import get_settings, Settings
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver

# Type checking imports
if TYPE_CHECKING:
    from app.services.secrets import SecretManagerService
    from app.services.klaviyo_client import KlaviyoClient

# Import Secret Manager service and KlaviyoClient for runtime
try:
    from app.services.secrets import SecretManagerService as _SecretManagerService
    from app.services.klaviyo_client import KlaviyoClient as _KlaviyoClient
    
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

# Fallback mode for development environments
DEVELOPMENT_MODE = os.getenv("ENVIRONMENT", "development") == "development"
SECRET_MANAGER_ENABLED = os.getenv("SECRET_MANAGER_ENABLED", "true").lower() == "true"


logger = logging.getLogger(__name__)

# All routes live under /api/admin/…
router = APIRouter(prefix="/api/admin", tags=["Admin Client Management"])


# ----------------------------
# Dependencies / helpers
# ----------------------------



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


def generate_client_slug(name: str) -> str:
    """Generate a URL-safe client slug from the client name."""
    import re
    
    # Convert to lowercase and replace spaces with hyphens
    slug = name.lower().strip()
    
    # Replace apostrophes and other special characters
    slug = slug.replace("'", "").replace("&", "and")
    
    # Replace multiple spaces/hyphens with single hyphen
    slug = re.sub(r'[\s\-]+', '-', slug)
    
    # Keep only alphanumeric characters and hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure it's not empty
    if not slug:
        slug = "client"
    
    return slug


class ClientCreate(BaseModel):
    # Basic fields
    name: str
    description: Optional[str] = ""
    contact_email: Optional[str] = ""
    contact_name: Optional[str] = ""
    website: Optional[str] = ""
    is_active: Optional[bool] = True
    
    # API fields
    klaviyo_api_key: Optional[str] = ""
    metric_id: Optional[str] = ""
    klaviyo_account_id: Optional[str] = ""
    
    # Brand Manager fields
    client_voice: Optional[str] = ""
    client_background: Optional[str] = ""
    
    # PM fields
    asana_project_link: Optional[str] = ""
    
    # Segments fields
    affinity_segment_1_name: Optional[str] = ""
    affinity_segment_1_definition: Optional[str] = ""
    affinity_segment_2_name: Optional[str] = ""
    affinity_segment_2_definition: Optional[str] = ""
    affinity_segment_3_name: Optional[str] = ""
    affinity_segment_3_definition: Optional[str] = ""
    
    # Growth fields
    key_growth_objective: Optional[str] = "subscriptions"
    timezone: Optional[str] = "UTC"


class ClientUpdate(BaseModel):
    # Basic fields
    name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None
    
    # API fields
    klaviyo_api_key: Optional[str] = None
    metric_id: Optional[str] = None
    klaviyo_account_id: Optional[str] = None
    
    # Brand Manager fields
    client_voice: Optional[str] = None
    client_background: Optional[str] = None
    
    # PM fields
    asana_project_link: Optional[str] = None
    
    # Segments fields
    affinity_segment_1_name: Optional[str] = None
    affinity_segment_1_definition: Optional[str] = None
    affinity_segment_2_name: Optional[str] = None
    affinity_segment_2_definition: Optional[str] = None
    affinity_segment_3_name: Optional[str] = None
    affinity_segment_3_definition: Optional[str] = None
    
    # Growth fields
    key_growth_objective: Optional[str] = None
    timezone: Optional[str] = None




async def _resolve_client_key_legacy(key_resolver: ClientKeyResolver, client_id: str) -> Optional[str]:
    """
    Legacy wrapper around ClientKeyResolver for backward compatibility.
    Uses the centralized resolver which handles all fallback logic.
    """
    if not client_id:
        return None
    
    try:
        return await key_resolver.get_client_klaviyo_key(client_id)
    except Exception as e:
        logger.error(f"Key resolution failed for client {client_id}: {e}")
        return None


async def _store_client_klaviyo_key_legacy(key_resolver: ClientKeyResolver, client_id: str, api_key: str) -> bool:
    """
    Legacy wrapper around ClientKeyResolver for storing API keys.
    Uses the centralized resolver which handles Secret Manager storage.
    
    Returns:
        True if successful, False otherwise
    """
    if not api_key:
        return False
    
    try:
        return await key_resolver.set_client_klaviyo_key(client_id, api_key)
    except Exception as e:
        logger.error(f"Failed to store API key for client {client_id}: {e}")
        if not DEVELOPMENT_MODE:
            raise HTTPException(
                    status_code=500,
                    detail="Secret Manager is required in production but is unavailable"
                )
        
        client_ref.update(update_data)
        
        return client_slug
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store Klaviyo key for client {client_id}: {e}")
        raise


# ----------------------------
# Admin/Utility endpoints
# ----------------------------

@router.get("/login")
async def admin_login(request: Request, password: str = ""):
    """Simple admin login that sets session. For internal use only."""
    # Check password against environment variable or default
    expected_password = os.getenv("ADMIN_PASSWORD", "emailpilot2025")

    if password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Set session
    request.session["user"] = {
        "email": "admin@emailpilot.ai",
        "name": "Admin User",
        "role": "admin"
    }

    return {
        "success": True,
        "message": "Logged in successfully",
        "user": request.session["user"]
    }

@router.get("/environment")
async def get_environment_info(settings: Settings = Depends(get_settings)):
    try:
        demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "false").lower() == "true"
        build_version = os.getenv("BUILD_VERSION", "dev")
        commit_sha = os.getenv("COMMIT_SHA", "unknown")
        firestore_project = os.getenv("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Check Secret Manager availability
        secret_manager_available = False
        secret_manager_error = None
        try:
            from app.services.secrets import SecretManagerService
            if firestore_project:
                test_service = SecretManagerService(firestore_project)
                # Quick test - try to list secrets
                test_service.list_secrets()
                secret_manager_available = True
        except Exception as e:
            secret_manager_error = str(e)
            logger.warning(f"Secret Manager not available: {e}")

        return {
            "demoMode": demo_mode,
            "environment": environment,
            "debug": debug,
            "apiBase": api_base,
            "firestoreProject": firestore_project,
            "buildVersion": build_version,
            "commitSha": commit_sha,
            "secretManagerEnabled": settings.secret_manager_enabled,
            "secretManagerAvailable": secret_manager_available,
            "secretManagerError": secret_manager_error,
            "developmentMode": DEVELOPMENT_MODE,
            "features": {
                "firestore": True,
                "secretManager": settings.secret_manager_enabled and secret_manager_available,
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
            "secretManagerEnabled": False,
            "secretManagerAvailable": False,
            "developmentMode": True,
            "error": str(e),
        }


@router.get("/clients")
async def get_all_clients(
    request: Request,
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Get all clients with their Klaviyo key status for calendar and admin UI"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        docs = db.collection("clients").stream()

        clients = []
        for doc in docs:
            if not doc.exists:
                continue

            data = doc.to_dict() or {}
            client_id = doc.id

            # Resolve Klaviyo key status
            resolved_key = await key_resolver.get_client_klaviyo_key(client_id)

            clients.append({
                "id": client_id,
                "name": data.get("name", "Unknown"),
                "client_slug": data.get("client_slug", ""),
                "description": data.get("description", ""),
                "is_active": data.get("is_active", True),
                "has_klaviyo_key": bool(resolved_key),
                "contact_email": data.get("contact_email", ""),
                "contact_name": data.get("contact_name", ""),
                "website": data.get("website", ""),
                "metric_id": data.get("metric_id", ""),
                "klaviyo_account_id": data.get("klaviyo_account_id", ""),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })

        return {
            "total_clients": len(clients),
            "clients": clients
        }

    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients/{client_id}")
async def get_client_details(
    client_id: str, 
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        data = doc.to_dict() or {}
        resolved_key = await key_resolver.get_client_klaviyo_key(client_id)
        details: Dict[str, Any] = {
            "id": client_id,
            # Basic fields
            "name": data.get("name", "Unknown"),
            "client_slug": data.get("client_slug", ""),
            "description": data.get("description", ""),
            "contact_email": data.get("contact_email", ""),
            "contact_name": data.get("contact_name", ""),
            "website": data.get("website", ""),
            "is_active": data.get("is_active", True),
            
            # API fields (NEVER return raw API keys)
            "metric_id": data.get("metric_id", ""),
            "klaviyo_account_id": data.get("klaviyo_account_id", ""),
            "has_klaviyo_key": bool(resolved_key),
            "klaviyo_key_preview": f"{resolved_key[:6]}...{resolved_key[-4:]}" if (resolved_key and len(resolved_key) > 10) else ("***" if resolved_key else ""),
            
            # Brand Manager fields
            "client_voice": data.get("client_voice", ""),
            "client_background": data.get("client_background", ""),
            
            # PM fields
            "asana_project_link": data.get("asana_project_link", ""),
            
            # Segments fields
            "affinity_segment_1_name": data.get("affinity_segment_1_name", ""),
            "affinity_segment_1_definition": data.get("affinity_segment_1_definition", ""),
            "affinity_segment_2_name": data.get("affinity_segment_2_name", ""),
            "affinity_segment_2_definition": data.get("affinity_segment_2_definition", ""),
            "affinity_segment_3_name": data.get("affinity_segment_3_name", ""),
            "affinity_segment_3_definition": data.get("affinity_segment_3_definition", ""),
            
            # Growth fields
            "key_growth_objective": data.get("key_growth_objective", "subscriptions"),
            "timezone": data.get("timezone", "UTC"),
            
            # Metadata fields
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "created_by": data.get("created_by", ""),
            "updated_by": data.get("updated_by", ""),
            
            # OAuth connection info (legacy)
            "klaviyo_oauth_account_id": data.get("klaviyo_oauth_account_id"),
            "oauth_connection_type": data.get("oauth_connection_type"),
            "oauth_connected_by": data.get("oauth_connected_by"),
            "oauth_connected_at": data.get("oauth_connected_at"),
            "klaviyo_account_name": data.get("klaviyo_account_name"),
            "klaviyo_account_email": data.get("klaviyo_account_email"),
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
async def create_client(
    client: ClientCreate, 
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    user = get_current_user_from_session(request)
    try:
        db = get_db()
        existing = list(db.collection("clients").where("name", "==", client.name).limit(1).stream())
        if existing:
            raise HTTPException(status_code=400, detail="Client name already exists")

        # Generate client slug from name
        client_slug = generate_client_slug(client.name)
        current_time = datetime.utcnow().isoformat()
        user_email = user.get("email", "unknown")
        
        # Store ALL client fields in a single Firestore document
        client_data = {
            # Basic fields
            "name": client.name,
            "client_slug": client_slug,
            "description": client.description or "",
            "contact_email": client.contact_email or "",
            "contact_name": client.contact_name or "",
            "website": client.website or "",
            "is_active": client.is_active,
            
            # API fields (NO raw API key stored here)
            "metric_id": client.metric_id or "",
            "klaviyo_account_id": client.klaviyo_account_id or "",
            "has_klaviyo_key": bool(client.klaviyo_api_key),
            
            # Brand Manager fields
            "client_voice": client.client_voice or "",
            "client_background": client.client_background or "",
            
            # PM fields
            "asana_project_link": client.asana_project_link or "",
            
            # Segments fields
            "affinity_segment_1_name": client.affinity_segment_1_name or "",
            "affinity_segment_1_definition": client.affinity_segment_1_definition or "",
            "affinity_segment_2_name": client.affinity_segment_2_name or "",
            "affinity_segment_2_definition": client.affinity_segment_2_definition or "",
            "affinity_segment_3_name": client.affinity_segment_3_name or "",
            "affinity_segment_3_definition": client.affinity_segment_3_definition or "",
            
            # Growth fields
            "key_growth_objective": client.key_growth_objective or "subscriptions",
            "timezone": client.timezone or "UTC",
            
            # Metadata fields
            "created_at": current_time,
            "updated_at": current_time,
            "created_by": user_email,
            "updated_by": user_email,
        }
        
        # Create the client document
        doc_ref = db.collection("clients").add(client_data)
        doc_id = doc_ref[1].id
        
        # Store Klaviyo API key in Secret Manager if provided (and update document with secret reference)
        if client.klaviyo_api_key:
            success = await key_resolver.set_client_klaviyo_key(doc_id, client.klaviyo_api_key)
            if not success:
                logger.warning(f"Failed to store API key for client {doc_id}")
            client_slug = generate_client_slug(client.name)
        
        return {
            "status": "success", 
            "message": "Client created successfully", 
            "client_id": doc_id, 
            "client_name": client.name,
            "client_slug": client_slug
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}")
async def update_client(
    client_id: str, 
    update: ClientUpdate, 
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    user = get_current_user_from_session(request)
    try:
        db = get_db()
        ref = db.collection("clients").document(client_id)
        doc = ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        current_data = doc.to_dict() or {}
        update_data: Dict[str, Any] = {}
        
        # Handle name update (check for duplicates and regenerate slug if needed)
        if update.name is not None:
            current_name = current_data.get("name")
            if update.name != current_name:
                exists = list(db.collection("clients").where("name", "==", update.name).limit(1).stream())
                if exists:
                    raise HTTPException(status_code=400, detail="Client name already exists")
                update_data["name"] = update.name
                # Regenerate slug when name changes
                update_data["client_slug"] = generate_client_slug(update.name)

        # Handle all basic fields
        if update.description is not None:
            update_data["description"] = update.description
        if update.contact_email is not None:
            update_data["contact_email"] = update.contact_email
        if update.contact_name is not None:
            update_data["contact_name"] = update.contact_name
        if update.website is not None:
            update_data["website"] = update.website
        if update.is_active is not None:
            update_data["is_active"] = update.is_active

        # Handle API fields
        if update.metric_id is not None:
            update_data["metric_id"] = update.metric_id
        if update.klaviyo_account_id is not None:
            update_data["klaviyo_account_id"] = update.klaviyo_account_id
            
        # Handle Klaviyo API key update
        if update.klaviyo_api_key is not None:
            if update.klaviyo_api_key == "":
                # Remove the key by deleting the secret and clearing references
                try:
                    if secret_manager:
                        # Try both old and new naming conventions
                        current_slug = current_data.get("client_slug", generate_client_slug(current_data.get("name", "")))
                        secret_names = [
                            f"klaviyo-api-{current_slug}",  # New convention
                            f"klaviyo-api-key-{client_id}",  # Old convention
                            current_data.get("klaviyo_api_key_secret", "")  # Stored reference
                        ]
                        for secret_name in secret_names:
                            if secret_name:
                                try:
                                    secret_manager.delete_secret(secret_name)
                                except Exception:
                                    pass  # Ignore if secret doesn't exist
                    
                    # Clear all API key references
                    update_data["klaviyo_api_key_secret"] = firestore.DELETE_FIELD
                    update_data["has_klaviyo_key"] = False
                    update_data["klaviyo_secret_name"] = firestore.DELETE_FIELD  # Legacy field
                    update_data["klaviyo_api_key"] = firestore.DELETE_FIELD  # Legacy field
                    update_data["klaviyo_private_key"] = firestore.DELETE_FIELD  # Legacy field
                    
                except Exception as e:
                    logger.warning(f"Failed to delete secret for client {client_id}: {e}")
            else:
                # Store new key in Secret Manager
                success = await key_resolver.set_client_klaviyo_key(client_id, update.klaviyo_api_key)
                if success:
                    update_data["has_klaviyo_key"] = True
                else:
                    logger.warning(f"Failed to store API key for client {client_id}")

        # Handle Brand Manager fields
        if update.client_voice is not None:
            update_data["client_voice"] = update.client_voice
        if update.client_background is not None:
            update_data["client_background"] = update.client_background

        # Handle PM fields
        if update.asana_project_link is not None:
            update_data["asana_project_link"] = update.asana_project_link

        # Handle Segments fields
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

        # Handle Growth fields
        if update.key_growth_objective is not None:
            update_data["key_growth_objective"] = update.key_growth_objective
        if update.timezone is not None:
            update_data["timezone"] = update.timezone

        # Update metadata
        update_data["updated_at"] = datetime.utcnow().isoformat()
        update_data["updated_by"] = user.get("email", "unknown")
        
        # Apply updates
        ref.update(update_data)
        
        return {
            "status": "success", 
            "message": "Client updated successfully", 
            "client_id": client_id, 
            "updated_fields": list(update_data.keys())
        }
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
async def migrate_legacy_keys(
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Migrate all legacy plaintext Klaviyo keys to Secret Manager."""
    get_current_user_from_session(request)
    
    if not SECRET_MANAGER_ENABLED:
        raise HTTPException(
            status_code=500, 
            detail="Secret Manager service not available or disabled. Check GOOGLE_CLOUD_PROJECT and permissions."
        )
    
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
                    success = await key_resolver.set_client_klaviyo_key(client_id, legacy_key)
                    migrated.append({
                        "client_id": client_id,
                        "client_name": client_name
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
async def test_klaviyo_connection(
    client_id: str, 
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Test Klaviyo connection using per-client API key from Secret Manager."""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")

        # Use the resolver to get the API key
        api_key = await key_resolver.get_client_klaviyo_key(client_id)
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


@router.get("/secret-manager/status")
async def secret_manager_status(request: Request, secret_manager: Optional["SecretManagerService"] = Depends(get_secret_manager_service)) -> Dict[str, Any]:
    """Check Secret Manager status and provide diagnostic information."""
    get_current_user_from_session(request)
    
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        environment = os.getenv("ENVIRONMENT", "development")
        sm_enabled = os.getenv("SECRET_MANAGER_ENABLED", "true").lower() == "true"
        
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": environment,
            "project_id": project_id,
            "secret_manager_enabled": sm_enabled,
            "secret_manager_available": secret_manager is not None,
            "development_mode": DEVELOPMENT_MODE,
            "status": "unknown",
            "message": "",
            "tests": {},
            "recommendations": []
        }
        
        if not sm_enabled:
            status.update({
                "status": "disabled",
                "message": "Secret Manager is explicitly disabled via SECRET_MANAGER_ENABLED=false",
                "recommendations": ["Enable Secret Manager by setting SECRET_MANAGER_ENABLED=true"]
            })
            return status
        
        if not project_id:
            status.update({
                "status": "error",
                "message": "GOOGLE_CLOUD_PROJECT environment variable not set",
                "recommendations": [
                    "Set GOOGLE_CLOUD_PROJECT environment variable",
                    "Example: export GOOGLE_CLOUD_PROJECT=your-project-id"
                ]
            })
            return status
        
        if not secret_manager:
            status.update({
                "status": "error" if not DEVELOPMENT_MODE else "warning",
                "message": "Secret Manager service not available - check authentication and permissions",
                "recommendations": [
                    "Run the diagnostic script: python check_secret_manager.py",
                    "Check Google Cloud authentication: gcloud auth application-default login",
                    "Verify IAM permissions for Secret Manager",
                    "Enable Secret Manager API: gcloud services enable secretmanager.googleapis.com"
                ]
            })
            return status
        
        # Test Secret Manager operations
        tests = {}
        
        # Test 1: List secrets
        try:
            secrets = secret_manager.list_secrets()
            tests["list_secrets"] = {
                "status": "success",
                "secret_count": len(secrets),
                "message": f"Successfully listed {len(secrets)} secrets"
            }
        except Exception as e:
            tests["list_secrets"] = {
                "status": "error",
                "error": str(e),
                "message": "Failed to list secrets"
            }
        
        # Test 2: Create test secret (if list succeeded)
        if tests["list_secrets"]["status"] == "success":
            test_secret_name = f"emailpilot-test-{int(datetime.utcnow().timestamp())}"
            try:
                secret_manager.create_secret(test_secret_name, "test-value", {"type": "diagnostic"})
                
                # Try to read it back
                retrieved = secret_manager.get_secret(test_secret_name)
                
                # Clean up
                secret_manager.delete_secret(test_secret_name)
                
                tests["create_secret"] = {
                    "status": "success",
                    "message": "Successfully created, read, and deleted test secret"
                }
            except Exception as e:
                tests["create_secret"] = {
                    "status": "error",
                    "error": str(e),
                    "message": "Failed to create test secret"
                }
        
        status["tests"] = tests
        
        # Determine overall status
        if all(test.get("status") == "success" for test in tests.values()):
            status.update({
                "status": "success",
                "message": "Secret Manager is fully operational"
            })
        elif any(test.get("status") == "error" for test in tests.values()):
            status.update({
                "status": "error",
                "message": "Secret Manager has operational issues",
                "recommendations": [
                    "Run full diagnostic: python check_secret_manager.py",
                    "Check IAM permissions for secretmanager.admin role"
                ]
            })
        else:
            status.update({
                "status": "warning",
                "message": "Secret Manager partially operational"
            })
        
        return status
        
    except Exception as e:
        logger.exception("Error checking Secret Manager status")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "message": f"Failed to check Secret Manager status: {str(e)}",
            "error": str(e),
            "recommendations": [
                "Run diagnostic script: python check_secret_manager.py",
                "Check server logs for detailed error information"
            ]
        }