from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from app.deps import get_db, get_secret_manager_service
from app.services.auth import get_current_user
from google.cloud import firestore
from app.core.settings import get_settings, Settings
from app.services.secrets import SecretManagerService
import httpx
import secrets
import json
import logging
import hashlib
import base64
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, quote

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for OAuth state (in production, use Redis or similar)
_oauth_states = {}

def generate_state() -> str:
    """Generate a secure random state parameter for CSRF protection"""
    return secrets.token_urlsafe(32)

def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge for OAuth 2.0"""
    # Generate a code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge using SHA256
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge

def store_state(state: str, user_email: str, service: str, code_verifier: Optional[str] = None) -> None:
    """Store OAuth state with user context and optional PKCE verifier"""
    _oauth_states[state] = {
        "user_email": user_email,
        "service": service,
        "created_at": datetime.utcnow(),
        "code_verifier": code_verifier  # Store for PKCE
    }

def verify_state(state: str) -> Optional[dict]:
    """Verify OAuth state and return user context"""
    return _oauth_states.pop(state, None)

async def store_oauth_token(
    user_email: str,
    service: str,
    token_data: dict,
    db: firestore.Client,
    secret_manager: SecretManagerService
) -> None:
    """Store OAuth tokens securely in Secret Manager and connection info in Firestore"""
    try:
        # Store tokens in Secret Manager
        secret_id = f"oauth-{service}-{user_email.replace('@', '-').replace('.', '-')}"
        secret_value = json.dumps(token_data)
        secret_manager.create_or_update_secret(secret_id, secret_value)
        
        # Store connection info in Firestore
        integration_data = {
            "service": service,
            "connected_at": datetime.utcnow(),
            "token_secret_id": secret_id,
            "status": "connected",
            "expires_at": token_data.get("expires_at") if token_data.get("expires_at") else None
        }
        
        # Add service-specific metadata
        if service == "asana" and token_data.get("data"):
            integration_data["user_id"] = token_data["data"].get("id")
            integration_data["user_name"] = token_data["data"].get("name")
            integration_data["user_email"] = token_data["data"].get("email")
        elif service == "klaviyo":
            integration_data["scope"] = token_data.get("scope")
        
        db.collection("users").document(user_email).collection("integrations").document(service).set(integration_data)
        logger.info(f"Stored {service} OAuth token for user {user_email}")
        
    except Exception as e:
        logger.error(f"Failed to store {service} OAuth token for {user_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store {service} credentials")

# ==============================================================================
# Asana OAuth Flow
# ==============================================================================

@router.get("/asana/auth")
async def asana_auth(
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """Initiate Asana OAuth flow"""
    if not settings.asana_client_id:
        raise HTTPException(status_code=500, detail="Asana client ID is not configured")
    
    state = generate_state()
    store_state(state, current_user["email"], "asana")
    
    # Asana OAuth scopes - omit scope parameter entirely to use app defaults
    # Or use 'default' which should work for most apps
    # If your app needs specific scopes, they must be configured in Asana Developer Console
    
    params = {
        "client_id": settings.asana_client_id,
        "redirect_uri": settings.asana_redirect_uri,
        "response_type": "code",
        "state": state
    }
    # Omitting scope parameter to use app's default scopes configured in Asana
    
    authorization_url = f"https://app.asana.com/-/oauth_authorize?{urlencode(params)}"
    return {"authorization_url": authorization_url}

@router.get("/asana/callback")
async def asana_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """Handle Asana OAuth callback"""
    try:
        # Check for OAuth errors or missing parameters
        if error or (not code or not state):
            error_msg = error or "authorization_cancelled"
            error_detail = error_description or "Authorization was denied or cancelled"
            logger.warning(f"Asana OAuth error: {error_msg} - {error_detail}")
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            service: "asana",
                            error: "{error_msg}",
                            message: "{error_detail}"
                        }}, "*");
                    }}
                    window.close();
                </script>
                <p>Authorization failed: {error_detail}</p>
                <p>This window will close automatically.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_response)
        
        # Verify state parameter
        state_data = verify_state(state)
        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
        
        user_email = state_data["user_email"]
        
        if not settings.asana_client_id or not settings.asana_client_secret:
            raise HTTPException(status_code=500, detail="Asana credentials not configured")

        # Exchange code for access token
        token_url = "https://app.asana.com/-/oauth_token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.asana_client_id,
            "client_secret": settings.asana_client_secret,
            "redirect_uri": settings.asana_redirect_uri,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload)

        if response.status_code != 200:
            logger.error(f"Asana token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Failed to retrieve access token")

        token_data = response.json()
        
        # Store the tokens securely
        await store_oauth_token(user_email, "asana", token_data, db, secret_manager)
        
        # Return HTML response that communicates with parent window and closes popup
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Success</title></head>
        <body>
            <script>
                console.log('Asana OAuth success, sending postMessage...');
                if (window.opener) {{
                    // Send to any origin since we're in a popup context
                    window.opener.postMessage({{
                        success: true,
                        service: "asana",
                        message: "Asana connected successfully",
                        close_popup: true
                    }}, "*");
                    console.log('PostMessage sent to opener');
                }}
                setTimeout(() => window.close(), 500);
            </script>
            <p>Authorization successful! This window will close automatically.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asana OAuth callback error: {e}")
        html_response = """
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <script>
                if (window.opener) {
                    window.opener.postMessage({
                        success: false,
                        service: "asana",
                        error: "oauth_error",
                        message: "Failed to complete Asana authorization"
                    }, "*");
                }
                window.close();
            </script>
            <p>Authorization failed due to an internal error.</p>
            <p>This window will close automatically.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response, status_code=500)

