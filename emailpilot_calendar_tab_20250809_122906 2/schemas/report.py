"""
Report schemas for request/response
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ReportBase(BaseModel):
    type: str  # weekly, monthly, audit
    title: str
    
class ReportCreate(ReportBase):
    client_id: Optional[int] = None

class ReportResponse(ReportBase):
    id: int
    client_id: Optional[int]
    status: str
    data: Optional[Dict[str, Any]] = None
    slack_posted: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True