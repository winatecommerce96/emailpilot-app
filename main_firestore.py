"""
EmailPilot FastAPI Application with Google Cloud Firestore Integration

This version uses Google Cloud Firestore for all data storage.
Replaces SQLite with cloud-native database for better scalability.
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IMPORTANT: Ensure we're running the correct implementation
# This prevents accidentally running old calendar-project code
CORRECT_IMPLEMENTATION_MARKER = "main_firestore.py"
current_file = os.path.basename(__file__)
if current_file != CORRECT_IMPLEMENTATION_MARKER:
    logger.warning(f"⚠️  Warning: Running from {current_file} instead of {CORRECT_IMPLEMENTATION_MARKER}")
    logger.warning("⚠️  Make sure you're using the correct EmailPilot implementation!")

# Ensure we're not importing from old calendar-project
if 'calendar-project' in sys.path or 'calendar_project' in str(Path.cwd()):
    logger.error("❌ ERROR: Old calendar-project detected in path!")
    logger.error("❌ Please run from /emailpilot-app/ directory instead")
    logger.error("❌ Use: uvicorn main_firestore:app --reload --port 8000")
    sys.exit(1)

# Import API routers
from app.api.admin import router as admin_router

try:
    from app.api.calendar import router as calendar_router
except ImportError:
    calendar_router = None
    logger.warning("Calendar router not available")
    
from app.api.mcp_local import router as mcp_router

# Import MCP Klaviyo router 
from app.api.mcp_klaviyo import router as mcp_klaviyo_router

# Import admin client management router
from app.api.admin_clients import router as admin_clients_router

# Import admin firestore router
from app.api.admin_firestore import router as admin_firestore_router

# Import auth router
from app.api.auth import router as auth_router

# Import Google auth router
from app.api.auth_google import router as google_auth_router

# Import goals router - Now using Firestore
from app.api.goals import router as goals_router

# Import performance router - Now simplified  
from app.api.performance import router as performance_router

# Import reports router - Now simplified
from app.api.reports import router as reports_router

# Import dashboard router - Now uses Firestore
from app.api.dashboard import router as dashboard_router

# Check if agent routers are available (optional)
try:
    import app.api.email_sms_agents as email_sms_agents
    AGENT_ROUTERS_AVAILABLE = True
except ImportError:
    AGENT_ROUTERS_AVAILABLE = False
    logger.info("Agent routers not available (optional feature)")

# Check if admin agents router is available
try:
    import app.api.admin_agents as admin_agents
    ADMIN_AGENT_ROUTERS_AVAILABLE = True
except ImportError:
    ADMIN_AGENT_ROUTERS_AVAILABLE = False
    logger.info("Admin agent routers not available (optional feature)")

import signal
import requests

# Import enhanced environment manager
from app.services.env_manager import get_env_manager

# Import settings for configuration
from app.core.config import settings

# Google Cloud Firestore
try:
    from google.cloud import firestore
    from app.services.firestore_client import get_firestore_client
except ImportError:
    raise ImportError("google-cloud-firestore not installed. Run: pip install google-cloud-firestore")

# Get authenticated Firestore client
def get_db():
    """Get Firestore database client"""
    return get_firestore_client()

# Approved email addresses - Add your team members here
APPROVED_EMAILS = [
    "damon@dspkmarketing.com",
    "user@emailpilot.ai",
    "admin@emailpilot.ai"
]

app = FastAPI(
    title="EmailPilot API",
    description="Klaviyo automation platform with integrated calendar and performance monitoring",
    version="2.0.0"
)

# Load environment variables at startup
try:
    env_manager = get_env_manager()
    loaded_vars = env_manager.load_all_vars()
    logger.info(f"Environment manager loaded with {len(loaded_vars)} variables")
except Exception as e:
    logger.error(f"Error loading environment variables at startup: {e}")

# Startup probe - validate secrets and Firestore connectivity
@app.on_event("startup")
async def startup_probe():
    """Validate critical configuration at startup - fail fast if secrets or Firestore are unavailable"""
    try:
        # Touch the critical values so any failure happens immediately and loudly
        _ = (settings.project, settings.secret_key)
        
        logger.info("✅ Startup probe passed: Critical secrets loaded from Secret Manager")
        logger.info(f"  Transport: {os.getenv('SECRET_MANAGER_TRANSPORT', 'rest')}")
        logger.info(f"  Project: {settings.project}")
        logger.info(f"  Environment: {settings.environment}")
        logger.info("✅ Using Firestore as the exclusive database")
        
        # Check secret key strength
        if len(settings.secret_key) < 32:
            logger.warning("⚠️  WARNING: SECRET_KEY is shorter than recommended (32+ chars)")
        else:
            logger.info("✅ SECRET_KEY has sufficient length")
        
        # Verify Firestore connectivity with a health check
        from app.services.firestore import ping
        from app.core.config import get_firestore_client
        
        try:
            ping(get_firestore_client())
            logger.info("✅ Firestore health check passed")
        except Exception as e:
            logger.warning(f"⚠️  Firestore health check had issues but continuing: {e}")
            
    except Exception as e:
        logger.error(f"❌ STARTUP PROBE FAILED: {e}")
        logger.error("Cannot start application without required configuration")
        logger.error("Check that:")
        logger.error("  1. GOOGLE_CLOUD_PROJECT is set or ADC is configured")
        logger.error("  2. Secret Manager has required secrets:")
        logger.error("     - emailpilot-secret-key")
        logger.error("     - emailpilot-google-credentials (Service Account JSON)")
        logger.error("  3. Service Account has necessary permissions:")
        logger.error("     - roles/secretmanager.secretAccessor")
        logger.error("     - roles/datastore.user")
        # Re-raise to prevent app from starting with missing configuration
        raise

# Add session middleware for OAuth
session_secret = getattr(settings, 'secret_key', None) or os.getenv('SECRET_KEY', 'fallback-secret-key-change-this-in-production')
app.add_middleware(SessionMiddleware, secret_key=session_secret)

# Configure CORS with comprehensive origins and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "https://emailpilot.ai",
        "https://www.emailpilot.ai",
        "https://*.emailpilot.ai",  # Allow all subdomains
        "https://*.vercel.app",     # Vercel deployments
        "https://*.netlify.app"     # Netlify deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type", 
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
        "X-API-Key",
        "Cache-Control"
    ],
    expose_headers=[
        "X-Total-Count",
        "X-Page-Count", 
        "Link"
    ]
)

# Firestore helper functions
def doc_to_dict(doc) -> Dict[str, Any]:
    """Convert Firestore document to dictionary with ID"""
    if not doc.exists:
        return None
    data = doc.to_dict()
    data['id'] = doc.id
    return data

def collection_to_list(docs) -> List[Dict[str, Any]]:
    """Convert Firestore documents to list of dictionaries"""
    return [doc_to_dict(doc) for doc in docs if doc.exists]


# Health check endpoints
@app.get("/api/")
async def root():
    return {
        "status": "healthy",
        "service": "EmailPilot API",
        "version": "2.0.0", 
        "database": "Firestore"
    }

# Simple health endpoint for monitoring
@app.get("/health")
async def health():
    """Lightweight health check endpoint for monitoring systems."""
    return {"status": "ok"}

# Version endpoint for deployment tracking
@app.get("/version")
async def version():
    """Version information endpoint for deployment tracking."""
    return {"version": "1.0.0"}

# Legacy clients endpoint (for backwards compatibility)
@app.get("/api/clients/")
async def get_clients_legacy():
    """Legacy endpoint for clients list - redirects to admin endpoint"""
    try:
        db = get_db()
        docs = list(db.collection("clients").stream())
        clients = []
        
        for doc in docs:
            if doc.exists:
                data = doc.to_dict()
                clients.append({
                    "id": doc.id,
                    "name": data.get("name", "Unknown"),
                    "metric_id": data.get("metric_id", ""),
                    "is_active": data.get("is_active", True),
                    "contact_email": data.get("contact_email", ""),
                    "website": data.get("website", "")
                })
        
        return clients
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        return []


# Static file routes - Legacy support for direct paths
@app.get("/app.js")
async def get_app():
    """Legacy route - redirect to static mount"""
    return FileResponse('frontend/public/dist/app.js', media_type='application/javascript')

@app.get("/logo.png")
async def get_logo():
    return FileResponse('frontend/public/logo.png', media_type='image/png')

@app.get("/logo2.png")
async def get_logo2():
    return FileResponse('frontend/public/logo2.png', media_type='image/png')

@app.get("/components/{filename}")
async def get_component(filename: str):
    """Legacy route - redirect to static mount"""
    return FileResponse(f'frontend/public/dist/{filename}', media_type='application/javascript')

@app.get("/dist/{filename}")
async def get_dist_component(filename: str):
    """Serve compiled components from dist directory"""
    return FileResponse(f'frontend/public/dist/{filename}', media_type='application/javascript')

# Serve frontend
@app.get("/")
async def get_frontend():
    return FileResponse('frontend/public/index.html')

@app.get("/admin")
async def get_admin_panel():
    return FileResponse('frontend/public/admin.html')

@app.get("/admin-oauth.html")
async def get_oauth_admin():
    return FileResponse('frontend/public/admin-oauth.html')

@app.get("/admin-agents.html")
async def get_agents_admin():
    return FileResponse('frontend/public/admin-agents.html')

@app.get("/test_oauth_frontend.html")
async def get_oauth_test():
    return FileResponse('frontend/public/test_oauth_frontend.html')

@app.get("/test-goals-working.html")
async def get_goals_test():
    return FileResponse('test-goals-working.html')

@app.get("/test-goals-dashboard.html")
async def get_goals_dashboard_test():
    return FileResponse('test-goals-dashboard.html')

@app.get("/test-goals-final.html")
async def get_goals_final_test():
    return FileResponse('test-goals-final.html')

@app.get("/health-detailed")
async def health_check():
    try:
        # Test Firestore connection
        db = get_db()
        test_doc = db.collection('_health').document('test')
        test_doc.set({'timestamp': datetime.utcnow().isoformat()})
        test_doc.delete()
        
        return {
            "status": "healthy",
            "database": "Firestore connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Include API routers with proper prefixes
app.include_router(admin_router, prefix="/api/admin", tags=["Administration"])

# Include all routers with appropriate prefixes
if calendar_router:
    app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])

# MCP Management routers
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Management"])

# MCP Klaviyo Management
app.include_router(mcp_klaviyo_router, prefix="/api/mcp/klaviyo", tags=["MCP Klaviyo Management"])

# Admin client management router - already has /api/admin/clients prefix internally
app.include_router(admin_clients_router, tags=["Admin Client Management"])

# Admin Firestore router
app.include_router(admin_firestore_router, prefix="/api/admin/firestore", tags=["Admin Firestore Configuration"])

# Authentication router  
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Google Authentication router - with different prefix to avoid conflicts
app.include_router(google_auth_router, prefix="/api/auth/google", tags=["Google Authentication"])

# Goals router - Now using Firestore
app.include_router(goals_router, tags=["Goals Management"])

# Performance router - Now simplified
app.include_router(performance_router, tags=["Performance Metrics"])

# Reports router - Now simplified
app.include_router(reports_router, tags=["Reports"])

# Dashboard router - Now uses Firestore
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# Conditionally include agent routers
if AGENT_ROUTERS_AVAILABLE:
    app.include_router(email_sms_agents.router, prefix="/api/agents/campaigns", tags=["Email/SMS Multi-Agent System"])

# Conditionally include admin agent routers  
if ADMIN_AGENT_ROUTERS_AVAILABLE:
    # Only include admin agent routes if the module is available
    try:
        app.include_router(admin_agents.router, prefix="/api/agents/admin", tags=["Admin Agent Management"])
    except Exception as e:
        logger.warning(f"Could not include admin agent router: {e}")

# Admin endpoints are now handled by the admin router included above

# File serving for static assets
app.mount("/static", StaticFiles(directory="frontend/public"), name="static")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_firestore:app", host="0.0.0.0", port=8000, reload=True)