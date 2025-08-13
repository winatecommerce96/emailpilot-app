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

# Import the new schemas and Gemini service
from app.schemas.calendar import CampaignPlanRequest, CampaignPlanResponse, CalendarChatRequest, AICalendarRequest
from app.services.gemini_service import GeminiService

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

class EventDuplicateRequest(BaseModel):
    new_date: Optional[str] = None

# Initialize Gemini service
gemini_service = GeminiService()

# Campaign Planning Endpoint with Gemini AI
@router.post("/plan-campaign", response_model=CampaignPlanResponse)
async def plan_campaign(request: CampaignPlanRequest):
    """
    Plan a comprehensive email/SMS campaign using Gemini AI
    
    This endpoint accepts campaign details and uses AI to generate:
    - A strategic campaign plan
    - Multiple calendar events with intelligent timing
    - Both email and SMS touchpoints
    - Events stored in Firestore calendar_events collection
    """
    try:
        logger.info(f"Planning campaign for client {request.client_id}: {request.campaign_type}")
        
        # Generate campaign plan using Gemini AI
        campaign_data = await gemini_service.plan_campaign(
            client_id=request.client_id,
            campaign_type=request.campaign_type,
            start_date=request.start_date,
            end_date=request.end_date,
            promotion_details=request.promotion_details
        )
        
        # Extract campaign strategy and events
        campaign_strategy = campaign_data.get("campaign_strategy", "Strategic campaign plan generated")
        events = campaign_data.get("events", [])
        
        # Create events in Firestore
        created_events = []
        touchpoint_counts = {"email": 0, "sms": 0, "push": 0}
        
        for event_data in events:
            try:
                # Prepare event data for Firestore
                event_record = {
                    "title": event_data.get("title", "Campaign Event"),
                    "date": event_data.get("date"),
                    "client_id": request.client_id,
                    "content": event_data.get("content", ""),
                    "color": event_data.get("color", "bg-gray-200 text-gray-800"),
                    "event_type": event_data.get("event_type", "email"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    # Add campaign metadata
                    "campaign_metadata": event_data.get("campaign_metadata", {}),
                    "generated_by_ai": True,
                    "campaign_type": request.campaign_type,
                    "promotion_details": request.promotion_details
                }
                
                # Add to Firestore
                doc_ref = db.collection('calendar_events').add(event_record)
                
                # Add ID to the event record for response
                event_record['id'] = doc_ref[1].id
                created_events.append(event_record)
                
                # Count touchpoint types
                event_type = event_data.get("event_type", "email")
                if event_type in touchpoint_counts:
                    touchpoint_counts[event_type] += 1
                
                logger.info(f"Created event: {event_record['title']} on {event_record['date']}")
                
            except Exception as e:
                logger.error(f"Error creating event {event_data.get('title', 'Unknown')}: {e}")
                continue
        
        # Prepare response
        response = CampaignPlanResponse(
            campaign_plan=campaign_strategy,
            events_created=created_events,
            total_events=len(created_events),
            touchpoints=touchpoint_counts
        )
        
        logger.info(f"Successfully created {len(created_events)} events for {request.campaign_type} campaign")
        return response
        
    except Exception as e:
        logger.error(f"Error planning campaign: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to plan campaign: {str(e)}"
        )

# Calendar Event Endpoints
@router.get("/events")
async def get_calendar_events(
    client_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get calendar events for a client"""
    try:
        # Query Firebase for events
        events_ref = db.collection('calendar_events')
        
        # If client_id is provided, filter by it
        if client_id:
            query = events_ref.where('client_id', '==', client_id)
        else:
            query = events_ref
        
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

@router.get("/events/{client_id}")
async def get_calendar_events_by_client(client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get calendar events for a specific client"""
    try:
        # Query events for the client - using where() which is the correct method
        events_ref = db.collection('calendar_events')
        query = events_ref.where('client_id', '==', client_id)
        
        # Apply date filters if provided
        if start_date:
            query = query.where('date', '>=', start_date)
        if end_date:
            query = query.where('date', '<=', end_date)
        
        # Execute query
        events = []
        for doc in query.stream():
            event_data = doc.to_dict()
            event_data['id'] = doc.id
            events.append(event_data)
        
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events for client {client_id}: {e}")
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

@router.post("/events/{event_id}/duplicate")
async def duplicate_calendar_event(event_id: str, request: EventDuplicateRequest):
    """Duplicate an existing calendar event with optional new date"""
    try:
        # Retrieve the original event
        event_ref = db.collection('calendar_events').document(event_id)
        event_doc = event_ref.get()
        
        if not event_doc.exists:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get the original event data
        original_data = event_doc.to_dict()
        
        # Create duplicate data by copying all fields except ID and timestamps
        duplicate_data = {
            "title": f"{original_data.get('title', 'Event')} (Copy)",
            "date": request.new_date or original_data.get('date'),
            "client_id": original_data.get('client_id'),
            "content": original_data.get('content', ''),
            "color": original_data.get('color', 'bg-gray-200 text-gray-800'),
            "event_type": original_data.get('event_type', 'general'),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Preserve additional metadata fields if they exist
            "segment": original_data.get('segment'),
            "send_time": original_data.get('send_time'),
            "subject_a": original_data.get('subject_a'),
            "subject_b": original_data.get('subject_b'),
            "preview_text": original_data.get('preview_text'),
            "main_cta": original_data.get('main_cta'),
            "offer": original_data.get('offer'),
            "ab_test": original_data.get('ab_test'),
            "campaign_metadata": original_data.get('campaign_metadata', {}),
            "campaign_type": original_data.get('campaign_type'),
            "promotion_details": original_data.get('promotion_details'),
            # Mark as duplicate
            "is_duplicate": True,
            "original_event_id": event_id,
            "duplicated_from": event_id
        }
        
        # Remove None values to keep the document clean
        duplicate_data = {k: v for k, v in duplicate_data.items() if v is not None}
        
        # Create the duplicate event in Firestore
        doc_ref = db.collection('calendar_events').add(duplicate_data)
        duplicate_id = doc_ref[1].id
        
        # Add the new ID to the response data
        duplicate_data['id'] = duplicate_id
        
        logger.info(f"Successfully duplicated event {event_id} to {duplicate_id}")
        
        return {
            "message": "Event duplicated successfully",
            "original_event_id": event_id,
            "duplicate_event_id": duplicate_id,
            "duplicate_event": duplicate_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating calendar event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate event: {str(e)}")

# Client Management Endpoints
@router.get("/clients")
async def get_calendar_clients(active_only: Optional[bool] = None):
    """Get clients for calendar with optional active filtering"""
    try:
        clients = []
        clients_ref = db.collection('clients')
        
        # Query documents
        query = clients_ref
        if active_only is True:
            query = query.where('is_active', '==', True)
        
        for doc in query.stream():
            client_data = doc.to_dict()
            if client_data is None:
                continue
                
            # Add document ID
            client_data['id'] = doc.id
            
            # Ensure required fields exist
            if 'name' not in client_data:
                client_data['name'] = f"Client {doc.id}"
            if 'is_active' not in client_data:
                client_data['is_active'] = True
            if 'email' not in client_data:
                client_data['email'] = client_data.get('contact_email', '')
            
            # Only add if client meets active filter criteria
            if active_only is True and not client_data.get('is_active', True):
                continue
            elif active_only is False and client_data.get('is_active', True):
                continue
            
            clients.append(client_data)
        
        # Sort by name for consistent ordering
        clients.sort(key=lambda x: x.get('name', ''))
        
        return clients
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        # Return demo clients as fallback
        demo_clients = [
            {"id": "demo1", "name": "Demo Client 1", "email": "demo1@example.com", "is_active": True},
            {"id": "demo2", "name": "Demo Client 2", "email": "demo2@example.com", "is_active": True}
        ]
        
        # Apply active filter to demo clients if needed
        if active_only is True:
            demo_clients = [c for c in demo_clients if c.get('is_active', True)]
        elif active_only is False:
            demo_clients = [c for c in demo_clients if not c.get('is_active', True)]
        
        return demo_clients

@router.post("/clients")
async def create_calendar_client(client_data: dict):
    """Create a new client"""
    try:
        if not client_data.get('name'):
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client_data['created_at'] = datetime.utcnow()
        client_data['updated_at'] = datetime.utcnow()
        # Set default is_active to True if not provided
        if 'is_active' not in client_data:
            client_data['is_active'] = True
        
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
        # Use Gemini service to process document
        campaigns = await gemini_service.process_campaign_document(request.doc_text)
        
        # If no campaigns returned, provide fallback
        if not campaigns:
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
async def calendar_ai_chat_legacy(request: AIRequest):
    """Legacy AI chat endpoint - deprecated in favor of /ai/chat-enhanced"""
    try:
        # Basic response for backward compatibility
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

@router.post("/ai/chat-enhanced")
async def calendar_ai_chat_enhanced(request: AICalendarRequest):
    """Enhanced AI-powered calendar chat with full CRUD operations support"""
    try:
        logger.info(f"Processing AI chat for client {request.client_id}: {request.message}")
        
        # Get current calendar events for context
        current_events = await get_calendar_events(client_id=request.client_id)
        
        # Get client information for context
        try:
            client_doc = db.collection('clients').document(request.client_id).get()
            client_name = client_doc.to_dict().get('name', 'Client') if client_doc.exists else 'Client'
        except:
            client_name = 'Client'
        
        # Convert Firestore events to schema format for Gemini service
        from app.schemas.calendar import CalendarEventResponse
        schema_events = []
        for event in current_events:
            try:
                # Convert the Firestore event to the expected schema format
                schema_event = CalendarEventResponse(
                    id=event.get('id', ''),
                    client_id=request.client_id,
                    title=event.get('title', ''),
                    content=event.get('content', ''),
                    event_date=datetime.strptime(event.get('date', '2024-01-01'), '%Y-%m-%d').date(),
                    color=event.get('color', 'bg-gray-200 text-gray-800'),
                    event_type=event.get('event_type', 'email'),
                    imported_from_doc=event.get('imported_from_doc', False),
                    import_doc_id=event.get('import_doc_id'),
                    original_event_id=event.get('original_event_id'),
                    created_at=event.get('created_at', datetime.utcnow()),
                    updated_at=event.get('updated_at', datetime.utcnow())
                )
                schema_events.append(schema_event)
            except Exception as e:
                logger.warning(f"Error converting event to schema: {e}")
                continue
        
        # Process the chat message with Gemini AI
        ai_response = await gemini_service.process_calendar_chat(
            message=request.message,
            client_name=client_name,
            events=schema_events,
            chat_history=request.chat_history
        )
        
        # If this is an action request, execute it
        if ai_response.is_action and ai_response.action:
            action_result = await execute_calendar_action(
                action=ai_response.action,
                client_id=request.client_id
            )
            
            return {
                "message": ai_response.message,
                "is_action": True,
                "action_executed": True,
                "action_result": action_result,
                "action_details": ai_response.action.dict()
            }
        else:
            # Regular conversational response
            return {
                "message": ai_response.message,
                "is_action": False,
                "action_executed": False,
                "suggestions": _generate_contextual_suggestions(current_events, client_name)
            }
            
    except Exception as e:
        logger.error(f"Error in enhanced AI chat: {e}")
        return {
            "message": "I'm sorry, I encountered an error processing your request. Please try again or rephrase your message.",
            "is_action": False,
            "action_executed": False,
            "error": str(e)
        }

async def execute_calendar_action(action, client_id: str) -> Dict[str, Any]:
    """Execute calendar actions based on AI interpretation"""
    try:
        if action.action == "create":
            # Create a new calendar event
            event_data = action.event
            if not event_data:
                raise ValueError("No event data provided for creation")
            
            # Ensure required fields
            event_data["client_id"] = client_id
            if "color" not in event_data:
                # Set default color based on event type or content
                if event_data.get("event_type") == "sms":
                    event_data["color"] = "bg-orange-300 text-orange-800"
                elif "cheese club" in event_data.get("title", "").lower():
                    event_data["color"] = "bg-green-200 text-green-800"
                elif "rrb" in event_data.get("title", "").lower():
                    event_data["color"] = "bg-red-300 text-red-800"
                else:
                    event_data["color"] = "bg-blue-200 text-blue-800"
            
            # Add timestamps
            event_data["created_at"] = datetime.utcnow()
            event_data["updated_at"] = datetime.utcnow()
            event_data["generated_by_ai"] = True
            
            # Create in Firestore
            doc_ref = db.collection('calendar_events').add(event_data)
            event_data["id"] = doc_ref[1].id
            
            return {
                "success": True,
                "action": "create",
                "event_id": doc_ref[1].id,
                "message": f"Successfully created event: {event_data.get('title', 'New Event')}",
                "created_event": event_data
            }
            
        elif action.action == "update":
            # Update an existing calendar event
            if not action.event_id:
                raise ValueError("No event ID provided for update")
            
            event_ref = db.collection('calendar_events').document(action.event_id)
            event_doc = event_ref.get()
            
            if not event_doc.exists:
                raise ValueError(f"Event with ID {action.event_id} not found")
            
            # Prepare update data
            update_data = action.updates or {}
            update_data["updated_at"] = datetime.utcnow()
            update_data["updated_by_ai"] = True
            
            # Update in Firestore
            event_ref.update(update_data)
            
            return {
                "success": True,
                "action": "update",
                "event_id": action.event_id,
                "message": f"Successfully updated event",
                "updates_applied": update_data
            }
            
        elif action.action == "delete":
            # Delete a calendar event
            if not action.event_id:
                raise ValueError("No event ID provided for deletion")
            
            event_ref = db.collection('calendar_events').document(action.event_id)
            event_doc = event_ref.get()
            
            if not event_doc.exists:
                raise ValueError(f"Event with ID {action.event_id} not found")
            
            # Get event title for confirmation
            event_data = event_doc.to_dict()
            event_title = event_data.get('title', 'Unknown Event')
            
            # Delete from Firestore
            event_ref.delete()
            
            return {
                "success": True,
                "action": "delete",
                "event_id": action.event_id,
                "message": f"Successfully deleted event: {event_title}",
                "deleted_event": event_data
            }
            
        else:
            raise ValueError(f"Unknown action: {action.action}")
            
    except Exception as e:
        logger.error(f"Error executing calendar action {action.action}: {e}")
        return {
            "success": False,
            "action": action.action,
            "message": f"Failed to execute action: {str(e)}",
            "error": str(e)
        }

def _generate_contextual_suggestions(events: List[Dict], client_name: str) -> List[str]:
    """Generate contextual suggestions based on current calendar state"""
    suggestions = []
    
    # Count event types
    email_count = sum(1 for e in events if e.get('event_type') == 'email')
    sms_count = sum(1 for e in events if e.get('event_type') == 'sms')
    
    # Current month event count
    current_month = datetime.now().strftime("%Y-%m")
    this_month_events = [e for e in events if e.get('date', '').startswith(current_month)]
    
    if len(this_month_events) < 4:
        suggestions.append("Consider adding more campaigns this month to meet revenue goals")
    
    if sms_count < email_count * 0.3:
        suggestions.append("Add SMS campaigns for better engagement rates")
    
    # Check for high-value campaign types
    high_value_campaigns = [e for e in events if any(keyword in e.get('title', '').lower() 
                           for keyword in ['cheese club', 'rrb', 'flash sale'])]
    
    if len(high_value_campaigns) < 2:
        suggestions.append("Schedule high-value campaigns like Cheese Club or RRB promotions")
    
    if not suggestions:
        suggestions.append("Your calendar looks well balanced! Consider adding seasonal campaigns.")
    
    return suggestions[:3]  # Limit to 3 suggestions

# Conversation History Management
@router.post("/ai/save-conversation")
async def save_conversation_history(request: Dict[str, Any]):
    """Save conversation history for context persistence"""
    try:
        client_id = request.get('client_id')
        conversation = request.get('conversation', [])
        
        if not client_id:
            raise HTTPException(status_code=400, detail="Client ID required")
        
        # Save to Firestore
        conversation_data = {
            "client_id": client_id,
            "conversation": conversation,
            "updated_at": datetime.utcnow(),
            "message_count": len(conversation)
        }
        
        # Use client_id as document ID for easy retrieval
        db.collection('calendar_conversations').document(client_id).set(conversation_data)
        
        return {
            "success": True,
            "message": "Conversation history saved",
            "message_count": len(conversation)
        }
        
    except Exception as e:
        logger.error(f"Error saving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai/conversation/{client_id}")
async def get_conversation_history(client_id: str):
    """Retrieve conversation history for a client"""
    try:
        doc_ref = db.collection('calendar_conversations').document(client_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return {
                "client_id": client_id,
                "conversation": data.get('conversation', []),
                "last_updated": data.get('updated_at'),
                "message_count": data.get('message_count', 0)
            }
        else:
            return {
                "client_id": client_id,
                "conversation": [],
                "last_updated": None,
                "message_count": 0
            }
            
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bulk Event Creation Endpoint
@router.post("/create-bulk-events")
async def create_bulk_events(request: dict):
    """Create multiple calendar events at once"""
    try:
        client_id = request.get("client_id")
        events = request.get("events", [])
        
        if not client_id:
            raise HTTPException(status_code=400, detail="client_id is required")
        if not events:
            raise HTTPException(status_code=400, detail="events list is required")
        
        created_events = []
        
        for event_data in events:
            try:
                # Prepare event data for Firestore
                event_record = {
                    "title": event_data.get("title", "Campaign Event"),
                    "date": event_data.get("event_date") or event_data.get("date"),
                    "client_id": client_id,
                    "content": event_data.get("content", ""),
                    "color": event_data.get("color", "bg-gray-200 text-gray-800"),
                    "event_type": event_data.get("event_type", "email"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    # Campaign metadata
                    "segment": event_data.get("segment"),
                    "send_time": event_data.get("send_time"),
                    "subject_a": event_data.get("subject_a"),
                    "subject_b": event_data.get("subject_b"),
                    "preview_text": event_data.get("preview_text"),
                    "main_cta": event_data.get("main_cta"),
                    "offer": event_data.get("offer"),
                    "ab_test": event_data.get("ab_test"),
                    "generated_by_ai": True
                }
                
                # Add to Firestore
                doc_ref = db.collection('calendar_events').add(event_record)
                
                # Add ID to the event record for response
                event_record['id'] = doc_ref[1].id
                created_events.append(event_record)
                
                logger.info(f"Created bulk event: {event_record['title']} on {event_record['date']}")
                
            except Exception as e:
                logger.error(f"Error creating bulk event {event_data.get('title', 'Unknown')}: {e}")
                continue
        
        return {
            "message": f"Successfully created {len(created_events)} events",
            "created_events": created_events,
            "total_created": len(created_events),
            "total_requested": len(events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Stats endpoint
@router.get("/stats")
async def get_calendar_stats(client_id: str):
    """Get calendar statistics for a client"""
    try:
        # Get current date
        now = datetime.utcnow()
        current_month_start = datetime(now.year, now.month, 1)
        next_month = current_month_start.replace(month=current_month_start.month + 1) if current_month_start.month < 12 else current_month_start.replace(year=current_month_start.year + 1, month=1)
        
        # Query events for the client
        events_ref = db.collection('calendar_events').where('client_id', '==', client_id)
        all_events = []
        
        for doc in events_ref.stream():
            event_data = doc.to_dict()
            event_data['id'] = doc.id
            all_events.append(event_data)
        
        # Calculate statistics
        total_events = len(all_events)
        events_this_month = 0
        events_next_month = 0
        event_types = {}
        upcoming_events = []
        
        for event in all_events:
            # Parse event date
            try:
                if 'date' in event:
                    event_date_str = event['date']
                    if isinstance(event_date_str, str):
                        event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    else:
                        event_date = event_date_str
                    
                    # Count events by month
                    if event_date.year == now.year and event_date.month == now.month:
                        events_this_month += 1
                    elif event_date.year == next_month.year and event_date.month == next_month.month:
                        events_next_month += 1
                    
                    # Add to upcoming if in the future
                    if event_date >= now:
                        upcoming_events.append(event)
            except:
                pass
            
            # Count event types
            event_type = event.get('event_type', 'general')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        # Sort upcoming events by date
        upcoming_events.sort(key=lambda x: x.get('date', ''))
        
        return {
            "total_events": total_events,
            "events_this_month": events_this_month,
            "events_next_month": events_next_month,
            "event_types": event_types,
            "upcoming_events": upcoming_events[:10]  # Return only next 10 events
        }
        
    except Exception as e:
        logger.error(f"Error getting calendar stats for client {client_id}: {e}")
        # Return empty stats on error
        return {
            "total_events": 0,
            "events_this_month": 0,
            "events_next_month": 0,
            "event_types": {},
            "upcoming_events": []
        }

# Health check
@router.get("/health")
async def calendar_health():
    """Check calendar API health"""
    return {
        "status": "healthy",
        "service": "calendar",
        "timestamp": datetime.utcnow().isoformat()
    }