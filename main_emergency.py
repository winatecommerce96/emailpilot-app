"""
EmailPilot API - Emergency minimal version
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="EmailPilot API",
    description="Emergency minimal version", 
    version="2.0.1"
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic endpoints
@app.get("/api/")
async def root():
    return {
        "status": "emergency",
        "service": "EmailPilot API",
        "version": "2.0.1", 
        "message": "Emergency mode - limited functionality"
    }

# Serve frontend
@app.get("/")
async def get_frontend():
    try:
        return FileResponse('frontend/public/index.html')
    except:
        return {"error": "Frontend not available in emergency mode"}

@app.get("/app.js")
async def get_app_js():
    try:
        return FileResponse('frontend/public/app.js', media_type='application/javascript')
    except:
        return {"error": "App.js not available in emergency mode"}

@app.get("/health")
async def health_check():
    return {
        "status": "emergency_healthy",
        "message": "Running in emergency mode"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)