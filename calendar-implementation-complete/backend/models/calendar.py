"""
Calendar models for EmailPilot
Handles calendar events and related data structures
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    event_date = Column(Date, nullable=False)
    color = Column(String(50), default="bg-gray-200 text-gray-800")
    
    # Foreign key to client
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Event type classification
    event_type = Column(String(100), nullable=True)  # RRB Promotion, Cheese Club, etc.
    
    # Campaign details
    segment = Column(String(255), nullable=True)
    send_time = Column(String(100), nullable=True)
    subject_a = Column(String(255), nullable=True)
    subject_b = Column(String(255), nullable=True)
    preview_text = Column(Text, nullable=True)
    main_cta = Column(String(255), nullable=True)
    offer = Column(Text, nullable=True)
    ab_test = Column(String(255), nullable=True)
    
    # Import metadata
    imported_from_doc = Column(Boolean, default=False)
    import_doc_id = Column(String(255), nullable=True)
    original_event_id = Column(String(100), nullable=True)  # For Firebase migration
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="calendar_events")


class CalendarImportLog(Base):
    __tablename__ = "calendar_import_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Import details
    import_type = Column(String(50), nullable=False)  # google_doc, csv, manual
    source_id = Column(String(255), nullable=True)  # doc_id, filename, etc.
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Results
    events_imported = Column(Integer, default=0)
    events_updated = Column(Integer, default=0)
    events_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Import data
    raw_data = Column(Text, nullable=True)  # JSON of imported data
    processed_data = Column(Text, nullable=True)  # JSON of processed events
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client")


class CalendarChatHistory(Base):
    __tablename__ = "calendar_chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Chat details
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    is_action = Column(Boolean, default=False)
    action_type = Column(String(50), nullable=True)  # create, update, delete
    action_result = Column(Text, nullable=True)  # JSON of action details
    
    # Session tracking
    session_id = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client")