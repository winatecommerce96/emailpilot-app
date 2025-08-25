"""
Klaviyo OAuth Integration Router
Handles OAuth flow for Klaviyo and auto-creates clients
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.cloud import firestore

from app.core.settings import Settings, get_settings
from app.deps import get_db, get_secret_manager_service
from app.repositories.clients_repo import ClientsRepository
from app.services.auth import get_current_user
from app.services.crypto_service import get_crypto_service
from app.services.klaviyo_oauth_service import KlaviyoOAuthService
from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Klaviyo OAuth"])

# In-memory storage for OAuth state (in production, use Redis or Firestore)
_oauth_states: Dict[str, Dict] = {}


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is mounted"""
    return {"status": "ok", "message": "Klaviyo OAuth router is mounted"}


@router.get("/oauth/start-simple")
async def start_klaviyo_oauth_simple(
    redirect_path: str = Query(default="/admin/clients")
):
    """
    Simplified OAuth start endpoint for testing - no auth required
    """
    import os
    
    client_id = os.getenv("KLAVIYO_OAUTH_CLIENT_ID", "test-client-id")
    redirect_uri = os.getenv("KLAVIYO_OAUTH_REDIRECT_URI", "http://localhost:8000/api/integrations/klaviyo/oauth/callback")
    scopes = os.getenv("KLAVIYO_OAUTH_SCOPES", "accounts:read,lists:read")
    
    # Build simple auth URL
    auth_base = "https://www.klaviyo.com/oauth/authorize"
    
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": f"simple-state-{secrets.token_urlsafe(16)}"
    }
    
    auth_url = f"{auth_base}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url, status_code=302)


def store_oauth_state(
    state: str,
    user_id: str,
    code_verifier: Optional[str] = None,
    redirect_path: Optional[str] = None
) -> None:
    """Store OAuth state with user context and PKCE verifier"""
    _oauth_states[state] = {
        "user_id": user_id,
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow(),
        "redirect_path": redirect_path or "/admin/clients"
    }
    
    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow()
    for key in list(_oauth_states.keys()):
        if (cutoff - _oauth_states[key]["created_at"]).seconds > 600:
            del _oauth_states[key]


def verify_oauth_state(state: str) -> Optional[Dict]:
    """Verify OAuth state and return user context"""
    return _oauth_states.pop(state, None)


async def emit_client_event(client_id: str, event_type: str = "created_or_updated"):
    """
    Emit client event for real-time updates
    
    Args:
        client_id: Client ID that was created or updated
        event_type: Type of event (created_or_updated)
    """
    try:
        # TODO: Implement WebSocket/SSE broadcasting
        # For now, just log the event
        logger.info(f"Client event: {event_type} - {client_id}")
        
        # If we have a message queue or pub/sub, publish here
        # await event_bus.publish("client." + event_type, {"client_id": client_id})
        
    except Exception as e:
        logger.error(f"Failed to emit client event: {e}")


def get_klaviyo_oauth_service(settings: Settings = Depends(get_settings)) -> KlaviyoOAuthService:
    """Get configured Klaviyo OAuth service"""
    client_id = os.getenv("KLAVIYO_OAUTH_CLIENT_ID", settings.klaviyo_oauth_client_id)
    client_secret = os.getenv("KLAVIYO_OAUTH_CLIENT_SECRET", settings.klaviyo_oauth_client_secret)
    redirect_uri = os.getenv("KLAVIYO_OAUTH_REDIRECT_URI", f"{settings.app_base_url}/api/integrations/klaviyo/oauth/callback")
    scopes = os.getenv("KLAVIYO_OAUTH_SCOPES", "accounts:read,campaigns:read,flows:read,lists:read,metrics:read,profiles:read,segments:read")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Klaviyo OAuth not configured. Please set KLAVIYO_OAUTH_CLIENT_ID and KLAVIYO_OAUTH_CLIENT_SECRET"
        )
    
    return KlaviyoOAuthService(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes.split(",") if scopes else None
    )


