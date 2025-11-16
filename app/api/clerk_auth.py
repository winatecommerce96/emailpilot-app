"""
Simple Clerk authentication for API endpoints
"""
import os
from typing import Optional
from fastapi import HTTPException, Header, status
from clerk_backend_api import Clerk

# Initialize Clerk client
clerk_client = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))


async def verify_clerk_session(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify Clerk session token from Authorization header.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        dict: User data from Clerk session

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        # Verify session with Clerk
        session = clerk_client.sessions.verify_token(token=token)

        # Get user information
        user = clerk_client.users.get(user_id=session.user_id)

        return {
            "user_id": user.id,
            "email": user.email_addresses[0].email_address if user.email_addresses else None,
            "session_id": session.id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
