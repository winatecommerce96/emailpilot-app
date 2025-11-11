"""
Modern Authentication API with Clerk integration
Supports multi-tenant, refresh tokens, and API keys
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import secrets
import hashlib
from pydantic import BaseModel, EmailStr
import httpx
import logging
from google.cloud import firestore

# Try to import Clerk, but make it optional
try:
    from clerk_backend_api import Clerk, models
    # In v4.0.0+, errors are in the models module
    ClerkAPIError = models.ClerkBaseError
    CLERK_AVAILABLE = True
except ImportError as e:
    Clerk = None
    ClerkAPIError = None
    CLERK_AVAILABLE = False
    logging.error(f"Clerk backend API import failed: {e}", exc_info=True)
    logging.warning("Clerk backend API not available. Install with: pip install clerk-backend-api")

from app.deps.firestore import get_db
from app.core.settings import get_settings, Settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication V2"])

# Security schemes
bearer_security = HTTPBearer(auto_error=False)
api_key_security = APIKeyHeader(name="X-API-Key", auto_error=False)

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    tenant_id: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TenantCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}

class APIKeyCreate(BaseModel):
    name: str
    scopes: Optional[list[str]] = ["read"]
    expires_in_days: Optional[int] = 90

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    tenant: Optional[Dict[str, Any]] = None

# Clerk client initialization
def get_clerk_client(settings: Settings) -> Optional[Clerk]:
    """Initialize Clerk client if configured"""
    if not CLERK_AVAILABLE:
        return None
    
    clerk_secret_key = settings.clerk_secret_key if hasattr(settings, 'clerk_secret_key') else None
    
    if clerk_secret_key and Clerk:
        return Clerk(bearer_auth=clerk_secret_key)
    return None

# Token management
def create_tokens(
    user_data: Dict[str, Any],
    tenant_id: Optional[str] = None,
    settings: Settings = None
) -> tuple[str, str]:
    """Create access and refresh tokens with tenant support"""
    # Access token payload
    access_payload = {
        "sub": user_data["email"],
        "user_id": user_data.get("id", user_data["email"]),
        "role": user_data.get("role", "user"),
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(minutes=15),  # Short-lived access token
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    # Refresh token payload
    refresh_payload = {
        "sub": user_data["email"],
        "user_id": user_data.get("id", user_data["email"]),
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(days=30),  # Long-lived refresh token
        "iat": datetime.utcnow(),
        "type": "refresh",
        "token_id": secrets.token_urlsafe(16)  # Unique ID for revocation
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
    """Verify JWT token or API key with multi-tenant support"""
    
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
        
        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check if token is revoked
        if is_token_revoked(payload.get("sub"), db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Get user data with tenant info
        user_data = get_user_with_tenant(payload.get("sub"), payload.get("tenant_id"), db)
        
        return user_data
        
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
    """Verify API key and return associated user/tenant data"""
    # Hash the API key for storage
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Look up API key in Firestore
    api_key_doc = db.collection("api_keys").where("key_hash", "==", key_hash).limit(1).get()
    
    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    key_data = api_key_doc[0].to_dict()
    
    # Check expiration
    if key_data.get("expires_at") and key_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    # Update last used timestamp
    db.collection("api_keys").document(api_key_doc[0].id).update({
        "last_used": datetime.utcnow(),
        "usage_count": firestore.Increment(1)
    })
    
    # Return user data with API key context
    return {
        "user_id": key_data["user_id"],
        "email": key_data["user_email"],
        "tenant_id": key_data.get("tenant_id"),
        "role": "api_key",
        "scopes": key_data.get("scopes", ["read"]),
        "api_key_name": key_data["name"]
    }

def is_token_revoked(user_email: str, db: firestore.Client) -> bool:
    """Check if user's tokens have been revoked"""
    revocation_doc = db.collection("token_revocations").document(user_email).get()
    
    if revocation_doc.exists:
        revocation_data = revocation_doc.to_dict()
        # All tokens issued before this timestamp are considered revoked
        revoked_before = revocation_data.get("revoked_before")
        if revoked_before:
            return True
    
    return False

