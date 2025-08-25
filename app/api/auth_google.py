"""
Google OAuth Authentication endpoints with Admin-only access
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from app.deps.firestore import get_db
from app.core.settings import get_settings, Settings
from app.services.secrets import SecretManagerService
from app.deps.secrets import get_secret_manager_service
from app.services.auth import (
    create_access_token, 
    get_admin_emails, 
    initialize_admin_user,
    create_session
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Google Authentication"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"

@router.get("/callback")
async def google_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Handle Google OAuth callback with Admin-only access"""
    
    # Handle error from Google
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(url="/?error=oauth_failed")
    
    if not code:
        logger.error("OAuth callback missing authorization code")
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Basic state validation (improve this in production with CSRF tokens)
    if state:
        # In production, validate state parameter against stored session state
        logger.info(f"OAuth callback with state: {state[:10]}...") # Log first 10 chars only
    
    # Get OAuth configuration from settings
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    redirect_uri = settings.google_oauth_redirect_uri
    
    if not client_id or not client_secret:
        logger.error("Google OAuth credentials not configured")
        return RedirectResponse(url="/?error=oauth_not_configured")
    
    try:
        logger.info("Step 1: Exchanging authorization code for tokens.")
        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
            logger.info(f"Step 2: Token response status code: {token_response.status_code}")
            token_response.raise_for_status()
            tokens = token_response.json()
            logger.info("Step 3: Successfully exchanged code for tokens.")
            
            # Get user info
            headers = {"Authorization": f"Bearer {tokens.get('access_token')}"}
            user_response = await client.get(GOOGLE_USERINFO, headers=headers)
            logger.info(f"Step 4: User info response status code: {user_response.status_code}")
            user_response.raise_for_status()
            user_info = user_response.json()
            logger.info("Step 5: Successfully retrieved user info.")
        
        user_email = user_info.get("email")
        if not user_email:
            logger.error("Step 6: No email found in Google user info.")
            return RedirectResponse(url="/?error=no_email")
        
        logger.info(f"Step 7: User email found: {user_email}")
        
        # Check if user is admin
        admin_emails = await get_admin_emails(db)
        logger.info(f"Step 8: Fetched admin emails: {admin_emails}")
        
        # If no admins exist, initialize first admin
        if not admin_emails:
            logger.info(f"Step 9: No admins found, initializing first admin: {user_email}")
            await initialize_admin_user(user_email, db)
            admin_emails = [user_email]
        
        if user_email not in admin_emails:
            logger.warning(f"Step 10: Non-admin user attempted login: {user_email}")
            return RedirectResponse(url="/?error=unauthorized&message=Admin access only")
        
        logger.info(f"Step 11: User is an authorized admin.")
        
        # Create JWT token (30 days for regular users)
        access_token = create_access_token(
            data={"sub": user_email, "role": "admin"},
            settings=settings,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        
        # Store session in Firestore
        session_id = await create_session(user_email, "admin", db, expires_hours=30*24)  # 30 days
        logger.info(f"Step 12: Created session with ID: {session_id}")
        
        # Update user information in Firestore
        user_doc = {
            "email": user_email,
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "google_id": user_info.get("sub", ""),
            "role": "admin",
            "last_login": datetime.now(),
            "session_id": session_id
        }
        
        # Upsert user
        db.collection("users").document(user_email).set(user_doc, merge=True)
        logger.info("Step 13: Upserted user document in Firestore.")
        
        # Instead of a redirect, return a simple HTML page with a script
        # to store the token and redirect on the client side.
        # This is a more robust way to handle the token after OAuth.
        html_content = f"""
        <html>
            <head>
                <title>Authenticating...</title>
            </head>
            <body>
                <p>Please wait while we redirect you...</p>
                <script>
                    // Store the session ID and token, then redirect.
                    localStorage.setItem('session_id', '{session_id}');
                    localStorage.setItem('access_token', '{access_token}');
                    window.location.href = '/';
                </script>
            </body>
        </html>
        """
        logger.info("Step 14: Returning HTML to client for final redirect.")
        return HTMLResponse(content=html_content)
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Google OAuth token exchange failed: {e.response.text}")
        return RedirectResponse(url="/?error=token_exchange_failed")
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        return RedirectResponse(url="/?error=authentication_failed")

@router.get("/login")
async def google_login_redirect(settings: Settings = Depends(get_settings)):
    """Redirect to Google OAuth login with state parameter"""
    
    client_id = settings.google_oauth_client_id
    redirect_uri = settings.google_oauth_redirect_uri
    
    if not client_id:
        logger.error("Google OAuth Client ID not configured")
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Generate state parameter for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # In production, store state in session or database for validation
    # For now, we'll log it for debugging
    logger.info(f"Generated OAuth state: {state[:10]}...")
    
    # Build Google OAuth URL with state
    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
        "&prompt=consent"
        f"&state={state}"
    )
    
    logger.info(f"Redirecting to Google OAuth with client_id: {client_id[:10]}...")
    return RedirectResponse(url=oauth_url)

