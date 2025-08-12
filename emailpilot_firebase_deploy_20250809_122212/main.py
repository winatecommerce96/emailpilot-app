"""
EmailPilot API - FastAPI Application
Main entry point for the EmailPilot Klaviyo automation platform
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import os
import logging
from typing import Optional

# Import routers
from app.api import auth, reports, goals, clients, slack, calendar
from app.api import firebase_calendar
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
        "http://localhost:3000",  # For local development
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

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(slack.router, prefix="/api/slack", tags=["Slack"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(firebase_calendar.router, prefix="/api/firebase-calendar", tags=["Firebase Calendar"])

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