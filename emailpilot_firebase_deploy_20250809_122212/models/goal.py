"""
Goal model for revenue goals
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    revenue_goal = Column(Float, nullable=False)
    calculation_method = Column(String(50), nullable=False)  # ai_suggested, manual, inherited
    notes = Column(Text, nullable=True)
    confidence = Column(String(20), default="medium")  # low, medium, high
    human_override = Column(Boolean, default=False)
    seasonal_multiplier = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="goals")
    
    # Ensure unique constraint per client/year/month
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )