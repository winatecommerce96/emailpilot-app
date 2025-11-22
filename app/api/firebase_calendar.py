"""
Firebase Calendar API endpoints for EmailPilot
Uses Firebase Firestore for scalable, robust calendar functionality
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, date
import json
import logging
import uuid

from app.api.auth import verify_token
from app.services.gemini_service import GeminiService
from app.services.google_service import GoogleService
from app.services.secret_manager import SecretManagerService
from app.deps import get_secret_manager_service
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from firebase_calendar_integration import firebase_calendar, firebase_clients, firebase_chat

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize stateless services
google_service = GoogleService()

# Dependency factory for GeminiService (uses Secret Manager)
def get_gemini_service(
    secret_manager: SecretManagerService = Depends(get_secret_manager_service),
) -> GeminiService:
    return GeminiService(secret_manager=secret_manager)

@router.get("/events")
async def get_calendar_events(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(verify_token)
):
    """Get calendar events for a client from Firebase"""
    try:
        events = await firebase_calendar.get_client_events(
            client_id=client_id,
            start_date=start_date,
            end_date=end_date
        )
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events")
async def create_calendar_event(
    event_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Create a new calendar event in Firebase"""
    try:
        # Validate required fields
        if not event_data.get('title') or not event_data.get('client_id') or not event_data.get('event_date'):
            raise HTTPException(status_code=400, detail="Missing required fields: title, client_id, event_date")
        
        # Verify client exists
        client = await firebase_clients.get_client(event_data['client_id'])
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create event
        event_id = await firebase_calendar.create_event(event_data)
        
        # Return created event
        created_event = await firebase_calendar.get_client_events(
            client_id=event_data['client_id']
        )
        created_event = next((e for e in created_event if e['id'] == event_id), None)
        
        return created_event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}")
