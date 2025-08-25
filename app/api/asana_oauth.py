"""
Asana OAuth endpoints for per-user connections.

Flow:
1) GET /api/asana/oauth/start -> redirect URL returned (client performs redirect)
2) GET /api/asana/oauth/callback?code=...&state=... -> exchanges code, stores tokens

User identity: uses session user (email) as user_id fallback unless a `user_id` is provided.
"""
from __future__ import annotations
import os
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse

from app.services.asana_oauth import AsanaOAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/asana/oauth", tags=["Asana OAuth"])


def _resolve_user_id(request: Request, explicit_user_id: Optional[str]) -> str:
    if explicit_user_id:
        return explicit_user_id
    # Use session user email as stable ID if available
    user = request.session.get("user") or {}
    uid = user.get("email") or user.get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.get("/start")
async def start_oauth(request: Request, redirect_uri: str = Query(...), user_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Return the Asana authorization URL for the user to visit."""
    uid = _resolve_user_id(request, user_id)
    state = uid  # simple state; could be enhanced with nonce
    service = AsanaOAuthService()
    url = service.get_authorization_url(redirect_uri=redirect_uri, state=state)
    return {"authorization_url": url, "state": state}


@router.get("/callback")
async def oauth_callback(request: Request, code: str, state: str, redirect_uri: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Handle Asana OAuth callback and store tokens for the user specified in state."""
    service = AsanaOAuthService()
    # In production verify state and match to session user
    uid = state
    # If redirect_uri not provided, infer current endpoint URL without query
    if not redirect_uri:
        host = request.headers.get("host")
        scheme = request.url.scheme
        redirect_uri = f"{scheme}://{host}{request.url.path}"
    tokens = await service.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
    service.store_tokens(uid, tokens)
    # Redirect back to a friendly UI page if available
    next_url = request.query_params.get("next") or "/user-management.html#connected=1"
    return RedirectResponse(url=next_url)


@router.get("/status")
async def oauth_status(request: Request, user_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    uid = _resolve_user_id(request, user_id)
    service = AsanaOAuthService()
    doc = service._user_integration_ref(uid).get()
    connected = doc.exists and bool((doc.to_dict() or {}).get("access_token"))
    return {"user_id": uid, "connected": connected}
