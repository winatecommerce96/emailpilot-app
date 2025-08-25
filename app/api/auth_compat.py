"""
Compatibility shim for legacy auth endpoints under /api/auth

Bridges to Google OAuth implementation so existing frontend calls
like GET /api/auth/me and POST /api/auth/login continue to work.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google.cloud import firestore
from app.core.settings import get_settings, Settings
from app.deps.firestore import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import Google OAuth handlers to reuse logic
from app.api.auth_google import (
    get_current_user as google_get_current_user,
    google_login_redirect as google_login_redirect,
    login as google_login,
    guest_login as google_guest_login,
    logout as google_logout
)

router = APIRouter()


@router.get("/me")
async def me_compat(
    request: Request,
    db: firestore.Client = Depends(get_db),
    settings: Settings = Depends(get_settings)
):
    """Return current user info (delegates to Google OAuth handler)."""
    return await google_get_current_user(
        request=request,
        db=db,
        settings=settings
    )


@router.post("/login")
async def login_compat_post(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
):
    """Handle POST login with credentials or redirect to Google OAuth."""
    try:
        # Check if this is a JSON request with credentials
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            # Handle JSON login request
            body = await request.json()
            if "email" in body and "password" in body:
                # This is a credentials login
                return await google_login(
                    credentials=body,
                    settings=settings,
                    db=db
                )
        
        # For all other cases, redirect to Google OAuth login
        return RedirectResponse(url="/api/auth/google/login", status_code=307)
    except Exception as e:
        logger.error(f"Login error: {e}")
        # Still try to redirect even on error
        return RedirectResponse(url="/api/auth/google/login", status_code=307)

@router.get("/login")
async def login_compat_get(settings: Settings = Depends(get_settings)):
    """Initiate login (GET) — delegate to Google OAuth login."""
    return await google_login_redirect(settings)


@router.post("/logout")
async def logout_compat(
    request: Request,
    db: firestore.Client = Depends(get_db)
):
    """Logout by clearing auth cookies and session from Firestore."""
    return await google_logout(request=request, db=db)

@router.post("/guest")
async def guest_compat(
    settings: Settings = Depends(get_settings),
    db: firestore.Client = Depends(get_db)
):
    """Create a guest session (delegates to Google auth handler)."""
    return await google_guest_login(settings=settings, db=db)
