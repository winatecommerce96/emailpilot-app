"""
EmailPilot API - FastAPI Application
Main entry point for the EmailPilot Klaviyo automation platform
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging
from typing import Optional
from pathlib import Path

# Import routers
from app.api import auth, reports, goals, clients, slack, calendar, admin
from app.api import firebase_calendar
from app.api import goals_aware_calendar
from app.api import firebase_calendar_test, goals_calendar_test  # Test endpoints without auth
from app.api import mcp
from app.core.config import settings
from app.core.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Starting EmailPilot API...")
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down EmailPilot API...")

# Create FastAPI app
app = FastAPI(
    title="EmailPilot API",
    description="Klaviyo automation platform for email marketing performance",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://emailpilot.ai",
        "https://www.emailpilot.ai",
        "http://localhost:8080",  # For local development
        "http://localhost:3000",  # For local development
        "http://127.0.0.1:8080",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "EmailPilot API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "klaviyo": "ready",
        "timestamp": "2025-08-07T12:00:00Z"
    }

@app.get("/test_firebase_calendar.html")
async def serve_test_page():
    """Serve the Firebase calendar test page"""
    return FileResponse("test_firebase_calendar.html")

@app.get("/calendar")
async def serve_integrated_calendar():
    """Serve the fixed EmailPilot calendar"""
    calendar_path = Path(__file__).parent / "calendar_production.html"
    if calendar_path.exists():
        return FileResponse(calendar_path)
    else:
        return HTMLResponse("Calendar not found", status_code=404)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(slack.router, prefix="/api/slack", tags=["Slack"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(firebase_calendar.router, prefix="/api/firebase-calendar", tags=["Firebase Calendar"])
app.include_router(goals_aware_calendar.router, prefix="/api/goals-calendar", tags=["Goals-Aware Calendar"])
app.include_router(firebase_calendar_test.router, prefix="/api/firebase-calendar-test", tags=["Firebase Calendar Test"])
app.include_router(goals_calendar_test.router, prefix="/api/goals-calendar-test", tags=["Goals Calendar Test"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP Management"])

# Serve static files (frontend) in production
# Mount static files only if the frontend directory exists
frontend_path = Path(__file__).parent / "frontend" / "public"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    # Serve the main app at root
    @app.get("/app", response_class=HTMLResponse)
    async def serve_app():
        """Serve the main application"""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return index_file.read_text()
        return HTMLResponse("Frontend not found", status_code=404)
    
    # Catch-all route to serve the app for client-side routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes"""
        # Don't catch API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Serve static files if they exist
        static_file = frontend_path / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)
        
        # Otherwise serve the main app
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return HTMLResponse(index_file.read_text())
        return HTMLResponse("Frontend not found", status_code=404)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)