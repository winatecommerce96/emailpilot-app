"""
Calendar API endpoints for EmailPilot
Handles calendar operations, events, and Google integrations
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json
import logging
import requests
import os

from app.core.database import get_db
from app.models.calendar import CalendarEvent
from app.models.client import Client
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate, 
    CalendarEventResponse,
    GoogleDocImportRequest,
    AIResponse
)
from app.services.calendar_service import CalendarService
from app.services.google_service import GoogleService
from app.services.gemini_service import GeminiService
from app.api.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
calendar_service = CalendarService()
google_service = GoogleService()
gemini_service = GeminiService()

@router.get("/events", response_model=List[CalendarEventResponse])
async def get_calendar_events(
    client_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Get calendar events with optional filtering"""
    try:
        events = await calendar_service.get_events(
            db=db,
            client_id=client_id,
            start_date=start_date,
            end_date=end_date
        )
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events", response_model=CalendarEventResponse)
async def create_calendar_event(
    event_data: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Create a new calendar event"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == event_data.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        event = await calendar_service.create_event(db=db, event_data=event_data)
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    event_id: int,
    event_data: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Update an existing calendar event"""
    try:
        event = await calendar_service.update_event(
            db=db,
            event_id=event_id,
            event_data=event_data
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Delete a calendar event"""
    try:
        success = await calendar_service.delete_event(db=db, event_id=event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/duplicate", response_model=CalendarEventResponse)
async def duplicate_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Duplicate an existing calendar event"""
    try:
        event = await calendar_service.duplicate_event(db=db, event_id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/google-doc")
async def import_from_google_doc(
    import_request: GoogleDocImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Import calendar events from Google Doc"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == import_request.client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Start background import process
        background_tasks.add_task(
            calendar_service.import_from_google_doc,
            db=db,
            client_id=import_request.client_id,
            doc_id=import_request.doc_id,
            access_token=import_request.access_token
        )
        
        return {"message": "Import started successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Google Doc import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def calendar_chat(
    client_id: int,
    message: str,
    chat_history: Optional[List[dict]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Chat with AI about calendar events"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get client's calendar events for context
        events = await calendar_service.get_events(db=db, client_id=client_id)
        
        # Process with Gemini
        response = await gemini_service.process_calendar_chat(
            message=message,
            client_name=client.name,
            events=events,
            chat_history=chat_history or []
        )
        
        # Check if response is an action
        if response.is_action:
            # Execute the action
            action_result = await calendar_service.execute_ai_action(
                db=db,
                action=response.action,
                client_id=client_id
            )
            return {
                "response": action_result["message"],
                "is_action": True,
                "action_type": response.action.get("action")
            }
        else:
            return {
                "response": response.message,
                "is_action": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing calendar chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{client_id}")
async def export_calendar_data(
    client_id: int,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Export calendar data for a client"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        events = await calendar_service.get_events(db=db, client_id=client_id)
        
        if format.lower() == "csv":
            return await calendar_service.export_to_csv(events)
        else:
            return {
                "client_name": client.name,
                "export_date": datetime.utcnow().isoformat(),
                "events": [event.dict() for event in events]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting calendar data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/client/{client_id}/stats")
async def get_client_calendar_stats(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Get calendar statistics for a client"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        stats = await calendar_service.get_client_stats(db=db, client_id=client_id)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client calendar stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))