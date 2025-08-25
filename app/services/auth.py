"""
JWT Authentication Service for EmailPilot
Handles JWT token creation, verification, and admin role management
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.settings import Settings, get_settings
from app.deps.firestore import get_db
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def create_access_token(data: Dict[str, Any], settings: Settings, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with user data
    
    Args:
        data: Dictionary containing user data (email, role, etc.)
        settings: The application settings object.
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    try:
        secret_key = settings.secret_key
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=30)  # 30 days default
            
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.algorithm)
        
        logger.info(f"Created access token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Verify and decode a JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        settings: The application settings object.
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        secret_key = settings.secret_key
        
        payload = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
        
        # Check if token has required fields
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.PyJWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(current_user: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get the current authenticated user information
    
    Args:
        current_user: Token payload from verify_token
        
    Returns:
        User information dictionary
    """
    return {
        "email": current_user.get("sub"),
        "role": current_user.get("role", "user"),
        "authenticated": True,
        "expires_at": current_user.get("exp")
    }

async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Verify JWT token and ensure user has admin privileges
    
    Args:
        credentials: HTTP Bearer token credentials
        settings: Application settings
        
    Returns:
        User information if admin, raises exception otherwise
    """
    try:
        # Decode the token
        token = credentials.credentials
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Check if user has admin role
        role = payload.get("role", "user")
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return payload
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require admin role for access with real-time validation
    
    Args:
        current_user: Current user information
        
    Returns:
        Admin user information
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin" or not current_user.get("is_admin", False):
        logger.warning(f"Non-admin user attempted admin access: {current_user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def check_admin_status(email: str, db) -> bool:
    """
    Check if a user has active admin status
    
    Args:
        email: User's email address
        db: Firestore database client
        
    Returns:
        True if user is an active admin, False otherwise
    """
    try:
        admin_doc = db.collection("admins").document(email).get()
        if not admin_doc.exists:
            return False
            
        admin_data = admin_doc.to_dict()
        return admin_data.get("is_active", False)
        
    except Exception as e:
        logger.error(f"Error checking admin status for {email}: {e}")
        return False

async def get_admin_emails(db) -> List[str]:
    """
    Get list of admin emails from Firestore
    
    Args:
        db: Firestore database client
        
    Returns:
        List of admin email addresses
    """
    try:
        admins_ref = db.collection("admins")
        docs = admins_ref.stream()
        
        admin_emails = []
        for doc in docs:
            data = doc.to_dict()
            if data and data.get("email") and data.get("is_active", True):
                admin_emails.append(data["email"])
        
        logger.info(f"Retrieved {len(admin_emails)} admin emails")
        return admin_emails
        
    except Exception as e:
        logger.error(f"Error retrieving admin emails: {e}")
        return []

async def initialize_admin_user(email: str, db) -> bool:
    """
    Initialize the first admin user in Firestore
    
    Args:
        email: Admin email address
        db: Firestore database client
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if admin already exists
        admin_doc = db.collection("admins").document(email).get()
        if admin_doc.exists:
            logger.info(f"Admin user already exists: {email}")
            return True
        
        # Create admin document
        admin_data = {
            "email": email,
            "created_at": datetime.now(),
            "is_active": True,
            "created_by": "system"
        }
        
        db.collection("admins").document(email).set(admin_data)
        
        # Also create user document with admin role
        user_data = {
            "email": email,
            "role": "admin",
            "created_at": datetime.now(),
            "last_login": datetime.now(),
            "is_active": True
        }
        
        db.collection("users").document(email).set(user_data, merge=True)
        
        logger.info(f"Successfully initialized admin user: {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing admin user {email}: {e}")
        return False

async def create_session(user_email: str, role: str, db, expires_hours: int = 24) -> str:
    """
    Create a user session in Firestore
    
    Args:
        user_email: User's email address
        role: User's role (admin/user)
        db: Firestore database client
        expires_hours: Session expiration in hours
        
    Returns:
        Session ID
    """
    try:
        session_data = {
            "user_email": user_email,
            "role": role,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=expires_hours),
            "is_active": True
        }
        
        # Create session document
        session_ref = db.collection("sessions").add(session_data)
        session_id = session_ref[1].id
        
        logger.info(f"Created session for user: {user_email}")
        return session_id
        
    except Exception as e:
        logger.error(f"Error creating session for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )

async def validate_session(session_id: str, db) -> Optional[Dict[str, Any]]:
    """
    Validate a user session
    
    Args:
        session_id: Session identifier
        db: Firestore database client
        
    Returns:
        Session data if valid, None if invalid/expired
    """
    try:
        session_doc = db.collection("sessions").document(session_id).get()
        
        if not session_doc.exists:
            return None
            
        session_data = session_doc.to_dict()
        
        # Check if session is active and not expired
        if not session_data.get("is_active", False):
            return None
            
        expires_at = session_data.get("expires_at")
        if expires_at and expires_at < datetime.now(timezone.utc):
            # Mark session as expired
            db.collection("sessions").document(session_id).update({"is_active": False})
            return None
            
        return session_data
        
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {e}")
        return None