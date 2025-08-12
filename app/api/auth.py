"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os

from app.core.config import settings

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
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
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
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
            
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
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": user
    }

@router.get("/me")
async def get_current_user(current_user: dict = Depends(verify_token)):
    """Get current user info"""
    return current_user

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