async def update_calendar_event(
    event_id: str,
    event_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Update an existing calendar event in Firebase"""
    try:
        success = await firebase_calendar.update_event(event_id, event_data)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Return updated event (you'd need to fetch it)
        return {"message": "Event updated successfully", "event_id": event_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    current_user: dict = Depends(verify_token)
):
    """Delete a calendar event from Firebase"""
    try:
        success = await firebase_calendar.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {"message": "Event deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/{event_id}/duplicate")
async def duplicate_calendar_event(
    event_id: str,
    current_user: dict = Depends(verify_token)
):
    """Duplicate an existing calendar event in Firebase"""
    try:
        new_event_id = await firebase_calendar.duplicate_event(event_id)
        if not new_event_id:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {"message": "Event duplicated successfully", "new_event_id": new_event_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/google-doc")
async def import_from_google_doc(
    import_data: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token),
    gemini_service: GeminiService = Depends(get_gemini_service),
):
    """Import calendar events from Google Doc (Firebase version)"""
    try:
        client_id = import_data.get('client_id')
        doc_id = import_data.get('doc_id')
        access_token = import_data.get('access_token')
        
        if not all([client_id, doc_id, access_token]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Verify client exists
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Start background import process, passing dependencies explicitly
        background_tasks.add_task(
            process_google_doc_import,
            client_id=client_id,
            doc_id=doc_id,
            access_token=access_token,
            gemini_service=gemini_service,
        )
        
        return {"message": "Import started successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Google Doc import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_google_doc_import(
    client_id: str,
    doc_id: str,
    access_token: str,
    gemini_service: GeminiService,
):
    """Background task to process Google Doc import"""
    try:
        # Extract document content
        doc_content = await google_service.get_document_content(doc_id, access_token)
        
        if not doc_content:
            logger.error("No content found in Google Doc")
            return
        
        # Process with Gemini AI
        campaigns = await gemini_service.process_campaign_document(doc_content)
        
        if not campaigns:
            logger.error("No campaigns extracted from document")
            return
        
        # Create events in Firebase
        for campaign in campaigns:
            try:
                event_data = {
                    'client_id': client_id,
                    'title': campaign.get('title', 'Untitled Campaign'),
                    'content': campaign.get('content', ''),
                    'event_date': campaign.get('date'),
                    'color': campaign.get('color', 'bg-gray-200 text-gray-800'),
                    'event_type': _extract_event_type_from_color(campaign.get('color', '')),
                    'imported_from_doc': True,
                    'import_doc_id': doc_id
                }
                
                await firebase_calendar.create_event(event_data)
                
            except Exception as e:
                logger.error(f"Failed to create event from campaign: {e}")
                continue
        
        logger.info(f"Import completed for client {client_id}")
        
    except Exception as e:
        logger.error(f"Background import failed: {e}")

def _extract_event_type_from_color(color: str) -> str:
    """Extract event type from color class"""
    color_map = {
        'bg-red-300': 'RRB Promotion',
        'bg-green-200': 'Cheese Club',
        'bg-blue-200': 'Nurturing/Education',
        'bg-purple-200': 'Community/Lifestyle',
        'bg-yellow-200': 'Re-engagement',
        'bg-orange-300': 'SMS Alert'
    }
    
    for color_class, event_type in color_map.items():
        if color_class in color:
            return event_type
    
    return 'Unclassified'

@router.post("/chat")
async def calendar_chat(
    chat_data: dict,
    current_user: dict = Depends(verify_token),
    gemini_service: GeminiService = Depends(get_gemini_service),
):
    """Chat with AI about calendar events (Firebase version)"""
    try:
        client_id = chat_data.get('client_id')
        message = chat_data.get('message')
        session_id = chat_data.get('session_id', str(uuid.uuid4()))
        
        if not client_id or not message:
            raise HTTPException(status_code=400, detail="Missing client_id or message")
        
        # Verify client exists
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get client's calendar events for context
        events = await firebase_calendar.get_client_events(client_id)
        
        # Get recent chat history
        chat_history = await firebase_chat.get_chat_history(client_id, session_id)
        
        # Process with Gemini
        response = await gemini_service.process_calendar_chat(
            message=message,
            client_name=client['name'],
            events=events,
            chat_history=[{
                'role': 'user' if i % 2 == 0 else 'model',
                'text': h['user_message'] if i % 2 == 0 else h['ai_response']
            } for i, h in enumerate(chat_history)]
        )
        
        # Check if response is an action
        is_action = response.is_action if hasattr(response, 'is_action') else False
        action_type = None
        
        if is_action and hasattr(response, 'action'):
            # Execute the action
            action_result = await execute_calendar_action(
                action=response.action.dict() if response.action else {},
                client_id=client_id
            )
            response_message = action_result.get('message', 'Action completed')
            action_type = response.action.action if response.action else None
        else:
            response_message = response.message if hasattr(response, 'message') else str(response)
        
        # Save chat interaction to Firebase
        await firebase_chat.save_chat_message(
            client_id=client_id,
            user_message=message,
            ai_response=response_message,
            is_action=is_action,
            action_type=action_type,
            session_id=session_id
        )
        
        return {
            "response": response_message,
            "is_action": is_action,
            "action_type": action_type,
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing calendar chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_calendar_action(action: dict, client_id: str) -> dict:
    """Execute AI-requested calendar actions"""
    action_type = action.get('action')
    
    if action_type == 'delete':
        event_id = action.get('eventId')
        if not event_id:
            return {"success": False, "message": "No event ID provided"}
        
        success = await firebase_calendar.delete_event(event_id)
        return {
            "success": success,
            "message": "Event deleted successfully" if success else "Failed to delete event"
        }
    
    elif action_type == 'update':
        event_id = action.get('eventId')
        updates = action.get('updates', {})
        
        if not event_id or not updates:
            return {"success": False, "message": "Missing event ID or updates"}
        
        success = await firebase_calendar.update_event(event_id, updates)
        return {
            "success": success,
            "message": "Event updated successfully" if success else "Failed to update event"
        }
    
    elif action_type == 'create':
        event_data = action.get('event', {})
        
        if not event_data:
            return {"success": False, "message": "No event data provided"}
        
        try:
            event_data['client_id'] = client_id
            event_id = await firebase_calendar.create_event(event_data)
            return {
                "success": True,
                "message": f"Event '{event_data.get('title', 'New Event')}' created successfully"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to create event: {str(e)}"}
    
    return {"success": False, "message": "Unknown action type"}

@router.get("/client/{client_id}/stats")
async def get_client_calendar_stats(
    client_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get calendar statistics for a client (Firebase version)"""
    try:
        # Verify client exists
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        stats = await firebase_calendar.get_client_stats(client_id)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client calendar stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{client_id}")
async def export_calendar_data(
    client_id: str,
    format: str = "json",
    current_user: dict = Depends(verify_token)
):
    """Export calendar data for a client (Firebase version)"""
    try:
        # Verify client exists
        client = await firebase_clients.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        events = await firebase_calendar.get_client_events(client_id)
        
        return {
            "client_name": client['name'],
            "export_date": datetime.utcnow().isoformat(),
            "total_events": len(events),
            "events": events
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting calendar data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Client management endpoints for Firebase
@router.get("/clients")
async def get_clients(current_user: dict = Depends(verify_token)):
    """Get all clients from Firebase"""
    try:
        clients = await firebase_clients.get_all_clients()
        return clients
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clients")
async def create_client(
    client_data: dict,
    current_user: dict = Depends(verify_token)
):
    """Create a new client in Firebase"""
    try:
        if not client_data.get('name'):
            raise HTTPException(status_code=400, detail="Client name is required")
        
        client_id = await firebase_clients.create_client(client_data)
        return {"message": "Client created successfully", "client_id": client_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail=str(e))
