"""
Root entry point for Calendar Project FastAPI application.

This file imports the main FastAPI app from app.main and can be used
for deployment with WSGI servers or direct execution.
"""

import os
import sys

# Add the current directory to Python path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the configured FastAPI app
from app.main import app

# Export the app for deployment
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    from app.config import get_settings
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and not settings.is_production(),
        log_level=settings.log_level.lower()
    )