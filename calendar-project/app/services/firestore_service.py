"""
Firestore Service Module for Calendar Application

This module provides comprehensive database operations for the calendar application
using Firebase Admin SDK. Handles client management, campaign data, calendar state,
and chat history with proper error handling and async operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from uuid import uuid4
import json

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import AsyncClient, AsyncTransaction
from google.cloud.exceptions import GoogleCloudError, NotFound, Conflict
from google.api_core import retry
import aiohttp

# Configure logging
logger = logging.getLogger(__name__)

class FirestoreServiceError(Exception):
    """Base exception for Firestore service operations"""
    pass

class ClientNotFoundError(FirestoreServiceError):
    """Raised when a client is not found"""
    pass

class CampaignNotFoundError(FirestoreServiceError):
    """Raised when a campaign is not found"""
    pass

class ValidationError(FirestoreServiceError):
    """Raised when data validation fails"""
    pass

class FirestoreService:
    """
    Comprehensive Firestore service for calendar application operations.
    
    Handles:
    - Client CRUD operations
    - Campaign data management
    - Calendar state persistence
    - Chat history storage
    - Transaction management
    """
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        """
        Initialize Firestore service.
        
        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account key file
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._db: Optional[AsyncClient] = None
        self._app: Optional[firebase_admin.App] = None
        
        # Collection names
        self.CLIENTS_COLLECTION = "clients"
        self.CAMPAIGNS_COLLECTION = "campaigns"
        self.CALENDAR_STATE_COLLECTION = "calendar_state"
        self.CHAT_HISTORY_COLLECTION = "chat_history"
        self.SYSTEM_CONFIG_COLLECTION = "system_config"
    
    async def initialize(self) -> None:
        """Initialize Firebase Admin SDK and Firestore client"""
        try:
            # Initialize Firebase Admin if not already done
            if not firebase_admin._apps:
                if self.credentials_path:
                    cred = credentials.Certificate(self.credentials_path)
                    self._app = firebase_admin.initialize_app(cred, {
                        'projectId': self.project_id
                    })
                else:
                    # Use default credentials (for Cloud Run, etc.)
                    self._app = firebase_admin.initialize_app()
            else:
                self._app = firebase_admin.get_app()
            
            # Create async Firestore client
            self._db = firestore.AsyncClient(project=self.project_id)
            
            logger.info("Firestore service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore service: {str(e)}")
            raise FirestoreServiceError(f"Initialization failed: {str(e)}")
    
    @property
    def db(self) -> AsyncClient:
        """Get Firestore database instance"""
        if not self._db:
            raise FirestoreServiceError("Firestore service not initialized. Call initialize() first.")
        return self._db
    
    # Client Management Operations
    
    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new client.
        
        Args:
            client_data: Client information (name, etc.)
            
        Returns:
            Created client data with ID and timestamps
            
        Raises:
            ValidationError: If client data is invalid
            Conflict: If client name already exists
        """
        try:
            # Validate required fields
            if not client_data.get('name'):
                raise ValidationError("Client name is required")
            
            # Check if client name already exists
            existing = await self.get_client_by_name(client_data['name'])
            if existing:
                raise Conflict(f"Client with name '{client_data['name']}' already exists")
            
            # Prepare client document
            client_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            client_doc = {
                'id': client_id,
                'name': client_data['name'],
                'created_at': now,
                'updated_at': now,
                'campaign_count': 0,
                'metadata': client_data.get('metadata', {}),
                'status': 'active'
            }
            
            # Save to Firestore
            await self.db.collection(self.CLIENTS_COLLECTION).document(client_id).set(client_doc)
            
            logger.info(f"Created client: {client_id} - {client_data['name']}")
            return client_doc
            
        except (ValidationError, Conflict):
            raise
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            raise FirestoreServiceError(f"Failed to create client: {str(e)}")
    
    async def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve client by ID.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client data or None if not found
        """
        try:
            doc_ref = self.db.collection(self.CLIENTS_COLLECTION).document(client_id)
            doc = await doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to retrieve client: {str(e)}")
    
    async def get_client_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve client by name.
        
        Args:
            name: Client name
            
        Returns:
            Client data or None if not found
        """
        try:
            query = self.db.collection(self.CLIENTS_COLLECTION).where('name', '==', name).limit(1)
            docs = await query.get()
            
            for doc in docs:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving client by name {name}: {str(e)}")
            raise FirestoreServiceError(f"Failed to retrieve client: {str(e)}")
    
    async def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Retrieve all clients with campaign counts.
        
        Returns:
            List of client data with metadata
        """
        try:
            clients = []
            
            # Get all clients
            query = self.db.collection(self.CLIENTS_COLLECTION).where('status', '==', 'active')
            docs = await query.get()
            
            for doc in docs:
                client_data = doc.to_dict()
                
                # Get campaign count for this client
                campaign_count = await self._count_campaigns_for_client(client_data['id'])
                client_data['campaign_count'] = campaign_count
                
                clients.append(client_data)
            
            # Sort by name
            clients.sort(key=lambda x: x['name'].lower())
            return clients
            
        except Exception as e:
            logger.error(f"Error retrieving all clients: {str(e)}")
            raise FirestoreServiceError(f"Failed to retrieve clients: {str(e)}")
    
    async def update_client(self, client_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update client information.
        
        Args:
            client_id: Client identifier
            update_data: Data to update
            
        Returns:
            Updated client data
            
        Raises:
            ClientNotFoundError: If client doesn't exist
        """
        try:
            doc_ref = self.db.collection(self.CLIENTS_COLLECTION).document(client_id)
            
            # Check if client exists
            doc = await doc_ref.get()
            if not doc.exists:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # Prepare update data
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            # Update document
            await doc_ref.update(update_data)
            
            # Return updated data
            updated_doc = await doc_ref.get()
            return updated_doc.to_dict()
            
        except ClientNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to update client: {str(e)}")
    
    async def delete_client(self, client_id: str, force: bool = False) -> None:
        """
        Delete client and optionally all associated campaigns.
        
        Args:
            client_id: Client identifier
            force: If True, delete even if campaigns exist
            
        Raises:
            ClientNotFoundError: If client doesn't exist
            Conflict: If client has campaigns and force=False
        """
        try:
            # Check if client exists
            client = await self.get_client_by_id(client_id)
            if not client:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # Check for existing campaigns
            campaign_count = await self._count_campaigns_for_client(client_id)
            if campaign_count > 0 and not force:
                raise Conflict(f"Client has {campaign_count} campaigns. Use force=True to delete anyway.")
            
            # Start transaction for atomic deletion
            transaction = self.db.transaction()
            await self._delete_client_transaction(transaction, client_id)
            
            logger.info(f"Deleted client: {client_id} - {client['name']}")
            
        except (ClientNotFoundError, Conflict):
            raise
        except Exception as e:
            logger.error(f"Error deleting client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to delete client: {str(e)}")
    
    @firestore.async_transactional
    async def _delete_client_transaction(self, transaction: AsyncTransaction, client_id: str) -> None:
        """Delete client and all associated data in a transaction"""
        # Delete all campaigns for this client
        campaigns_ref = self.db.collection(self.CAMPAIGNS_COLLECTION).where('client_id', '==', client_id)
        campaigns = await campaigns_ref.get()
        
        for campaign in campaigns:
            transaction.delete(campaign.reference)
        
        # Delete client document
        client_ref = self.db.collection(self.CLIENTS_COLLECTION).document(client_id)
        transaction.delete(client_ref)
    
    # Campaign Management Operations
    
    async def create_campaign(self, client_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new campaign for a client.
        
        Args:
            client_id: Client identifier
            campaign_data: Campaign information
            
        Returns:
            Created campaign data
            
        Raises:
            ClientNotFoundError: If client doesn't exist
            ValidationError: If campaign data is invalid
        """
        try:
            # Verify client exists
            client = await self.get_client_by_id(client_id)
            if not client:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # Validate campaign data
            if not campaign_data.get('title'):
                raise ValidationError("Campaign title is required")
            
            # Prepare campaign document
            campaign_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            campaign_doc = {
                'id': campaign_id,
                'client_id': client_id,
                'title': campaign_data['title'],
                'description': campaign_data.get('description', ''),
                'start_date': campaign_data.get('start_date'),
                'end_date': campaign_data.get('end_date'),
                'status': campaign_data.get('status', 'draft'),
                'campaign_type': campaign_data.get('campaign_type', 'email'),
                'priority': campaign_data.get('priority', 'medium'),
                'created_at': now,
                'updated_at': now,
                'metadata': campaign_data.get('metadata', {})
            }
            
            # Validate dates
            if campaign_doc['start_date'] and campaign_doc['end_date']:
                if campaign_doc['end_date'] < campaign_doc['start_date']:
                    raise ValidationError("End date must be after start date")
            
            # Save campaign
            await self.db.collection(self.CAMPAIGNS_COLLECTION).document(campaign_id).set(campaign_doc)
            
            # Update client campaign count
            await self._update_client_campaign_count(client_id)
            
            logger.info(f"Created campaign: {campaign_id} for client {client_id}")
            return campaign_doc
            
        except (ClientNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            raise FirestoreServiceError(f"Failed to create campaign: {str(e)}")
    
    async def get_campaigns_by_client(self, client_id: str, status: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve campaigns for a specific client.
        
        Args:
            client_id: Client identifier
            status: Optional status filter
            
        Returns:
            List of campaign data
        """
        try:
            query = self.db.collection(self.CAMPAIGNS_COLLECTION).where('client_id', '==', client_id)
            
            if status:
                query = query.where('status', '==', status)
            
            # Order by start date
            query = query.order_by('start_date', direction=firestore.Query.DESCENDING)
            
            docs = await query.get()
            campaigns = [doc.to_dict() for doc in docs]
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error retrieving campaigns for client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to retrieve campaigns: {str(e)}")
    
    async def bulk_create_campaigns(self, client_id: str, campaigns_data: List[Dict[str, Any]], 
                                    replace_existing: bool = False) -> List[Dict[str, Any]]:
        """
        Create multiple campaigns in bulk.
        
        Args:
            client_id: Client identifier
            campaigns_data: List of campaign data
            replace_existing: Whether to replace existing campaigns
            
        Returns:
            List of created campaign data
        """
        try:
            # Verify client exists
            client = await self.get_client_by_id(client_id)
            if not client:
                raise ClientNotFoundError(f"Client {client_id} not found")
            
            # If replacing, delete existing campaigns first
            if replace_existing:
                await self.delete_campaigns_by_client(client_id)
            
            # Create campaigns in batch
            created_campaigns = []
            batch = self.db.batch()
            
            for campaign_data in campaigns_data:
                campaign_id = str(uuid4())
                now = datetime.now(timezone.utc)
                
                campaign_doc = {
                    'id': campaign_id,
                    'client_id': client_id,
                    'title': campaign_data['title'],
                    'description': campaign_data.get('description', ''),
                    'start_date': campaign_data.get('start_date'),
                    'end_date': campaign_data.get('end_date'),
                    'status': campaign_data.get('status', 'draft'),
                    'campaign_type': campaign_data.get('campaign_type', 'email'),
                    'priority': campaign_data.get('priority', 'medium'),
                    'created_at': now,
                    'updated_at': now,
                    'metadata': campaign_data.get('metadata', {})
                }
                
                # Add to batch
                doc_ref = self.db.collection(self.CAMPAIGNS_COLLECTION).document(campaign_id)
                batch.set(doc_ref, campaign_doc)
                created_campaigns.append(campaign_doc)
            
            # Execute batch
            await batch.commit()
            
            # Update client campaign count
            await self._update_client_campaign_count(client_id)
            
            logger.info(f"Created {len(created_campaigns)} campaigns for client {client_id}")
            return created_campaigns
            
        except ClientNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error bulk creating campaigns: {str(e)}")
            raise FirestoreServiceError(f"Failed to bulk create campaigns: {str(e)}")
    
    async def update_campaign(self, campaign_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update campaign information.
        
        Args:
            campaign_id: Campaign identifier
            update_data: Data to update
            
        Returns:
            Updated campaign data
        """
        try:
            doc_ref = self.db.collection(self.CAMPAIGNS_COLLECTION).document(campaign_id)
            
            # Check if campaign exists
            doc = await doc_ref.get()
            if not doc.exists:
                raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            # Update document
            await doc_ref.update(update_data)
            
            # Return updated data
            updated_doc = await doc_ref.get()
            return updated_doc.to_dict()
            
        except CampaignNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to update campaign: {str(e)}")
    
    async def delete_campaigns_by_client(self, client_id: str) -> int:
        """
        Delete all campaigns for a specific client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Number of campaigns deleted
        """
        try:
            query = self.db.collection(self.CAMPAIGNS_COLLECTION).where('client_id', '==', client_id)
            docs = await query.get()
            
            if not docs:
                return 0
            
            # Delete in batches
            batch_size = 500
            deleted_count = 0
            
            for i in range(0, len(docs), batch_size):
                batch = self.db.batch()
                batch_docs = docs[i:i + batch_size]
                
                for doc in batch_docs:
                    batch.delete(doc.reference)
                    deleted_count += 1
                
                await batch.commit()
            
            # Update client campaign count
            await self._update_client_campaign_count(client_id)
            
            logger.info(f"Deleted {deleted_count} campaigns for client {client_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting campaigns for client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to delete campaigns: {str(e)}")
    
    # Calendar State Management
    
    async def save_calendar_state(self, client_id: str, state_data: Dict[str, Any]) -> None:
        """
        Save calendar view state for a client.
        
        Args:
            client_id: Client identifier
            state_data: Calendar state (view mode, filters, etc.)
        """
        try:
            doc_ref = self.db.collection(self.CALENDAR_STATE_COLLECTION).document(client_id)
            
            state_doc = {
                'client_id': client_id,
                'state': state_data,
                'updated_at': datetime.now(timezone.utc)
            }
            
            await doc_ref.set(state_doc)
            logger.debug(f"Saved calendar state for client {client_id}")
            
        except Exception as e:
            logger.error(f"Error saving calendar state for client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to save calendar state: {str(e)}")
    
    async def load_calendar_state(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Load calendar view state for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Calendar state data or None if not found
        """
        try:
            doc_ref = self.db.collection(self.CALENDAR_STATE_COLLECTION).document(client_id)
            doc = await doc_ref.get()
            
            if doc.exists:
                return doc.to_dict().get('state')
            return None
            
        except Exception as e:
            logger.error(f"Error loading calendar state for client {client_id}: {str(e)}")
            raise FirestoreServiceError(f"Failed to load calendar state: {str(e)}")
    
    # Chat History Management
    
    async def save_chat_message(self, message_data: Dict[str, Any]) -> str:
        """
        Save chat message to history.
        
        Args:
            message_data: Chat message data (user message, AI response, context)
            
        Returns:
            Message ID
        """
        try:
            message_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            message_doc = {
                'id': message_id,
                'client_id': message_data.get('client_id'),
                'user_message': message_data['user_message'],
                'ai_response': message_data['ai_response'],
                'context': message_data.get('context', {}),
                'timestamp': now,
                'session_id': message_data.get('session_id')
            }
            
            await self.db.collection(self.CHAT_HISTORY_COLLECTION).document(message_id).set(message_doc)
            return message_id
            
        except Exception as e:
            logger.error(f"Error saving chat message: {str(e)}")
            raise FirestoreServiceError(f"Failed to save chat message: {str(e)}")
    
    async def get_chat_history(self, client_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve chat history.
        
        Args:
            client_id: Optional client filter
            limit: Maximum number of messages to return
            
        Returns:
            List of chat messages
        """
        try:
            query = self.db.collection(self.CHAT_HISTORY_COLLECTION)
            
            if client_id:
                query = query.where('client_id', '==', client_id)
            
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = await query.get()
            messages = [doc.to_dict() for doc in docs]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {str(e)}")
            raise FirestoreServiceError(f"Failed to retrieve chat history: {str(e)}")
    
    # Helper Methods
    
    async def _count_campaigns_for_client(self, client_id: str) -> int:
        """Count campaigns for a specific client"""
        try:
            query = self.db.collection(self.CAMPAIGNS_COLLECTION).where('client_id', '==', client_id)
            docs = await query.get()
            return len(docs)
            
        except Exception as e:
            logger.error(f"Error counting campaigns for client {client_id}: {str(e)}")
            return 0
    
    async def _update_client_campaign_count(self, client_id: str) -> None:
        """Update campaign count for a client"""
        try:
            count = await self._count_campaigns_for_client(client_id)
            doc_ref = self.db.collection(self.CLIENTS_COLLECTION).document(client_id)
            await doc_ref.update({
                'campaign_count': count,
                'updated_at': datetime.now(timezone.utc)
            })
            
        except Exception as e:
            logger.error(f"Error updating campaign count for client {client_id}: {str(e)}")
    
    async def count_active_campaigns(self, client_id: str) -> int:
        """
        Count active campaigns for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Number of active campaigns
        """
        try:
            query = self.db.collection(self.CAMPAIGNS_COLLECTION) \
                .where('client_id', '==', client_id) \
                .where('status', 'in', ['active', 'scheduled'])
            
            docs = await query.get()
            return len(docs)
            
        except Exception as e:
            logger.error(f"Error counting active campaigns for client {client_id}: {str(e)}")
            return 0
    
    async def get_recent_campaigns(self, client_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent campaigns for a client.
        
        Args:
            client_id: Client identifier
            limit: Maximum number of campaigns to return
            
        Returns:
            List of recent campaigns
        """
        try:
            query = self.db.collection(self.CAMPAIGNS_COLLECTION) \
                .where('client_id', '==', client_id) \
                .order_by('updated_at', direction=firestore.Query.DESCENDING) \
                .limit(limit)
            
            docs = await query.get()
            campaigns = [doc.to_dict() for doc in docs]
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error retrieving recent campaigns for client {client_id}: {str(e)}")
            return []
    
    # System Configuration
    
    async def save_system_config(self, config_key: str, config_data: Dict[str, Any]) -> None:
        """Save system configuration"""
        try:
            doc_ref = self.db.collection(self.SYSTEM_CONFIG_COLLECTION).document(config_key)
            
            config_doc = {
                'key': config_key,
                'data': config_data,
                'updated_at': datetime.now(timezone.utc)
            }
            
            await doc_ref.set(config_doc)
            
        except Exception as e:
            logger.error(f"Error saving system config {config_key}: {str(e)}")
            raise FirestoreServiceError(f"Failed to save system config: {str(e)}")
    
    async def load_system_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Load system configuration"""
        try:
            doc_ref = self.db.collection(self.SYSTEM_CONFIG_COLLECTION).document(config_key)
            doc = await doc_ref.get()
            
            if doc.exists:
                return doc.to_dict().get('data')
            return None
            
        except Exception as e:
            logger.error(f"Error loading system config {config_key}: {str(e)}")
            raise FirestoreServiceError(f"Failed to load system config: {str(e)}")
    
    # Health Check and Utilities
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Firestore connection.
        
        Returns:
            Health status information
        """
        try:
            # Test basic connectivity
            test_doc = self.db.collection('health_check').document('test')
            await test_doc.set({'timestamp': datetime.now(timezone.utc)})
            
            # Clean up test document
            await test_doc.delete()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc),
                'database': 'connected'
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc),
                'error': str(e)
            }
    
    async def close(self) -> None:
        """Close Firestore connection and cleanup resources"""
        try:
            if self._db:
                # Firestore client doesn't have explicit close method
                # But we can clean up references
                self._db = None
            
            logger.info("Firestore service closed")
            
        except Exception as e:
            logger.error(f"Error closing Firestore service: {str(e)}")


# Global service instance (initialized in main application)
firestore_service: Optional[FirestoreService] = None

async def get_firestore_service() -> FirestoreService:
    """
    Dependency injection for FastAPI endpoints.
    
    Returns:
        Initialized Firestore service instance
    """
    if not firestore_service:
        raise FirestoreServiceError("Firestore service not initialized")
    
    return firestore_service

async def initialize_firestore_service(project_id: str = None, credentials_path: str = None) -> FirestoreService:
    """
    Initialize global Firestore service instance.
    
    Args:
        project_id: Google Cloud project ID
        credentials_path: Path to service account credentials
        
    Returns:
        Initialized service instance
    """
    global firestore_service
    
    if not firestore_service:
        firestore_service = FirestoreService(project_id=project_id, credentials_path=credentials_path)
        await firestore_service.initialize()
    
    return firestore_service