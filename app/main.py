from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.deps.firestore import get_db
from app.api import auth_v2, calendar, admin_clients
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/public"), name="static")

# Register authentication routes
app.include_router(auth_v2.router, prefix="/api/auth/v2", tags=["authentication"])

# Register calendar routes
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])

# Register admin client management routes
app.include_router(admin_clients.router, tags=["admin"])

@app.get("/health")
def health():
    return {"status": "ok", "revision": os.getenv("K_REVISION")}

@app.get("/goals/{user_id}")
def get_goals(user_id: str, db = Depends(get_db)):
    docs = db.collection("goals").where("userId", "==", user_id).stream()
    return [d.to_dict() | {"id": d.id} for d in docs]

# Serve calendar approval page
@app.get("/calendar-approval.html")
async def serve_calendar_approval():
    return FileResponse('frontend/public/calendar-approval.html')

@app.get("/static/calendar-approval.html")
async def serve_static_approval():
    return FileResponse('frontend/public/static/calendar-approval.html')
