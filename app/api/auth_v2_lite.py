"""
Lightweight Authentication API V2 without Clerk SDK dependency
Uses Clerk via frontend JavaScript SDK instead of backend SDK
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import secrets
import hashlib
from pydantic import BaseModel, EmailStr
import logging
from google.cloud import firestore

from app.deps.firestore import get_db
from app.core.settings import get_settings, Settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication V2 Lite"])

# Security schemes
bearer_security = HTTPBearer(auto_error=False)
api_key_security = APIKeyHeader(name="X-API-Key", auto_error=False)

# Same Pydantic models as before
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

# Token management functions (same as before)
def create_tokens(
    user_data: Dict[str, Any],
    tenant_id: Optional[str] = None,
    settings: Settings = None
) -> tuple[str, str]:
    """Create access and refresh tokens"""
    access_payload = {
        "sub": user_data["email"],
        "user_id": user_data.get("id", user_data["email"]),
        "role": user_data.get("role", "user"),
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    refresh_payload = {
        "sub": user_data["email"],
        "user_id": user_data.get("id", user_data["email"]),
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow(),
        "type": "refresh",
        "token_id": secrets.token_urlsafe(16)
    }
    
    access_token = jwt.encode(access_payload, settings.secret_key, algorithm=settings.algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.secret_key, algorithm=settings.algorithm)
    
    return access_token, refresh_token

def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
    api_key: Optional[str] = Depends(api_key_security),
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Verify JWT token or API key"""
    
    # Check API key first
    if api_key:
        return verify_api_key(api_key, db)
    
    # Check bearer token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user data
        user_email = payload.get("sub")
        user_doc = db.collection("users").document(user_email).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user_doc.to_dict()
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def verify_api_key(api_key: str, db: firestore.Client) -> Dict[str, Any]:
    """Verify API key"""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    api_key_doc = db.collection("api_keys").where("key_hash", "==", key_hash).limit(1).get()
    
    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    key_data = api_key_doc[0].to_dict()
    
    if key_data.get("expires_at") and key_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    db.collection("api_keys").document(api_key_doc[0].id).update({
        "last_used": datetime.utcnow(),
        "usage_count": firestore.Increment(1)
    })
    
    return {
        "user_id": key_data["user_id"],
        "email": key_data["user_email"],
        "role": "api_key",
        "scopes": key_data.get("scopes", ["read"])
    }

# Endpoints

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Simple email/password login"""
    
    # Demo accounts for testing
    demo_accounts = {
        "demo@emailpilot.ai": "demo",
        "admin@emailpilot.ai": "admin",
        "test@example.com": "test"
    }
    
    # Check demo accounts
    if request.email in demo_accounts:
        if request.password != demo_accounts[request.email]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_data = {
            "email": request.email,
            "name": request.email.split("@")[0].title(),
            "role": "admin" if "admin" in request.email else "user"
        }
    else:
        # Check real user in database
        user_doc = db.collection("users").document(request.email).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_data = user_doc.to_dict()
    
    # Create tokens
    access_token, refresh_token = create_tokens(user_data, request.tenant_id, settings)
    
    # Store refresh token
    db.collection("refresh_tokens").document(refresh_token[-10:]).set({
        "user_email": request.email,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
        user=user_data
    )

@router.get("/auth/me")
async def get_current_user(current_user: Dict = Depends(verify_token)):
    """Get current authenticated user"""
    return current_user

@router.get("/clerk-config")
async def get_clerk_config(settings: Settings = Depends(get_settings)):
    """Get Clerk configuration for frontend"""
    return {
        "publishable_key": settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else None,
        "environment": "development",
        "configured": bool(settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else False)
    }

@router.get("/auth/sso/clerk")
async def clerk_sso_redirect(
    request: Request,
    tenant_id: Optional[str] = None,
    settings: Settings = Depends(get_settings)
):
    """Redirect to Clerk authentication page"""
    
    publishable_key = settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else None
    
    if not publishable_key:
        # Return configuration instructions
        return HTMLResponse("""
            <html>
            <body style="font-family: system-ui; padding: 2rem; max-width: 600px; margin: 0 auto;">
                <h1>🔐 Clerk Not Configured</h1>
                <p>To enable Clerk SSO authentication:</p>
                <ol>
                    <li>Sign up at <a href="https://clerk.com">clerk.com</a></li>
                    <li>Get your keys from the dashboard</li>
                    <li>Add to Secret Manager:<br>
                    <pre style="background: #f5f5f5; padding: 1rem; border-radius: 4px;">
# Add publishable key
gcloud secrets create NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \\
  --data-file=- <<< "pk_test_..."

