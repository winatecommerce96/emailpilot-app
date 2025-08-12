#!/usr/bin/env python3
"""
Firebase Calendar Integration for EmailPilot
Implements calendar functionality using Firebase Firestore for scalability
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin

logger = logging.getLogger(__name__)

class FirebaseCalendarService:
    """Service for managing calendar data in Firebase Firestore"""
    
    def __init__(self):
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to get service account from environment or file
                service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'emailpilot-calendar')
                
                if service_account_path and os.path.exists(service_account_path):
                    # Use service account file
                    cred = credentials.Certificate(service_account_path)
                    initialize_app(cred, {'projectId': project_id})
                else:
                    # Use default credentials (for Cloud Run, etc.)
                    initialize_app(options={'projectId': project_id})
                
                logger.info(f"Firebase initialized for project: {project_id}")
            
            self.db = firestore.client()
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    async def get_client_events(self, client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Get calendar events for a client"""
        try:
            query = self.db.collection('calendar_events').where('client_id', '==', client_id)
            
            if start_date:
                query = query.where('event_date', '>=', start_date)
            if end_date:
                query = query.where('event_date', '<=', end_date)
            
            docs = query.order_by('event_date').stream()
            
            events = []
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events for client {client_id}: {e}")
            return []
    
    async def create_event(self, event_data: Dict) -> str:
        """Create a new calendar event"""
        try:
            # Add timestamps
            event_data['created_at'] = firestore.SERVER_TIMESTAMP
            event_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Create document
            doc_ref = self.db.collection('calendar_events').add(event_data)
            event_id = doc_ref[1].id
            
            logger.info(f"Created event: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            raise
    
    async def update_event(self, event_id: str, updates: Dict) -> bool:
        """Update an existing calendar event"""
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            
            self.db.collection('calendar_events').document(event_id).update(updates)
            
            logger.info(f"Updated event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}")
            return False
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            self.db.collection('calendar_events').document(event_id).delete()
            
            logger.info(f"Deleted event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return False
    
    async def duplicate_event(self, event_id: str) -> Optional[str]:
        """Duplicate an existing calendar event"""
        try:
            # Get original event
            doc = self.db.collection('calendar_events').document(event_id).get()
            
            if not doc.exists:
                return None
            
            # Create copy
            event_data = doc.to_dict()
            event_data['title'] = f"{event_data['title']} (Copy)"
            
            # Remove timestamps to generate new ones
            event_data.pop('created_at', None)
            event_data.pop('updated_at', None)
            
            return await self.create_event(event_data)
            
        except Exception as e:
            logger.error(f"Error duplicating event {event_id}: {e}")
            return None
    
    async def get_client_stats(self, client_id: str) -> Dict:
        """Get calendar statistics for a client"""
        try:
            # Get all events for client
            events = await self.get_client_events(client_id)
            
            # Calculate stats
            now = datetime.now()
            current_month_start = now.replace(day=1).strftime('%Y-%m-%d')
            next_month = (now.replace(day=28).replace(month=now.month+1) if now.month < 12 
                         else now.replace(day=28, month=1, year=now.year+1))
            next_month_start = next_month.replace(day=1).strftime('%Y-%m-%d')
            
            total_events = len(events)
            events_this_month = len([e for e in events if e['event_date'] >= current_month_start and e['event_date'] < next_month_start])
            events_next_month = len([e for e in events if e['event_date'] >= next_month_start])
            
            # Event types breakdown
            event_types = {}
            for event in events:
                event_type = event.get('event_type', 'Unclassified')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Upcoming events (next 7 days)
            upcoming_date = (now.strftime('%Y-%m-%d'), 
                           (now + timedelta(days=7)).strftime('%Y-%m-%d'))
            upcoming_events = [e for e in events 
                             if upcoming_date[0] <= e['event_date'] <= upcoming_date[1]][:5]
            
            return {
                'total_events': total_events,
                'events_this_month': events_this_month,
                'events_next_month': events_next_month,
                'event_types': event_types,
                'upcoming_events': upcoming_events
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for client {client_id}: {e}")
            return {}


class FirebaseClientService:
    """Service for managing client data in Firebase Firestore"""
    
    def __init__(self):
        self.db = firestore.client()
    
    async def get_all_clients(self) -> List[Dict]:
        """Get all active clients"""
        try:
            docs = self.db.collection('clients').where('is_active', '==', True).stream()
            
            clients = []
            for doc in docs:
                client_data = doc.to_dict()
                client_data['id'] = doc.id
                clients.append(client_data)
            
            return clients
            
        except Exception as e:
            logger.error(f"Error fetching clients: {e}")
            return []
    
    async def get_client(self, client_id: str) -> Optional[Dict]:
        """Get a specific client"""
        try:
            doc = self.db.collection('clients').document(client_id).get()
            
            if doc.exists:
                client_data = doc.to_dict()
                client_data['id'] = doc.id
                return client_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching client {client_id}: {e}")
            return None
    
    async def create_client(self, client_data: Dict) -> str:
        """Create a new client"""
        try:
            client_data['created_at'] = firestore.SERVER_TIMESTAMP
            client_data['updated_at'] = firestore.SERVER_TIMESTAMP
            client_data['is_active'] = True
            
            doc_ref = self.db.collection('clients').add(client_data)
            client_id = doc_ref[1].id
            
            logger.info(f"Created client: {client_id}")
            return client_id
            
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise
    
    async def update_client(self, client_id: str, updates: Dict) -> bool:
        """Update an existing client"""
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            
            self.db.collection('clients').document(client_id).update(updates)
            
            logger.info(f"Updated client: {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating client {client_id}: {e}")
            return False


class FirebaseChatService:
    """Service for managing AI chat history in Firebase Firestore"""
    
    def __init__(self):
        self.db = firestore.client()
    
    async def save_chat_message(self, client_id: str, user_message: str, ai_response: str, 
                               is_action: bool = False, action_type: str = None, 
                               session_id: str = None) -> str:
        """Save a chat interaction"""
        try:
            chat_data = {
                'client_id': client_id,
                'user_message': user_message,
                'ai_response': ai_response,
                'is_action': is_action,
                'action_type': action_type,
                'session_id': session_id,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection('calendar_chat_history').add(chat_data)
            chat_id = doc_ref[1].id
            
            return chat_id
            
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            raise
    
    async def get_chat_history(self, client_id: str, session_id: str = None, 
                             limit: int = 10) -> List[Dict]:
        """Get chat history for a client"""
        try:
            query = self.db.collection('calendar_chat_history').where('client_id', '==', client_id)
            
            if session_id:
                query = query.where('session_id', '==', session_id)
            
            docs = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            history = []
            for doc in docs:
                chat_data = doc.to_dict()
                chat_data['id'] = doc.id
                history.append(chat_data)
            
            return list(reversed(history))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []


# Initialize services
firebase_calendar = FirebaseCalendarService()
firebase_clients = FirebaseClientService()
firebase_chat = FirebaseChatService()