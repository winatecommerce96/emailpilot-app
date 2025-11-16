from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.deps.firestore import get_db
from app.api import auth_v2, calendar, admin_clients, mcp_registry, clients_public, goals
import os

app = FastAPI()

# Add session middleware for admin authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    max_age=86400 * 7  # 7 days
)

# Mount static files from built React app (Vite output)
frontend_dist = "frontend/dist"
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

# Mount legacy static files for historical calendar versions
frontend_public = "frontend/public"
if os.path.exists(frontend_public):
    app.mount("/static", StaticFiles(directory=frontend_public), name="static")

# Register authentication routes
app.include_router(auth_v2.router, prefix="/api/auth/v2", tags=["authentication"])

# Register calendar routes
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])

# Register admin client management routes
app.include_router(admin_clients.router, tags=["admin"])

# Register MCP registry routes
app.include_router(mcp_registry.router, tags=["mcp-registry"])

# Register public clients route (no auth required for calendar)
app.include_router(clients_public.router, prefix="/api/clients", tags=["clients-public"])

# Register goals routes
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])

@app.get("/")
async def root():
    """Serve the React app with Clerk authentication"""
    frontend_file = 'frontend/dist/index.html'
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

@app.get("/calendar")
async def serve_calendar():
    """Serve React app at /calendar path for load balancer routing"""
    frontend_file = 'frontend/dist/index.html'
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {"error": "Frontend not deployed", "message": "React app not built"}

# Historical calendar versions for comparison
@app.get("/calendar_v1_timeline")
async def serve_calendar_v1():
    """Nov 11: Hourly timeline week view with campaign filters"""
    return FileResponse('frontend/public/calendar_v1_timeline.html')

@app.get("/calendar_v2_simplified")
async def serve_calendar_v2():
    """Nov 11: Simplified campaign layout with improved light mode"""
    return FileResponse('frontend/public/calendar_v2_simplified.html')

@app.get("/calendar_v3_stable")
async def serve_calendar_v3():
    """Nov 12: Stable version with field name fix"""
    return FileResponse('frontend/public/calendar_v3_stable.html')

@app.get("/calendar_v4_nov8")
async def serve_calendar_v4():
    """Nov 8: Archived version from .tmp file"""
    return FileResponse('frontend/public/calendar_v4_nov8.html')

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