@router.get("/asana/status")
async def asana_status(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db)
):
    """Check Asana connection status"""
    try:
        user_email = current_user["email"]
        integration_doc = db.collection("users").document(user_email).collection("integrations").document("asana").get()
        
        if not integration_doc.exists:
            return {
                "connected": False,
                "service": "asana"
            }
        
        integration_data = integration_doc.to_dict()
        return {
            "connected": integration_data.get("status") == "connected",
            "service": "asana",
            "connected_at": integration_data.get("connected_at"),
            "user_name": integration_data.get("user_name"),
            "user_email": integration_data.get("user_email")
        }
        
    except Exception as e:
        logger.error(f"Error checking Asana status for {current_user['email']}: {e}")
        return {
            "connected": False,
            "service": "asana",
            "error": "Failed to check connection status"
        }

@router.post("/asana/disconnect")
async def asana_disconnect(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """Disconnect Asana integration"""
    try:
        user_email = current_user["email"]
        
        # Get integration data to find secret ID
        integration_doc = db.collection("users").document(user_email).collection("integrations").document("asana").get()
        
        if integration_doc.exists:
            integration_data = integration_doc.to_dict()
            secret_id = integration_data.get("token_secret_id")
            
            # Delete from Secret Manager
            if secret_id:
                try:
                    secret_manager.delete_secret(secret_id)
                except Exception as e:
                    logger.warning(f"Failed to delete secret {secret_id}: {e}")
            
            # Delete from Firestore
            db.collection("users").document(user_email).collection("integrations").document("asana").delete()
        
        return {
            "success": True,
            "service": "asana",
            "message": "Asana disconnected successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Asana for {current_user['email']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Asana")

# ==============================================================================
# Klaviyo OAuth Flow
# ==============================================================================

@router.get("/klaviyo/auth")
async def klaviyo_auth(
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """Initiate Klaviyo OAuth flow with PKCE"""
    if not settings.klaviyo_client_id:
        raise HTTPException(status_code=500, detail="Klaviyo client ID is not configured")
    
    state = generate_state()
    # Generate PKCE parameters for Klaviyo
    code_verifier, code_challenge = generate_pkce_pair()
    store_state(state, current_user["email"], "klaviyo", code_verifier)
    
    # Klaviyo OAuth scopes - optimized for EmailPilot's campaign management needs
    # Read access for analytics/reporting, write access for campaign/flow automation
    # Added accounts:read for discovering user's Klaviyo accounts
    scope = "accounts:read campaigns:read campaigns:write flows:read flows:write metrics:read profiles:read templates:read lists:read"
    
    params = {
        "client_id": settings.klaviyo_client_id,
        "redirect_uri": settings.klaviyo_redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"  # SHA256 method for PKCE
    }
    
    authorization_url = f"https://www.klaviyo.com/oauth/authorize?{urlencode(params)}"
    return {"authorization_url": authorization_url}

@router.get("/klaviyo/callback")
async def klaviyo_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """Handle Klaviyo OAuth callback"""
    try:
        # Check for OAuth errors or missing parameters
        if error or (not code or not state):
            error_msg = error or "authorization_cancelled"
            error_detail = error_description or "Authorization was denied or cancelled"
            logger.warning(f"Klaviyo OAuth error: {error_msg} - {error_detail}")
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            success: false,
                            service: "klaviyo",
                            error: "{error_msg}",
                            message: "{error_detail}"
                        }}, "*");
                    }}
                    window.close();
                </script>
                <p>Authorization failed: {error_detail}</p>
                <p>This window will close automatically.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_response)
        
        # Verify state parameter
        state_data = verify_state(state)
        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
        
        user_email = state_data["user_email"]
        code_verifier = state_data.get("code_verifier")  # Get PKCE verifier
        
        if not settings.klaviyo_client_id or not settings.klaviyo_client_secret:
            raise HTTPException(status_code=500, detail="Klaviyo credentials not configured")

        # Exchange code for access token with PKCE
        token_url = "https://a.klaviyo.com/oauth/token"
        
        # Klaviyo requires Basic Auth with client credentials in header, NOT in body
        auth_string = f"{settings.klaviyo_client_id}:{settings.klaviyo_client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8'))
        auth_header = f"Basic {auth_bytes.decode('utf-8')}"
        
        payload = {
            "grant_type": "authorization_code",
            "redirect_uri": settings.klaviyo_redirect_uri,
            "code": code,
            "code_verifier": code_verifier  # Include PKCE verifier
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": auth_header
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Klaviyo token exchange failed with status {response.status_code}: {response.text}")
            logger.error(f"Request payload: {payload}")
            logger.error(f"Request headers: {dict(headers)}")
            
            # Provide more specific error details
            try:
                error_data = response.json()
                error_detail = error_data.get('error', 'Unknown error')
                error_description = error_data.get('error_description', 'No description available')
                raise HTTPException(
                    status_code=400, 
                    detail=f"Klaviyo OAuth error: {error_detail} - {error_description}"
                )
            except Exception:
                raise HTTPException(status_code=400, detail="Failed to retrieve access token")

        token_data = response.json()
        
        # Store the tokens securely
        await store_oauth_token(user_email, "klaviyo", token_data, db, secret_manager)
        
        # Return HTML response that communicates with parent window and closes popup
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Success</title></head>
        <body>
            <script>
                console.log('Klaviyo OAuth success, sending postMessage...');
                if (window.opener) {{
                    // Send to any origin since we're in a popup context
                    window.opener.postMessage({{
                        success: true,
                        service: "klaviyo", 
                        message: "Klaviyo connected successfully",
                        close_popup: true
                    }}, "*");
                    console.log('PostMessage sent to opener');
                }}
                setTimeout(() => window.close(), 500);
            </script>
            <p>Authorization successful! This window will close automatically.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Klaviyo OAuth callback error: {e}")
        html_response = """
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <script>
                if (window.opener) {
                    window.opener.postMessage({
                        success: false,
                        service: "klaviyo",
                        error: "oauth_error", 
                        message: "Failed to complete Klaviyo authorization"
                    }, "*");
                }
                window.close();
            </script>
            <p>Authorization failed due to an internal error.</p>
            <p>This window will close automatically.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_response, status_code=500)

@router.get("/klaviyo/status")
async def klaviyo_status(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db)
):
    """Check Klaviyo connection status"""
    try:
        user_email = current_user["email"]
        integration_doc = db.collection("users").document(user_email).collection("integrations").document("klaviyo").get()
        
        if not integration_doc.exists:
            return {
                "connected": False,
                "service": "klaviyo"
            }
        
        integration_data = integration_doc.to_dict()
        return {
            "connected": integration_data.get("status") == "connected",
            "service": "klaviyo",
            "connected_at": integration_data.get("connected_at"),
            "scope": integration_data.get("scope")
        }
        
    except Exception as e:
        logger.error(f"Error checking Klaviyo status for {current_user['email']}: {e}")
        return {
            "connected": False,
            "service": "klaviyo",
            "error": "Failed to check connection status"
        }

@router.post("/klaviyo/disconnect")
async def klaviyo_disconnect(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """Disconnect Klaviyo integration"""
    try:
        user_email = current_user["email"]
        
        # Get integration data to find secret ID
        integration_doc = db.collection("users").document(user_email).collection("integrations").document("klaviyo").get()
        
        if integration_doc.exists:
            integration_data = integration_doc.to_dict()
            secret_id = integration_data.get("token_secret_id")
            
            # Delete from Secret Manager
            if secret_id:
                try:
                    secret_manager.delete_secret(secret_id)
                except Exception as e:
                    logger.warning(f"Failed to delete secret {secret_id}: {e}")
            
            # Delete from Firestore
            db.collection("users").document(user_email).collection("integrations").document("klaviyo").delete()
        
        return {
            "success": True,
            "service": "klaviyo",
            "message": "Klaviyo disconnected successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Klaviyo for {current_user['email']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Klaviyo")
