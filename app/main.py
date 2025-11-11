from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.deps.firestore import get_db
from app.api import auth_v2, calendar, admin_clients, firebase_calendar
import os

app = FastAPI()

# Add session middleware for admin authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    max_age=86400 * 7  # 7 days
)

# Mount static files if frontend directory exists (optional for API-only deployment)
frontend_dir = "frontend/public"
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Register authentication routes
app.include_router(auth_v2.router, prefix="/api/auth/v2", tags=["authentication"])

# Register calendar routes
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])

# Register Firebase calendar events API
app.include_router(firebase_calendar.router, prefix="/api/calendar", tags=["calendar-events"])

# Register admin client management routes
app.include_router(admin_clients.router, tags=["admin"])

@app.get("/")
async def root():
    """Serve the main calendar interface at root path or API info"""
    frontend_file = 'frontend/public/calendar_master.html'
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {
        "message": "EmailPilot API",
        "status": "running",
        "endpoints": {
            "calendar": "/api/calendar/workflow",
            "auth": "/api/auth/v2/login",
            "health": "/health"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "revision": os.getenv("K_REVISION")}

@app.get("/goals/{user_id}")
def get_goals(user_id: str, db = Depends(get_db)):
    docs = db.collection("goals").where("userId", "==", user_id).stream()
    return [d.to_dict() | {"id": d.id} for d in docs]

# Serve calendar approval page (only if frontend exists)
@app.get("/calendar-approval.html")
async def serve_calendar_approval():
    frontend_file = 'frontend/public/calendar-approval.html'
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {"error": "Frontend not deployed", "message": "This is an API-only deployment"}

@app.get("/static/calendar-approval.html")
async def serve_static_approval():
    frontend_file = 'frontend/public/static/calendar-approval.html'
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {"error": "Frontend not deployed", "message": "This is an API-only deployment"}
