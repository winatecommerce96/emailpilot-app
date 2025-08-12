"""
Calendar API Router for EmailPilot
Provides endpoints for calendar functionality with Firebase integration
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
import json
import logging
import os
from firebase_admin import firestore, auth
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    # Use default credentials in Cloud Run
    firebase_admin.initialize_app()

db = firestore.client()

# Pydantic models
class CalendarEvent(BaseModel):
    title: str
    date: str
    client_id: str
    content: Optional[str] = ""
    color: Optional[str] = "bg-gray-200 text-gray-800"
    event_type: Optional[str] = "general"

class CalendarEventUpdate(BaseModel):
    title: Optional[str]
    date: Optional[str]
    content: Optional[str]
    color: Optional[str]
    event_type: Optional[str]

class AIRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    client_id: Optional[str]

class DocumentImportRequest(BaseModel):
    doc_text: str
    client_id: str

# Calendar Event Endpoints
@router.get("/events")
async def get_calendar_events(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get calendar events for a client"""
    try:
        # Query Firebase for events
        events_ref = db.collection('calendar_events')
        query = events_ref.where('client_id', '==', client_id)
        
        if start_date:
            query = query.where('date', '>=', start_date)
        if end_date:
            query = query.where('date', '<=', end_date)
        
        events = []
        for doc in query.stream():
            event_data = doc.to_dict()
            event_data['id'] = doc.id
            events.append(event_data)
        
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events")
async def create_calendar_event(event: CalendarEvent):
    """Create a new calendar event"""
    try:
        event_data = event.dict()
        event_data['created_at'] = datetime.utcnow()
        event_data['updated_at'] = datetime.utcnow()
        
        # Add to Firebase
        doc_ref = db.collection('calendar_events').add(event_data)
        
        return {
            "id": doc_ref[1].id,
            "message": "Event created successfully",
            **event_data
        }
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}")
async def update_calendar_event(event_id: str, updates: CalendarEventUpdate):
    """Update an existing calendar event"""
    try:
        event_ref = db.collection('calendar_events').document(event_id)
        event_doc = event_ref.get()
        
        if not event_doc.exists:
            raise HTTPException(status_code=404, detail="Event not found")
        
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow()
        
        event_ref.update(update_data)
        
        return {"message": "Event updated successfully", "event_id": event_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """Delete a calendar event"""
    try:
        event_ref = db.collection('calendar_events').document(event_id)
        event_doc = event_ref.get()
        
        if not event_doc.exists:
            raise HTTPException(status_code=404, detail="Event not found")
        
        event_ref.delete()
        
        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Client Management Endpoints
@router.get("/clients")
async def get_calendar_clients():
    """Get all clients for calendar"""
    try:
        clients = []
        clients_ref = db.collection('clients')
        
        for doc in clients_ref.stream():
            client_data = doc.to_dict()
            client_data['id'] = doc.id
            clients.append(client_data)
        
        return clients
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        # Return demo clients as fallback
        return [
            {"id": "demo1", "name": "Demo Client 1", "email": "demo1@example.com"},
            {"id": "demo2", "name": "Demo Client 2", "email": "demo2@example.com"}
        ]

@router.post("/clients")
async def create_calendar_client(client_data: dict):
    """Create a new client"""
    try:
        if not client_data.get('name'):
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client_data['created_at'] = datetime.utcnow()
        client_data['updated_at'] = datetime.utcnow()
        
        doc_ref = db.collection('clients').add(client_data)
        
        return {
            "id": doc_ref[1].id,
            "message": "Client created successfully",
            **client_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Goals Integration Endpoints
@router.get("/goals/{client_id}")
async def get_client_goals(
    client_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get revenue goals for a client"""
    try:
        goals_ref = db.collection('goals')
        query = goals_ref.where('client_id', '==', client_id)
        
        if year:
            query = query.where('year', '==', year)
        if month is not None:
            query = query.where('month', '==', month)
        
        goals = []
        for doc in query.stream():
            goal_data = doc.to_dict()
            goal_data['id'] = doc.id
            goals.append(goal_data)
        
        # Return demo goal if none found
        if not goals:
            current_date = datetime.now()
            goals = [{
                "id": "demo-goal",
                "client_id": client_id,
                "monthly_revenue": 50000,
                "year": year or current_date.year,
                "month": month if month is not None else current_date.month
            }]
        
        return goals
    except Exception as e:
        logger.error(f"Error fetching client goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/{client_id}")
async def get_calendar_dashboard(client_id: str):
    """Get calendar dashboard with goals and progress"""
    try:
        current_date = datetime.now()
        
        # Get current month's goal
        goals = await get_client_goals(
            client_id, 
            current_date.year, 
            current_date.month
        )
        
        # Get current month's events
        events = await get_calendar_events(
            client_id,
            f"{current_date.year}-{current_date.month:02d}-01",
            f"{current_date.year}-{current_date.month:02d}-31"
        )
        
        # Calculate revenue progress
        campaign_multipliers = {
            'cheese club': 2.0,
            'rrb': 1.5,
            'sms': 1.3,
            're-engagement': 1.2,
            'nurturing': 0.8,
            'education': 0.8,
            'community': 0.7,
            'lifestyle': 0.7
        }
        
        total_revenue = 0
        for event in events:
            base_revenue = 500  # Base revenue per campaign
            title_lower = (event.get('title', '') or '').lower()
            
            multiplier = 1.0
            for key, mult in campaign_multipliers.items():
                if key in title_lower:
                    multiplier = mult
                    break
            
            total_revenue += base_revenue * multiplier
        
        goal_amount = goals[0]['monthly_revenue'] if goals else 50000
        achievement_percentage = (total_revenue / goal_amount * 100) if goal_amount > 0 else 0
        
        # Determine status
        if achievement_percentage >= 100:
            status = {"label": "Achieved", "color": "green", "emoji": "🎉"}
        elif achievement_percentage >= 75:
            status = {"label": "On Track", "color": "blue", "emoji": "✅"}
        elif achievement_percentage >= 50:
            status = {"label": "Warning", "color": "yellow", "emoji": "⚠️"}
        else:
            status = {"label": "At Risk", "color": "red", "emoji": "🚨"}
        
        return {
            "client_id": client_id,
            "current_month": current_date.strftime("%B %Y"),
            "goal": goal_amount,
            "current_revenue": total_revenue,
            "achievement_percentage": achievement_percentage,
            "status": status,
            "campaign_count": len(events),
            "recommendations": get_recommendations(achievement_percentage)
        }
    except Exception as e:
        logger.error(f"Error getting calendar dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_recommendations(achievement_percentage: float) -> List[str]:
    """Get strategic recommendations based on achievement"""
    if achievement_percentage >= 100:
        return [
            "Excellent performance! Consider stretch goals",
            "Focus on maintaining quality",
            "Document successful strategies"
        ]
    elif achievement_percentage >= 75:
        return [
            "You're on track to meet your goal",
            "Add 1-2 more high-value campaigns",
            "Consider a Cheese Club promotion"
        ]
    elif achievement_percentage >= 50:
        return [
            "Schedule more campaigns to reach goal",
            "Focus on high-revenue campaign types",
            "Add SMS alerts for quick wins"
        ]
    else:
        return [
            "Urgent: Add high-value campaigns immediately",
            "Consider RRB promotions (1.5x revenue)",
            "Schedule Cheese Club campaigns (2x revenue)",
            "Implement SMS campaign series"
        ]

# AI Integration Endpoints
@router.post("/ai/summarize")
async def summarize_document(request: DocumentImportRequest):
    """Parse document text into calendar campaigns using AI"""
    try:
        # This would integrate with Gemini API
        # For now, return a mock response
        campaigns = [
            {
                "date": "2024-01-15",
                "title": "January Cheese Club Launch",
                "content": "Monthly cheese club promotion",
                "color": "bg-green-200 text-green-800"
            },
            {
                "date": "2024-01-20",
                "title": "RRB Mid-Month Sale",
                "content": "Red Ribbon Box promotion",
                "color": "bg-red-200 text-red-800"
            }
        ]
        
        return campaigns
    except Exception as e:
        logger.error(f"Error summarizing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai/chat")
async def calendar_ai_chat(request: AIRequest):
    """AI-powered calendar planning assistance"""
    try:
        # This would integrate with Gemini API
        # For now, return a helpful response
        response = {
            "response": "Based on your current calendar, I recommend adding high-value campaigns like Cheese Club promotions to reach your revenue goals.",
            "suggestions": [
                "Add a Cheese Club campaign (2x revenue multiplier)",
                "Schedule an RRB promotion (1.5x revenue)",
                "Include SMS alerts for engagement"
            ],
            "action": None
        }
        
        # Check if this is an action request
        message_lower = request.message.lower()
        if "delete" in message_lower:
            response["action"] = {"type": "delete", "target": "campaign"}
        elif "create" in message_lower or "add" in message_lower:
            response["action"] = {"type": "create", "target": "campaign"}
        elif "update" in message_lower or "change" in message_lower:
            response["action"] = {"type": "update", "target": "campaign"}
        
        return response
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@router.get("/health")
async def calendar_health():
    """Check calendar API health"""
    return {
        "status": "healthy",
        "service": "calendar",
        "timestamp": datetime.utcnow().isoformat()
    }