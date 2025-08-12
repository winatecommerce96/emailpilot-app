"""
EmailPilot API - Simplified version with Google OAuth
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os
import json

# Approved email addresses - Add your team members here
APPROVED_EMAILS = [
    "damon@winatecommerce.com",
    "admin@emailpilot.ai",
    # Add more approved emails here
]

# Create FastAPI app
app = FastAPI(
    title="EmailPilot API",
    description="Klaviyo automation platform for email marketing performance", 
    version="1.0.0"
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/api/")
async def root():
    return {
        "status": "healthy",
        "service": "EmailPilot API",
        "version": "1.0.0"
    }

# Serve static files directly from root
@app.get("/app.js")
async def get_app_js():
    return FileResponse('frontend/public/app.js', media_type='application/javascript')

# Serve frontend
@app.get("/")
async def get_frontend():
    return FileResponse('frontend/public/index.html')

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "klaviyo": "ready",
        "version": "1.0.0"
    }

# Authentication endpoints
@app.get("/api/auth/google")
async def google_login():
    """Redirect to Google OAuth"""
    return {
        "auth_url": "https://accounts.google.com/oauth/authorize",
        "message": "Use Google OAuth popup - this is a demo response"
    }

@app.post("/api/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    data = await request.json()
    
    # In a real implementation, you would verify the Google token
    # For now, we'll accept the user info if they're in the approved list
    user_email = data.get("email", "")
    
    if user_email not in APPROVED_EMAILS:
        raise HTTPException(status_code=403, detail="Access denied. Email not in approved list.")
    
    # Store user in session
    request.session["user"] = {
        "email": user_email,
        "name": data.get("name", "User"),
        "picture": data.get("picture", "")
    }
    
    return {
        "access_token": "demo-token",
        "user": request.session["user"]
    }

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return {"message": "Logged out successfully"}

# Protected route helper
def get_current_user_from_session(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

# Basic API endpoints (now protected)
@app.get("/api/clients/")
async def get_clients(request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    return [
        {
            "id": 1, 
            "name": "Demo Client 1", 
            "is_active": True,
            "metric_id": "metric_12345",
            "created_at": "2025-08-01T10:00:00Z",
            "updated_at": "2025-08-01T10:00:00Z"
        },
        {
            "id": 2, 
            "name": "Demo Client 2", 
            "is_active": True,
            "metric_id": "metric_67890",
            "created_at": "2025-08-02T10:00:00Z", 
            "updated_at": "2025-08-02T10:00:00Z"
        }
    ]

@app.get("/api/reports/latest/weekly")
async def get_latest_weekly(request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    return {
        "status": "completed",
        "generated_at": "2025-08-07T12:00:00Z",
        "summary": "Weekly report generated successfully"
    }

@app.post("/api/reports/weekly/generate")
async def generate_weekly(request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    return {
        "status": "started",
        "message": "Weekly report generation started"
    }

@app.get("/api/clients/{client_id}")
async def get_client(client_id: int, request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    # Mock client detail with stats
    return {
        "id": client_id,
        "name": f"Demo Client {client_id}",
        "is_active": True,
        "metric_id": f"metric_{client_id}2345",
        "created_at": "2025-08-01T10:00:00Z",
        "updated_at": "2025-08-01T10:00:00Z",
        "stats": {
            "goals_count": 3,
            "reports_count": 12,
            "latest_report": "2025-08-07T12:00:00Z"
        }
    }

@app.post("/api/clients/")
async def create_client(request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    data = await request.json()
    return {
        "id": 999,
        "name": data.get("name", "New Client"),
        "is_active": True,
        "metric_id": data.get("metric_id", ""),
        "created_at": "2025-08-09T10:00:00Z",
        "updated_at": "2025-08-09T10:00:00Z"
    }

@app.put("/api/clients/{client_id}")
async def update_client(client_id: int, request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    data = await request.json()
    return {
        "id": client_id,
        "name": data.get("name", f"Updated Client {client_id}"),
        "is_active": data.get("is_active", True),
        "metric_id": data.get("metric_id", f"metric_{client_id}2345"),
        "created_at": "2025-08-01T10:00:00Z",
        "updated_at": "2025-08-09T10:00:00Z"
    }

@app.delete("/api/clients/{client_id}")
async def deactivate_client(client_id: int, request: Request):
    get_current_user_from_session(request)  # Ensure user is authenticated
    return {"message": "Client deactivated successfully"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)