#!/usr/bin/env python3
"""
Minimal test server for workflow editor
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Create app
app = FastAPI(title="Workflow Test Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/public"), name="static")

# Add workflow routes
from app.api.workflow_fixed import router as workflow_router
app.include_router(workflow_router, tags=["Workflow"])

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "workflow": "enabled"}

if __name__ == "__main__":
    print("Starting test server on http://localhost:8001")
    print("Access editor at: http://localhost:8001/static/workflow_editor.html")
    uvicorn.run(app, host="0.0.0.0", port=8001)