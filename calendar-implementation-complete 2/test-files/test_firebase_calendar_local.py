#!/usr/bin/env python3
"""
Local Firebase Calendar Test Server
Bypasses authentication for easy testing of Firebase calendar functionality
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import logging
from datetime import datetime
from typing import List, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Firebase services for testing without credentials
class MockFirebaseCalendarService:
    def __init__(self):
        self.events = [
            {
                'id': 'test-event-1',
                'client_id': 'test-client-1', 
                'title': 'Welcome Email Campaign',
                'content': 'Welcome new subscribers with special offer',
                'event_date': '2025-09-15',
                'event_type': 'Nurturing/Education',
                'color': 'bg-blue-200 text-blue-800',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            },
            {
                'id': 'test-event-2',
                'client_id': 'test-client-1',
                'title': 'Monthly Newsletter',
                'content': 'Monthly product updates and news',
                'event_date': '2025-09-20', 
                'event_type': 'Community/Lifestyle',
                'color': 'bg-purple-200 text-purple-800',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
        ]
    
    async def get_client_events(self, client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        return [e for e in self.events if e['client_id'] == client_id]
    
    async def create_event(self, event_data):
        event_id = f"test-event-{len(self.events) + 1}"
        event = {
            'id': event_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            **event_data
        }
        self.events.append(event)
        return event_id
    
    async def update_event(self, event_id: str, updates):
        for i, event in enumerate(self.events):
            if event['id'] == event_id:
                self.events[i].update(updates)
                self.events[i]['updated_at'] = datetime.utcnow().isoformat()
                return True
        return False
    
    async def delete_event(self, event_id: str):
        for i, event in enumerate(self.events):
            if event['id'] == event_id:
                del self.events[i]
                return True
        return False
    
    async def get_client_stats(self, client_id: str):
        client_events = [e for e in self.events if e['client_id'] == client_id]
        return {
            'total_events': len(client_events),
            'events_this_month': len(client_events),
            'events_next_month': 0,
            'event_types': {'Demo': len(client_events)},
            'upcoming_events': client_events[:3]
        }

class MockFirebaseClientService:
    def __init__(self):
        self.clients = [
            {
                'id': 'test-client-1',
                'name': 'Demo Client',
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }
        ]
    
    async def get_all_clients(self):
        return [c for c in self.clients if c['is_active']]
    
    async def get_client(self, client_id: str):
        for client in self.clients:
            if client['id'] == client_id:
                return client
        return None
    
    async def create_client(self, client_data):
        client_id = f"test-client-{len(self.clients) + 1}"
        client = {
            'id': client_id,
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            **client_data
        }
        self.clients.append(client)
        return client_id

# Initialize mock services
mock_calendar = MockFirebaseCalendarService()
mock_clients = MockFirebaseClientService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔥 Starting Firebase Calendar Test Server")
    logger.info("📝 Mock Firebase services initialized")
    logger.info("✅ No authentication required for testing")
    yield
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(title="EmailPilot Firebase Calendar Test", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
async def root():
    return {"message": "🔥 Firebase Calendar Test Server", "status": "running"}

# Firebase Calendar API endpoints (without auth)
@app.get("/api/firebase-calendar/events")
async def get_calendar_events(client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    try:
        events = await mock_calendar.get_client_events(client_id, start_date, end_date)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/firebase-calendar/events")
async def create_calendar_event(event_data: dict):
    try:
        if not event_data.get('title') or not event_data.get('client_id') or not event_data.get('event_date'):
            raise HTTPException(status_code=400, detail="Missing required fields: title, client_id, event_date")
        
        client = await mock_clients.get_client(event_data['client_id'])
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        event_id = await mock_calendar.create_event(event_data)
        
        # Return created event
        events = await mock_calendar.get_client_events(event_data['client_id'])
        created_event = next((e for e in events if e['id'] == event_id), None)
        
        return created_event
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/firebase-calendar/events/{event_id}")
async def update_calendar_event(event_id: str, event_data: dict):
    try:
        success = await mock_calendar.update_event(event_id, event_data)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event updated successfully", "event_id": event_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/firebase-calendar/events/{event_id}")
async def delete_calendar_event(event_id: str):
    try:
        success = await mock_calendar.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/firebase-calendar/clients")
async def get_clients():
    try:
        clients = await mock_clients.get_all_clients()
        return clients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/firebase-calendar/clients")
async def create_client(client_data: dict):
    try:
        if not client_data.get('name'):
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client_id = await mock_clients.create_client(client_data)
        return {"message": "Client created successfully", "client_id": client_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/firebase-calendar/client/{client_id}/stats")
async def get_client_stats(client_id: str):
    try:
        client = await mock_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        stats = await mock_calendar.get_client_stats(client_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/firebase-calendar/chat")
async def calendar_chat(chat_data: dict):
    message = chat_data.get('message', '')
    return {
        "response": f"Mock AI response to: {message}. Firebase calendar functionality is working!",
        "is_action": False,
        "session_id": "test-session"
    }

# Test endpoints
@app.get("/test/firebase-connection")
async def test_firebase():
    return {
        "firebase_connection": "✅ Mock Firebase services working",
        "clients_available": len(mock_clients.clients),
        "events_available": len(mock_calendar.events),
        "status": "ready_for_testing"
    }

@app.get("/test/calendar-data")
async def test_calendar_data():
    return {
        "mock_clients": mock_clients.clients,
        "mock_events": mock_calendar.events,
        "test_client_id": "test-client-1"
    }

if __name__ == "__main__":
    import uvicorn
    print("🔥 Starting Firebase Calendar Test Server")
    print("📍 http://localhost:8080")
    print("✅ No Firebase credentials required - using mock services")
    print("🧪 Test endpoints:")
    print("   • GET /test/firebase-connection")
    print("   • GET /test/calendar-data") 
    print("   • GET /api/firebase-calendar/clients")
    print("   • GET /api/firebase-calendar/events?client_id=test-client-1")
    uvicorn.run(app, host="0.0.0.0", port=8080)