def get_user_with_tenant(email: str, tenant_id: Optional[str], db: firestore.Client) -> Dict[str, Any]:
    """Get user data with tenant information"""
    # Get user document
    user_doc = db.collection("users").document(email).get()
    
    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_data = user_doc.to_dict()
    
    # Get tenant data if tenant_id is provided
    tenant_data = None
    if tenant_id:
        tenant_doc = db.collection("tenants").document(tenant_id).get()
        if tenant_doc.exists:
            tenant_data = tenant_doc.to_dict()
            # Check if user has access to this tenant
            if email not in tenant_data.get("members", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this tenant"
                )
    
    return {
        **user_data,
        "tenant": tenant_data,
        "tenant_id": tenant_id
    }

# Endpoints

@router.post("/auth/clerk/callback")
async def clerk_callback(
    request: Request,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Handle Clerk webhook callbacks for user management"""
    clerk = get_clerk_client(settings)
    
    if not clerk:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clerk is not configured"
        )
    
    try:
        # Parse Clerk webhook
        body = await request.json()
        event_type = body.get("type")
        data = body.get("data")
        
        if event_type == "user.created":
            # Sync new user to Firestore
            user_data = {
                "clerk_id": data["id"],
                "email": data["email_addresses"][0]["email_address"],
                "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                "picture": data.get("image_url", ""),
                "created_at": datetime.utcnow(),
                "role": "user"
            }
            
            db.collection("users").document(user_data["email"]).set(user_data)
            logger.info(f"Synced Clerk user: {user_data['email']}")
            
        elif event_type == "user.updated":
            # Update existing user
            email = data["email_addresses"][0]["email_address"]
            updates = {
                "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                "picture": data.get("image_url", ""),
                "updated_at": datetime.utcnow()
            }
            
            db.collection("users").document(email).update(updates)
            logger.info(f"Updated Clerk user: {email}")
            
        elif event_type == "user.deleted":
            # Mark user as deleted (soft delete)
            email = data["email_addresses"][0]["email_address"]
            db.collection("users").document(email).update({
                "deleted_at": datetime.utcnow(),
                "is_active": False
            })
            logger.info(f"Soft deleted Clerk user: {email}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Clerk webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Enhanced login with Clerk fallback and multi-tenant support"""
    
    # Try Clerk authentication first
    clerk = get_clerk_client(settings)
    user_data = None
    
    if clerk:
        try:
            # Authenticate with Clerk
            sessions = clerk.sessions.list(email=request.email)
            if sessions and sessions.data:
                # User exists in Clerk
                user = sessions.data[0].user
                user_data = {
                    "id": user.id,
                    "email": request.email,
                    "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                    "picture": user.image_url or "",
                    "role": "user"
                }
        except Exception as e:
            if ClerkAPIError and isinstance(e, ClerkAPIError):
                logger.warning(f"Clerk authentication failed: {e}")
            else:
                logger.warning(f"Authentication error: {e}")
    
    # Fallback to local authentication
    if not user_data:
        # Check local database
        user_doc = db.collection("users").document(request.email).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_data = user_doc.to_dict()
        
        # In production, verify password hash
        # For now, we'll accept any password for demo accounts
        demo_accounts = ["demo@emailpilot.ai", "admin@emailpilot.ai"]
        if request.email not in demo_accounts:
            # Here you would verify the actual password hash
            pass
    
    # Check tenant access if tenant_id provided
    tenant_data = None
    if request.tenant_id:
        tenant_doc = db.collection("tenants").document(request.tenant_id).get()
        if not tenant_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        tenant_data = tenant_doc.to_dict()
        if request.email not in tenant_data.get("members", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    
    # Create tokens
    access_token, refresh_token = create_tokens(user_data, request.tenant_id, settings)
    
    # Store refresh token
    db.collection("refresh_tokens").document(refresh_token[-10:]).set({
        "user_email": request.email,
        "tenant_id": request.tenant_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    })
    
    # Update last login
    db.collection("users").document(request.email).update({
        "last_login": datetime.utcnow()
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,  # 15 minutes
        user=user_data,
        tenant=tenant_data
    )

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Refresh access token using refresh token"""
    try:
        # Decode refresh token
        payload = jwt.decode(request.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token exists and is valid
        token_id = request.refresh_token[-10:]
        token_doc = db.collection("refresh_tokens").document(token_id).get()
        
        if not token_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired"
            )
        
        token_data = token_doc.to_dict()
        
        # Get user data
        user_data = get_user_with_tenant(payload["sub"], payload.get("tenant_id"), db)
        
        # Create new tokens
        new_access_token, new_refresh_token = create_tokens(
            user_data,
            payload.get("tenant_id"),
            settings
        )
        
        # Replace old refresh token with new one
        db.collection("refresh_tokens").document(token_id).delete()
        db.collection("refresh_tokens").document(new_refresh_token[-10:]).set({
            "user_email": payload["sub"],
            "tenant_id": payload.get("tenant_id"),
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)
        })
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=900,
            user=user_data,
            tenant=user_data.get("tenant")
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/auth/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Register new user with optional Clerk integration"""
    
    # Check if user already exists
    existing_user = db.collection("users").document(request.email).get()
    if existing_user.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Try to create user in Clerk first
    clerk = get_clerk_client(settings)
    clerk_user_id = None
    
    if clerk:
        try:
            clerk_user = clerk.users.create(
                email_address=[request.email],
                password=request.password,
                first_name=request.name.split()[0] if request.name else "",
                last_name=" ".join(request.name.split()[1:]) if len(request.name.split()) > 1 else ""
            )
            clerk_user_id = clerk_user.id
        except Exception as e:
            if ClerkAPIError and isinstance(e, ClerkAPIError):
                logger.warning(f"Failed to create Clerk user: {e}")
            else:
                logger.warning(f"Failed to create user: {e}")
    
    # Create user in Firestore
    user_data = {
        "email": request.email,
        "name": request.name,
        "company": request.company,
        "role": "user",
        "clerk_id": clerk_user_id,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    # Hash password for local storage (in production)
    # from passlib.context import CryptContext
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # user_data["password_hash"] = pwd_context.hash(request.password)
    
    db.collection("users").document(request.email).set(user_data)
    
    # Handle tenant creation/assignment
    tenant_data = None
    if request.tenant_id:
        # Join existing tenant
        tenant_doc = db.collection("tenants").document(request.tenant_id).get()
        if tenant_doc.exists:
            tenant_data = tenant_doc.to_dict()
            members = tenant_data.get("members", [])
            if request.email not in members:
                members.append(request.email)
                db.collection("tenants").document(request.tenant_id).update({
                    "members": members
                })
    elif request.company:
        # Create new tenant for the company
        tenant_id = request.company.lower().replace(" ", "-")
        tenant_data = {
            "id": tenant_id,
            "name": request.company,
            "owner": request.email,
            "members": [request.email],
            "created_at": datetime.utcnow(),
            "settings": {}
        }
        db.collection("tenants").document(tenant_id).set(tenant_data)
        request.tenant_id = tenant_id
    
    # Create tokens
    access_token, refresh_token = create_tokens(user_data, request.tenant_id, settings)
    
    # Store refresh token
    db.collection("refresh_tokens").document(refresh_token[-10:]).set({
        "user_email": request.email,
        "tenant_id": request.tenant_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
        user=user_data,
        tenant=tenant_data
    )

@router.post("/auth/logout")
async def logout(
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """Logout user and revoke tokens"""
    
    # Revoke all tokens for this user
    db.collection("token_revocations").document(current_user["email"]).set({
        "revoked_before": datetime.utcnow(),
        "revoked_by": current_user["email"]
    })
    
    # Delete refresh tokens
    refresh_tokens = db.collection("refresh_tokens").where("user_email", "==", current_user["email"]).get()
    for token_doc in refresh_tokens:
        token_doc.reference.delete()
    
    return {"message": "Logged out successfully"}

@router.get("/auth/me")
async def get_current_user(current_user: Dict = Depends(verify_token)):
    """Get current authenticated user with tenant info"""
    return current_user

@router.get("/clerk-config")
async def get_clerk_config(settings: Settings = Depends(get_settings)):
    """Get Clerk configuration for frontend"""
    return {
        "publishable_key": settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else None,
        "environment": "development",
        "configured": bool(settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else False)
    }

@router.post("/auth/api-keys", response_model=Dict[str, Any])
async def create_api_key(
    request: APIKeyCreate,
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """Create new API key for authenticated user"""
    
    # Generate API key
    api_key = f"ek_{'live' if current_user.get('tenant_id') else 'test'}_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Store API key
    key_data = {
        "name": request.name,
        "key_hash": key_hash,
        "key_prefix": api_key[:12],  # Store prefix for identification
        "user_id": current_user.get("user_id", current_user["email"]),
        "user_email": current_user["email"],
        "tenant_id": current_user.get("tenant_id"),
        "scopes": request.scopes,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "last_used": None,
        "usage_count": 0
    }
    
    doc_ref = db.collection("api_keys").add(key_data)[1]
    
    return {
        "id": doc_ref.id,
        "api_key": api_key,  # Only returned once
        "name": request.name,
        "scopes": request.scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "message": "Store this API key securely. It won't be shown again."
    }

@router.get("/auth/api-keys")
async def list_api_keys(
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """List user's API keys (without revealing the actual keys)"""
    
    keys = db.collection("api_keys").where("user_email", "==", current_user["email"]).get()
    
    return [
        {
            "id": key.id,
            "name": key.to_dict()["name"],
            "key_prefix": key.to_dict()["key_prefix"],
            "scopes": key.to_dict()["scopes"],
            "created_at": key.to_dict()["created_at"],
            "expires_at": key.to_dict().get("expires_at"),
            "last_used": key.to_dict().get("last_used"),
            "usage_count": key.to_dict().get("usage_count", 0)
        }
        for key in keys
    ]

@router.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """Revoke an API key"""
    
    # Get the API key document
    key_doc = db.collection("api_keys").document(key_id).get()
    
    if not key_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    key_data = key_doc.to_dict()
    
    # Verify ownership
    if key_data["user_email"] != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own API keys"
        )
    
    # Delete the API key
    db.collection("api_keys").document(key_id).delete()
    
    return {"message": "API key revoked successfully"}

@router.post("/tenants", response_model=Dict[str, Any])
async def create_tenant(
    request: TenantCreate,
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """Create new tenant (organization)"""
    
    # Generate tenant ID
    tenant_id = request.name.lower().replace(" ", "-")
    
    # Check if tenant already exists
    existing = db.collection("tenants").document(tenant_id).get()
    if existing.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this name already exists"
        )
    
    # Create tenant
    tenant_data = {
        "id": tenant_id,
        "name": request.name,
        "domain": request.domain,
        "owner": current_user["email"],
        "members": [current_user["email"]],
        "settings": request.settings or {},
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    db.collection("tenants").document(tenant_id).set(tenant_data)
    
    return tenant_data

@router.get("/tenants")
async def list_user_tenants(
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db)
):
    """List tenants user has access to"""
    
    tenants = db.collection("tenants").where("members", "array_contains", current_user["email"]).get()
    
    return [
        {
            "id": tenant.id,
            **tenant.to_dict()
        }
        for tenant in tenants
    ]

@router.post("/tenants/{tenant_id}/switch")
async def switch_tenant(
    tenant_id: str,
    current_user: Dict = Depends(verify_token),
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Switch to a different tenant"""
    
    # Verify user has access to the tenant
    tenant_doc = db.collection("tenants").document(tenant_id).get()
    
    if not tenant_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant_data = tenant_doc.to_dict()
    
    if current_user["email"] not in tenant_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )
    
    # Create new tokens for the tenant
    access_token, refresh_token = create_tokens(current_user, tenant_id, settings)
    
    # Store refresh token
    db.collection("refresh_tokens").document(refresh_token[-10:]).set({
        "user_email": current_user["email"],
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
        user=current_user,
        tenant=tenant_data
    )

# SSO Endpoints

@router.get("/auth/sso/clerk")
async def clerk_sso_redirect(
    tenant_id: Optional[str] = None,
    settings: Settings = Depends(get_settings)
):
    """Redirect to Clerk SSO login"""
    
    # The publishable key contains the frontend API domain
    clerk_publishable_key = settings.clerk_frontend_api if hasattr(settings, 'clerk_frontend_api') else None
    
    if not clerk_publishable_key:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clerk SSO is not configured. NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY not found in Secret Manager."
        )
    
    # Extract domain from publishable key (format: pk_test_XXX.clerk.accounts.dev)
    # The publishable key format is pk_[test|live]_[subdomain].clerk.accounts.[dev|com]
    if clerk_publishable_key.startswith('pk_'):
        parts = clerk_publishable_key.split('_', 2)
        if len(parts) >= 3:
            domain_part = parts[2].split('.')[0]
            env = 'dev' if 'test' in clerk_publishable_key else 'com'
            clerk_domain = f"{domain_part}.clerk.accounts.{env}"
        else:
            # Fallback to a default pattern
            clerk_domain = "your-app.clerk.accounts.dev"
    else:
        # If it's already a domain (for backward compatibility)
        clerk_domain = clerk_publishable_key
    
    # Build Clerk sign-in URL
    redirect_url = f"https://{clerk_domain}/sign-in"
    
    if tenant_id:
        redirect_url += f"?redirect_url=/api/auth/v2/auth/clerk/callback?tenant_id={tenant_id}"
    else:
        redirect_url += "?redirect_url=/api/auth/v2/auth/clerk/callback"
    
    return RedirectResponse(url=redirect_url)

@router.get("/auth/sso/google")
async def google_sso_redirect(
    tenant_id: Optional[str] = None,
    settings: Settings = Depends(get_settings)
):
    """Redirect to Google OAuth (keeping for backward compatibility)"""
    
    client_id = settings.google_oauth_client_id
    redirect_uri = settings.google_oauth_redirect_uri.replace("/auth/google/", "/auth/v2/auth/google/")
    
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured"
        )
    
    # Generate state with tenant_id
    import json
    import base64
    
    state_data = {
        "tenant_id": tenant_id,
        "nonce": secrets.token_urlsafe(16)
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    # Build Google OAuth URL
    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
        "&prompt=select_account"
        f"&state={state}"
    )
    
    return RedirectResponse(url=oauth_url)

@router.get("/auth/google/callback")
async def google_oauth_callback_v2(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Enhanced Google OAuth callback with tenant support"""
    
    if error:
        return RedirectResponse(url=f"/?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Decode state to get tenant_id
    import json
    import base64
    
    tenant_id = None
    if state:
        try:
            state_data = json.loads(base64.urlsafe_b64decode(state))
            tenant_id = state_data.get("tenant_id")
        except:
            pass
    
    # Exchange code for tokens (similar to existing implementation)
    # ... (reuse existing Google OAuth token exchange logic)
    
    # Create enhanced tokens with tenant support
    # ... (create tokens with tenant_id)
    
    # Redirect with tokens
    return RedirectResponse(url=f"/?auth=success&tenant={tenant_id or 'default'}")