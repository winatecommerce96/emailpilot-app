#!/usr/bin/env python3
"""Test script to add calendar route to FastAPI"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Calendar Test Server"}

@app.get("/calendar.html")
async def serve_calendar():
    calendar_path = Path(__file__).parent / "frontend" / "public" / "calendar.html"
    if calendar_path.exists():
        return FileResponse(calendar_path)
    else:
        return {"error": f"Calendar not found at {calendar_path}"}

if __name__ == "__main__":
    print("Starting test server on http://localhost:8081/calendar.html")
    uvicorn.run(app, host="0.0.0.0", port=8081)