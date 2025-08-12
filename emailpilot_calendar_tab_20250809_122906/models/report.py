"""
Report model for generated reports
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)  # None for company-wide
    type = Column(String(50), nullable=False)  # weekly, monthly, audit
    status = Column(String(20), default="pending")  # pending, completed, failed
    title = Column(String(255), nullable=False)
    data = Column(JSON, nullable=True)  # Report data in JSON format
    slack_posted = Column(String(20), default="no")  # no, yes, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="reports")