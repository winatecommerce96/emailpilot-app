"""
Pydantic schemas for calendar operations
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any

class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    event_date: date
    color: str = Field(default="bg-gray-200 text-gray-800", max_length=50)
    event_type: Optional[str] = None
    
    # Campaign details
    segment: Optional[str] = None
    send_time: Optional[str] = None
    subject_a: Optional[str] = None
    subject_b: Optional[str] = None
    preview_text: Optional[str] = None
    main_cta: Optional[str] = None
    offer: Optional[str] = None
    ab_test: Optional[str] = None

class CalendarEventCreate(CalendarEventBase):
    client_id: str

class CalendarEventUpdate(CalendarEventBase):
    title: Optional[str] = None
    event_date: Optional[date] = None
    client_id: Optional[str] = None

class CalendarEventResponse(CalendarEventBase):
    id: str
    client_id: str
    imported_from_doc: bool = False
    import_doc_id: Optional[str] = None
    original_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GoogleDocImportRequest(BaseModel):
    client_id: str
    doc_id: str
    access_token: str

class CalendarChatRequest(BaseModel):
    client_id: str
    message: str
    chat_history: Optional[List[Dict[str, Any]]] = []

class AICalendarRequest(BaseModel):
    """Enhanced AI request for calendar operations"""
    message: str
    client_id: str
    chat_history: Optional[List[Dict[str, Any]]] = []
    context: Optional[Dict[str, Any]] = {}

class CampaignPlanRequest(BaseModel):
    """Request schema for AI-powered campaign planning"""
    client_id: str = Field(..., description="Client identifier")
    campaign_type: str = Field(..., description="Type of campaign: New Product, Limited Time Offer, Flash Sale, Other")
    start_date: str = Field(..., description="Campaign start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="Campaign end date in YYYY-MM-DD format")
    promotion_details: str = Field(..., description="Details about the promotion, product, or campaign objective")

class CampaignPlanResponse(BaseModel):
    """Response schema for campaign planning"""
    campaign_plan: str = Field(..., description="AI-generated campaign strategy")
    events_created: List[Dict[str, Any]] = Field(..., description="List of calendar events created")
    total_events: int = Field(..., description="Total number of events created")
    touchpoints: Dict[str, int] = Field(..., description="Breakdown of touchpoints by type")

class AIAction(BaseModel):
    action: str  # create, update, delete
    event_id: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    updates: Optional[Dict[str, Any]] = None

class AIResponse(BaseModel):
    message: str
    is_action: bool = False
    action: Optional[AIAction] = None

class CalendarImportLogResponse(BaseModel):
    id: str
    client_id: str
    import_type: str
    source_id: Optional[str] = None
    status: str
    events_imported: int = 0
    events_updated: int = 0
    events_failed: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CalendarStatsResponse(BaseModel):
    total_events: int
    events_this_month: int
    events_next_month: int
    event_types: Dict[str, int]
    upcoming_events: List[CalendarEventResponse]

class CalendarExportResponse(BaseModel):
    client_name: str
    export_date: str
    total_events: int
    events: List[CalendarEventResponse]