"""
Calendar API Router Module

FastAPI router for calendar application with client management,
campaign operations, AI chat integration, and Google Docs/Sheets integration.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator
import httpx
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(prefix="/api", tags=["calendar"])

# Pydantic Models for Request/Response Validation

class ClientBase(BaseModel):
    """Base client model with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Client name")

class ClientCreate(ClientBase):
    """Model for creating a new client"""
    pass

class ClientResponse(ClientBase):
    """Model for client response data"""
    id: str = Field(..., description="Unique client identifier")
    created_at: datetime = Field(..., description="Client creation timestamp")
    campaign_count: Optional[int] = Field(0, description="Number of campaigns for this client")

    class Config:
        from_attributes = True

class CampaignBase(BaseModel):
    """Base campaign model"""
    title: str = Field(..., min_length=1, max_length=500, description="Campaign title")
    description: Optional[str] = Field(None, max_length=2000, description="Campaign description")
    start_date: datetime = Field(..., description="Campaign start date")
    end_date: Optional[datetime] = Field(None, description="Campaign end date")
    status: str = Field("draft", pattern="^(draft|scheduled|active|completed|cancelled)$")
    campaign_type: str = Field("email", pattern="^(email|sms|push|social)$")
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$")

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class CampaignCreate(CampaignBase):
    """Model for creating/updating campaigns"""
    pass

class CampaignResponse(CampaignBase):
    """Model for campaign response data"""
    id: str = Field(..., description="Unique campaign identifier")
    client_id: str = Field(..., description="Associated client identifier")
    created_at: datetime = Field(..., description="Campaign creation timestamp")
    updated_at: datetime = Field(..., description="Campaign last update timestamp")

    class Config:
        from_attributes = True

class CampaignBulkCreate(BaseModel):
    """Model for bulk campaign creation/update"""
    campaigns: List[CampaignCreate] = Field(..., description="List of campaigns to create/update")
    replace_existing: bool = Field(False, description="Whether to replace all existing campaigns")

class ChatMessage(BaseModel):
    """Model for AI chat messages"""
    message: str = Field(..., min_length=1, max_length=5000, description="Chat message content")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for the AI")
    client_id: Optional[str] = Field(None, description="Client context for personalized responses")

class ChatResponse(BaseModel):
    """Model for AI chat responses"""
    response: str = Field(..., description="AI response message")
    suggestions: Optional[List[str]] = Field(None, description="Optional action suggestions")
    timestamp: datetime = Field(default_factory=datetime.now)

class GoogleDocImport(BaseModel):
    """Model for Google Doc import request"""
    doc_url: str = Field(..., pattern=r"^https://docs\.google\.com/document/", description="Google Doc URL")
    client_id: str = Field(..., description="Target client for imported campaigns")
    import_mode: str = Field("append", pattern="^(append|replace)$", description="Import mode")

class GoogleSheetCommit(BaseModel):
    """Model for Google Sheet commit request"""
    sheet_url: str = Field(..., pattern=r"^https://docs\.google\.com/spreadsheets/", description="Google Sheet URL")
    client_id: Optional[str] = Field(None, description="Client to commit (all clients if None)")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Date range for commit")

class ImportResponse(BaseModel):
    """Model for import operation response"""
    success: bool = Field(..., description="Import success status")
    imported_count: int = Field(..., description="Number of campaigns imported")
    skipped_count: int = Field(0, description="Number of campaigns skipped")
    messages: List[str] = Field(default_factory=list, description="Import messages/warnings")

class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    timestamp: datetime = Field(default_factory=datetime.now)

# Dependency functions for common operations

async def get_client_or_404(client_id: str) -> Dict[str, Any]:
    """Retrieve client or raise 404 if not found"""
    # TODO: Replace with actual database query
    # This is a placeholder - implement with your database layer
    client = await get_client_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found"
        )
    return client

# API Endpoints

@router.get("/clients", response_model=List[ClientResponse])
async def get_all_clients():
    """
    Retrieve all clients with their basic information and campaign counts.
    
    Returns:
        List of clients with metadata
    """
    try:
        clients_data = await fetch_all_clients()
        return [ClientResponse(**client) for client in clients_data]
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clients"
        )

@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(client_data: ClientCreate):
    """
    Create a new client.
    
    Args:
        client_data: Client creation data
        
    Returns:
        Created client information
        
    Raises:
        400: If client name already exists
        500: If database operation fails
    """
    try:
        # Check if client name already exists
        existing_client = await get_client_by_name(client_data.name)
        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client with name '{client_data.name}' already exists"
            )
        
        # Create new client
        client_dict = client_data.dict()
        new_client = await create_new_client(client_dict)
        return ClientResponse(**new_client)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client"
        )

@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: str):
    """
    Delete a client and all associated campaigns.
    
    Args:
        client_id: ID of the client to delete
        
    Raises:
        404: If client not found
        409: If client has active campaigns
        500: If database operation fails
    """
    try:
        client = await get_client_or_404(client_id)
        
        # Check for active campaigns
        active_campaigns = await count_active_campaigns(client_id)
        if active_campaigns > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete client with {active_campaigns} active campaigns"
            )
        
        await delete_client_by_id(client_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client"
        )