@router.get("/oauth/start")
async def start_klaviyo_oauth(
    redirect_path: Optional[str] = Query("/admin/clients", description="Path to redirect after OAuth"),
    settings: Settings = Depends(get_settings),
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate Klaviyo OAuth flow
    
    This endpoint:
    1. Validates user session
    2. Generates PKCE challenge for enhanced security
    3. Stores state for CSRF protection
    4. Redirects to Klaviyo consent page
    """
    try:
        # Current user is now properly authenticated via dependency injection
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get OAuth configuration
        client_id = os.getenv("KLAVIYO_OAUTH_CLIENT_ID") or settings.klaviyo_oauth_client_id
        client_secret = os.getenv("KLAVIYO_OAUTH_CLIENT_SECRET") or settings.klaviyo_oauth_client_secret
        redirect_uri = os.getenv("KLAVIYO_OAUTH_REDIRECT_URI") or settings.klaviyo_oauth_redirect_uri
        scopes = os.getenv("KLAVIYO_OAUTH_SCOPES", settings.klaviyo_oauth_scopes)
        
        if not client_id or not client_secret:
            logger.error("Klaviyo OAuth not configured - missing client_id or client_secret")
            raise HTTPException(
                status_code=500,
                detail="Klaviyo OAuth not configured. Please set KLAVIYO_OAUTH_CLIENT_ID and KLAVIYO_OAUTH_CLIENT_SECRET"
            )
        
        # Create OAuth service
        service = KlaviyoOAuthService(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes.split(",") if scopes else None
        )
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Generate PKCE pair for enhanced security
        code_verifier, code_challenge = service.generate_pkce_pair()
        
        # Store state with user context
        user_id = current_user.get("email") or current_user.get("id")
        store_oauth_state(state, user_id, code_verifier, redirect_path)
        
        # Build authorization URL
        auth_url = service.build_auth_url(state, code_challenge)
        
        logger.info(f"Starting Klaviyo OAuth for user {user_id}, redirecting to: {auth_url}")
        
        return RedirectResponse(url=auth_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Klaviyo OAuth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/oauth/callback")
async def klaviyo_oauth_callback(
    code: str = Query(..., description="Authorization code from Klaviyo"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    error_description: Optional[str] = Query(None, description="Error description"),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
    service: KlaviyoOAuthService = Depends(get_klaviyo_oauth_service),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """
    Handle Klaviyo OAuth callback
    
    This endpoint:
    1. Validates state for CSRF protection
    2. Exchanges code for tokens
    3. Fetches Klaviyo account metadata
    4. Creates or updates client in Firestore
    5. Stores encrypted tokens
    6. Redirects to admin clients page
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error: {error} - {error_description}")
            return RedirectResponse(
                url=f"/admin/clients?error=oauth_failed&message={error_description or error}",
                status_code=302
            )
        
        # Verify state
        state_data = verify_oauth_state(state)
        if not state_data:
            logger.error("Invalid OAuth state")
            return RedirectResponse(
                url="/admin/clients?error=invalid_state",
                status_code=302
            )
        
        # Verify user matches
        user_id = current_user.get("email") or current_user.get("id")
        if user_id != state_data["user_id"]:
            logger.error(f"User mismatch: {user_id} != {state_data['user_id']}")
            return RedirectResponse(
                url="/admin/clients?error=user_mismatch",
                status_code=302
            )
        
        # Exchange code for tokens
        code_verifier = state_data.get("code_verifier")
        token = await service.exchange_code_for_token(code, code_verifier)
        
        # Fetch Klaviyo account profile
        account = await service.get_account_profile(token.access_token)
        
        # Encrypt tokens
        crypto_service = get_crypto_service()
        encrypted_tokens = {
            "access_token": crypto_service.encrypt(token.access_token),
            "refresh_token": crypto_service.encrypt(token.refresh_token) if token.refresh_token else None
        }
        
        # Store OAuth tokens in Secret Manager
        oauth_secret_id = f"oauth-klaviyo-{user_id.replace('@', '-').replace('.', '-')}-{account.id}"
        oauth_data = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "scope": token.scope,
            "account_id": account.id,
            "account_name": account.name,
            "encrypted": False  # Mark as unencrypted in Secret Manager (we encrypt in Firestore)
        }
        secret_manager.create_or_update_secret(oauth_secret_id, json.dumps(oauth_data))
        
        # Create or update client
        clients_repo = ClientsRepository(db)
        client = await clients_repo.upsert_client_from_klaviyo(
            user_id=user_id,
            account=account,
            token=token,
            encrypted_tokens=encrypted_tokens
        )
        
        # Store connection info in user's integrations
        integration_data = {
            "service": "klaviyo",
            "connected_at": datetime.utcnow(),
            "token_secret_id": oauth_secret_id,
            "status": "connected",
            "expires_at": token.expires_at,
            "account_id": account.id,
            "account_name": account.name,
            "client_id": client.client_id,
            "scope": token.scope
        }
        
        db.collection("users").document(user_id).collection("integrations").document("klaviyo").set(integration_data)
        
        # Emit event for real-time updates
        await emit_client_event(client.client_id, "created_or_updated")
        
        logger.info(f"Successfully connected Klaviyo account {account.id} for user {user_id}, created/updated client {client.client_id}")
        
        # Redirect back to admin clients with success indicator
        redirect_path = state_data.get("redirect_path", "/admin/clients")
        return RedirectResponse(
            url=f"{redirect_path}?connected=klaviyo&client_id={client.client_id}",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Klaviyo OAuth callback failed: {e}")
        return RedirectResponse(
            url="/admin/clients?error=callback_failed&message=" + str(e),
            status_code=302
        )
    finally:
        # Clean up OAuth service
        await service.close()


@router.post("/oauth/refresh/{client_id}")
async def refresh_klaviyo_token(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
    service: KlaviyoOAuthService = Depends(get_klaviyo_oauth_service),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """
    Refresh OAuth tokens for a client
    
    Args:
        client_id: Client ID to refresh tokens for
    
    Returns:
        Success status
    """
    try:
        # Get client
        clients_repo = ClientsRepository(db)
        client = await clients_repo.get_client(client_id)
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Verify ownership
        user_id = current_user.get("email") or current_user.get("id")
        if client.owner_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to refresh this client's tokens")
        
        # Get encrypted refresh token
        if not client.oauth or not client.oauth.get("refresh_token"):
            raise HTTPException(status_code=400, detail="No refresh token available")
        
        # Decrypt refresh token
        crypto_service = get_crypto_service()
        refresh_token = crypto_service.decrypt(client.oauth["refresh_token"])
        
        # Refresh token
        new_token = await service.refresh_token(refresh_token)
        
        # Encrypt new tokens
        encrypted_tokens = {
            "access_token": crypto_service.encrypt(new_token.access_token),
            "refresh_token": crypto_service.encrypt(new_token.refresh_token) if new_token.refresh_token else client.oauth["refresh_token"]
        }
        
        # Update tokens in repository
        success = await clients_repo.update_oauth_tokens(
            client_id,
            encrypted_tokens,
            new_token.expires_at
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update tokens")
        
        # Update Secret Manager
        oauth_secret_id = f"oauth-klaviyo-{user_id.replace('@', '-').replace('.', '-')}-{client.klaviyo['account_id']}"
        oauth_data = {
            "access_token": new_token.access_token,
            "refresh_token": new_token.refresh_token or refresh_token,
            "expires_at": new_token.expires_at.isoformat() if new_token.expires_at else None,
            "scope": new_token.scope,
            "account_id": client.klaviyo["account_id"],
            "account_name": client.klaviyo["account_name"],
            "refreshed_at": datetime.utcnow().isoformat()
        }
        secret_manager.create_or_update_secret(oauth_secret_id, json.dumps(oauth_data))
        
        logger.info(f"Successfully refreshed tokens for client {client_id}")
        
        return {"success": True, "message": "Tokens refreshed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh tokens for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await service.close()


@router.get("/status")
async def get_klaviyo_oauth_status(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db)
):
    """
    Get Klaviyo OAuth connection status for current user
    
    Returns:
        Connection status and linked accounts
    """
    try:
        user_id = current_user.get("email") or current_user.get("id")
        
        # Check for Klaviyo integration
        integration_doc = db.collection("users").document(user_id).collection("integrations").document("klaviyo").get()
        
        if not integration_doc.exists:
            return {
                "connected": False,
                "accounts": []
            }
        
        integration_data = integration_doc.to_dict()
        
        # Get linked clients
        clients_repo = ClientsRepository(db)
        clients = await clients_repo.list_clients(user_id=user_id, source="klaviyo")
        
        return {
            "connected": True,
            "connection_date": integration_data.get("connected_at"),
            "expires_at": integration_data.get("expires_at"),
            "accounts": [
                {
                    "client_id": client.client_id,
                    "account_id": client.klaviyo.get("account_id"),
                    "account_name": client.klaviyo.get("account_name"),
                    "status": client.status,
                    "created_at": client.created_at
                }
                for client in clients
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get Klaviyo OAuth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))