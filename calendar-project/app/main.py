"""
Main FastAPI Application for Calendar Project

This is the main FastAPI application that initializes all services,
configures middleware, sets up routing, and handles the application lifecycle.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.routers.api import router as api_router


# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log") if settings.is_production() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize templates
templates = None
if os.path.exists(settings.templates_directory):
    templates = Jinja2Templates(directory=settings.templates_directory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown events.
    
    This replaces the deprecated @app.on_event("startup") and @app.on_event("shutdown")
    decorators with the new lifespan parameter approach.
    """
    
    # Startup
    logger.info(f"Starting up {settings.app_name} v{settings.app_version}...")
    
    try:
        # Initialize Firestore service
        logger.info("Initializing Firestore service...")
        from app.services.firestore_service import initialize_firestore_service
        
        firestore_service = await initialize_firestore_service(
            project_id=settings.google_cloud_project,
            credentials_path=settings.google_application_credentials
        )
        if firestore_service:
            logger.info("Firestore service initialized successfully")
        else:
            logger.warning("Firestore service could not be initialized")
        
        # Initialize Google services
        logger.info("Initializing Google services...")
        from app.services.google_service import GoogleService
        
        # Google service is initialized when instantiated
        google_service = GoogleService()
        logger.info("Google services initialized successfully")
        
        # Database adapter is available via function imports
        logger.info("Database adapter functions are available")
        from app.services import database_adapter
        logger.info("Database adapter initialized successfully")
        
        logger.info(f"{settings.app_name} startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services during startup: {str(e)}")
        if settings.is_production():
            # In production, we might want to fail fast
            raise
        else:
            # In development, log the error but continue
            logger.warning("Continuing with partial initialization in development mode")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}...")
    
    try:
        # Cleanup services
        logger.info("Cleaning up services...")
        
        # Cleanup Google services HTTP client
        try:
            from app.services.google_service import GoogleService
            google_service = GoogleService()
            await google_service.http_client.aclose()
            logger.info("Google service HTTP client cleanup completed")
        except Exception as e:
            logger.warning(f"Google service cleanup warning: {e}")
            
        # Firestore cleanup is handled by Firebase Admin SDK automatically
        logger.info("Service cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {str(e)}")
    
    logger.info(f"{settings.app_name} shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    docs_url=settings.docs_url if not settings.is_production() else None,
    redoc_url=settings.redoc_url if not settings.is_production() else None,
    openapi_url=settings.openapi_url if not settings.is_production() else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if os.path.exists(settings.static_directory):
    app.mount("/static", StaticFiles(directory=settings.static_directory), name="static")
    logger.info(f"Static files mounted from {settings.static_directory}")
else:
    logger.warning(f"Static directory not found: {settings.static_directory}")

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)
logger.info(f"API router included with prefix: {settings.api_prefix}")


# Root endpoint - serve main HTML template
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serve the main calendar application HTML template.
    
    Falls back to JSON response if template is not available.
    """
    try:
        if templates and os.path.exists(f"{settings.templates_directory}/calendar.html"):
            return templates.TemplateResponse(
                "calendar.html",
                {
                    "request": request,
                    "app_name": settings.app_name,
                    "app_version": settings.app_version,
                    "debug": settings.debug
                }
            )
        elif templates and os.path.exists(f"{settings.templates_directory}/index.html"):
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "app_name": settings.app_name,
                    "app_version": settings.app_version,
                    "debug": settings.debug
                }
            )
        else:
            # Fallback JSON response
            return JSONResponse(
                content={
                    "message": f"{settings.app_name} is running",
                    "version": settings.app_version,
                    "docs": "/docs" if not settings.is_production() else None,
                    "health": "/health"
                }
            )
    except Exception as e:
        logger.error(f"Error serving root template: {str(e)}")
        return JSONResponse(
            content={
                "message": f"{settings.app_name} is running",
                "version": settings.app_version,
                "error": "Template loading failed"
            }
        )


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Checks the status of all critical services and returns detailed health information.
    """
    health_status = {
        "status": "healthy",
        "timestamp": "",
        "version": settings.app_version,
        "services": {}
    }
    
    try:
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat()
        
        # Check Firestore service
        try:
            from app.services.firestore_service import get_firestore_service
            firestore_service = await get_firestore_service()
            if firestore_service:
                firestore_health = await firestore_service.health_check()
                health_status["services"]["firestore"] = firestore_health
            else:
                health_status["services"]["firestore"] = {
                    "status": "unavailable",
                    "message": "Service not initialized"
                }
        except Exception as e:
            health_status["services"]["firestore"] = {
                "status": "error",
                "message": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check Google services
        try:
            from app.services.google_service import GoogleService
            google_service = GoogleService()
            # Simple check - if we can instantiate the service, it's available
            health_status["services"]["google"] = {
                "status": "healthy",
                "message": "Google service available"
            }
        except Exception as e:
            health_status["services"]["google"] = {
                "status": "error", 
                "message": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check database adapter
        try:
            from app.services import database_adapter
            # Try to get firestore service through the adapter
            from app.services.firestore_service import get_firestore_service
            firestore_service = await get_firestore_service()
            if firestore_service:
                health_status["services"]["database"] = {
                    "status": "healthy",
                    "message": "Database adapter and Firestore available"
                }
            else:
                health_status["services"]["database"] = {
                    "status": "unavailable",
                    "message": "Firestore service not available"
                }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error",
                "message": str(e)
            }
            health_status["status"] = "degraded"
        
        # Overall status determination
        service_statuses = [
            service.get("status", "unknown") 
            for service in health_status["services"].values()
        ]
        
        if any(status == "error" for status in service_statuses):
            health_status["status"] = "unhealthy"
        elif any(status in ["degraded", "warning"] for status in service_statuses):
            health_status["status"] = "degraded"
        
        # Return appropriate HTTP status
        if health_status["status"] == "unhealthy":
            return JSONResponse(
                content=health_status,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        elif health_status["status"] == "degraded":
            return JSONResponse(
                content=health_status,
                status_code=status.HTTP_200_OK
            )
        else:
            return health_status
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "error",
                "message": "Health check failed",
                "error": str(e)
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with proper logging and response format."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed information."""
    logger.warning(f"Validation error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "status_code": 422,
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with proper logging."""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.is_production():
        error_message = "An internal error occurred"
        error_details = None
    else:
        error_message = str(exc)
        error_details = exc.__class__.__name__
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "status_code": 500,
                "message": error_message,
                "details": error_details,
                "path": str(request.url.path)
            }
        }
    )


# Additional utility endpoints for development
if not settings.is_production():
    
    @app.get("/debug/config")
    async def debug_config():
        """Debug endpoint to view current configuration (development only)."""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "google_cloud_project": settings.google_cloud_project,
            "static_directory": settings.static_directory,
            "templates_directory": settings.templates_directory,
            "log_level": settings.log_level
        }
    
    @app.get("/debug/routes")
    async def debug_routes():
        """Debug endpoint to list all routes (development only)."""
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods'):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods),
                    "name": route.name
                })
        return {"routes": routes}


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} directly with uvicorn")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and not settings.is_production(),
        log_level=settings.log_level.lower(),
        access_log=True
    )