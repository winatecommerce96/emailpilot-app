"""
Database Adapter Module

This module provides adapter functions that connect the API endpoints
in api.py to the Firestore service, implementing all the required
database operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .firestore_service import (
    get_firestore_service,
    FirestoreService,
    ClientNotFoundError,
    CampaignNotFoundError,
    ValidationError,
    FirestoreServiceError
)

# Client Operations

async def fetch_all_clients() -> List[Dict[str, Any]]:
    """Fetch all clients from database"""
    service = await get_firestore_service()
    return await service.get_all_clients()

async def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """Get client by ID"""
    service = await get_firestore_service()
    return await service.get_client_by_id(client_id)

async def get_client_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get client by name"""
    service = await get_firestore_service()
    return await service.get_client_by_name(name)

async def create_new_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new client in database"""
    service = await get_firestore_service()
    return await service.create_client(client_data)

async def delete_client_by_id(client_id: str) -> None:
    """Delete client from database"""
    service = await get_firestore_service()
    await service.delete_client(client_id, force=False)

async def count_active_campaigns(client_id: str) -> int:
    """Count active campaigns for client"""
    service = await get_firestore_service()
    return await service.count_active_campaigns(client_id)

# Campaign Operations

async def fetch_campaigns_by_client(client_id: str) -> List[Dict[str, Any]]:
    """Fetch campaigns for specific client"""
    service = await get_firestore_service()
    return await service.get_campaigns_by_client(client_id)

async def bulk_create_campaigns(client_id: str, campaigns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bulk create/update campaigns"""
    service = await get_firestore_service()
    return await service.bulk_create_campaigns(client_id, campaigns)

async def delete_campaigns_by_client(client_id: str) -> None:
    """Delete all campaigns for client"""
    service = await get_firestore_service()
    await service.delete_campaigns_by_client(client_id)

async def fetch_recent_campaigns(client_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent campaigns for client"""
    service = await get_firestore_service()
    return await service.get_recent_campaigns(client_id, limit)

# AI and Integration Operations

async def call_gemini_ai(context: Dict[str, Any]) -> Dict[str, Any]:
    """Call Gemini AI service"""
    # TODO: Implement Gemini AI integration
    # This would typically involve making API calls to Google's Gemini API
    # For now, return a placeholder response
    return {
        "response": "AI service integration not yet implemented. This is a placeholder response.",
        "suggestions": ["Implement Gemini AI integration", "Add proper context handling", "Configure API credentials"]
    }

async def import_campaigns_from_doc(doc_id: str, client_id: str, mode: str) -> Dict[str, Any]:
    """Import campaigns from Google Doc"""
    # TODO: Implement Google Doc integration
    # This would involve using Google Docs API to read document content
    # and parse campaign information
    return {
        "success": True,
        "imported_count": 0,
        "skipped_count": 0,
        "messages": ["Google Doc import not yet implemented"]
    }

async def commit_calendar_to_sheet(params: Dict[str, Any]) -> Dict[str, Any]:
    """Commit calendar to Google Sheet"""
    # TODO: Implement Google Sheets integration
    # This would involve using Google Sheets API to write campaign data
    return {
        "rows_updated": 0,
        "message": "Google Sheets integration not yet implemented"
    }

# Chat History Operations

async def save_chat_message(user_message: str, ai_response: str, 
                           client_id: str = None, context: Dict[str, Any] = None) -> str:
    """Save chat message to history"""
    service = await get_firestore_service()
    message_data = {
        'user_message': user_message,
        'ai_response': ai_response,
        'client_id': client_id,
        'context': context or {}
    }
    return await service.save_chat_message(message_data)

async def get_chat_history(client_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get chat history for client or global"""
    service = await get_firestore_service()
    return await service.get_chat_history(client_id, limit)

# Calendar State Operations

async def save_calendar_state(client_id: str, state_data: Dict[str, Any]) -> None:
    """Save calendar view state for a client"""
    service = await get_firestore_service()
    await service.save_calendar_state(client_id, state_data)

async def load_calendar_state(client_id: str) -> Optional[Dict[str, Any]]:
    """Load calendar view state for a client"""
    service = await get_firestore_service()
    return await service.load_calendar_state(client_id)