@router.get("/me")
async def get_current_user(
    request: Request,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Get current user from session with enhanced validation"""
    try:
        # Get session from cookie or header
        session_id = request.cookies.get("session_id")
        token = None
        
        # Try to get from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_or_session = auth_header.split(" ")[1]
            # Check if it's a JWT token (contains dots) or session ID
            if "." in token_or_session:
                token = token_or_session
            else:
                session_id = token_or_session
        
        # If we have a JWT token, validate it
        if token:
            try:
                import jwt
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                user_email = payload.get("sub")
                user_role = payload.get("role", "user")
                
                # Get user data from Firestore
                user_doc = db.collection("users").document(user_email).get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                else:
                    # Create basic user data from JWT
                    user_data = {
                        "email": user_email,
                        "name": user_email.split("@")[0],
                        "role": user_role
                    }
                
                # Check if user is an admin
                is_admin = user_role == "admin"
                if not is_admin:
                    admin_doc = db.collection("admins").document(user_email).get()
                    if admin_doc.exists:
                        admin_data = admin_doc.to_dict()
                        is_admin = admin_data.get("is_active", False)
                
                return {
                    "email": user_email,
                    "name": user_data.get("name", ""),
                    "picture": user_data.get("picture", ""),
                    "role": "admin" if is_admin else "user",
                    "is_admin": is_admin
                }
                
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError:
                # Not a valid JWT, treat as session ID
                session_id = token
        
        if not session_id and not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # If we only have session_id, validate session using the auth service
        if session_id and not token:
            from app.services.auth import validate_session
            session_data = await validate_session(session_id, db)
            
            if not session_data:
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            
            # Get user data
            user_email = session_data.get("user_email")
            user_doc = db.collection("users").document(user_email).get()
            
            if not user_doc.exists:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_data = user_doc.to_dict()
            
            # Check if user is still an active admin
            is_admin = False
            admin_doc = db.collection("admins").document(user_email).get()
            if admin_doc.exists:
                admin_data = admin_doc.to_dict()
                is_admin = admin_data.get("is_active", False)
            
            # Return user data with current admin status
            return {
                "email": user_data.get("email"),
                "name": user_data.get("name", ""),
                "picture": user_data.get("picture", ""),
                "role": "admin" if is_admin else "user",
                "is_admin": is_admin,
                "session_id": session_id,
                "session_expires": session_data.get("expires_at"),
                "last_login": user_data.get("last_login")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login(
    credentials: dict,
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
):
    """Simple email/password login for development"""
    email = credentials.get("email", "").lower()
    password = credentials.get("password", "")
    
    # For development, accept any password for demo accounts
    demo_accounts = ["demo@emailpilot.ai", "admin@emailpilot.ai", "user@emailpilot.ai"]
    
    if email not in demo_accounts:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Determine role
    role = "admin" if "admin" in email else "user"
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": email, "role": role},
        settings=settings,
        expires_delta=timedelta(hours=24)
    )
    
    # Store/update user in Firestore
    user_doc = {
        "email": email,
        "name": email.split("@")[0].title(),
        "picture": "",
        "role": role,
        "last_login": datetime.now()
    }
    
    db.collection("users").document(email).set(user_doc, merge=True)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "name": user_doc["name"],
            "role": role,
            "is_admin": role == "admin"
        }
    }

@router.post("/guest")
async def guest_login(
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
):
    """Create a guest session"""
    import uuid
    
    # Generate guest ID
    guest_id = f"guest_{uuid.uuid4().hex[:8]}"
    email = f"{guest_id}@guest.emailpilot.ai"
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": email, "role": "guest"},
        settings=settings,
        expires_delta=timedelta(hours=1)  # Short-lived for guests
    )
    
    # Store guest user
    user_doc = {
        "email": email,
        "name": f"Guest User",
        "picture": "",
        "role": "guest",
        "is_guest": True,
        "created_at": datetime.now()
    }
    
    db.collection("users").document(email).set(user_doc)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "name": user_doc["name"],
            "role": "guest",
            "is_admin": False,
            "is_guest": True
        }
    }

@router.post("/test-login")
async def test_login(
    email: str = "demo@emailpilot.ai",
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
):
    """Test login endpoint for development - creates a valid JWT token"""
    # Create JWT token
    access_token = create_access_token(
        data={"sub": email, "role": "admin"},
        settings=settings,
        expires_delta=timedelta(hours=24)
    )
    
    # Store user in Firestore if not exists
    user_doc = {
        "email": email,
        "name": email.split("@")[0].title(),
        "picture": "",
        "role": "admin",
        "last_login": datetime.now()
    }
    
    db.collection("users").document(email).set(user_doc, merge=True)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": email,
            "name": user_doc["name"],
            "role": "admin",
            "is_admin": True
        }
    }

@router.get("/status")
async def google_auth_status(settings: Settings = Depends(get_settings)):
    """Check Google OAuth configuration status"""
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    redirect_uri = settings.google_oauth_redirect_uri
    
    return {
        "configured": bool(client_id and client_secret),
        "client_id_set": bool(client_id),
        "client_secret_set": bool(client_secret),
        "redirect_uri": redirect_uri,
        "source": "settings"
    }

@router.post("/logout")
async def logout(
    request: Request,
    db: firestore.Client = Depends(get_db)
):
    """Logout user by clearing session and cookies"""
    try:
        # Get session from cookie or header
        session_id = request.cookies.get("session_id")
        auth_header = request.headers.get("Authorization")
        
        # Clear session from Firestore if we have a session_id
        if session_id:
            try:
                # Delete session from Firestore
                sessions_ref = db.collection("sessions")
                session_doc = sessions_ref.document(session_id).get()
                if session_doc.exists:
                    sessions_ref.document(session_id).delete()
                    logger.info(f"Cleared session {session_id} from Firestore")
            except Exception as e:
                logger.warning(f"Failed to clear session from Firestore: {e}")
        
        # Create response
        response = JSONResponse({"message": "Logged out successfully"})
        
        # Clear cookies
        is_prod = False  # Adjust based on your environment detection
        cookie_kwargs = {
            "httponly": True,
            "secure": is_prod,
            "samesite": "lax"
        }
        
        response.delete_cookie("access_token", **cookie_kwargs)
        response.delete_cookie("session_id", **cookie_kwargs)
        
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        # Even if there's an error, still clear the cookies
        response = JSONResponse({"message": "Logged out"})
        response.delete_cookie("access_token")
        response.delete_cookie("session_id")
        return response

@router.post("/oauth-config")
async def update_oauth_config(
    request: Request,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """Update Google OAuth credentials in Secret Manager"""
    # This endpoint is likely for an admin UI, so we'll keep the secret_manager dependency here
    # for writing the secrets. But reading will be done through settings.
    
    session_id = request.cookies.get("session_id")
    auth_header = request.headers.get("Authorization")
    
    if not session_id and not auth_header:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        body = await request.json()
        client_id = body.get("client_id")
        client_secret = body.get("client_secret")
        redirect_uri = body.get("redirect_uri")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=400, detail="client_id and client_secret are required")
        
        # Use create_or_update_secret for better persistence
        secret_manager.create_or_update_secret("google-oauth-client-id", client_id)
        secret_manager.create_or_update_secret("google-oauth-client-secret", client_secret)
        if redirect_uri:
            secret_manager.create_or_update_secret("google-oauth-redirect-uri", redirect_uri)
        
        logger.info("Google OAuth credentials saved to Secret Manager")
        
        return {"status": "success", "message": "OAuth credentials updated"}
        
    except Exception as e:
        logger.error(f"Error updating OAuth config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update OAuth configuration: {str(e)}")