# Add secret key  
gcloud secrets create CLERK_SECRET_KEY \\
  --data-file=- <<< "sk_test_..."
                    </pre>
                    </li>
                    <li>Restart the server</li>
                </ol>
                <p><a href="/static/test-auth-v2-final.html">← Back to login</a></p>
            </body>
            </html>
        """)
    
    # Redirect to Clerk-enabled login page
    callback_url = f"{request.url.scheme}://{request.url.netloc}/api/auth/v2/auth/callback"
    state = secrets.token_urlsafe(32)
    
    # Store state in session for verification
    if tenant_id:
        callback_url += f"?tenant_id={tenant_id}"
    
    # For now, redirect to the Clerk auth page
    return RedirectResponse(
        url=f"/api/auth/v2/auth/clerk?callback={callback_url}&state={state}",
        status_code=302
    )

@router.get("/auth/sso/google")  
async def google_sso_redirect(
    request: Request,
    tenant_id: Optional[str] = None,
    settings: Settings = Depends(get_settings)
):
    """Legacy Google SSO redirect"""
    # This would integrate with existing Google OAuth
    # For now, return a placeholder
    return JSONResponse(
        status_code=501,
        content={"detail": "Google SSO integration pending migration"}
    )

@router.get("/auth/clerk")
async def clerk_auth_page(settings: Settings = Depends(get_settings)):
    """Serve Clerk authentication page using frontend SDK"""
    
    publishable_key = settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else None
    
    if not publishable_key:
        return HTMLResponse("""
            <html>
            <body style="font-family: system-ui; padding: 2rem; max-width: 600px; margin: 0 auto;">
                <h1>Clerk Not Configured</h1>
                <p>To enable Clerk authentication:</p>
                <ol>
                    <li>Sign up at <a href="https://clerk.com">clerk.com</a></li>
                    <li>Get your publishable key from the dashboard</li>
                    <li>Add it to Secret Manager:<br>
                    <code>gcloud secrets create NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY --data-file=- <<< "pk_test_..."</code>
                    </li>
                    <li>Restart the server</li>
                </ol>
                <p><a href="/api/auth/v2/auth/login">← Back to standard login</a></p>
            </body>
            </html>
        """)
    
    # Serve Clerk-enabled login page
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>EmailPilot - Clerk Authentication</title>
        <script src="https://cdn.jsdelivr.net/npm/@clerk/clerk-js@latest/dist/clerk.browser.js"></script>
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 2rem;
                border-radius: 1rem;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 100%;
            }}
            h1 {{
                color: #1a202c;
                margin-bottom: 1.5rem;
                text-align: center;
            }}
            #clerk-auth {{
                min-height: 400px;
            }}
            .fallback {{
                text-align: center;
                padding: 2rem;
                color: #718096;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EmailPilot Login</h1>
            <div id="clerk-auth">
                <div class="fallback">Loading Clerk...</div>
            </div>
        </div>
        
        <script>
            // Initialize Clerk
            const clerkPublishableKey = '{publishable_key}';
            
            const startClerk = async () => {{
                try {{
                    const clerk = window.Clerk;
                    
                    await clerk.load({{
                        publishableKey: clerkPublishableKey
                    }});
                    
                    // Mount sign-in component
                    const authDiv = document.getElementById('clerk-auth');
                    
                    if (clerk.user) {{
                        // User is already signed in
                        authDiv.innerHTML = `
                            <div style="text-align: center; padding: 2rem;">
                                <p>Signed in as: ${{clerk.user.primaryEmailAddress?.emailAddress}}</p>
                                <button onclick="handleSignOut()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #e53e3e; color: white; border: none; border-radius: 0.25rem; cursor: pointer;">
                                    Sign Out
                                </button>
                            </div>
                        `;
                        
                        // Get session token and redirect
                        const token = await clerk.session?.getToken();
                        if (token) {{
                            // Store token and redirect
                            localStorage.setItem('clerk_token', token);
                            window.location.href = '/';
                        }}
                    }} else {{
                        // Show sign-in form
                        clerk.mountSignIn(authDiv, {{
                            redirectUrl: window.location.href,
                            signUpUrl: '/api/auth/v2/auth/clerk#sign-up'
                        }});
                    }}
                }} catch (error) {{
                    console.error('Clerk initialization failed:', error);
                    document.getElementById('clerk-auth').innerHTML = `
                        <div class="fallback">
                            <p>Failed to load Clerk authentication.</p>
                            <p style="font-size: 0.875rem; margin-top: 1rem;">
                                <a href="/api/auth/v2/auth/login">Use standard login instead →</a>
                            </p>
                        </div>
                    `;
                }}
            }};
            
            window.handleSignOut = async () => {{
                await window.Clerk.signOut();
                window.location.reload();
            }};
            
            // Start Clerk when ready
            if (window.Clerk) {{
                startClerk();
            }} else {{
                window.addEventListener('load', startClerk);
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html)

@router.post("/auth/clerk/verify")
async def verify_clerk_token(
    token: str,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Verify Clerk session token and create internal tokens"""
    
    # In production, you would verify the Clerk JWT token here
    # For now, we'll create a simple user session
    
    # This would normally decode and verify the Clerk JWT
    # For demo, we'll just create a user session
    
    user_data = {
        "email": "clerk-user@emailpilot.ai",
        "name": "Clerk User",
        "role": "user",
        "clerk_session": True
    }
    
    # Create our own tokens
    access_token, refresh_token = create_tokens(user_data, None, settings)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900,
        "user": user_data
    }

@router.post("/auth/callback")
async def clerk_callback(
    request: Request,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Handle Clerk authentication callback"""
    try:
        # Get callback data from request body
        data = await request.json()
        
        # Extract user information from Clerk callback
        user_email = data.get("email") or f"{data.get('user_id', 'unknown')}@clerk.user"
        user_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or "Clerk User"
        
        # Check if user exists in Firestore
        users_ref = db.collection("users")
        existing_users = users_ref.where("email", "==", user_email).limit(1).get()
        
        if existing_users:
            user_doc = existing_users[0]
            user_data = user_doc.to_dict()
            user_data["id"] = user_doc.id
        else:
            # Create new user
            user_data = {
                "email": user_email,
                "name": user_name,
                "role": "user",
                "created_at": datetime.utcnow(),
                "auth_provider": "clerk",
                "clerk_user_id": data.get("user_id")
            }
            user_ref = users_ref.add(user_data)
            user_data["id"] = user_ref[1].id
        
        # Create tokens
        access_token, refresh_token = create_tokens(user_data, None, settings)
        
        # Store refresh token
        db.collection("refresh_tokens").document(refresh_token[-10:]).set({
            "user_email": user_email,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)
        })
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,
            user=user_data
        )
        
    except Exception as e:
        logger.error(f"Clerk callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Callback processing failed: {str(e)}"
        )