@router.get("/clients/{client_id}/campaigns", response_model=List[CampaignResponse])
async def get_client_campaigns(client_id: str):
    """
    Retrieve all campaigns for a specific client.
    
    Args:
        client_id: ID of the client
        
    Returns:
        List of campaigns for the client
        
    Raises:
        404: If client not found
    """
    try:
        await get_client_or_404(client_id)
        campaigns_data = await fetch_campaigns_by_client(client_id)
        return [CampaignResponse(**campaign) for campaign in campaigns_data]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching campaigns for client {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve campaigns"
        )

@router.post("/clients/{client_id}/campaigns", response_model=List[CampaignResponse])
async def create_update_campaigns(client_id: str, campaign_data: CampaignBulkCreate):
    """
    Create or update campaigns for a client.
    
    Args:
        client_id: ID of the client
        campaign_data: Campaign creation/update data
        
    Returns:
        List of created/updated campaigns
        
    Raises:
        404: If client not found
        400: If campaign data is invalid
    """
    try:
        await get_client_or_404(client_id)
        
        if campaign_data.replace_existing:
            # Delete existing campaigns first
            await delete_campaigns_by_client(client_id)
        
        # Create/update campaigns
        campaigns_list = [campaign.dict() for campaign in campaign_data.campaigns]
        campaigns = await bulk_create_campaigns(client_id, campaigns_list)
        return [CampaignResponse(**campaign) for campaign in campaigns]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaigns for client {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create/update campaigns"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(message_data: ChatMessage):
    """
    Send message to Gemini AI for calendar assistance.
    
    Args:
        message_data: Chat message and context
        
    Returns:
        AI response with suggestions
        
    Raises:
        400: If message is invalid
        503: If AI service is unavailable
    """
    try:
        # Prepare context for AI
        context = {
            "message": message_data.message,
            "context": message_data.context or {},
            "client_id": message_data.client_id
        }
        
        # Add client information if provided
        if message_data.client_id:
            client = await get_client_by_id(message_data.client_id)
            if client:
                context["client_info"] = client
                context["recent_campaigns"] = await fetch_recent_campaigns(message_data.client_id)
        
        # Call Gemini AI service
        ai_response = await call_gemini_ai(context)
        
        # Save chat message to history
        chat_response = ChatResponse(
            response=ai_response.get("response", ""),
            suggestions=ai_response.get("suggestions", [])
        )
        
        await save_chat_message(
            user_message=message_data.message,
            ai_response=chat_response.response,
            client_id=message_data.client_id,
            context=context
        )
        
        return chat_response
    except Exception as e:
        logger.error(f"Error in AI chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable"
        )

@router.post("/import-doc", response_model=ImportResponse)
async def import_google_doc(import_data: GoogleDocImport):
    """
    Import campaigns from Google Doc.
    
    Args:
        import_data: Google Doc import configuration
        
    Returns:
        Import results with counts and messages
        
    Raises:
        404: If client not found
        400: If document is inaccessible
        503: If Google API is unavailable
    """
    try:
        await get_client_or_404(import_data.client_id)
        
        # Extract document ID from URL
        doc_id = extract_google_doc_id(import_data.doc_url)
        if not doc_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google Doc URL"
            )
        
        # Import campaigns from document
        import_result = await import_campaigns_from_doc(
            doc_id, 
            import_data.client_id, 
            import_data.import_mode
        )
        
        return ImportResponse(**import_result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing Google Doc: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to import from Google Doc"
        )

@router.post("/commit-sheet", response_model=Dict[str, Any])
async def commit_to_google_sheet(commit_data: GoogleSheetCommit):
    """
    Commit calendar data to Google Sheet.
    
    Args:
        commit_data: Google Sheet commit configuration
        
    Returns:
        Commit results with status and metadata
        
    Raises:
        400: If sheet is inaccessible
        503: If Google API is unavailable
    """
    try:
        # Extract sheet ID from URL
        sheet_id = extract_google_sheet_id(commit_data.sheet_url)
        if not sheet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google Sheet URL"
            )
        
        # Prepare data for commit
        commit_params = {
            "sheet_id": sheet_id,
            "client_id": commit_data.client_id,
            "date_range": commit_data.date_range
        }
        
        # Commit to sheet
        commit_result = await commit_calendar_to_sheet(commit_params)
        
        return {
            "success": True,
            "committed_rows": commit_result.get("rows_updated", 0),
            "sheet_url": commit_data.sheet_url,
            "timestamp": datetime.now(),
            "message": "Calendar successfully committed to Google Sheet"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing to Google Sheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to commit to Google Sheet"
        )

# Import database adapter functions
from ..services.database_adapter import (
    fetch_all_clients,
    get_client_by_id,
    get_client_by_name,
    create_new_client,
    delete_client_by_id,
    count_active_campaigns,
    fetch_campaigns_by_client,
    bulk_create_campaigns,
    delete_campaigns_by_client,
    fetch_recent_campaigns,
    call_gemini_ai,
    import_campaigns_from_doc,
    commit_calendar_to_sheet,
    save_chat_message
)

def extract_google_doc_id(url: str) -> Optional[str]:
    """Extract document ID from Google Doc URL"""
    import re
    pattern = r"/document/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def extract_google_sheet_id(url: str) -> Optional[str]:
    """Extract sheet ID from Google Sheet URL"""
    import re
    pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None