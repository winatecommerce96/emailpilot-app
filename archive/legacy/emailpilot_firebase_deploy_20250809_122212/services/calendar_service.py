"""
Calendar service for handling calendar operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import json
import logging
import csv
import io

from app.models.calendar import CalendarEvent, CalendarImportLog
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventResponse,
    CalendarStatsResponse,
    AIAction
)
from app.services.google_service import GoogleService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.google_service = GoogleService()
        self.gemini_service = GeminiService()

    async def get_events(
        self,
        db: Session,
        client_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[CalendarEventResponse]:
        """Get calendar events with optional filtering"""
        query = db.query(CalendarEvent)
        
        if client_id:
            query = query.filter(CalendarEvent.client_id == client_id)
        
        if start_date:
            query = query.filter(CalendarEvent.event_date >= start_date)
            
        if end_date:
            query = query.filter(CalendarEvent.event_date <= end_date)
        
        events = query.order_by(CalendarEvent.event_date).all()
        
        return [CalendarEventResponse.from_orm(event) for event in events]

    async def create_event(
        self,
        db: Session,
        event_data: CalendarEventCreate
    ) -> CalendarEventResponse:
        """Create a new calendar event"""
        db_event = CalendarEvent(**event_data.dict())
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Created calendar event: {db_event.title} for client {db_event.client_id}")
        
        return CalendarEventResponse.from_orm(db_event)

    async def update_event(
        self,
        db: Session,
        event_id: int,
        event_data: CalendarEventUpdate
    ) -> Optional[CalendarEventResponse]:
        """Update an existing calendar event"""
        db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        
        if not db_event:
            return None
        
        # Update only provided fields
        update_data = event_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_event, field, value)
        
        db_event.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Updated calendar event: {db_event.title}")
        
        return CalendarEventResponse.from_orm(db_event)

    async def delete_event(self, db: Session, event_id: int) -> bool:
        """Delete a calendar event"""
        db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        
        if not db_event:
            return False
        
        title = db_event.title
        db.delete(db_event)
        db.commit()
        
        logger.info(f"Deleted calendar event: {title}")
        
        return True

    async def duplicate_event(
        self,
        db: Session,
        event_id: int
    ) -> Optional[CalendarEventResponse]:
        """Duplicate an existing calendar event"""
        original_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        
        if not original_event:
            return None
        
        # Create new event with "(Copy)" suffix
        new_event_data = {
            "title": f"{original_event.title} (Copy)",
            "content": original_event.content,
            "event_date": original_event.event_date,
            "color": original_event.color,
            "event_type": original_event.event_type,
            "client_id": original_event.client_id,
            "segment": original_event.segment,
            "send_time": original_event.send_time,
            "subject_a": original_event.subject_a,
            "subject_b": original_event.subject_b,
            "preview_text": original_event.preview_text,
            "main_cta": original_event.main_cta,
            "offer": original_event.offer,
            "ab_test": original_event.ab_test
        }
        
        db_event = CalendarEvent(**new_event_data)
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Duplicated calendar event: {db_event.title}")
        
        return CalendarEventResponse.from_orm(db_event)

    async def import_from_google_doc(
        self,
        db: Session,
        client_id: int,
        doc_id: str,
        access_token: str
    ) -> None:
        """Import calendar events from Google Doc (background task)"""
        import_log = CalendarImportLog(
            client_id=client_id,
            import_type="google_doc",
            source_id=doc_id,
            status="processing"
        )
        
        db.add(import_log)
        db.commit()
        
        try:
            # Extract text from Google Doc
            doc_content = await self.google_service.get_document_content(doc_id, access_token)
            
            if not doc_content:
                raise Exception("No content found in document")
            
            import_log.raw_data = doc_content
            db.commit()
            
            # Process with Gemini AI
            campaigns = await self.gemini_service.process_campaign_document(doc_content)
            
            if not campaigns:
                raise Exception("No campaigns extracted from document")
            
            import_log.processed_data = json.dumps(campaigns)
            
            # Create events
            events_created = 0
            events_failed = 0
            
            for campaign in campaigns:
                try:
                    event_data = CalendarEventCreate(
                        title=campaign.get("title", "Untitled Campaign"),
                        content=campaign.get("content", ""),
                        event_date=datetime.strptime(campaign.get("date"), "%Y-%m-%d").date(),
                        color=campaign.get("color", "bg-gray-200 text-gray-800"),
                        client_id=client_id,
                        imported_from_doc=True,
                        import_doc_id=doc_id
                    )
                    
                    await self.create_event(db, event_data)
                    events_created += 1
                    
                except Exception as e:
                    logger.error(f"Failed to create event from campaign: {e}")
                    events_failed += 1
                    continue
            
            # Update import log
            import_log.events_imported = events_created
            import_log.events_failed = events_failed
            import_log.status = "completed"
            import_log.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Import completed: {events_created} events created, {events_failed} failed")
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            import_log.status = "failed"
            import_log.error_message = str(e)
            import_log.completed_at = datetime.utcnow()
            db.commit()
            raise

    async def execute_ai_action(
        self,
        db: Session,
        action: Dict[str, Any],
        client_id: int
    ) -> Dict[str, Any]:
        """Execute an AI-requested action on calendar events"""
        action_type = action.get("action")
        
        if action_type == "delete":
            event_id = action.get("eventId")
            if not event_id:
                return {"success": False, "message": "No event ID provided"}
            
            # Convert Firebase-style ID to database ID if needed
            db_event = db.query(CalendarEvent).filter(
                and_(
                    CalendarEvent.client_id == client_id,
                    CalendarEvent.original_event_id == event_id
                )
            ).first()
            
            if not db_event:
                # Try direct ID lookup
                try:
                    db_event = db.query(CalendarEvent).filter(
                        CalendarEvent.id == int(event_id.replace("event-", ""))
                    ).first()
                except:
                    pass
            
            if db_event:
                success = await self.delete_event(db, db_event.id)
                return {
                    "success": success,
                    "message": "Event deleted successfully" if success else "Failed to delete event"
                }
            else:
                return {"success": False, "message": "Event not found"}
                
        elif action_type == "update":
            event_id = action.get("eventId")
            updates = action.get("updates", {})
            
            if not event_id or not updates:
                return {"success": False, "message": "Missing event ID or updates"}
            
            # Find event (similar logic as delete)
            db_event = db.query(CalendarEvent).filter(
                and_(
                    CalendarEvent.client_id == client_id,
                    CalendarEvent.original_event_id == event_id
                )
            ).first()
            
            if not db_event:
                try:
                    db_event = db.query(CalendarEvent).filter(
                        CalendarEvent.id == int(event_id.replace("event-", ""))
                    ).first()
                except:
                    pass
            
            if db_event:
                update_data = CalendarEventUpdate(**updates)
                updated_event = await self.update_event(db, db_event.id, update_data)
                return {
                    "success": True,
                    "message": "Event updated successfully"
                }
            else:
                return {"success": False, "message": "Event not found"}
                
        elif action_type == "create":
            event_data = action.get("event", {})
            
            if not event_data:
                return {"success": False, "message": "No event data provided"}
            
            try:
                create_data = CalendarEventCreate(
                    client_id=client_id,
                    **event_data
                )
                new_event = await self.create_event(db, create_data)
                return {
                    "success": True,
                    "message": f"Event '{new_event.title}' created successfully"
                }
            except Exception as e:
                return {"success": False, "message": f"Failed to create event: {str(e)}"}
        
        return {"success": False, "message": "Unknown action type"}

    async def get_client_stats(
        self,
        db: Session,
        client_id: int
    ) -> CalendarStatsResponse:
        """Get calendar statistics for a client"""
        now = datetime.now()
        current_month_start = now.replace(day=1).date()
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        next_month_end = (next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Total events
        total_events = db.query(CalendarEvent).filter(
            CalendarEvent.client_id == client_id
        ).count()
        
        # Events this month
        events_this_month = db.query(CalendarEvent).filter(
            and_(
                CalendarEvent.client_id == client_id,
                CalendarEvent.event_date >= current_month_start,
                CalendarEvent.event_date < next_month.date()
            )
        ).count()
        
        # Events next month
        events_next_month = db.query(CalendarEvent).filter(
            and_(
                CalendarEvent.client_id == client_id,
                CalendarEvent.event_date >= next_month.date(),
                CalendarEvent.event_date <= next_month_end.date()
            )
        ).count()
        
        # Event types count
        event_types = db.query(
            CalendarEvent.event_type,
            func.count(CalendarEvent.id)
        ).filter(
            CalendarEvent.client_id == client_id
        ).group_by(CalendarEvent.event_type).all()
        
        event_types_dict = {
            event_type or "Unclassified": count 
            for event_type, count in event_types
        }
        
        # Upcoming events (next 7 days)
        upcoming_date = now.date() + timedelta(days=7)
        upcoming_events = db.query(CalendarEvent).filter(
            and_(
                CalendarEvent.client_id == client_id,
                CalendarEvent.event_date >= now.date(),
                CalendarEvent.event_date <= upcoming_date
            )
        ).order_by(CalendarEvent.event_date).limit(5).all()
        
        return CalendarStatsResponse(
            total_events=total_events,
            events_this_month=events_this_month,
            events_next_month=events_next_month,
            event_types=event_types_dict,
            upcoming_events=[CalendarEventResponse.from_orm(event) for event in upcoming_events]
        )

    async def export_to_csv(self, events: List[CalendarEventResponse]) -> str:
        """Export events to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Title", "Date", "Type", "Segment", "Send Time", 
            "Subject A", "Subject B", "Preview Text", "Main CTA", "Offer", "A/B Test"
        ])
        
        # Write data
        for event in events:
            writer.writerow([
                event.title,
                event.event_date.strftime("%Y-%m-%d"),
                event.event_type or "",
                event.segment or "",
                event.send_time or "",
                event.subject_a or "",
                event.subject_b or "",
                event.preview_text or "",
                event.main_cta or "",
                event.offer or "",
                event.ab_test or ""
            ])
        
        return output.getvalue()