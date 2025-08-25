"""
Admin Asana configuration endpoints using Secret Manager.
Allows setting and validating Asana OAuth app credentials.
Also surfaces aggregate info about connected users.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.secrets import SecretManagerService
from app.deps import get_secret_manager_service, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/asana", tags=["Admin Asana"])


class SetAsanaSecretsRequest(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


@router.get("/status")
async def asana_status(secret_manager: SecretManagerService = Depends(get_secret_manager_service)) -> Dict[str, Any]:
    """Returns whether OAuth client creds exist and connected users count."""
    ok_id = False
    ok_secret = False
    try:
        ok_id = bool(secret_manager.get_secret("asana-oauth-client-id"))
    except Exception:
        ok_id = False
    try:
        ok_secret = bool(secret_manager.get_secret("asana-oauth-client-secret"))
    except Exception:
        ok_secret = False

    # Count connected users (best-effort)
    connected_users = 0
    try:
        db = get_db()
        # Firestore has no count queries without aggregation; iterate limited subset
        # For admin visibility, sample first 200 users
        users = list(db.collection("users").limit(200).stream())
        for u in users:
            doc = (
                db.collection("users").document(u.id).collection("integrations").document("asana").get()
            )
            if doc.exists and (doc.to_dict() or {}).get("access_token"):
                connected_users += 1
    except Exception:
        pass

    return {
        "client_id_configured": ok_id,
        "client_secret_configured": ok_secret,
        "connected_users_sample": connected_users,
    }


@router.post("/secrets")
async def set_asana_secrets(payload: SetAsanaSecretsRequest, secret_manager: SecretManagerService = Depends(get_secret_manager_service)) -> Dict[str, Any]:
    """Create or update Asana OAuth client credentials in Secret Manager."""
    try:
        changed = []
        if payload.client_id:
            secret_manager.create_secret("asana-oauth-client-id", payload.client_id, labels={"app": "emailpilot", "type": "asana", "cred": "client_id"})
            changed.append("client_id")
        if payload.client_secret:
            secret_manager.create_secret("asana-oauth-client-secret", payload.client_secret, labels={"app": "emailpilot", "type": "asana", "cred": "client_secret"})
            changed.append("client_secret")
        if not changed:
            raise HTTPException(status_code=400, detail="No values provided")
        return {"updated": changed}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set Asana secrets: {e}")
        raise HTTPException(status_code=500, detail="Failed to set Asana secrets")

