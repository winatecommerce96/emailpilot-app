"""
Goal schemas for request/response
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GoalBase(BaseModel):
    year: int
    month: int  # 1-12
    revenue_goal: float
    calculation_method: str = "manual"
    notes: Optional[str] = None
    human_override: bool = False

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    revenue_goal: Optional[float] = None
    notes: Optional[str] = None
    human_override: Optional[bool] = None

class GoalResponse(GoalBase):
    id: int
    client_id: int
    confidence: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True