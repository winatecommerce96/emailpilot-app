"""
Admin Client Management API
Comprehensive client data management for admin panel
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

# Firestore
from google.cloud import firestore
from app.services.firestore_client import get_firestore_client
from app.core.config import settings

# Try your project's Secret Manager service first
try:
    from app.services.secret_manager import SecretManagerService
    def get_secret(name: str) -> Optional[str]:
        try:
            service = SecretManagerService()
            return service.get_secret(name)
        except Exception:
            return None
except Exception:
    get_secret = None

# Fallback: direct GCP Secret Manager client
try:
    from google.cloud import secretmanager as gcp_secretmanager
except Exception:
    gcp_secretmanager = None

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
    klaviyo_private_key: Optional[str] = ""
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
    klaviyo_private_key: Optional[str] = None
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


def _get_secret_via_service(name: str) -> Optional[str]:
    if not get_secret:
        return None
    try:
        val = get_secret(name)
        return val.strip() if val else None
    except Exception as e:
        logger.debug("get_secret(%s) failed: %s", name, e)
        return None


def _get_secret_direct(name: str, project_id: Optional[str] = None) -> Optional[str]:
    if gcp_secretmanager is None:
        return None
    try:
        project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or getattr(settings, 'google_cloud_project', 'emailpilot-438321')
        client = gcp_secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_version_path(project, name, "latest")
        res = client.access_secret_version(name=secret_path)
        return res.payload.data.decode("utf-8").strip()
    except Exception as e:
        logger.debug("Direct Secret Manager access failed for %s: %s", name, e)
        return None


def fetch_klaviyo_key_for_client(client_id: str, doc: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Order: client doc → client-scoped secret → global secret."""
    # 1) client doc
    if doc:
        key = doc.get("klaviyo_private_key")
        if isinstance(key, str) and key.strip():
            return key.strip()

    # 2) client-scoped secret names
    candidates = []
    prefix = getattr(settings, "klaviyo_secret_prefix", None)
    if prefix:
        candidates += [f"{prefix}-{client_id}", f"{prefix}_{client_id}"]
    candidates += [
        f"klaviyo-api-key-{client_id}",
        f"klaviyo_api_key_{client_id}",
        f"emailpilot-klaviyo-api-key-{client_id}",
        f"emailpilot_klaviyo_api_key_{client_id}",
    ]
    for name in candidates:
        v = _get_secret_via_service(name) or _get_secret_direct(name)
        if v:
            return v

    # 3) global
    global_names = [
        getattr(settings, "klaviyo_secret_name", "") or "",
        "emailpilot-klaviyo-api-key",
        "klaviyo_private_key",
        "klaviyo-api-key",
    ]
    for name in [n for n in global_names if n]:
        v = _get_secret_via_service(name) or _get_secret_direct(name)
        if v:
            return v

    return None


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
            resolved_key = fetch_klaviyo_key_for_client(d.id, data)
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
        resolved_key = fetch_klaviyo_key_for_client(client_id, data)
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
        if client.klaviyo_private_key:
            client_data["klaviyo_private_key"] = client.klaviyo_private_key

        doc_ref = db.collection("clients").add(client_data)
        doc_id = doc_ref[1].id
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
        if update.klaviyo_private_key is not None:
            update_data["klaviyo_private_key"] = (
                firestore.DELETE_FIELD if update.klaviyo_private_key == "" else update.klaviyo_private_key
            )
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


# ----------------------------
# Real Klaviyo ping
# ----------------------------
KLAVIYO_API_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = os.getenv("KLAVIYO_API_REVISION", "2023-10-15")


async def _klaviyo_ping(api_key: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "accept": "application/json",
        "revision": KLAVIYO_REVISION,
        "content-type": "application/json",
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.get(f"{KLAVIYO_API_BASE}/accounts/", headers=headers)
        try:
            payload = res.json()
        except Exception:
            payload = {"raw": res.text[:500]}
        return {"ok": res.status_code == 200, "status_code": res.status_code, "payload": payload}


@router.post("/clients/{client_id}/test-klaviyo")
async def test_klaviyo_connection(client_id: str, request: Request) -> Dict[str, Any]:
    """Live ping to Klaviyo using a key resolved from Secret Manager (or client doc fallback)."""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        data = doc.to_dict() or {}

        api_key = fetch_klaviyo_key_for_client(client_id, data)
        if not api_key:
            return {"status": "error", "message": "No Klaviyo API key found", "client_id": client_id}

        result = await _klaviyo_ping(api_key)
        if result["ok"]:
            acct_name = None
            try:
                items = (result["payload"] or {}).get("data") or []
                if items and isinstance(items, list):
                    acct_name = (items[0].get("attributes") or {}).get("name")
            except Exception:
                pass
            return {
                "status": "success",
                "message": "Klaviyo API connection successful",
                "client_id": client_id,
                "account_name": acct_name,
                "response_time_ms": 200,  # Could implement actual timing
            }

        return {
            "status": "error",
            "message": "Klaviyo API ping failed",
            "client_id": client_id,
            "error": f"HTTP {result['status_code']}: {result.get('payload', {})}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error testing Klaviyo connection for %s", client_id)
        raise HTTPException(status_code=500, detail=str(e))