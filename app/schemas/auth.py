"""
Authentication-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class User(BaseModel):
    """User model for authentication responses"""
    id: int | str
    name: str
    email: str
    role: str = "user"

class AuthSession(BaseModel):
    """Session response model"""
    authenticated: bool
    user: Optional[User] = None
    demo_mode: Optional[bool] = False

class LoginRequest(BaseModel):
    """Login request model"""
    email: str = Field(..., description="User email address")
    password: str = Field(default="demo", description="Password")

class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User