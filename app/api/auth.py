"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os

from app.core.settings import get_settings

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Simple authentication for now - you can enhance with Google OAuth later
DEMO_USERS = {
    "admin@emailpilot.ai": {
        "id": 1,
        "name": "Admin User",
        "role": "admin",
        "email": "admin@emailpilot.ai"
    },
    "user@emailpilot.ai": {
        "id": 2,
        "name": "Regular User", 
        "role": "user",
        "email": "user@emailpilot.ai"
    },
    "demo@emailpilot.ai": {
        "id": 3,
        "name": "Demo User",
        "role": "user", 
        "email": "demo@emailpilot.ai"
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=get_settings().access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_settings().secret_key, algorithm=get_settings().algorithm)
    return encoded_jwt

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify JWT token"""
    # Check if demo mode is enabled
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    
    if demo_mode and not credentials:
        # Return demo user when no credentials provided in demo mode
        return DEMO_USERS["demo@emailpilot.ai"]
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().algorithm])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        # Handle guest users (temporary users not in DEMO_USERS)
        if email.endswith("@guest.emailpilot.ai"):
            guest_id = email.split("@")[0]
            return {
                "id": guest_id,
                "name": "Guest User",
                "role": "guest",
                "email": email,
                "is_guest": True
            }
            
        if email not in DEMO_USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        return DEMO_USERS[email]
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.post("/login")
async def login(email: str, password: str = "demo"):
    """Simple login endpoint"""
    
    # Demo authentication - replace with real authentication
    if email not in DEMO_USERS or password != "demo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user = DEMO_USERS[email]
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_expire_minutes * 60,
        "user": user
    }

@router.post("/register")
async def register(email: str, password: str, name: str, company: str = ""):
    """Simple registration endpoint"""
    
    # For demo purposes, create a new user entry
    if email in DEMO_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Create new user
    new_user = {
        "id": len(DEMO_USERS) + 1,
        "name": name,
        "role": "user",
        "email": email,
        "company": company
    }
    
    # Add to demo users (in real app, save to database)
    DEMO_USERS[email] = new_user
    
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_expire_minutes * 60,
        "user": new_user
    }

@router.post("/guest")
async def guest_access():
    """Create guest session"""
    
    # Create a temporary guest user
    guest_id = f"guest_{datetime.utcnow().timestamp()}"
    guest_user = {
        "id": guest_id,
        "name": "Guest User",
        "role": "guest",
        "email": f"{guest_id}@guest.emailpilot.ai",
        "is_guest": True
    }
    
    access_token_expires = timedelta(minutes=60)  # Shorter expiry for guests
    access_token = create_access_token(
        data={"sub": guest_user["email"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 60 * 60,  # 1 hour
        "user": guest_user
    }

@router.get("/me")
async def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user info"""
    return current_user

@router.post("/google/callback")
async def google_demo_callback(user_data: dict):
    """Demo Google OAuth callback endpoint for development"""
    
    # Extract user info from request
    email = user_data.get("email", "").strip()
    name = user_data.get("name", "").strip()
    picture = user_data.get("picture", "")
    
    if not email or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and name are required"
        )
    
    # Check if user is admin
    admin_emails = {"damon@winatecommerce.com", "admin@emailpilot.ai"}
    is_admin = email in admin_emails
    
    # Check if user exists in demo users or create a new demo user
    if email in DEMO_USERS:
        user = DEMO_USERS[email]
        user["is_admin"] = is_admin
    else:
        # Create new demo user
        user = {
            "id": len(DEMO_USERS) + 1,
            "name": name,
            "role": "admin" if is_admin else "user",
            "email": email,
            "picture": picture,
            "is_admin": is_admin
        }
    
    # Create access token
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_expire_minutes * 60,
        "user": user
    }

@router.post("/logout")
async def logout():
    """Logout endpoint"""
    return {"message": "Logged out successfully"}

@router.get("/session")
async def get_session():
    """Get current session - supports demo mode"""
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    
    if demo_mode:
        return {
            "authenticated": True,
            "user": DEMO_USERS["demo@emailpilot.ai"],
            "demo_mode": True
        }
    else:
        return {
            "authenticated": False,
            "user": None,
            "demo_mode": False
        }