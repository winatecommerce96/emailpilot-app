#!/usr/bin/env python3
"""
Local test version of EmailPilot with calendar functionality
This version uses SQLAlchemy for testing without Firebase setup
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import os
import logging
from datetime import datetime
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_emailpilot.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer)
    title = Column(String)
    content = Column(Text)
    event_date = Column(Date)
    event_type = Column(String)
    color = Column(String, default="bg-gray-200 text-gray-800")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Create tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create sample data
    db = SessionLocal()
    try:
        # Check if sample client exists
        sample_client = db.query(Client).filter(Client.name == "Demo Client").first()
        if not sample_client:
            sample_client = Client(name="Demo Client")
            db.add(sample_client)
            db.commit()
            db.refresh(sample_client)
            logger.info("Created sample client")
            
            # Create sample events
            sample_events = [
                CalendarEvent(
                    client_id=sample_client.id,
                    title="Welcome Email Campaign",
                    content="Welcome new subscribers with special offer",
                    event_date=datetime(2025, 9, 15).date(),
                    event_type="Nurturing/Education",
                    color="bg-blue-200 text-blue-800"
                ),
                CalendarEvent(
                    client_id=sample_client.id,
                    title="Monthly Newsletter",
                    content="Monthly product updates and news",
                    event_date=datetime(2025, 9, 20).date(),
                    event_type="Community/Lifestyle", 
                    color="bg-purple-200 text-purple-800"
                )
            ]
            
            for event in sample_events:
                db.add(event)
            
            db.commit()
            logger.info("Created sample calendar events")
            
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
    finally:
        db.close()
    
    yield
    logger.info("Shutting down...")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create FastAPI app
app = FastAPI(title="EmailPilot Calendar Test", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple auth mock - no actual verification for testing
def verify_token():
    return {"id": 1, "name": "Test User", "role": "admin"}

# Optional auth dependency for testing
def optional_auth():
    return {"id": 1, "name": "Test User", "role": "admin"}

# API Endpoints
@app.get("/")
async def root():
    return FileResponse("frontend/public/index.html")

@app.get("/api/clients")
async def get_clients(db: Session = Depends(get_db)):
    clients = db.query(Client).filter(Client.is_active == True).all()
    return [{"id": c.id, "name": c.name, "is_active": c.is_active} for c in clients]

@app.post("/api/clients")
async def create_client(client_data: dict, db: Session = Depends(get_db)):
    client = Client(name=client_data["name"])
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"id": client.id, "name": client.name, "is_active": client.is_active}

@app.get("/api/calendar/events")
async def get_events(
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(CalendarEvent)
    if client_id:
        query = query.filter(CalendarEvent.client_id == client_id)
    
    events = query.all()
    return [{
        "id": e.id,
        "client_id": e.client_id,
        "title": e.title,
        "content": e.content,
        "event_date": e.event_date.isoformat(),
        "event_type": e.event_type,
        "color": e.color,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat()
    } for e in events]

@app.post("/api/calendar/events")
async def create_event(
    event_data: dict,
    db: Session = Depends(get_db)
):
    event = CalendarEvent(
        client_id=event_data["client_id"],
        title=event_data["title"],
        content=event_data.get("content", ""),
        event_date=datetime.fromisoformat(event_data["event_date"]).date(),
        event_type=event_data.get("event_type", ""),
        color=event_data.get("color", "bg-gray-200 text-gray-800")
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return {
        "id": event.id,
        "client_id": event.client_id,
        "title": event.title,
        "content": event.content,
        "event_date": event.event_date.isoformat(),
        "event_type": event.event_type,
        "color": event.color,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat()
    }

@app.put("/api/calendar/events/{event_id}")
async def update_event(
    event_id: int,
    event_data: dict,
    db: Session = Depends(get_db)
):
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    for key, value in event_data.items():
        if key == "event_date" and isinstance(value, str):
            value = datetime.fromisoformat(value).date()
        setattr(event, key, value)
    
    event.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Event updated successfully"}

@app.delete("/api/calendar/events/{event_id}")
async def delete_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    
    return {"message": "Event deleted successfully"}

@app.post("/api/calendar/events/{event_id}/duplicate")
async def duplicate_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    original = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Event not found")
    
    duplicate = CalendarEvent(
        client_id=original.client_id,
        title=f"{original.title} (Copy)",
        content=original.content,
        event_date=original.event_date,
        event_type=original.event_type,
        color=original.color
    )
    db.add(duplicate)
    db.commit()
    
    return {"message": "Event duplicated successfully"}

@app.post("/api/calendar/chat")
async def calendar_chat(
    chat_data: dict
):
    # Simple mock response
    message = chat_data.get("message", "")
    if "how many" in message.lower():
        return {
            "response": "You have 2 campaigns scheduled for this month.",
            "is_action": False
        }
    else:
        return {
            "response": "I'm a simple test version. The full AI chat will be available with Firebase integration.",
            "is_action": False
        }

@app.get("/api/calendar/client/{client_id}/stats")
async def get_client_stats(
    client_id: int,
    db: Session = Depends(get_db)
):
    events = db.query(CalendarEvent).filter(CalendarEvent.client_id == client_id).all()
    
    return {
        "total_events": len(events),
        "events_this_month": len(events),
        "events_next_month": 0,
        "event_types": {"Demo": len(events)},
        "upcoming_events": []
    }

# Mock auth endpoints
@app.post("/api/auth/google/callback")
async def auth_callback(auth_data: dict):
    return {
        "user": {
            "id": 1,
            "name": auth_data.get("name", "Test User"),
            "email": auth_data.get("email", "test@example.com")
        }
    }

@app.get("/api/auth/me")
async def get_me():
    return {"id": 1, "name": "Test User", "email": "test@example.com"}

@app.post("/api/auth/logout")
async def logout():
    return {"message": "Logged out"}

# Serve static files
app.mount("/", StaticFiles(directory="frontend/public", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("🧪 Starting EmailPilot Calendar Test Server")
    print("📍 http://localhost:8080")
    print("✅ This version uses SQLite for testing (no Firebase required)")
    uvicorn.run(app, host="0.0.0.0", port=8080)